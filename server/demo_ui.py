"""
Hackathon-judge demo UI for the live HF Space.

What this gives the judge when they click the Space link:

- One-screen Gradio panel.
- Pick a scenario family from the 5 elite ones (basic / RAG / executive
  alignment / silo-breaker / stealth-adaptive).
- Click "Run episode" -> we play the heuristic policy for up to 30 steps
  in the env, then re-run the same scenario seed with the *trained* LLM
  policy (if available on the Hub) and show side-by-side results.
- Outputs:
  - reward delta (trained vs heuristic) with a clear winner indicator
  - the agent's per-step action stream, with reasoning
  - a chart of per-step reward
  - a status badge for the trained adapter ("ready" / "training in progress")

The point is for a non-technical reviewer to see
"agent observed X -> agent did Y -> reward Z" on screen in 10 seconds.

Mounted at ``/demo`` on the FastAPI app via ``gr.mount_gradio_app``.
"""

from __future__ import annotations

import json
from typing import Any

import gradio as gr

from immunoorg.agents.defender import (
    format_observation_for_llm,
    get_defender_prompt,
)
from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import (
    ActionType,
    DiagnosticAction,
    ImmunoAction,
    StrategicAction,
    TacticalAction,
)
from training.dataset_generator import DatasetConfig, DatasetGenerator
from training.scenario_hooks import (
    apply_scenario_hooks,
    attach_hooks,
    training_step_penalty,
)


# ─── Scenario catalogue ─────────────────────────────────────────────────────


_SCENARIO_LABEL = {
    "basic_containment": "1. Basic Containment (warm-up)",
    "rag_grounding": "2. RAG-Grounding (use CVE intel, not blunt isolate)",
    "executive_alignment": "3. Executive Alignment (uptime directive overrides instinct)",
    "silo_breaker": "4. Silo-Breaker (org friction blocks tactical actions)",
    "stealth_adaptive": "5. Stealth & Adaptive (multi-step investigation)",
}
_LABEL_TO_FAMILY = {v: k for k, v in _SCENARIO_LABEL.items()}


_SCENARIO_CACHE: dict[str, dict[str, Any]] = {}


def _scenario_for(family: str) -> dict[str, Any]:
    """Generate one balanced elite scenario per family, cached."""
    if family in _SCENARIO_CACHE:
        return _SCENARIO_CACHE[family]
    gen = DatasetGenerator(DatasetConfig(
        dataset_type="elite",
        output_dir="/tmp/_demo_scenarios",
        verbose=False,
        compress_output=False,
    ))
    scenarios = gen.generate_elite_scenario_mix_dataset(total=5)
    for sc in scenarios:
        if sc["family"] == family and family not in _SCENARIO_CACHE:
            _SCENARIO_CACHE[family] = sc
    return _SCENARIO_CACHE[family]


# ─── Heuristic policy (mirrors scripts/generate_training_evidence.py) ──────


def _heuristic_action(env, obs):
    phase = obs.current_phase.value
    nodes = obs.visible_nodes
    compromised = [n for n in nodes if n.compromised and not n.isolated]
    hooks = getattr(env, "_active_scenario_hooks", {}) or {}

    if hooks.get("inject_rag_best_mitigation") and phase in ("detection", "containment") and compromised:
        return ImmunoAction(action_type=ActionType.TACTICAL,
                            tactical_action=TacticalAction.SNAPSHOT_FORENSICS,
                            target=compromised[0].id,
                            reasoning="RAG: forensic snapshot before patching the rootkit.")
    if hooks.get("board_uptime_no_isolate") and phase == "containment":
        target = compromised[0].id if compromised else (nodes[0].id if nodes else "")
        return ImmunoAction(action_type=ActionType.TACTICAL,
                            tactical_action=TacticalAction.DEPLOY_PATCH,
                            target=target,
                            reasoning="Board directive: patch instead of isolating.")
    if hooks.get("force_denials_on_isolate") and phase in ("containment", "rca", "refactor"):
        return ImmunoAction(action_type=ActionType.STRATEGIC,
                            strategic_action=StrategicAction.ESTABLISH_DEVSECOPS,
                            target="dept-security", secondary_target="dept-engineering",
                            reasoning="Approver keeps denying; restructure the org.")
    if hooks.get("stealthy_initial_attack") and phase == "detection":
        return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                            diagnostic_action=DiagnosticAction.VULNERABILITY_SCAN,
                            reasoning="Stealth attack: deeper scan first.")

    if phase == "detection":
        target = compromised[0].id if compromised else (nodes[0].id if nodes else "")
        return ImmunoAction(action_type=ActionType.TACTICAL,
                            tactical_action=TacticalAction.SCAN_LOGS,
                            target=target, reasoning="Detection: scan for indicators.")
    if phase == "containment":
        if compromised:
            return ImmunoAction(action_type=ActionType.TACTICAL,
                                tactical_action=TacticalAction.ISOLATE_NODE,
                                target=compromised[0].id, reasoning="Isolate compromised node.")
        return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                            diagnostic_action=DiagnosticAction.TIMELINE_RECONSTRUCT,
                            reasoning="Reconstruct timeline.")
    if phase == "rca":
        return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                            diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
                            reasoning="Find the silo behind the failure.")
    if phase == "refactor":
        return ImmunoAction(action_type=ActionType.STRATEGIC,
                            strategic_action=StrategicAction.REDUCE_BUREAUCRACY,
                            target="dept-management", reasoning="Reduce approval latency.")
    return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                        diagnostic_action=DiagnosticAction.MEASURE_ORG_LATENCY,
                        reasoning="Validate org improvements.")


# ─── Episode runners ───────────────────────────────────────────────────────


def _run_episode(scenario, policy_fn, max_steps=30):
    """Roll out a policy on a scenario, return (frames, total_reward).

    `policy_fn(env, obs)` -> ImmunoAction
    """
    env = ImmunoOrgEnvironment(
        difficulty=int(scenario["difficulty"]),
        seed=int(scenario["seed"]),
    )
    hooks = scenario.get("hooks") or {}
    attach_hooks(env, hooks)
    obs = env.reset()
    apply_scenario_hooks(env, hooks)

    frames = []
    total = 0.0
    for step in range(min(max_steps, env.state.max_steps)):
        action = policy_fn(env, obs)
        obs, reward, done = env.step(action)
        shaped = float(reward) + float(training_step_penalty(env, action))
        total += shaped
        frames.append({
            "step": step + 1,
            "phase": obs.current_phase.value,
            "action_type": action.action_type.value,
            "action": (
                (action.tactical_action and action.tactical_action.value)
                or (action.strategic_action and action.strategic_action.value)
                or (action.diagnostic_action and action.diagnostic_action.value)
                or "?"
            ),
            "target": action.target or "-",
            "reasoning": action.reasoning,
            "reward": round(shaped, 3),
            "threats_left": len(env.attacks.get_active_attacks()),
        })
        if done:
            break
    return frames, total


def _trained_policy(env, obs):
    """Trained-LLM policy. Falls back to heuristic if the adapter isn't on
    the Hub yet (e.g. the HPC run hasn't pushed)."""
    from immunoorg.trained_agent import TrainedAgentUnavailable, TrainedDefender

    try:
        td = TrainedDefender.get()
        obs_text = format_observation_for_llm(obs.model_dump())
        sys_prompt = get_defender_prompt()
        data = td.predict_action(obs_text, sys_prompt)
    except TrainedAgentUnavailable:
        return _heuristic_action(env, obs)

    try:
        atype = ActionType(data.get("action_type", "diagnostic"))
    except Exception:
        atype = ActionType.DIAGNOSTIC

    kwargs = dict(
        action_type=atype,
        target=data.get("target") or "",
        secondary_target=data.get("secondary_target"),
        parameters=data.get("parameters") or {},
        reasoning=data.get("reasoning") or "",
    )
    try:
        if atype == ActionType.TACTICAL and data.get("tactical_action"):
            kwargs["tactical_action"] = TacticalAction(data["tactical_action"])
        elif atype == ActionType.STRATEGIC and data.get("strategic_action"):
            kwargs["strategic_action"] = StrategicAction(data["strategic_action"])
        elif atype == ActionType.DIAGNOSTIC and data.get("diagnostic_action"):
            kwargs["diagnostic_action"] = DiagnosticAction(data["diagnostic_action"])
    except Exception:
        kwargs["diagnostic_action"] = DiagnosticAction.QUERY_BELIEF_MAP
        kwargs["action_type"] = ActionType.DIAGNOSTIC

    return ImmunoAction(**kwargs)


# ─── Gradio handler ────────────────────────────────────────────────────────


def _frames_to_table(frames):
    return [[f["step"], f["phase"], f["action_type"], f["action"],
             f["target"], f["reward"], f["threats_left"], f["reasoning"][:90]]
            for f in frames]


def _trained_status_text() -> str:
    try:
        from immunoorg.trained_agent import TrainedDefender

        s = TrainedDefender.get().status()
    except Exception as e:
        return f"⚠️ trained adapter status check failed: {e}"

    if s.get("repo_exists"):
        if s.get("loaded"):
            return f"✅ Trained adapter LOADED from `{s['repo_id']}` (sha {s.get('sha','?')[:7]})"
        return (f"🟢 Trained adapter found on the Hub at `{s['repo_id']}` — "
                f"will load on first 'Run trained agent' click.")
    return (f"⏳ Trained adapter not on the Hub yet at `{s['repo_id']}`. "
            f"HPC pipeline run-in-progress — heuristic policy will be used "
            f"until the LoRA is pushed.")


def run_demo(scenario_label, max_steps):
    family = _LABEL_TO_FAMILY[scenario_label]
    scenario = _scenario_for(family)

    heur_frames, heur_total = _run_episode(scenario, _heuristic_action, int(max_steps))
    trained_frames, trained_total = _run_episode(scenario, _trained_policy, int(max_steps))

    # Per-step reward chart
    import numpy as np

    chart_data = {
        "step": list(range(1, max(len(heur_frames), len(trained_frames)) + 1)),
    }
    chart_data["heuristic"] = (
        [f["reward"] for f in heur_frames]
        + [None] * (len(chart_data["step"]) - len(heur_frames))
    )
    chart_data["trained"] = (
        [f["reward"] for f in trained_frames]
        + [None] * (len(chart_data["step"]) - len(trained_frames))
    )

    delta = trained_total - heur_total
    if delta > 0.5:
        verdict = f"🏆 Trained agent WINS by **{delta:+.2f}** reward over heuristic baseline"
    elif delta < -0.5:
        verdict = f"📉 Trained agent UNDERPERFORMS heuristic by **{delta:+.2f}** (try more training)"
    else:
        verdict = f"➖ Trained ≈ heuristic this episode (Δ = {delta:+.2f})"

    summary_md = f"""
### Scenario: **{scenario_label}**

| Policy | total reward (over {len(heur_frames)} step{'' if len(heur_frames)==1 else 's'}) | threats_left at end |
| --- | ---: | ---: |
| Heuristic baseline | {heur_total:+.2f} | {heur_frames[-1]['threats_left'] if heur_frames else '?'} |
| Trained LLM | {trained_total:+.2f} | {trained_frames[-1]['threats_left'] if trained_frames else '?'} |

{verdict}
"""

    return (
        summary_md,
        _frames_to_table(heur_frames),
        _frames_to_table(trained_frames),
        chart_data,
        _trained_status_text(),
    )


# ─── Build the UI ──────────────────────────────────────────────────────────


def build_demo() -> gr.Blocks:
    table_headers = ["step", "phase", "type", "action", "target",
                     "reward", "threats", "reasoning (truncated)"]

    with gr.Blocks(title="ImmunoOrg 2.0 — Live Demo") as demo:
        gr.Markdown(
            """
# 🛡️ ImmunoOrg 2.0 — Live Demo

The agent has to defend an enterprise from a cyber-attack **and**
restructure the organization that lets the attack succeed in the first
place. Pick one of the 5 scenario families and watch the heuristic
baseline play it head-to-head against the GRPO-trained LLM defender.

> 📚 [Problem statement](https://github.com/Charannoo/immunoorg/blob/master/PROBLEM_STATEMENT.md)
> · [Source](https://github.com/Charannoo/immunoorg)
> · [Blog](https://github.com/Charannoo/immunoorg/blob/master/BLOG_POST.md)
> · [Training notebook](https://github.com/Charannoo/immunoorg/blob/master/ImmunoOrg_Training_Colab.ipynb)
            """
        )

        status_md = gr.Markdown(_trained_status_text())

        with gr.Row():
            scenario_dd = gr.Dropdown(
                choices=list(_SCENARIO_LABEL.values()),
                value=list(_SCENARIO_LABEL.values())[1],
                label="Scenario family",
            )
            steps_sl = gr.Slider(5, 30, value=15, step=1, label="Max steps per episode")
            run_btn = gr.Button("Run episode", variant="primary")

        summary_md = gr.Markdown()

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Heuristic baseline")
                heur_table = gr.Dataframe(headers=table_headers, wrap=True)
            with gr.Column():
                gr.Markdown("### Trained LLM (or heuristic fallback)")
                trained_table = gr.Dataframe(headers=table_headers, wrap=True)

        chart = gr.LinePlot(
            x="step", y="heuristic",
            title="Per-step reward (heuristic = orange, trained = blue)",
            height=260,
        )

        gr.Markdown(
            """
---

### What the agent is reasoning about

- 28 actions across 3 categories: **tactical** (block_port, isolate_node, deploy_patch…),
  **strategic** (merge_departments, reduce_bureaucracy, establish_devsecops…),
  **diagnostic** (correlate_failure, identify_silo, vulnerability_scan…).
- 5-track composable reward:
  uptime (25%) · threat neutralization (25%) · bureaucracy efficiency (20%) ·
  code-patch quality (20%) · pipeline integrity (10%).
- Trained on the elite 20/20/20/20/20 mix of scenario families
  (basic / RAG / executive / silo / stealth) with TRL GRPO + Unsloth.
            """
        )

        run_btn.click(
            run_demo,
            inputs=[scenario_dd, steps_sl],
            outputs=[summary_md, heur_table, trained_table, chart, status_md],
        )

    return demo


__all__ = ["build_demo"]
