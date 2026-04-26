"""
Hackathon-judge demo UI for the live HF Space.

What this gives the judge when they click the Space link:

- One-screen Gradio panel (episode demo + **War Room** LLM debate accordion).
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

import asyncio
from collections import Counter
from typing import Any

import gradio as gr

from server.war_room_debate import run_war_room_debate

from immunoorg.agents.defender import (
    format_observation_for_llm,
    get_defender_prompt,
)
from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import (
    ActionType,
    DiagnosticAction,
    ImmunoAction,
    PipelineGate,
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


def _mesh_gate_label(env: ImmunoOrgEnvironment) -> str:
    gate = getattr(env, "_last_pipeline_gate", None)
    if gate is None:
        return "—"
    if isinstance(gate, PipelineGate):
        return gate.value
    return str(gate)


def _telemetry_row(env: ImmunoOrgEnvironment, obs) -> dict[str, str | int | float]:
    """Surface War Room, 4-gate mesh, migration/honeypots, MITRE-ish vector."""
    mig = {}
    try:
        mig = env.migration_engine.get_progress() or {}
    except Exception:
        pass
    honeys = mig.get("active_honeypots") or []
    if not isinstance(honeys, list):
        honeys = []
    att = "—"
    if obs.detected_attacks:
        att = obs.detected_attacks[0].vector.value
    d0 = obs.directives[0] if obs.directives else "—"
    if isinstance(d0, str) and len(d0) > 36:
        d0 = d0[:33] + "…"
    return {
        "mesh_ok": round(float(getattr(env, "_last_pipeline_integrity", 1.0) or 1.0), 2),
        "gate": _mesh_gate_label(env)[:28],
        "war_room": int(getattr(env, "_last_war_room_turns", 0) or 0),
        "honeypots": len(honeys),
        "migr": str(mig.get("current_phase", "—"))[:14] if mig.get("active") else "off",
        "migr_pct": int(100 * float(mig.get("progress_pct", 0) or 0)) if mig.get("active") else 0,
        "honeytokens": int(mig.get("honeytoken_activations", 0) or 0) if mig.get("active") else 0,
        "attack_vec": str(att)[:22],
        "directive": str(d0),
    }


def _pick_demo_action(env: ImmunoOrgEnvironment, obs, policy_fn, step_index: int, showcase_migration: bool):
    """Optional injected steps so judges see migration + honeypots (not honeycomb UI — decoy nodes)."""
    if not showcase_migration:
        return policy_fn(env, obs)
    phase = obs.current_phase.value
    if env.migration_engine.state is None and step_index == 1 and phase in (
        "detection", "containment", "rca", "refactor",
    ):
        return ImmunoAction(
            action_type=ActionType.TACTICAL,
            tactical_action=TacticalAction.START_MIGRATION,
            target="core-backbone",
            reasoning="[Demo] Start 50-step polymorphic migration (decoys, honeypots, honeytokens).",
            parameters={"compliance": "SOC2"},
        )
    if env.migration_engine.state and step_index >= 3 and step_index % 4 == 0:
        return ImmunoAction(
            action_type=ActionType.TACTICAL,
            tactical_action=TacticalAction.DEPLOY_HONEYPOT,
            target="edge-pool",
            reasoning="[Demo] Deploy honeypot node on the migration track.",
        )
    return policy_fn(env, obs)


def _run_episode(scenario, policy_fn, max_steps=30, *, showcase_migration: bool = False):
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
        action = _pick_demo_action(env, obs, policy_fn, step, showcase_migration)
        obs, reward, done = env.step(action)
        shaped = float(reward) + float(training_step_penalty(env, action))
        total += shaped
        tel = _telemetry_row(env, obs)
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
            **tel,
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
    out = []
    for f in frames:
        out.append([
            f["step"],
            f["phase"],
            f["action_type"],
            f["action"],
            f["target"],
            f["reward"],
            f["threats_left"],
            f["mesh_ok"],
            f["gate"],
            f["war_room"],
            f["honeypots"],
            f["migr"],
            f["migr_pct"],
            f["honeytokens"],
            f["attack_vec"],
            f["directive"],
            f["reasoning"][:72],
        ])
    return out


def _feature_dashboard_figure(heur_frames: list, trained_frames: list):
    """Plotly: pipeline integrity, honeypots, honeytokens, War Room turns."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "4-gate DevSecOps mesh — pipeline integrity (1.0 = clean)",
            "Honeypots deployed (moving-target / decoy layer)",
            "Honeytoken activations (trap callbacks)",
            "War Room — consensus rounds (CISO / DevOps / Architect)",
        ),
    )
    specs = [
        ("mesh_ok", "Heuristic", "#ff7f0e", "Trained", "#1f77b4"),
        ("honeypots", "Heuristic honeypots", "#ff7f0e", "Trained honeypots", "#1f77b4"),
        ("honeytokens", "Heuristic honeytokens", "#ff7f0e", "Trained honeytokens", "#1f77b4"),
        ("war_room", "Heuristic WR turns", "#ff7f0e", "Trained WR turns", "#1f77b4"),
    ]
    for row, (key, n1, c1, n2, c2) in enumerate(specs, start=1):
        xh = [f["step"] for f in heur_frames]
        yh = [f[key] for f in heur_frames]
        xt = [f["step"] for f in trained_frames]
        yt = [f[key] for f in trained_frames]
        fig.add_trace(
            go.Scatter(
                x=xh, y=yh, mode="lines+markers", name=n1,
                line=dict(color=c1, shape="hv"), legendgroup="h", showlegend=(row == 1),
            ),
            row=row, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=xt, y=yt, mode="lines+markers", name=n2,
                line=dict(color=c2, shape="hv", dash="dash"), legendgroup="t", showlegend=(row == 1),
            ),
            row=row, col=1,
        )
    fig.update_layout(
        height=780,
        margin=dict(t=36, b=24, l=48, r=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        font=dict(size=11),
    )
    fig.update_xaxes(title_text="step", row=4, col=1)
    return fig


def _mesh_gate_bar_figure(heur_frames: list, trained_frames: list):
    """Grouped bar: how often each mesh gate fired (per episode)."""
    import plotly.graph_objects as go

    def counts(frames: list) -> dict[str, int]:
        c: Counter[str] = Counter()
        for f in frames:
            g = str(f.get("gate") or "").strip()
            if g and g != "—":
                # Short labels for x axis
                short = g.replace("gate", "").replace("_", " ")[:22]
                c[short] += 1
        return dict(c)

    ch, ct = counts(heur_frames), counts(trained_frames)
    if not ch and not ct:
        fig = go.Figure()
        fig.add_annotation(
            text="No mesh gate catches this episode (pipeline stayed clean).",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(height=280, margin=dict(t=40, b=20))
        return fig

    keys = sorted(set(ch) | set(ct), key=lambda k: (ch.get(k, 0) + ct.get(k, 0)), reverse=True)[:12]
    fig = go.Figure(
        data=[
            go.Bar(name="Heuristic", x=keys, y=[ch.get(k, 0) for k in keys], marker_color="#ff7f0e"),
            go.Bar(name="Trained", x=keys, y=[ct.get(k, 0) for k in keys], marker_color="#1f77b4"),
        ]
    )
    fig.update_layout(
        title="Mesh gate catches (count of steps where each gate flagged)",
        barmode="group",
        height=320,
        margin=dict(t=50, b=80, l=48, r=24),
        xaxis_tickangle=-28,
        font=dict(size=11),
    )
    return fig


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


def run_demo(scenario_label, max_steps, showcase_migration):
    family = _LABEL_TO_FAMILY[scenario_label]
    scenario = _scenario_for(family)
    show_mig = bool(showcase_migration)

    heur_frames, heur_total = _run_episode(
        scenario, _heuristic_action, int(max_steps), showcase_migration=show_mig
    )
    trained_frames, trained_total = _run_episode(
        scenario, _trained_policy, int(max_steps), showcase_migration=show_mig
    )

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

    dash = _feature_dashboard_figure(heur_frames, trained_frames)
    gates = _mesh_gate_bar_figure(heur_frames, trained_frames)

    return (
        summary_md,
        _frames_to_table(heur_frames),
        _frames_to_table(trained_frames),
        chart_data,
        dash,
        gates,
        _trained_status_text(),
    )


# ─── War Room (LLM debate) — same Gradio page as episode demo ────────────


def _format_war_room_markdown(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(
        f"*LLM: `{data.get('model')}` · backend: `{data.get('llm_provider', '?')}`*\n"
    )
    verdict = data.get("verdict") or {}
    lines.append("## Final verdict\n")
    ca = verdict.get("consensus_action")
    lines.append(
        f"**{verdict.get('status', '—')}**"
        + (f" — action: `{ca}`" if ca else "")
        + "\n"
    )
    for v in verdict.get("votes_detail") or []:
        lines.append(f"- **{v.get('agent')}:** {v.get('action')}")
    lines.append("\n## Initial positions\n")
    for a in data.get("agents") or []:
        warn = ""
        if a.get("hallucination_flags"):
            warn = " ⚠️ *flags (cross-exam)*: " + "; ".join(a["hallucination_flags"])
        lines.append(
            f"### {a.get('display_name', '?')}{warn}\n\n"
            f"**Proposed action:** `{a.get('proposed_action', '—')}`\n\n"
            f"{a.get('position_text', '')}\n"
        )
    lines.append("\n## Cross-examination\n")
    for c in data.get("cross_examination") or []:
        xf = ""
        if c.get("hallucination_flags"):
            xf = "\n\n⚠️ " + " · ".join(c["hallucination_flags"])
        lines.append(
            f"**{c.get('examiner_name')}** → **{c.get('target_name')}**{xf}\n\n"
            f"{c.get('text', '')}\n\n---\n"
        )
    return "\n".join(lines)


def _war_room_handler(
    threat_type: str,
    severity: float,
    source_ip: str,
    target_service: str,
    description: str,
    preference: str,
) -> str:
    tt = (threat_type or "").strip()
    sip = (source_ip or "").strip()
    tgt = (target_service or "").strip()
    desc = (description or "").strip()
    if not tt or not sip or not tgt or not desc:
        return "**Fill threat type, source IP, target service, and description.**"
    pref = (preference or "").strip() or None
    try:
        sev = int(severity)
    except (TypeError, ValueError):
        sev = 5
    sev = max(1, min(10, sev))
    try:
        data = asyncio.run(
            run_war_room_debate(
                threat_type=tt,
                severity=sev,
                source_ip=sip,
                target_service=tgt,
                description=desc,
                preference_injection=pref,
            )
        )
    except RuntimeError as e:
        return f"**Configuration error:** {e}"
    except Exception as e:
        return f"**Error:** `{type(e).__name__}: {e}`"
    return _format_war_room_markdown(data)


# ─── Build the UI ──────────────────────────────────────────────────────────


def build_demo() -> gr.Blocks:
    table_headers = [
        "step", "phase", "type", "action", "target", "reward", "threats",
        "pipeline", "mesh gate", "WR turns", "honeypots", "migr phase",
        "migr %", "honeytokens", "attack vec", "directive", "reasoning",
    ]

    with gr.Blocks(title="ImmunoOrg 2.0 — Live Demo", analytics_enabled=False) as demo:
        gr.Markdown(
            """
# 🛡️ ImmunoOrg 2.0 — Live Demo

The agent has to defend an enterprise from a cyber-attack **and**
restructure the organization that lets the attack succeed in the first
place. Pick one of the 5 scenario families and watch the heuristic
baseline play it head-to-head against the GRPO-trained LLM defender.

**What the extra columns show (backend features, live from the sim):**

| Column | Feature in codebase |
| --- | --- |
| **pipeline / mesh gate** | 4-gate **DevSecOps Mesh** (`devsecops_mesh.py`): AST → semantic → Terraform → sandbox; gate shows which layer flagged a payload. |
| **WR turns** | **War Room** multi-agent debate rounds toward consensus (`war_room.py`). |
| **honeypots / migr / honeytokens** | **50-step polymorphic migration** (`migration_engine.py`): decoy phase, honeypot nodes, honeytoken activations — *not* a separate “honeycomb” UI; honeypots are tactical decoys here. |
| **attack vec** | Active attack vector (feeds **MITRE** / kill-chain context in the full env). |
| **directive** | Board directive text when the scenario injects one. |

**Charts below:** interactive **Plotly** dashboards — pipeline/decoys/War Room time series, plus **mesh gate** catch counts.

> 📚 [Problem statement](https://github.com/Charannoo/immunoorg/blob/master/PROBLEM_STATEMENT.md)
> · [Source](https://github.com/Charannoo/immunoorg)
> · [Blog](https://github.com/Charannoo/immunoorg/blob/master/BLOG_POST.md)
> · [Training notebook](https://github.com/Charannoo/immunoorg/blob/master/ImmunoOrg_Training_Colab.ipynb)
            """
        )

        with gr.Accordion(
            "🎭 Live LLM War Room — 3-agent debate (CISO / DevOps / Architect)",
            open=False,
        ):
            gr.Markdown(
                "Same page as the episode demo. Runs **initial positions** + **cross-examination** "
                "via your configured LLM API (**GROQ_API_KEY**, **OPENAI_API_KEY**, or "
                "**ANTHROPIC_API_KEY** in Space secrets). Optional: `POST /api/war-room` for scripts."
            )
            with gr.Row():
                wr_threat = gr.Textbox(
                    label="Threat type",
                    placeholder="e.g. SQL injection probe",
                )
                wr_sev = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label="Severity (1–10)",
                )
            with gr.Row():
                wr_ip = gr.Textbox(label="Source IP", placeholder="203.0.113.42")
                wr_tgt = gr.Textbox(label="Target service", placeholder="api-payments")
            wr_desc = gr.Textbox(
                label="Description",
                lines=3,
                placeholder="What was observed…",
            )
            wr_pref = gr.Textbox(
                label="Preference injection (optional board directive)",
                placeholder="Breaks deadlock → Architect wins",
            )
            wr_btn = gr.Button("Run War Room debate", variant="secondary")
            wr_out = gr.Markdown("*Results appear here after you run the debate.*")
            wr_btn.click(
                _war_room_handler,
                inputs=[
                    wr_threat,
                    wr_sev,
                    wr_ip,
                    wr_tgt,
                    wr_desc,
                    wr_pref,
                ],
                outputs=[wr_out],
            )

        status_md = gr.Markdown(_trained_status_text())

        with gr.Row():
            scenario_dd = gr.Dropdown(
                choices=list(_SCENARIO_LABEL.values()),
                value=list(_SCENARIO_LABEL.values())[1],
                label="Scenario family",
            )
            steps_sl = gr.Slider(5, 30, value=15, step=1, label="Max steps per episode")
            mig_cb = gr.Checkbox(
                value=True,
                label="Demo: run START_MIGRATION + honeypot beats (shows decoys/honeytokens)",
            )
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

        gr.Markdown("### Feature dashboards (Plotly — zoom/pan/hover)")
        with gr.Row():
            signals_plot = gr.Plot(label="Pipeline, honeypots, honeytokens, War Room")
            gate_plot = gr.Plot(label="Which mesh gate fired (AST / semantic / Terraform / sandbox)")

        gr.Markdown(
            """
---

### What the agent is reasoning about

- 28 actions across 3 categories: **tactical** (block_port, isolate_node, deploy_patch, **deploy_honeypot**, start_migration…),
  **strategic** (merge_departments, reduce_bureaucracy, establish_devsecops…),
  **diagnostic** (correlate_failure, identify_silo, vulnerability_scan…).
- 5-track composable reward:
  uptime (25%) · threat neutralization (25%) · bureaucracy efficiency (20%) ·
  code-patch quality (20%) · pipeline integrity (10%) — pipeline ties to **mesh** columns.
- Trained on the elite 20/20/20/20/20 mix of scenario families
  (basic / RAG / executive / silo / stealth) with TRL GRPO + Unsloth.

Uncheck **Demo: migration + honeypot** for a “pure” heuristic/LLM comparison without injected migration steps.
            """
        )

        run_btn.click(
            run_demo,
            inputs=[scenario_dd, steps_sl, mig_cb],
            outputs=[
                summary_md, heur_table, trained_table, chart,
                signals_plot, gate_plot, status_md,
            ],
        )

    return demo


__all__ = ["build_demo"]
