"""
ImmunoOrg OpenEnv wire-protocol models
=======================================

These are the over-the-wire request / response shapes that the FastAPI
server (``server.main``) and the OpenEnv client (``client.py``) both
agree on. They are intentionally thinner than the rich internal
``immunoorg.models.ImmunoAction`` / ``ImmunoObservation`` so that
clients do not have to depend on server-side state representations
(``ImmunoState`` carries history that has no business going to a
client).

Putting them in the package — instead of in ``server/main.py`` —
respects the OpenEnv guidance that "clients should never import
server internals".
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ResetRequest(BaseModel):
    seed: Optional[int] = None
    difficulty: int = 1
    task: Optional[str] = None


class ImmunoOrgAction(BaseModel):
    """Single action sent to ``POST /step``."""

    action_type: str = "tactical"
    tactical_action: Optional[str] = None
    strategic_action: Optional[str] = None
    diagnostic_action: Optional[str] = None
    target: str = ""
    secondary_target: Optional[str] = None
    parameters: dict[str, Any] = {}
    reasoning: str = ""


class StepEnvelope(BaseModel):
    """OpenEnv-style request body: ``{ "action": {...} }``."""

    action: ImmunoOrgAction


class ImmunoOrgObservation(BaseModel):
    """Observation payload returned in ``/reset`` and ``/step`` responses."""

    done: bool
    episode_id: str
    current_phase: str
    step_count: int
    sim_time: float
    threat_level: float
    system_downtime: float
    action_result: str
    action_success: bool
    visible_nodes: list[dict[str, Any]]
    detected_attacks: list[dict[str, Any]]
    recent_logs: list[dict[str, Any]]
    network_health_summary: dict[str, Any]
    org_nodes: list[dict[str, Any]]
    pending_approvals: list[dict[str, Any]]
    belief_map_feedback: str
    alerts: list[str]


class StepResponse(BaseModel):
    observation: ImmunoOrgObservation
    reward: float
    done: bool
    info: dict[str, Any]


__all__ = [
    "ResetRequest",
    "ImmunoOrgAction",
    "StepEnvelope",
    "ImmunoOrgObservation",
    "StepResponse",
]
