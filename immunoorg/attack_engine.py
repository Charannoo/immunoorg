"""
Attack Engine
=============
Reactive adversary that generates attacks based on curriculum level,
observes defender actions, and adapts its strategy.

ImmunoOrg 2.0 - Phase 1: Supports both template-based and LLM-driven adversaries
"""

from __future__ import annotations

import random
from typing import Any

from immunoorg.models import (
    Attack, AttackVector, LogEntry, LogSeverity, NetworkNode,
)
from immunoorg.network_graph import NetworkGraph
from immunoorg.llm_adversary import LLMAdversary


# Attack templates by difficulty level
ATTACK_TEMPLATES: dict[int, list[dict[str, Any]]] = {
    1: [
        {"vector": AttackVector.SQL_INJECTION, "severity": 0.4, "stealth": 0.2,
         "description": "Single-point SQL injection on exposed database port"},
        {"vector": AttackVector.XSS, "severity": 0.3, "stealth": 0.3,
         "description": "XSS on web application"},
        {"vector": AttackVector.CREDENTIAL_STUFFING, "severity": 0.35, "stealth": 0.4,
         "description": "Credential stuffing on login endpoint"},
    ],
    2: [
        {"vector": AttackVector.LATERAL_MOVEMENT, "severity": 0.6, "stealth": 0.5,
         "description": "Lateral movement from web tier to app tier"},
        {"vector": AttackVector.PRIVILEGE_ESCALATION, "severity": 0.65, "stealth": 0.4,
         "description": "Privilege escalation after initial foothold"},
        {"vector": AttackVector.PHISHING, "severity": 0.5, "stealth": 0.6,
         "description": "Spear phishing targeting management endpoints"},
    ],
    3: [
        {"vector": AttackVector.RANSOMWARE, "severity": 0.8, "stealth": 0.3,
         "description": "Ransomware deployment with lateral spread"},
        {"vector": AttackVector.SUPPLY_CHAIN, "severity": 0.75, "stealth": 0.7,
         "description": "Supply chain compromise via dependency injection"},
        {"vector": AttackVector.DDOS, "severity": 0.6, "stealth": 0.1,
         "description": "DDoS to create distraction for data exfil"},
    ],
    4: [
        {"vector": AttackVector.APT_BACKDOOR, "severity": 0.9, "stealth": 0.9,
         "description": "APT campaign with persistent backdoor and C2 channels"},
        {"vector": AttackVector.ZERO_DAY, "severity": 0.95, "stealth": 0.8,
         "description": "Zero-day exploit chain targeting multiple services"},
        {"vector": AttackVector.SUPPLY_CHAIN, "severity": 0.85, "stealth": 0.85,
         "description": "Multi-stage supply chain attack with delayed activation"},
    ],
}


class AttackEngine:
    """Generates and manages attacks with reactive adversary behavior.
    
    Supports two modes:
    - Template-based (default): Uses fixed attack templates
    - LLM-driven: Uses reasoned attack planning with network analysis
    """

    def __init__(
        self,
        network: NetworkGraph,
        difficulty: int = 1,
        seed: int | None = None,
        use_llm_adversary: bool = False,
    ):
        self.network = network
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.active_attacks: list[Attack] = []
        self.contained_attacks: list[Attack] = []
        self.attack_history: list[dict[str, Any]] = []
        self.defender_actions_observed: list[str] = []
        self.adaptation_counter: int = 0
        self.use_llm_adversary = use_llm_adversary
        
        # Initialize LLM adversary if enabled
        self.llm_adversary: LLMAdversary | None = None
        if use_llm_adversary:
            self.llm_adversary = LLMAdversary(network, difficulty, seed)

    def generate_initial_attack(self, sim_time: float) -> Attack:
        """Generate the initial attack for an episode."""
        if self.use_llm_adversary and self.llm_adversary:
            # Use LLM-driven adversary
            attack = self.llm_adversary.generate_next_attack(sim_time)
            target_node = attack.target_node
            self.active_attacks.append(attack)
            self.attack_history.append({
                "time": sim_time,
                "event": "initial_attack",
                "vector": attack.vector.value,
                "target": target_node,
                "description": f"LLM-planned: {attack.metadata.get('rationale', 'N/A')}",
                "plan_id": attack.metadata.get("plan_id"),
            })
            # Compromise the target node
            target = self.network.get_node(target_node)
            if target:
                self.network.compromise_node(target_node, attack.vector, sim_time)
            return attack
        else:
            # Use template-based adversary (original behavior)
            templates = ATTACK_TEMPLATES.get(self.difficulty, ATTACK_TEMPLATES[1])
            template = self.rng.choice(templates)

            # Pick target node based on attack vector
            target = self._select_target(template["vector"])

            attack = Attack(
                vector=template["vector"],
                source_node="external",
                target_node=target.id if target else "",
                entry_point=self._find_entry_point(target, template["vector"]),
                severity=template["severity"],
                started_at=sim_time,
                stealth=template["stealth"],
                lateral_path=[target.id] if target else [],
            )

            # Compromise the target node
            if target:
                self.network.compromise_node(target.id, template["vector"], sim_time)

            self.active_attacks.append(attack)
            self.attack_history.append({
                "time": sim_time,
                "event": "initial_attack",
                "vector": template["vector"].value,
                "target": target.id if target else "unknown",
                "description": template["description"],
            })
            return attack

    def _select_target(self, vector: AttackVector) -> NetworkNode | None:
        """Select an appropriate target node for the attack vector."""
        nodes = self.network.get_all_nodes()
        if not nodes:
            return None

        # Vector-specific targeting
        preference_map = {
            AttackVector.SQL_INJECTION: ["data"],
            AttackVector.XSS: ["web"],
            AttackVector.CREDENTIAL_STUFFING: ["web", "management"],
            AttackVector.LATERAL_MOVEMENT: ["app"],
            AttackVector.PRIVILEGE_ESCALATION: ["app", "management"],
            AttackVector.PHISHING: ["management"],
            AttackVector.RANSOMWARE: ["data", "app"],
            AttackVector.DDOS: ["web", "dmz"],
            AttackVector.APT_BACKDOOR: ["management", "app"],
            AttackVector.SUPPLY_CHAIN: ["app"],
            AttackVector.ZERO_DAY: ["dmz", "web"],
        }

        preferred_tiers = preference_map.get(vector, ["app"])
        candidates = [n for n in nodes if n.tier in preferred_tiers and not n.compromised and not n.isolated]

        if not candidates:
            candidates = [n for n in nodes if not n.compromised and not n.isolated]

        if not candidates:
            return None

        # Prefer nodes with higher vulnerability
        candidates.sort(
            key=lambda n: max((p.vulnerability_score for p in n.ports), default=0),
            reverse=True,
        )
        # Weighted random from top candidates
        top = candidates[:max(1, len(candidates) // 2)]
        return self.rng.choice(top)

    def _find_entry_point(self, node: NetworkNode | None, vector: AttackVector) -> str:
        """Find the entry point (port/service) for the attack."""
        if not node or not node.ports:
            return "unknown"
        open_ports = [p for p in node.ports if p.status == PortStatus.OPEN]
        if open_ports:
            most_vulnerable = max(open_ports, key=lambda p: p.vulnerability_score)
            return f"{most_vulnerable.service}:{most_vulnerable.port_number}"
        return "unknown"

    def adversary_tick(self, sim_time: float) -> list[Attack]:
        """Adversary takes a reactive step — propagates attacks, adapts strategy."""
        new_attacks: list[Attack] = []

        for attack in self.active_attacks:
            if attack.contained:
                continue

            # Propagate laterally based on difficulty
            if self.difficulty >= 2:
                newly_compromised = self.network.propagate_attack(
                    attack.target_node, attack, sim_time
                )
                for nc in newly_compromised:
                    attack.damage_dealt += 0.1

            # Accumulate damage
            attack.damage_dealt += attack.severity * 0.02

        # At higher difficulties, launch follow-up attacks
        if self.difficulty >= 3 and self.rng.random() < 0.05 * self.difficulty:
            new_attack = self._launch_followup_attack(sim_time)
            if new_attack:
                new_attacks.append(new_attack)

        # Reactive adaptation based on observed defender actions
        if self.adaptation_counter >= 3 and self.difficulty >= 2:
            self._adapt_strategy()
            self.adaptation_counter = 0

        return new_attacks

    def observe_defender_action(self, action_name: str) -> None:
        """Adversary observes what the defender does and adapts."""
        self.defender_actions_observed.append(action_name)
        self.adaptation_counter += 1
        
        # If using LLM adversary, also notify it
        if self.llm_adversary:
            self.llm_adversary.observe_defender_action(action_name)

    def _adapt_strategy(self) -> None:
        """Adapt attack strategy based on observed defender patterns."""
        recent = self.defender_actions_observed[-5:]

        # If defender is blocking ports, pivot to credential-based attacks
        if "block_port" in recent:
            for attack in self.active_attacks:
                if not attack.contained:
                    attack.stealth += 0.1

        # If defender is isolating nodes, speed up lateral movement
        if "isolate_node" in recent:
            for attack in self.active_attacks:
                if not attack.contained:
                    attack.severity += 0.05

    def _launch_followup_attack(self, sim_time: float) -> Attack | None:
        """Launch a follow-up attack exploiting a different vector."""
        used_vectors = {a.vector for a in self.active_attacks}
        available = [v for v in AttackVector if v not in used_vectors]
        if not available:
            return None

        vector = self.rng.choice(available)
        target = self._select_target(vector)
        if not target:
            return None

        attack = Attack(
            vector=vector,
            source_node="external",
            target_node=target.id,
            entry_point=self._find_entry_point(target, vector),
            severity=0.3 + self.difficulty * 0.15,
            started_at=sim_time,
            stealth=0.3 + self.difficulty * 0.1,
            lateral_path=[target.id],
        )
        self.network.compromise_node(target.id, vector, sim_time)
        self.active_attacks.append(attack)
        self.attack_history.append({
            "time": sim_time, "event": "followup_attack",
            "vector": vector.value, "target": target.id,
        })
        return attack

    def contain_attack(self, attack_id: str, sim_time: float) -> bool:
        """Mark an attack as contained."""
        for attack in self.active_attacks:
            if attack.id == attack_id:
                attack.contained = True
                attack.contained_at = sim_time
                self.contained_attacks.append(attack)
                return True
        return False

    def get_active_attacks(self) -> list[Attack]:
        return [a for a in self.active_attacks if not a.contained]

    def get_total_damage(self) -> float:
        return sum(a.damage_dealt for a in self.active_attacks)
    
    def get_adversary_rationale(self) -> str:
        """Get the reasoning behind the adversary's current strategy."""
        if self.llm_adversary:
            return self.llm_adversary.get_attack_rationale()
        return "Template-based adversary (no reasoning available)"

    def generate_harder_attack(self, sim_time: float, org_weaknesses: list[str]) -> Attack:
        """Generate a harder attack for the self-improvement loop."""
        # Use org weaknesses to pick attack vector
        weakness_vector_map = {
            "no_devsecops": AttackVector.SUPPLY_CHAIN,
            "slow_approval": AttackVector.RANSOMWARE,
            "silo_security_engineering": AttackVector.LATERAL_MOVEMENT,
            "weak_monitoring": AttackVector.APT_BACKDOOR,
            "excessive_trust": AttackVector.PHISHING,
        }

        vector = AttackVector.APT_BACKDOOR
        for weakness in org_weaknesses:
            if weakness in weakness_vector_map:
                vector = weakness_vector_map[weakness]
                break

        target = self._select_target(vector)
        attack = Attack(
            vector=vector,
            source_node="external",
            target_node=target.id if target else "",
            entry_point=self._find_entry_point(target, vector),
            severity=min(1.0, 0.5 + self.difficulty * 0.15),
            started_at=sim_time,
            stealth=min(1.0, 0.4 + self.difficulty * 0.15),
            lateral_path=[target.id] if target else [],
        )

        if target:
            self.network.compromise_node(target.id, vector, sim_time)
        self.active_attacks.append(attack)
        return attack


# Need PortStatus imported
from immunoorg.models import PortStatus
