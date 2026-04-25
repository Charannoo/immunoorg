"""
ImmunoOrg 2.0 — FastAPI OpenEnv Server
=======================================
Implements the OpenEnv REST API without requiring the openenv package.
Endpoints: GET /health  POST /reset  POST /step  GET /state
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from immunoorg.models import (
    ActionType, TacticalAction, StrategicAction, DiagnosticAction, ImmunoAction,
)
from immunoorg.environment import ImmunoOrgEnvironment


# ─── Request / Response schemas ──────────────────────────────────────────────

class ResetRequest(BaseModel):
    seed: Optional[int] = None
    difficulty: int = 1
    task: Optional[str] = None


class ImmunoOrgAction(BaseModel):
    action_type: str = "tactical"
    tactical_action: Optional[str] = None
    strategic_action: Optional[str] = None
    diagnostic_action: Optional[str] = None
    target: str = ""
    secondary_target: Optional[str] = None
    parameters: dict[str, Any] = {}
    reasoning: str = ""

class StepEnvelope(BaseModel):
    """OpenEnv-style request body: { action: {...} }"""
    action: ImmunoOrgAction

class ImmunoOrgObservation(BaseModel):
    """OpenEnv-style observation payload returned in responses."""
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


# ─── Global environment instance ─────────────────────────────────────────────

_env: Optional[ImmunoOrgEnvironment] = None
_episode_id: str = ""

_training_lock = threading.Lock()
_training_proc: subprocess.Popen | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _training_secret_ok(provided: str | None) -> bool:
    expected = (os.environ.get("TRAINING_SECRET") or "").strip()
    if not expected or provided is None:
        return False
    if len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


def _require_training_token(token: str | None) -> None:
    if not (os.environ.get("TRAINING_SECRET") or "").strip():
        raise HTTPException(
            status_code=503,
            detail="Training trigger is disabled. Set TRAINING_SECRET in Space secrets.",
        )
    if not _training_secret_ok(token):
        raise HTTPException(status_code=404, detail="Not found")


def _get_env() -> ImmunoOrgEnvironment:
    if _env is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")
    return _env


def _build_action(req: ImmunoOrgAction) -> ImmunoAction:
    try:
        atype = ActionType(req.action_type)
    except ValueError:
        atype = ActionType.TACTICAL

    tactical = TacticalAction(req.tactical_action) if req.tactical_action else None
    strategic = StrategicAction(req.strategic_action) if req.strategic_action else None
    diagnostic = DiagnosticAction(req.diagnostic_action) if req.diagnostic_action else None

    return ImmunoAction(
        action_type=atype,
        tactical_action=tactical,
        strategic_action=strategic,
        diagnostic_action=diagnostic,
        target=req.target or "",
        secondary_target=req.secondary_target,
        parameters=req.parameters or {},
        reasoning=req.reasoning or "",
    )


def _obs_to_payload(obs, done: bool) -> ImmunoOrgObservation:
    return ImmunoOrgObservation(
        done=done,
        episode_id=_episode_id,
        current_phase=obs.current_phase.value,
        step_count=obs.step_count,
        sim_time=obs.sim_time,
        threat_level=obs.threat_level,
        system_downtime=obs.system_downtime,
        action_result=obs.action_result,
        action_success=obs.action_success,
        visible_nodes=[n.model_dump() for n in obs.visible_nodes],
        detected_attacks=[a.model_dump() for a in obs.detected_attacks],
        recent_logs=[lg.model_dump() for lg in obs.recent_logs[:10]],
        network_health_summary=obs.network_health_summary,
        org_nodes=[n.model_dump() for n in obs.org_nodes],
        pending_approvals=[a.model_dump() for a in obs.pending_approvals],
        belief_map_feedback=obs.belief_map_feedback,
        alerts=obs.alerts,
    )


def _step_response(obs, reward: float, done: bool) -> StepResponse:
    observation = _obs_to_payload(obs, done=done)
    info = {
        "episode_id": _episode_id,
        "phase": observation.current_phase,
        "step_count": observation.step_count,
    }
    return StepResponse(observation=observation, reward=reward, done=done, info=info)


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="ImmunoOrg 2.0 OpenEnv API",
    description="The Autonomous, Self-Healing Enterprise — OpenEnv RL Environment",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": "ImmunoOrg",
        "episode_active": _env is not None,
    }


@app.get("/")
async def root():
    return {
        "name": "ImmunoOrg 2.0",
        "description": "Autonomous, Self-Healing Enterprise — OpenEnv RL Environment",
        "endpoints": [
            "/health",
            "/reset",
            "/step",
            "/state",
            "/admin/training/start",
            "/admin/training/status",
            "/admin/training/log",
        ],
        "hf_space": "https://huggingface.co/spaces/hirann/immunoorg-2",
        "version": "2.0.0",
        "training": "Set TRAINING_SECRET (Space secret). Start: GET /admin/training/start?token=...&smoke_test=true",
    }


@app.get("/admin/training/start")
async def admin_training_start(
    token: str | None = Query(None, description="Must match TRAINING_SECRET"),
    smoke_test: bool = Query(False),
    model: str = Query("Qwen/Qwen2.5-0.5B-Instruct"),
    epochs: int = Query(1, ge=1, le=20),
):
    """Start GRPO training in a background process (logs to persistent /data when available)."""
    global _training_proc
    _require_training_token(token)

    with _training_lock:
        if _training_proc is not None and _training_proc.poll() is None:
            raise HTTPException(status_code=409, detail="Training already running")

        repo = _repo_root()
        from training.grpo_training_pipeline import log_file, training_root

        out_dir = training_root() / "checkpoints" / "immunoorg-defender"
        log_path = log_file()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-u",
            "-m",
            "training.grpo_training_pipeline",
            "run",
            "--model",
            model,
            "--epochs",
            str(epochs),
            "--output-dir",
            str(out_dir),
        ]
        if smoke_test:
            cmd.append("--smoke-test")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        log_f = open(log_path, "ab", buffering=0)

        _training_proc = subprocess.Popen(
            cmd,
            cwd=str(repo),
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )

    return {
        "status": "started",
        "pid": _training_proc.pid,
        "log_file": str(log_path),
        "smoke_test": smoke_test,
        "model": model,
        "epochs": epochs,
    }


@app.get("/admin/training/status")
async def admin_training_status(token: str | None = Query(None)):
    _require_training_token(token)
    try:
        from training.grpo_training_pipeline import status_file

        p = status_file()
        if not p.exists():
            return {"state": "never_started"}
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/training/log")
async def admin_training_log(
    token: str | None = Query(None),
    lines: int = Query(200, ge=1, le=5000),
):
    _require_training_token(token)
    try:
        from training.grpo_training_pipeline import log_file

        p = log_file()
        if not p.exists():
            return PlainTextResponse("(no log yet)\n", media_type="text/plain; charset=utf-8")
        text = p.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(text[-lines:]) + ("\n" if text else "")
        return PlainTextResponse(tail, media_type="text/plain; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/reset")
async def reset(req: ResetRequest = ResetRequest()) -> StepResponse:
    global _env, _episode_id
    _episode_id = str(uuid.uuid4())
    _env = ImmunoOrgEnvironment(difficulty=req.difficulty, seed=req.seed)
    obs = _env.reset()
    return _step_response(obs, reward=0.0, done=False)


@app.post("/step")
async def step(req: ImmunoOrgAction | StepEnvelope):
    env = _get_env()
    action_req = req.action if isinstance(req, StepEnvelope) else req
    action = _build_action(action_req)
    obs, reward, done = env.step(action)
    return _step_response(obs, reward=reward, done=done)


class DirectiveRequest(BaseModel):
    directive: str

@app.post("/directive")
async def inject_directive(req: DirectiveRequest):
    env = _get_env()
    env.inject_directive(req.directive)
    return {"status": "success", "directive": req.directive}

@app.get("/state")
async def state():
    env = _get_env()
    s = env.state
    return {
        "episode_id": _episode_id,
        "step_count": s.step_count,
        "difficulty_level": s.difficulty_level,
        "current_phase": s.current_phase.value,
        "threat_level": s.threat_level,
        "total_downtime": s.total_downtime,
        "total_damage": s.total_damage,
        "org_chaos_score": s.org_chaos_score,
        "cumulative_reward": s.cumulative_reward,
        "active_attacks": len(s.active_attacks),
        "contained_attacks": len(s.contained_attacks),
        "org_changes_made": s.org_changes_made,
        "termination_reason": s.termination_reason,
        # 2.0 metrics
        "migration_progress": env.migration_engine.get_progress() if env.migration_engine else {},
        "pipeline_integrity": env._last_pipeline_integrity,
        "war_room_debates": len(env.war_room.debate_history) if env.war_room else 0,
        "patronus_score": env.executive_context.get_patronus_score() if env.executive_context else 0.5,
        "reasoning_traces": [t.model_dump() for t in s.reasoning_traces],
    }



@app.get("/openenv.yaml")
async def get_openenv_yaml():
    """Serve the environment manifest."""
    try:
        with open("openenv.yaml", "r") as f:
            content = f.read()
        return PlainTextResponse(content, media_type="text/yaml")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="openenv.yaml not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
