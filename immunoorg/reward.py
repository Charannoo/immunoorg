"""
Multi-Objective 5-Track Reward Function
========================================
ImmunoOrg 2.0 Composable Reward Model:

  Track 1 — Uptime Score          (25%) : Penalizes downtime, dropped sessions, slow APIs
  Track 2 — Threat Neutralization (25%) : Rewards trapping attacker, containing blast radius
  Track 3 — Bureaucracy Efficiency(20%) : War Room consensus speed, coalition stability
  Track 4 — Code Quality          (20%) : Mercor-aligned inverse token reward for patches
  Track 5 — Pipeline Integrity    (10%) : Gate 1 catch = max; Gate 4 catch = min

Interaction mechanics:
  - Pipeline Integrity 1.5x multiplier when Gate 1 catches a threat (shift-left bonus)
  - Self-improvement bonus: patches added to training earn persistent cross-episode signal
  - Uptime vs Threat tension: isolate = max threat score, zero uptime score
"""

from __future__ import annotations

import math
import re
from typing import Any

from immunoorg.models import ImmunoAction, ImmunoState, IncidentPhase, PipelineGate


class RewardCalculator:
    """Computes the 5-track composable multi-objective reward."""

    # 2.0 Blueprint weights
    DEFAULT_WEIGHTS = {
        "uptime": 0.25,
        "threat_neutralization": 0.25,
        "bureaucracy_efficiency": 0.20,
        "code_quality": 0.20,
        "pipeline_integrity": 0.10,
    }

    def __init__(self, coefficients: dict[str, float] | None = None):
        # Legacy coefficient support for curriculum engine compatibility
        self.coefficients = coefficients or {
            "alpha": 1.0,   # Threat neutralization
            "beta": 0.3,    # System downtime penalty
            "gamma": 0.1,   # Org chaos penalty
            "delta": 0.2,   # Belief map accuracy
            "epsilon": 0.1, # Reasoning quality
        }
        self.weights = dict(self.DEFAULT_WEIGHTS)
        self.partial_rewards_log: list[dict[str, float]] = []
        # Track running scores per track for dashboard
        self._track_totals: dict[str, float] = {k: 0.0 for k in self.DEFAULT_WEIGHTS}

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
        # 2.0 new parameters (optional — backwards-compatible)
        war_room_turns: int = 0,
        pipeline_integrity_score: float = 1.0,
        patch_quality_score: float = 0.0,
        patronus_score: float = 0.5,
        pipeline_gate: PipelineGate | None = None,
    ) -> float:
        """Compute 5-track composable reward for a single step."""
        partial: dict[str, float] = {}
        reward = 0.0

        # ══ TRACK 1: UPTIME (25%) ══════════════════════════════════════════
        uptime_score = 0.0
        if downtime_delta > 0:
            uptime_score = -self.weights["uptime"] * downtime_delta * 0.3
        else:
            uptime_score = self.weights["uptime"] * 0.05  # Small reward for keeping systems up
        # Penalty for isolating a non-compromised node (over-containment)
        if self._is_false_positive(action, state):
            uptime_score -= self.weights["uptime"] * 0.5
            partial["false_positive"] = -self.weights["uptime"] * 0.5
        reward += uptime_score
        partial["uptime"] = uptime_score
        self._track_totals["uptime"] += uptime_score

        # ══ TRACK 2: THREAT NEUTRALIZATION (25%) ══════════════════════════
        threat_score = 0.0
        threats_neutralized = max(0, threats_before - threats_after)
        if threats_neutralized > 0:
            threat_score += self.weights["threat_neutralization"] * threats_neutralized * 0.8
        # Belief map accuracy bonus (root cause understanding)
        belief_bonus = self.weights["threat_neutralization"] * belief_accuracy * 0.3
        threat_score += belief_bonus
        # Org chaos penalty
        chaos_penalty = -self.weights["threat_neutralization"] * org_chaos * 0.2
        threat_score += chaos_penalty
        reward += threat_score
        partial["threat_neutralization"] = threat_score
        self._track_totals["threat_neutralization"] += threat_score

        # ══ TRACK 3: BUREAUCRACY EFFICIENCY (20%) ════════════════════════
        bureaucracy_score = 0.0
        if war_room_turns > 0:
            # Lower turns-to-consensus = better. >9 turns = deadlock penalty
            efficiency = max(0.0, 1.0 - (war_room_turns / 9.0))
            bureaucracy_score = self.weights["bureaucracy_efficiency"] * efficiency * 0.4
        # Strategic healing bonus (org refactor actions at right phase)
        if action.strategic_action and action_success:
            if state.current_phase == IncidentPhase.ORG_REFACTOR:
                bureaucracy_score += self.weights["bureaucracy_efficiency"] * 0.3
                partial["healing_bonus"] = self.weights["bureaucracy_efficiency"] * 0.3
        reward += bureaucracy_score
        partial["bureaucracy_efficiency"] = bureaucracy_score
        self._track_totals["bureaucracy_efficiency"] += bureaucracy_score

        # ══ TRACK 4: CODE QUALITY / MERCOR (20%) ══════════════════════════
        code_quality_score = 0.0
        if patch_quality_score > 0:
            # Mercor: exponentially scaled reward for concise, high-quality patches
            code_quality_score = self.weights["code_quality"] * patch_quality_score * 2.0
        # Patronus AI schema drift adaptation bonus
        patronus_bonus = self.weights["code_quality"] * (patronus_score - 0.5) * 0.3
        code_quality_score += patronus_bonus
        reward += code_quality_score
        partial["code_quality"] = code_quality_score
        self._track_totals["code_quality"] += code_quality_score

        # ══ TRACK 5: PIPELINE INTEGRITY (10%) ════════════════════════════
        pipeline_score = self.weights["pipeline_integrity"] * pipeline_integrity_score * 0.5
        reward += pipeline_score
        partial["pipeline_integrity"] = pipeline_score
        self._track_totals["pipeline_integrity"] += pipeline_score

        # ══ PIPELINE INTEGRITY MULTIPLIER (Shift-Left Bonus) ══════════════
        # If Gate 1 caught the threat, all other scores get 1.5x for this step
        if pipeline_gate == PipelineGate.AST_INTERCEPTOR and pipeline_integrity_score < 1.0:
            multiplier_bonus = (reward - pipeline_score) * 0.5  # +50% of non-pipeline reward
            reward += multiplier_bonus
            partial["shift_left_multiplier"] = multiplier_bonus

        # ══ PHASE-APPROPRIATE ACTION BONUS ════════════════════════════════
        phase_bonus = self._phase_appropriate_action_bonus(state.current_phase, action)
        if phase_bonus > 0:
            reward += phase_bonus
            partial["phase_bonus"] = phase_bonus

        # ══ GENERAL ACTION SUCCESS / FAILURE ══════════════════════════════
        if action_success:
            reward += 0.05
            partial["action_success"] = 0.05
        else:
            reward -= 0.08
            partial["action_failure"] = -0.08

        # ══ PHASE TRANSITION BONUS ════════════════════════════════════════
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

    def get_track_scores(self) -> dict[str, float]:
        """Get current running totals per reward track (for dashboard)."""
        return dict(self._track_totals)

    @staticmethod
    def compute_patch_quality_score(token_count: int, test_pass_rate: float, regression_count: int) -> float:
        """
        Mercor bonus: Inversely scaled reward for patch quality.
        A concise 20-line patch with 100% test coverage outscores
        a bloated 500-line patch with defensive boilerplate.

        Formula: quality = (1 / log2(token_count + 2)) * test_pass_rate * penalty
        """
        if token_count <= 0:
            return 0.0
        conciseness = 1.0 / math.log2(token_count + 2)
        regression_penalty = max(0.0, 1.0 - regression_count * 0.2)
        return min(1.0, conciseness * test_pass_rate * regression_penalty * 3.0)
