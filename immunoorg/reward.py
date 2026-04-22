"""
Multi-Objective Reward Function
================================
R = α·ThreatNeutralized − β·SystemDowntime − γ·OrgChaos + δ·BeliefAccuracy + ε·ReasoningQuality
Plus partial reward signals for intermediate achievements.
"""

from __future__ import annotations

import re
from typing import Any

from immunoorg.models import ImmunoAction, ImmunoState, IncidentPhase


class RewardCalculator:
    """Computes multi-objective rewards with partial signals."""

    def __init__(self, coefficients: dict[str, float] | None = None):
        self.coefficients = coefficients or {
            "alpha": 1.0,   # Threat neutralization
            "beta": 0.3,    # System downtime penalty
            "gamma": 0.1,   # Org chaos penalty
            "delta": 0.2,   # Belief map accuracy
            "epsilon": 0.1, # Reasoning quality
        }
        self.partial_rewards_log: list[dict[str, float]] = []

    def set_coefficients(self, coefficients: dict[str, float]) -> None:
        self.coefficients.update(coefficients)

    def compute_step_reward(
        self,
        state: ImmunoState,
        action: ImmunoAction,
        action_success: bool,
        threats_before: int,
        threats_after: int,
        belief_accuracy: float,
        org_chaos: float,
        downtime_delta: float,
    ) -> float:
        """Compute reward for a single step."""
        α = self.coefficients["alpha"]
        β = self.coefficients["beta"]
        γ = self.coefficients["gamma"]
        δ = self.coefficients["delta"]
        ε = self.coefficients["epsilon"]

        reward = 0.0
        partial = {}

        # === THREAT NEUTRALIZATION ===
        threats_neutralized = max(0, threats_before - threats_after)
        if threats_neutralized > 0:
            threat_reward = α * threats_neutralized * 0.3
            reward += threat_reward
            partial["threat_neutralized"] = threat_reward

        # === SYSTEM DOWNTIME PENALTY ===
        if downtime_delta > 0:
            # Increased penalty to prevent "block everything" strategy
            downtime_penalty = -β * downtime_delta * 0.5 
            reward += downtime_penalty
            partial["downtime_penalty"] = downtime_penalty

        # === ORG CHAOS PENALTY ===
        if org_chaos > 0:
            # Stronger penalty for organizational destruction
            chaos_penalty = -γ * org_chaos * 2.0
            reward += chaos_penalty
            partial["chaos_penalty"] = chaos_penalty

        # === BELIEF MAP ACCURACY ===
        belief_reward = δ * belief_accuracy * 0.1
        reward += belief_reward
        partial["belief_accuracy"] = belief_reward

        # === REASONING QUALITY ===
        reasoning_score = self._score_reasoning(action.reasoning)
        reasoning_reward = ε * reasoning_score * 0.1
        reward += reasoning_reward
        partial["reasoning_quality"] = reasoning_reward

        # === PARTIAL REWARD SIGNALS ===

        # Correct action for current phase
        phase_bonus = self._phase_appropriate_action_bonus(state.current_phase, action)
        if phase_bonus > 0:
            reward += phase_bonus
            partial["phase_bonus"] = phase_bonus

        # Action success/failure
        if action_success:
            reward += 0.05
            partial["action_success"] = 0.05
        else:
            reward -= 0.1
            partial["action_failure"] = -0.1

        # False positive penalty
        if self._is_false_positive(action, state):
            reward -= 0.2
            partial["false_positive"] = -0.2

        # Phase transition bonus
        phase_transition = self._check_phase_transition_bonus(state)
        if phase_transition > 0:
            reward += phase_transition
            partial["phase_transition"] = phase_transition

        self.partial_rewards_log.append(partial)
        return reward

    def compute_episode_reward(
        self,
        state: ImmunoState,
        belief_accuracy: float,
        org_efficiency: float,
    ) -> float:
        """Compute end-of-episode bonus/penalty."""
        reward = 0.0

        # All threats contained bonus
        active = len(state.active_attacks)
        contained = len(state.contained_attacks)
        total = active + contained
        if total > 0:
            containment_ratio = contained / total
            if containment_ratio >= 1.0:
                reward += 1.0  # Full containment
            else:
                reward += containment_ratio * 0.5

        # Full cycle bonus (went through all phases)
        phases_visited = {p.get("phase") for p in state.phase_history}
        all_phases = {ph.value for ph in IncidentPhase}
        if all_phases.issubset(phases_visited):
            reward += 0.5  # Completed full Detection→Validation cycle

        # Belief map accuracy bonus
        if belief_accuracy >= 0.8:
            reward += 0.3
        elif belief_accuracy >= 0.5:
            reward += 0.15

        # Org efficiency improvement
        reward += org_efficiency * 0.2

        # Speed bonus — fewer steps = better
        speed_ratio = 1.0 - (state.step_count / max(1, state.max_steps))
        reward += speed_ratio * 0.2

        return reward

    def _score_reasoning(self, reasoning: str) -> float:
        """Score the quality of the agent's reasoning chain (0-1)."""
        if not reasoning:
            return 0.0

        score = 0.0

        # Length check (not too short, not padding)
        word_count = len(reasoning.split())
        if 10 <= word_count <= 200:
            score += 0.2
        elif word_count > 5:
            score += 0.1

        # Contains causal reasoning keywords
        causal_keywords = ["because", "therefore", "since", "indicates", "correlates",
                          "caused by", "leads to", "results in", "evidence", "root cause"]
        for kw in causal_keywords:
            if kw in reasoning.lower():
                score += 0.1
                break

        # Contains action justification
        justification_keywords = ["should", "need to", "priority", "critical",
                                 "mitigate", "prevent", "reduce", "eliminate"]
        for kw in justification_keywords:
            if kw in reasoning.lower():
                score += 0.1
                break

        # References specific entities
        if re.search(r'(node|port|department|server|attack|vulnerability)', reasoning.lower()):
            score += 0.1

        # Structured thinking
        if any(marker in reasoning for marker in ["1.", "2.", "Step", "First", "Then", "Finally"]):
            score += 0.1

        return min(1.0, score)

    def _phase_appropriate_action_bonus(self, phase: IncidentPhase, action: ImmunoAction) -> float:
        """Bonus for taking actions appropriate to the current incident phase."""
        phase_action_map = {
            IncidentPhase.DETECTION: ["scan_logs", "vulnerability_scan", "trace_attack_path",
                                      "escalate_alert", "enable_ids"],
            IncidentPhase.CONTAINMENT: ["block_port", "isolate_node", "quarantine_traffic",
                                        "rotate_credentials"],
            IncidentPhase.ROOT_CAUSE_ANALYSIS: ["correlate_failure", "timeline_reconstruct",
                                                 "identify_silo", "audit_permissions",
                                                 "query_belief_map"],
            IncidentPhase.ORG_REFACTOR: ["merge_departments", "create_shortcut_edge",
                                         "reduce_bureaucracy", "update_approval_protocol",
                                         "establish_devsecops", "add_cross_functional_team",
                                         "rewrite_policy"],
            IncidentPhase.VALIDATION: ["scan_logs", "vulnerability_scan", "measure_org_latency"],
        }

        appropriate = phase_action_map.get(phase, [])
        action_name = (
            action.tactical_action.value if action.tactical_action else
            action.strategic_action.value if action.strategic_action else
            action.diagnostic_action.value if action.diagnostic_action else ""
        )

        if action_name in appropriate:
            return 0.1
        return 0.0

    def _is_false_positive(self, action: ImmunoAction, state: ImmunoState) -> bool:
        """Check if the action targets a non-compromised node (false positive)."""
        if action.tactical_action and action.tactical_action.value in ("block_port", "isolate_node"):
            target = action.target
            for node in state.network_nodes:
                if node.id == target and not node.compromised:
                    return True
        return False

    def _check_phase_transition_bonus(self, state: ImmunoState) -> float:
        """Bonus for naturally transitioning between phases."""
        if len(state.phase_history) < 2:
            return 0.0
        # Check if the latest transition follows the expected order
        expected_order = [IncidentPhase.DETECTION, IncidentPhase.CONTAINMENT,
                         IncidentPhase.ROOT_CAUSE_ANALYSIS, IncidentPhase.ORG_REFACTOR,
                         IncidentPhase.VALIDATION]
        if len(state.phase_history) >= 2:
            prev = state.phase_history[-2].get("phase")
            curr = state.phase_history[-1].get("phase")
            prev_idx = next((i for i, p in enumerate(expected_order) if p.value == prev), -1)
            curr_idx = next((i for i, p in enumerate(expected_order) if p.value == curr), -1)
            if curr_idx == prev_idx + 1:
                return 0.15  # Correct forward progression
        return 0.0

    def get_partial_rewards_summary(self) -> dict[str, float]:
        """Summarize all partial rewards accumulated."""
        summary: dict[str, float] = {}
        for partial in self.partial_rewards_log:
            for key, val in partial.items():
                summary[key] = summary.get(key, 0.0) + val
        return summary
