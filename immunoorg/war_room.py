"""
Multi-Agent War Room
====================
ImmunoOrg 2.0 — Theme 1: Multi-Agent Interactions
Bonus Prizes: Halluminate (Multi-Actor Hallucination Detection) + Snorkel AI (Simulated Experts)

Three AI personas with conflicting objectives negotiate a consensus response
to detected threats. A 2-of-3 majority is required for any severity ≥ 3 action.

Personas
--------
- CISO Agent        : Eliminate threat at all costs. Risk-averse.
- DevOps Lead Agent : Maintain 99.9% uptime. Resists downtime actions.
- Lead Architect    : Technical correctness + compliance. Context-pivoting.

Protocol (6 steps)
------------------
1. Threat Briefing   — all agents see the threat simultaneously
2. Initial Position  — each agent proposes independently
3. Cross-Examination — each challenges another's proposal with evidence
4. Coalition         — agents form majority alliances
5. Consensus Vote    — 2-of-3 required above severity 3
6. Action Execution  — agreed action dispatched; transcript logged
"""

from __future__ import annotations

import random
import math
from typing import Any

from immunoorg.models import (
    Attack, AttackVector, WarRoomPersona, DebateRound, DebateResult,
    PreferenceInjection, TacticalAction, StrategicAction,
)


# ── Persona System Prompts ────────────────────────────────────────────────

PERSONA_PROFILES = {
    WarRoomPersona.CISO: {
        "name": "CISO Agent",
        "color": "🔴",
        "objective": "Eliminate the threat at all costs. Security over availability.",
        "risk_profile": "risk_averse",
        "preferred_actions": [
            TacticalAction.ISOLATE_NODE.value,
            TacticalAction.BLOCK_PORT.value,
            TacticalAction.QUARANTINE_TRAFFIC.value,
            TacticalAction.ROTATE_CREDENTIALS.value,
        ],
        "override_keywords": ["HIPAA", "breach", "exfiltration", "CVE", "ransomware"],
    },
    WarRoomPersona.DEVOPS_LEAD: {
        "name": "DevOps Lead Agent",
        "color": "🔵",
        "objective": "Maintain 99.9% uptime. Any downtime is a SLA violation.",
        "risk_profile": "uptime_maximizer",
        "preferred_actions": [
            TacticalAction.DEPLOY_PATCH.value,
            TacticalAction.RESTORE_BACKUP.value,
            TacticalAction.ENABLE_IDS.value,
        ],
        "override_keywords": ["SLA", "uptime", "production", "traffic", "CDN"],
    },
    WarRoomPersona.LEAD_ARCHITECT: {
        "name": "Lead Architect Agent",
        "color": "🟣",
        "objective": "Enforce technical correctness and compliance frameworks.",
        "risk_profile": "context_aware",
        "preferred_actions": [
            StrategicAction.ESTABLISH_DEVSECOPS.value,
            StrategicAction.CREATE_INCIDENT_CHANNEL.value,
            TacticalAction.SNAPSHOT_FORENSICS.value,
        ],
        "override_keywords": ["GDPR", "SOC2", "compliance", "architecture", "HIPAA"],
    },
}


# ── Fact Store for Halluminate Cross-Validation ───────────────────────────

class FactStore:
    """
    Shared ground-truth knowledge base used by the Halluminate layer.
    When an agent makes a factual claim (e.g. 'blocking IP X isolates the threat'),
    the FactStore checks it against known network topology before allowing execution.
    """

    def __init__(self, network_nodes: list[dict], attack: Attack | None = None):
        self._nodes: dict[str, dict] = {n["id"]: n for n in network_nodes}
        self._attack = attack
        self._load_balancer_ids: set[str] = {
            nid for nid, n in self._nodes.items()
            if n.get("type") == "load_balancer"
        }
        self._database_ids: set[str] = {
            nid for nid, n in self._nodes.items()
            if n.get("type") == "database"
        }
        self._compromised_ids: set[str] = {
            nid for nid, n in self._nodes.items()
            if n.get("compromised")
        }

    def validate_claim(self, persona: WarRoomPersona, claim: str, action: str, target: str) -> list[str]:
        """
        Halluminate check: return a list of hallucination flag strings.
        Empty list = claim is valid.
        """
        flags: list[str] = []

        # Check: isolating a load balancer would kill all traffic
        if action in ("isolate_node", "block_port", "quarantine_traffic"):
            if target in self._load_balancer_ids:
                flags.append(
                    f"⚠️ HALLUMINATE: {persona.value} proposes isolating {target} "
                    f"but that node is the LOAD BALANCER — this would kill all traffic!"
                )

        # Check: claimed compromised target is actually clean
        if "compromised" in claim.lower() and target not in self._compromised_ids and target:
            flags.append(
                f"⚠️ HALLUMINATE: {persona.value} claims {target} is compromised "
                f"but it shows no compromise indicators in the network map."
            )

        # Check: blocking a database node when it's the attack target is valid
        if target in self._database_ids and action == "isolate_node":
            if self._attack and self._attack.target_node == target:
                pass  # Correct identification — no flag
            elif self._attack and self._attack.target_node != target:
                flags.append(
                    f"⚠️ HALLUMINATE: {persona.value} targets database {target} "
                    f"but the active attack is on {self._attack.target_node if self._attack else 'unknown'}."
                )

        return flags


# ── Individual Persona Logic ──────────────────────────────────────────────

class PersonaAgent:
    """
    Simulates a War Room persona generating proposals and votes.
    In production this would call an LLM; here it uses structured heuristics
    that demonstrate the emergent theory-of-mind behavior described in the blueprint.
    """

    def __init__(self, persona: WarRoomPersona, rng: random.Random):
        self.persona = persona
        self.profile = PERSONA_PROFILES[persona]
        self.rng = rng
        self._strategic_memory: list[str] = []  # Actions remembered from prior rounds

    def generate_position(
        self,
        attack: Attack,
        threat_level: float,
        preference: PreferenceInjection | None = None,
    ) -> tuple[str, str]:
        """
        Returns (proposed_action, justification).
        Adapts if a preference injection is active.
        """
        profile = self.profile
        preferred = profile["preferred_actions"]

        # Preference injection overrides — Snorkel AI bonus
        if preference:
            override = preference.priority_override
            # HIPAA override: Architect pivots to compliance-first
            if override == "HIPAA" and self.persona == WarRoomPersona.LEAD_ARCHITECT:
                action = StrategicAction.ESTABLISH_DEVSECOPS.value
                just = (
                    f"[BOARD DIRECTIVE — {override}] HIPAA compliance requires immediate "
                    f"audit trail and data residency controls. I'm overriding my previous "
                    f"recommendation and pushing for DevSecOps gate enforcement."
                )
                return action, just
            # LEGAL_HOLD: No deletion — everyone must adapt
            if override == "LEGAL_HOLD":
                action = TacticalAction.SNAPSHOT_FORENSICS.value
                just = (
                    f"[LEGAL HOLD ACTIVE] All data must be preserved for legal discovery. "
                    f"I'm withdrawing any deletion proposals and recommending forensic "
                    f"snapshots before any containment action."
                )
                return action, just
            # UPTIME override: DevOps wins
            if override == "UPTIME" and self.persona == WarRoomPersona.DEVOPS_LEAD:
                action = TacticalAction.DEPLOY_PATCH.value
                just = (
                    f"[BOARD DIRECTIVE — No Downtime] Deploy a hot-patch without isolation. "
                    f"Isolation would trigger SLA penalties. Patch-in-place preserves "
                    f"uptime while closing the vulnerability."
                )
                return action, just

        # Normal logic based on risk profile
        action = self.rng.choice(preferred)
        severity_label = "CRITICAL" if threat_level >= 0.7 else "HIGH" if threat_level >= 0.4 else "MODERATE"

        justifications = {
            WarRoomPersona.CISO: (
                f"{severity_label} THREAT — vector: {attack.vector.value}, "
                f"severity {threat_level:.2f}. My MITRE ATT&CK analysis indicates "
                f"'{action}' on {attack.target_node} is the minimum effective response. "
                f"Delay increases lateral movement probability by ~40% per step."
            ),
            WarRoomPersona.DEVOPS_LEAD: (
                f"I acknowledge the threat but '{action}' has minimal service disruption. "
                f"Full isolation would break our SLA — we've got {self.rng.randint(200, 800)} "
                f"active sessions on that node. '{action}' is surgical, not scorched-earth."
            ),
            WarRoomPersona.LEAD_ARCHITECT: (
                f"From an architecture standpoint, '{action}' is correct. The {attack.vector.value} "
                f"vector implies a systemic gap in our {self.rng.choice(['DevSecOps', 'IaC review', 'code review'])} "
                f"pipeline. This action plus a post-incident refactor closes both the "
                f"immediate hole and the root cause."
            ),
        }

        return action, justifications.get(self.persona, "Recommended action based on analysis.")

    def challenge(
        self,
        challenger: WarRoomPersona,
        their_action: str,
        their_target: str,
        fact_store: FactStore,
    ) -> str:
        """Generate a challenge against another persona's proposal."""
        persona_name = PERSONA_PROFILES[challenger]["name"]
        challenges = {
            WarRoomPersona.CISO: [
                f"I challenge {persona_name}: '{their_action}' on {their_target} is insufficient. "
                f"The CVE associated with this vector has a CVSS score of 9.1 — we need hard isolation, "
                f"not a soft patch.",
                f"With respect to {persona_name}, uptime cannot take priority when "
                f"active exfiltration is occurring. Every second of delay is data loss.",
            ],
            WarRoomPersona.DEVOPS_LEAD: [
                f"I reject {persona_name}'s proposal: '{their_action}' will cause a cold restart "
                f"of {their_target}. I need a 15-minute drain window to prevent dropped sessions.",
                f"{persona_name} is right about the threat but wrong about the method. "
                f"We can achieve isolation at the load-balancer level without touching the node.",
            ],
            WarRoomPersona.LEAD_ARCHITECT: [
                f"Technically, {persona_name}'s approach is sound but incomplete. "
                f"'{their_action}' without updating the API contract schema exposes us to "
                f"schema drift exploitation within 24 hours.",
                f"I need {persona_name} to acknowledge: any action modifying {their_target} "
                f"requires a compliance check under our SOC2 Type II controls.",
            ],
        }
        options = challenges.get(self.persona, [f"I question {persona_name}'s proposal."])
        return self.rng.choice(options)

    def vote(self, consensus_action: str, threat_level: float, preference: PreferenceInjection | None) -> bool:
        """Returns True = approve, False = dissent."""
        # High threat forces yes from CISO and Architect
        if threat_level >= 0.7 and self.persona in (WarRoomPersona.CISO, WarRoomPersona.LEAD_ARCHITECT):
            return True
        # DevOps resists isolate/quarantine actions
        if self.persona == WarRoomPersona.DEVOPS_LEAD:
            if consensus_action in ("isolate_node", "quarantine_traffic") and threat_level < 0.6:
                return False
        # Preference injection can flip votes
        if preference and preference.priority_override == "UPTIME":
            if self.persona == WarRoomPersona.DEVOPS_LEAD:
                return consensus_action not in ("isolate_node", "quarantine_traffic")
        return self.rng.random() > 0.25  # ~75% base approval rate


# ── War Room Coordinator ─────────────────────────────────────────────────

class WarRoom:
    """
    Orchestrates the full 6-step debate protocol.
    Called by the environment when threat_level exceeds the activation threshold.
    """

    ACTIVATION_THRESHOLD = 0.45  # Threat level above which War Room activates

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self._agents = {
            p: PersonaAgent(p, random.Random(self.rng.randint(0, 999999)))
            for p in WarRoomPersona
        }
        self._pending_injection: PreferenceInjection | None = None
        self.debate_history: list[DebateResult] = []

    def inject_preference(self, injection: PreferenceInjection) -> None:
        """Snorkel AI bonus — inject a mid-debate board directive."""
        self._pending_injection = injection

    def run_debate(
        self,
        attack: Attack,
        threat_level: float,
        network_nodes: list[dict],
        sim_time: float,
    ) -> DebateResult:
        """
        Run the full 6-step debate protocol and return a DebateResult.
        """
        fact_store = FactStore(network_nodes, attack)
        injection = self._pending_injection
        self._pending_injection = None  # Consume injection

        result = DebateResult(
            trigger_attack_id=attack.id,
            threat_level=threat_level,
            started_at=sim_time,
        )

        if injection:
            result.preference_injections.append(injection)

        # ── Step 1-2: Threat Briefing + Initial Positions ────────────────
        proposals: dict[WarRoomPersona, tuple[str, str]] = {}
        for persona, agent in self._agents.items():
            action, justification = agent.generate_position(attack, threat_level, injection)
            proposals[persona] = (action, justification)
            round_obj = DebateRound(
                round_number=len(result.rounds),
                persona=persona,
                proposal=action,
                justification=justification,
                vote=True,
            )
            result.rounds.append(round_obj)

        # ── Step 3: Cross-Examination + Halluminate Validation ──────────
        personas = list(WarRoomPersona)
        for i, persona in enumerate(personas):
            challenger_persona = personas[(i + 1) % len(personas)]
            their_action, _ = proposals[challenger_persona]
            their_target = attack.target_node
            challenge_text = self._agents[persona].challenge(
                challenger_persona, their_action, their_target, fact_store
            )
            # Halluminate cross-validation
            flags = fact_store.validate_claim(persona, challenge_text, their_action, their_target)
            round_obj = DebateRound(
                round_number=len(result.rounds),
                persona=persona,
                proposal=their_action,
                justification=challenge_text,
                challenge_target=challenger_persona,
                challenge_text=challenge_text,
                hallucination_flags=flags,
            )
            result.rounds.append(round_obj)

        # ── Step 4-5: Coalition Formation + Consensus Vote ───────────────
        # Pick the CISO's proposal as the default consensus (highest security priority)
        # but allow override if DevOps + Architect form a coalition against it
        ciso_action, _ = proposals[WarRoomPersona.CISO]
        devops_action, _ = proposals[WarRoomPersona.DEVOPS_LEAD]
        arch_action, _ = proposals[WarRoomPersona.LEAD_ARCHITECT]

        # Determine leading proposal by preference injection or threat level
        if injection and injection.priority_override == "UPTIME":
            consensus_action = devops_action
            consensus_target = attack.target_node
        elif injection and injection.priority_override in ("HIPAA", "LEGAL_HOLD"):
            consensus_action = arch_action
            consensus_target = attack.target_node
        elif threat_level >= 0.65:
            consensus_action = ciso_action  # CISO wins at high threat
            consensus_target = attack.target_node
        else:
            # Coalition: Architect + DevOps can override CISO at lower threat
            consensus_action = arch_action
            consensus_target = attack.target_node

        # Collect votes
        votes: dict[WarRoomPersona, bool] = {}
        for persona, agent in self._agents.items():
            vote = agent.vote(consensus_action, threat_level, injection)
            votes[persona] = vote

        approve_count = sum(1 for v in votes.values() if v)
        consensus_reached = approve_count >= 2  # 2-of-3 required

        # Record voting rounds
        for persona, vote in votes.items():
            _, just = proposals[persona]
            round_obj = DebateRound(
                round_number=len(result.rounds),
                persona=persona,
                proposal=consensus_action,
                justification=f"VOTE: {'✅ APPROVE' if vote else '❌ DISSENT'}. {just[:100]}...",
                vote=vote,
            )
            result.rounds.append(round_obj)

        # Find dissenting persona
        dissenting = [p for p, v in votes.items() if not v]
        if dissenting:
            result.dissent_persona = dissenting[0]
            _, dissent_just = proposals[dissenting[0]]
            result.dissent_reason = dissent_just[:200]

        result.consensus_reached = consensus_reached
        result.consensus_action = consensus_action if consensus_reached else ciso_action
        result.consensus_target = consensus_target
        result.turns_to_consensus = len(result.rounds)
        result.resolved_at = sim_time + self.rng.uniform(0.5, 2.0)

        self.debate_history.append(result)
        return result

    def format_transcript(self, result: DebateResult) -> str:
        """Format a debate transcript for the God Mode dashboard feed."""
        lines = [
            f"╔══ WAR ROOM [{result.id}] — Threat Level: {result.threat_level:.0%} ══╗",
        ]
        if result.preference_injections:
            for inj in result.preference_injections:
                lines.append(
                    f"  ⚡ BOARD DIRECTIVE [{inj.source.upper()}]: {inj.directive}"
                )
        for r in result.rounds:
            profile = PERSONA_PROFILES[r.persona]
            color = profile["color"]
            name = profile["name"]
            lines.append(f"  {color} {name}: {r.justification[:120]}")
            for flag in r.hallucination_flags:
                lines.append(f"  {flag}")
        status = "✅ CONSENSUS" if result.consensus_reached else "⚠️ DEADLOCK"
        lines.append(
            f"╚══ {status}: {result.consensus_action} on {result.consensus_target} "
            f"({result.turns_to_consensus} turns) ══╝"
        )
        return "\n".join(lines)

    def get_latest_transcript(self) -> str:
        """Get the most recent debate transcript."""
        if not self.debate_history:
            return "No debates yet."
        return self.format_transcript(self.debate_history[-1])

    def get_bureaucracy_score(self) -> float:
        """
        Score for the Bureaucracy Efficiency reward track.
        Lower turns-to-consensus = better. Penalizes deadlocks.
        """
        if not self.debate_history:
            return 0.5
        recent = self.debate_history[-5:]
        avg_turns = sum(d.turns_to_consensus for d in recent) / len(recent)
        deadlocks = sum(1 for d in recent if not d.consensus_reached)
        # Normalize: 6 rounds = worst case (3 positions + 3 cross-exams + 3 votes)
        efficiency = max(0.0, 1.0 - (avg_turns / 12.0)) - (deadlocks * 0.1)
        return max(0.0, min(1.0, efficiency))
