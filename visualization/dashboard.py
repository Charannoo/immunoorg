"""
ImmunoOrg Gradio Dashboard
============================
Interactive demo showing live network/org graphs, belief map, and metrics.
"""

from __future__ import annotations

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import (
    ImmunoAction, ActionType, TacticalAction, StrategicAction, DiagnosticAction,
    PreferenceInjection,
)
from immunoorg.agents.llm_agent import ImmunoDefenderAgent
from visualization.metrics import (
    plot_improvement_trajectory, plot_curriculum_progress,
    plot_belief_accuracy_convergence, plot_reward_breakdown,
)


# Global state
env: ImmunoOrgEnvironment | None = None
agent: ImmunoDefenderAgent | None = None
episode_log: list[dict] = []
belief_accuracy_history: list[float] = []
war_room_log: list[str] = []  # War room transcript lines
pipeline_event_log: list[dict] = []  # Mesh gate events



def build_network_graph_viz() -> go.Figure:
    """Build a Plotly network graph visualization."""
    if not env or not env.network:
        return go.Figure().update_layout(title="No environment", template="plotly_dark")

    nodes = env.network.get_all_nodes()
    edges = env.network.get_all_edges()

    # Position nodes by tier
    tier_x = {"dmz": 0, "web": 1, "app": 2, "data": 3, "management": 2.5}
    tier_counts: dict[str, int] = {}
    positions: dict[str, tuple[float, float]] = {}

    for node in nodes:
        tier = node.tier
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        x = tier_x.get(tier, 2)
        y = tier_counts[tier] * 1.5
        positions[node.id] = (x, y)

    # Edges
    edge_x, edge_y = [], []
    for edge in edges:
        if edge.source in positions and edge.target in positions:
            x0, y0 = positions[edge.source]
            x1, y1 = positions[edge.target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    # Nodes
    node_x = [positions[n.id][0] for n in nodes if n.id in positions]
    node_y = [positions[n.id][1] for n in nodes if n.id in positions]
    node_colors = []
    node_labels = []
    for n in nodes:
        if n.id not in positions:
            continue
        if n.compromised and not n.isolated:
            node_colors.append("#ef4444")  # Red
        elif n.isolated:
            node_colors.append("#6b7280")  # Gray
        elif n.health < 0.5:
            node_colors.append("#f59e0b")  # Yellow
        else:
            node_colors.append("#22c55e")  # Green
        status = "🔴COMPROMISED" if n.compromised else "🟢OK"
        node_labels.append(f"{n.id}<br>{n.type.value}<br>HP:{n.health:.0%} {status}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(width=1, color="#4b5563"), hoverinfo="none"))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text",
                             marker=dict(size=20, color=node_colors, line=dict(width=2, color="white")),
                             text=[n.id.split("-")[-1] for n in nodes if n.id in positions],
                             textposition="top center",
                             hovertext=node_labels, hoverinfo="text"))

    fig.update_layout(
        title="🖥️ Network Graph — Technical Layer",
        template="plotly_dark", showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400,
        annotations=[
            dict(x=tier_x[t], y=0, text=t.upper(), showarrow=False,
                 font=dict(size=12, color="#9ca3af"))
            for t in tier_x
        ],
    )
    return fig


def build_org_graph_viz() -> go.Figure:
    """Build an org graph visualization."""
    if not env or not env.org:
        return go.Figure().update_layout(title="No environment", template="plotly_dark")

    nodes = env.org.get_all_nodes()
    edges = env.org.get_active_edges()

    # Circular layout
    import math
    active_nodes = [n for n in nodes if n.active]
    positions = {}
    for i, n in enumerate(active_nodes):
        angle = 2 * math.pi * i / max(1, len(active_nodes))
        positions[n.id] = (math.cos(angle) * 3, math.sin(angle) * 3)

    edge_x, edge_y = [], []
    for e in edges:
        if e.source in positions and e.target in positions:
            x0, y0 = positions[e.source]
            x1, y1 = positions[e.target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    node_x = [positions[n.id][0] for n in active_nodes if n.id in positions]
    node_y = [positions[n.id][1] for n in active_nodes if n.id in positions]
    labels = [f"🏢 {n.name}\nTrust: {n.trust_score:.2f}\nLatency: {n.response_latency:.1f}"
              for n in active_nodes if n.id in positions]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(width=2, color="#6366f1"), hoverinfo="none"))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        marker=dict(size=30, color="#6366f1", line=dict(width=2, color="white")),
        text=[n.name[:8] for n in active_nodes if n.id in positions],
        textposition="top center", hovertext=labels, hoverinfo="text",
    ))

    fig.update_layout(
        title="🏛️ Organizational Graph — Socio Layer",
        template="plotly_dark", showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400,
    )
    return fig


def reset_env(difficulty: int) -> tuple:
    global env, episode_log, belief_accuracy_history, agent
    env = ImmunoOrgEnvironment(difficulty=int(difficulty), seed=42)
    # Load the trained RL model from HF Hub
    agent = ImmunoDefenderAgent(
        seed=42, 
        llm_provider="openai", 
        model_path="your-username/immunoorg-patronus-rl" # REPLACE WITH YOUR HF PATH
    )
    obs = env.reset()
    episode_log = []
    belief_accuracy_history = []



    status = f"✅ Episode started | Difficulty: {difficulty} | Phase: {obs.current_phase.value}"
    net_fig = build_network_graph_viz()
    org_fig = build_org_graph_viz()
    obs_text = format_obs(obs)
    return status, net_fig, org_fig, obs_text, "0.00", "0.000"


def take_action(action_type: str, action_name: str, target: str, reasoning: str, autonomous: bool) -> tuple:
    global episode_log, belief_accuracy_history, war_room_log, pipeline_event_log
    if not env:
        return "❌ Environment not initialized", None, None, "", "0.00", "0.000", "", ""
    
    if autonomous and agent:
        # Use the LLM Agent to decide
        obs_before = env.reset() if env.state.step_count == 0 else env._build_observation("Continuing", True)
        action = agent.act(obs_before)
        # Update UI inputs to reflect agent's decision
        # Note: Gradio doesn't allow modifying inputs directly from a function easily, 
        # but we can return the updated values if we add them to outputs.
    else:
        action = build_action(action_type, action_name, target, reasoning)
    
    obs, reward, terminated = env.step(action)


    acc = env.belief_map.calculate_belief_accuracy() if env.belief_map else 0.0
    belief_accuracy_history.append(acc)
    episode_log.append({"step": env.state.step_count, "action": action_name, "reward": reward})

    # Capture War Room transcript
    if env.war_room and env.war_room.debate_history:
        transcript = env.war_room.get_latest_transcript()
        war_room_log.append(transcript)

    # Capture Pipeline events
    if env.devsecops_mesh:
        recent_events = env.devsecops_mesh.get_recent_events(3)
        for evt in recent_events:
            pipeline_event_log.append({
                "gate": evt.gate.value, "severity": evt.severity.value,
                "threat": evt.threat_type or "clean", "summary": evt.payload_summary[:60],
                "score": f"{evt.security_score:.1f}",
            })

    status = f"{'🏁 DONE' if terminated else '▶️ Step'} {env.state.step_count} | Phase: {obs.current_phase.value} | Reward: {reward:+.3f}"
    if terminated:
        status += f" | Reason: {env.state.termination_reason}"

    net_fig = build_network_graph_viz()
    org_fig = build_org_graph_viz()
    obs_text = format_obs(obs)
    threat = f"{obs.threat_level:.2f}"
    cum_reward = f"{env.state.cumulative_reward:.3f}"
    war_room_text = "\n\n".join(war_room_log[-3:]) or "No debates yet."
    pipeline_text = format_pipeline_log()
    return status, net_fig, org_fig, obs_text, threat, cum_reward, war_room_text, pipeline_text


def build_reasoning_heatmap() -> str:
    """Format reasoning traces as a 'heatmap' of triggers."""
    if not env:
        return "No environment initialized."
    traces = env.state.reasoning_traces
    if not traces:
        return "No reasoning traces recorded yet."
    
    lines = ["### 🧠 Reasoning Heatmap (Decision Triggers)", 
             "| Step | Trigger | Observation Snippet | Rationale |",
             "| :--- | :--- | :--- | :--- |"]
    
    for t in traces[-10:]:
        color = "🔴" if "Containment" in t.decision_trigger else "🔵" if "Structural" in t.decision_trigger else "🟢"
        lines.append(f"| {t.step} | {color} {t.decision_trigger} | *{t.observation_snippet}* | {t.rationale[:100]}... |")
    
    return "\n".join(lines)
    if not pipeline_event_log:
        return "No pipeline events yet."
    lines = []
    for evt in pipeline_event_log[-8:]:
        icon = "🚫" if evt["severity"] == "blocked" else ("⚠️" if evt["severity"] == "warned" else ("🔧" if evt["severity"] == "sanitized" else "✅"))
        lines.append(f"{icon} [{evt['gate']}] {evt['threat']} | score:{evt['score']} | {evt['summary']}")
    return "\n".join(lines)


def inject_board_directive(directive: str) -> tuple:
    if not env:
        return "❌ Environment not initialized", "No active directives"
    env.inject_directive(directive)
    directives_text = "\n".join([f"- {d}" for d in env.state.directives]) or "No active directives"
    return f"✅ Directive Injected: {directive}", directives_text


def inject_preference(directive: str, priority: str) -> str:
    if not env:
        return "❌ Environment not initialized"
    injection = PreferenceInjection(
        directive=directive,
        priority_override=priority,
        source="board",
        injected_at=env.state.sim_time if env.state else 0.0,
    )
    env.war_room.inject_preference(injection)
    return f"⚡ Preference injected: [{priority}] {directive}"


def build_5track_chart() -> go.Figure:
    """Build a bar chart of the 5 reward tracks."""
    if not env or not env.reward_calc:
        return go.Figure().update_layout(title="No data", template="plotly_dark")
    tracks = env.reward_calc.get_track_scores()
    labels = list(tracks.keys())
    values = list(tracks.values())
    colors = ["#22c55e", "#ef4444", "#6366f1", "#f59e0b", "#06b6d4"]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors[:len(labels)],
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        title="📊 5-Track Composable Reward (Running Totals)",
        template="plotly_dark", height=300,
        xaxis_title="Track", yaxis_title="Cumulative Score",
        showlegend=False,
    )
    return fig


def build_honeytoken_table() -> str:
    """Format honeytoken activations as markdown table."""
    if not env or not env.migration_engine:
        return "No migration active."
    data = env.migration_engine.get_honeytoken_map_data()
    if not data:
        return "🍯 No honeytoken activations yet. Start migration to deploy tokens."
    lines = ["| Token | Type | Geo | IP | Confidence |",
             "| :--- | :--- | :--- | :--- | :---: |"]
    for row in data[-8:]:
        lines.append(
            f"| {row['token_id']} | {row['type']} | {row['geo']} "
            f"| {row['ip']} | {row['confidence']:.0%} |"
        )
    return "\n".join(lines)


def build_migration_progress() -> str:
    """Format migration progress for the dashboard."""
    if not env or not env.migration_engine:
        return "Migration engine not initialized."
    prog = env.migration_engine.get_progress()
    if not prog.get("active"):
        return "⏸ Migration not started. Use action `start_migration` to begin 50-step MTD workflow."
    bar_filled = int(prog['progress_pct'] * 20)
    bar = '█' * bar_filled + '░' * (20 - bar_filled)
    return (
        f"🚀 **Polymorphic Migration Active**\n"
        f"Phase: `{prog['current_phase']}` | Step: {prog['current_step']}/{prog['total_steps']}\n"
        f"`{bar}` {prog['progress_pct']:.0%}\n"
        f"🍯 Honeytoken activations: **{prog['honeytoken_activations']}** | "
        f"Zero-downtime: {'✅' if prog['zero_downtime'] else '❌'}"
    )


def build_action(atype: str, aname: str, target: str, reasoning: str) -> ImmunoAction:
    action = ImmunoAction(action_type=ActionType(atype), target=target, reasoning=reasoning)
    if atype == "tactical":
        try: action.tactical_action = TacticalAction(aname)
        except ValueError: pass
    elif atype == "strategic":
        try: action.strategic_action = StrategicAction(aname)
        except ValueError: pass
    elif atype == "diagnostic":
        try: action.diagnostic_action = DiagnosticAction(aname)
        except ValueError: pass
    return action


def format_obs(obs) -> str:
    from immunoorg.agents.defender import format_observation_for_llm
    return format_observation_for_llm(obs.model_dump())


def get_metrics_plots() -> tuple:
    if not env:
        empty = go.Figure().update_layout(template="plotly_dark", title="No data")
        return empty, empty

    belief_fig = plot_belief_accuracy_convergence(belief_accuracy_history) or go.Figure()
    reward_fig = plot_reward_breakdown(
        env.reward_calc.get_partial_rewards_summary() if env.reward_calc else {}
    ) or go.Figure()
    return belief_fig, reward_fig


def build_dashboard():
    """Build the Gradio dashboard."""
    tactical_actions = [a.value for a in TacticalAction]
    strategic_actions = [a.value for a in StrategicAction]
    diagnostic_actions = [a.value for a in DiagnosticAction]
    all_actions = tactical_actions + strategic_actions + diagnostic_actions

    with gr.Blocks(
        title="ImmunoOrg — The Self-Healing Autonomous Enterprise",
        theme=gr.themes.Base(primary_hue="indigo", secondary_hue="emerald"),
        css="""
        .gradio-container { max-width: 1400px !important; }
        h1 { text-align: center; background: linear-gradient(135deg, #6366f1, #22c55e);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        """
    ) as demo:
        gr.Markdown("# 🛡️ ImmunoOrg: The Self-Healing Autonomous Enterprise")
        gr.Markdown("*Dual-layer RL environment: Network Security × Organizational Dynamics*")

        with gr.Row():
            status_box = gr.Textbox(label="Status", interactive=False, scale=3)
            threat_box = gr.Textbox(label="Threat Level", interactive=False, scale=1)
            reward_box = gr.Textbox(label="Cumulative Reward", interactive=False, scale=1)

        with gr.Row():
            with gr.Column(scale=1):
                network_plot = gr.Plot(label="Network Graph")
            with gr.Column(scale=1):
                org_plot = gr.Plot(label="Org Graph")

        # ── Control Panel ──────────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🎮 Control Panel")
                difficulty = gr.Slider(1, 4, value=1, step=1, label="Difficulty Level")
                reset_btn = gr.Button("🔄 Reset Episode", variant="primary")

                autonomous_mode = gr.Checkbox(label="🤖 Autonomous Patronus Mode", value=False)

                action_type = gr.Radio(["tactical", "strategic", "diagnostic"], value="tactical", label="Action Type")
                action_name = gr.Dropdown(all_actions, label="Action", value="scan_logs")
                target = gr.Textbox(label="Target (node/dept ID)", value="")
                reasoning = gr.Textbox(label="Reasoning", lines=2, value="Investigating the situation.")
                step_btn = gr.Button("▶️ Execute Action", variant="primary")

            with gr.Column(scale=2):
                obs_display = gr.Markdown(label="Observation")

        # ── War Room Feed ──────────────────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### ⚔️ War Room — Multi-Agent Debate Feed")
        gr.Markdown("*CISO 🔴 vs DevOps 🔵 vs Lead Architect 🟣 — 2-of-3 consensus required*")
        with gr.Row():
            with gr.Column(scale=2):
                war_room_feed = gr.Textbox(
                    label="Live Debate Transcript",
                    lines=12, interactive=False,
                    value="No debates yet. Threat level must reach 0.45 to trigger War Room."
                )
            with gr.Column(scale=1):
                gr.Markdown("**⚡ Preference Injection (Snorkel AI Bonus)**")
                pref_directive = gr.Textbox(
                    label="Board Directive",
                    value="Prioritize HIPAA compliance over all else"
                )
                pref_priority = gr.Dropdown(
                    ["HIPAA", "UPTIME", "LEGAL_HOLD", "GDPR", "PR_CRISIS"],
                    label="Override Type", value="HIPAA"
                )
                inject_btn = gr.Button("⚡ Inject Board Directive", variant="stop")
                inject_status = gr.Textbox(label="Injection Status", interactive=False)

        # ── CEO Dashboard — Board Directives ──────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 👔 CEO Dashboard — Board Directives")
        gr.Markdown("*Inject high-level constraints that the Defender agent must follow*")
        with gr.Row():
            with gr.Column(scale=1):
                ceo_directive = gr.Textbox(
                    label="New Board Directive", 
                    placeholder="e.g., 'Emergency: All budgets cut by 50%, maintain 100% uptime for DB'"
                )
                ceo_inject_btn = gr.Button("📢 Broadcast Directive", variant="primary")
                ceo_inject_status = gr.Textbox(label="Broadcast Status", interactive=False)
            with gr.Column(scale=2):
                active_directives = gr.Markdown("No active directives.")

        # ── Reasoning Heatmap — Interpretability ────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 🧬 Reasoning Heatmap — Interpretability")
        gr.Markdown("*Visualizing the agent's internal decision triggers and rationale*")
        with gr.Row():
            reasoning_display = gr.Markdown("No reasoning traces recorded yet.")
            refresh_reasoning_btn = gr.Button("🔄 Refresh Reasoning Heatmap")

        # ── CI/CD Pipeline Gate View ────────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 🔒 AI DevSecOps Mesh — Pipeline Gate Events")
        gr.Markdown("*Gate 1: AST | Gate 2: Semantic | Gate 3: Terraform | Gate 4: MicroVM*")
        with gr.Row():
            pipeline_feed = gr.Textbox(
                label="Pipeline Events (last 8)", lines=8, interactive=False,
                value="No pipeline events yet."
            )

        # ── Migration + Honeytoken Panel ────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 🚀 Polymorphic Migration + 🍯 Honeytoken Map")
        with gr.Row():
            with gr.Column(scale=1):
                migration_display = gr.Markdown("Migration not started.")
                refresh_migration_btn = gr.Button("🔄 Refresh Migration Status")
            with gr.Column(scale=2):
                honeytoken_display = gr.Markdown("No honeytoken activations yet.")

        # ── 5-Track Reward Dashboard ────────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 📊 5-Track Composable Reward Model")
        with gr.Row():
            with gr.Column(scale=1):
                track_chart = gr.Plot(label="Track Scores")
                refresh_tracks_btn = gr.Button("📊 Refresh Reward Tracks")
            with gr.Column(scale=1):
                belief_plot = gr.Plot(label="Belief Map Accuracy")
            with gr.Column(scale=1):
                reward_plot = gr.Plot(label="Reward Breakdown")
        metrics_btn = gr.Button("📊 Refresh All Metrics")

        # ── Evidence Panel ──────────────────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("### 🏆 Proof of Intelligence — Hackathon Evidence")

        with gr.Row():
            if os.path.exists("evidence_policy_comparison.png"):
                gr.Image("evidence_policy_comparison.png", label="Policy Comparison: Random vs Heuristic")
            else:
                gr.Markdown("*Run `python generate_evidence.py` to generate charts*")
            if os.path.exists("evidence_self_improvement.png"):
                gr.Image("evidence_self_improvement.png", label="Self-Improvement Trajectory")
            else:
                gr.Markdown("*Run `python generate_evidence.py` to generate charts*")

        with gr.Row():
            if os.path.exists("evidence_org_before_after.png"):
                gr.Image("evidence_org_before_after.png", label="Before vs After Org Restructuring")
            else:
                gr.Markdown("*Run `python generate_evidence.py` to generate charts*")

        with gr.Row():
            if os.path.exists("demo_results.json"):
                with open("demo_results.json") as f:
                    demo_data = json.load(f)
                summary_parts = ["**Demo Results Summary:**\n"]
                level_results = demo_data.get("level_results", {})
                for lvl in sorted(level_results.keys(), key=int):
                    r = level_results[lvl]
                    rand_r = r.get("random", {}).get("avg_reward", 0)
                    heur_r = r.get("heuristic", {}).get("avg_reward", 0)
                    summary_parts.append(f"- **Level {lvl}:** Random={rand_r:+.2f} | Heuristic={heur_r:+.2f}")
                si = demo_data.get("self_improvement", [])
                if si:
                    summary_parts.append(f"\n**Self-Improvement:** Gen 0 reward={si[0]['total_reward']:+.2f} → Gen {len(si)-1} reward={si[-1]['total_reward']:+.2f}")
                gr.Markdown("\n".join(summary_parts))

        # Events
        reset_btn.click(
            reset_env, inputs=[difficulty],
            outputs=[status_box, network_plot, org_plot, obs_display, threat_box, reward_box]
        )
        step_btn.click(
            take_action, inputs=[action_type, action_name, target, reasoning, autonomous_mode],
            outputs=[status_box, network_plot, org_plot, obs_display,
                     threat_box, reward_box, war_room_feed, pipeline_feed]
        )

        inject_btn.click(
            inject_preference, inputs=[pref_directive, pref_priority],
            outputs=[inject_status]
        )
        ceo_inject_btn.click(
            inject_board_directive, inputs=[ceo_directive],
            outputs=[ceo_inject_status, active_directives]
        )
        refresh_reasoning_btn.click(
            build_reasoning_heatmap, outputs=[reasoning_display]
        )
        metrics_btn.click(
            get_metrics_plots, outputs=[belief_plot, reward_plot]
        )
        refresh_tracks_btn.click(
            build_5track_chart, outputs=[track_chart]
        )
        refresh_migration_btn.click(
            lambda: (build_migration_progress(), build_honeytoken_table()),
            outputs=[migration_display, honeytoken_display]
        )

    return demo


if __name__ == "__main__":
    demo = build_dashboard()
    demo.launch(server_name="0.0.0.0", server_port=7861, share=False)
