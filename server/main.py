"""
ImmunoOrg OpenEnv Server
========================
Properly subclasses openenv.core.Environment and uses create_fastapi_app.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from openenv.core import Environment, Action, Observation, State, create_fastapi_app

from immunoorg.models import (
    ActionType, TacticalAction, StrategicAction, DiagnosticAction,
    IncidentPhase, NetworkNode, NetworkEdge, OrgNode, OrgEdge,
    Attack, ApprovalRequest, LogEntry,
)
from immunoorg.environment import ImmunoOrgEnvironment


# === OpenEnv-compatible Action/Observation ===

class ImmunoOrgAction(Action):
    """OpenEnv Action subclass."""
    action_type: str = "tactical"
    tactical_action: str | None = None
    strategic_action: str | None = None
    diagnostic_action: str | None = None
    target: str = ""
    secondary_target: str | None = None
    parameters: dict[str, Any] = {}
    reasoning: str = ""


class ImmunoOrgObservation(Observation):
    """OpenEnv Observation subclass. Inherits done, reward, metadata."""
    current_phase: str = "detection"
    step_count: int = 0
    sim_time: float = 0.0
    threat_level: float = 0.0
    system_downtime: float = 0.0
    action_result: str = ""
    action_success: bool = True
    visible_nodes: list[dict[str, Any]] = []
    detected_attacks: list[dict[str, Any]] = []
    recent_logs: list[dict[str, Any]] = []
    network_health_summary: dict[str, float] = {}
    org_nodes: list[dict[str, Any]] = []
    pending_approvals: list[dict[str, Any]] = []
    belief_map_feedback: str = ""
    alerts: list[str] = []


class ImmunoOrgState(State):
    """OpenEnv State subclass. Inherits episode_id, step_count."""
    difficulty_level: int = 1
    current_phase: str = "detection"
    threat_level: float = 0.0
    total_downtime: float = 0.0
    total_damage: float = 0.0
    org_chaos_score: float = 0.0
    cumulative_reward: float = 0.0
    active_attacks: int = 0
    contained_attacks: int = 0
    org_changes_made: int = 0
    self_improvement_generation: int = 0
    termination_reason: str = ""


# === OpenEnv Environment ===

class ImmunoOrgOpenEnv(Environment[ImmunoOrgAction, ImmunoOrgObservation, ImmunoOrgState]):
    """OpenEnv Environment subclass wrapping ImmunoOrgEnvironment."""

    def __init__(self, difficulty: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.difficulty = difficulty
        self.env: ImmunoOrgEnvironment | None = None
        self._state = ImmunoOrgState()

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ImmunoOrgObservation:
        difficulty = kwargs.get("difficulty", self.difficulty)
        self.env = ImmunoOrgEnvironment(difficulty=difficulty, seed=seed)
        obs = self.env.reset(task=kwargs.get("task"))

        self._state = ImmunoOrgState(
            episode_id=episode_id or self.env.state.episode_id,
            step_count=0,
            difficulty_level=difficulty,
            current_phase=obs.current_phase.value,
            threat_level=obs.threat_level,
        )

        return self._to_openenv_obs(obs, done=False, reward=0.0)

    def step(
        self,
        action: ImmunoOrgAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> ImmunoOrgObservation:
        if self.env is None:
            return ImmunoOrgObservation(
                done=True, reward=0.0,
                action_result="Environment not initialized. Call reset() first.",
                action_success=False,
            )

        # Convert OpenEnv action to internal action
        from immunoorg.models import ImmunoAction
        internal_action = ImmunoAction(
            action_type=ActionType(action.action_type) if action.action_type else ActionType.TACTICAL,
            tactical_action=TacticalAction(action.tactical_action) if action.tactical_action else None,
            strategic_action=StrategicAction(action.strategic_action) if action.strategic_action else None,
            diagnostic_action=DiagnosticAction(action.diagnostic_action) if action.diagnostic_action else None,
            target=action.target or "",
            secondary_target=action.secondary_target,
            parameters=action.parameters or {},
            reasoning=action.reasoning or "",
        )

        obs, reward, terminated = self.env.step(internal_action)

        # Update state
        self._state.step_count = self.env.state.step_count
        self._state.current_phase = obs.current_phase.value
        self._state.threat_level = obs.threat_level
        self._state.total_downtime = self.env.state.total_downtime
        self._state.total_damage = self.env.state.total_damage
        self._state.org_chaos_score = self.env.state.org_chaos_score
        self._state.cumulative_reward = self.env.state.cumulative_reward
        self._state.active_attacks = len(self.env.state.active_attacks)
        self._state.contained_attacks = len(self.env.state.contained_attacks)
        self._state.org_changes_made = self.env.state.org_changes_made
        self._state.self_improvement_generation = self.env.state.self_improvement_generation
        self._state.termination_reason = self.env.state.termination_reason

        return self._to_openenv_obs(obs, done=terminated, reward=reward)

    def state(self) -> ImmunoOrgState:
        return self._state

    def close(self) -> None:
        self.env = None

    def _to_openenv_obs(self, obs, done: bool, reward: float) -> ImmunoOrgObservation:
        """Convert internal observation to OpenEnv observation."""
        return ImmunoOrgObservation(
            done=done,
            reward=reward,
            metadata={
                "cumulative_reward": self.env.state.cumulative_reward if self.env else 0,
                "phase": obs.current_phase.value,
                "belief_accuracy": self.env.belief_map.calculate_belief_accuracy() if self.env and self.env.belief_map else 0,
            },
            current_phase=obs.current_phase.value,
            step_count=obs.step_count,
            sim_time=obs.sim_time,
            threat_level=obs.threat_level,
            system_downtime=obs.system_downtime,
            action_result=obs.action_result,
            action_success=obs.action_success,
            visible_nodes=[n.model_dump() for n in obs.visible_nodes],
            detected_attacks=[a.model_dump() for a in obs.detected_attacks],
            recent_logs=[l.model_dump() for l in obs.recent_logs[:10]],
            network_health_summary=obs.network_health_summary,
            org_nodes=[n.model_dump() for n in obs.org_nodes],
            pending_approvals=[a.model_dump() for a in obs.pending_approvals],
            belief_map_feedback=obs.belief_map_feedback,
            alerts=obs.alerts,
        )


# === Create the FastAPI app using OpenEnv's factory ===

def env_factory():
    return ImmunoOrgOpenEnv(difficulty=1)

app = create_fastapi_app(env_factory, ImmunoOrgAction, ImmunoOrgObservation)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
