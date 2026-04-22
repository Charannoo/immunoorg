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
)
from visualization.metrics import (
    plot_improvement_trajectory, plot_curriculum_progress,
    plot_belief_accuracy_convergence, plot_reward_breakdown,
)

# Global state
env: ImmunoOrgEnvironment | None = None
episode_log: list[dict] = []
belief_accuracy_history: list[float] = []


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
    global env, episode_log, belief_accuracy_history
    env = ImmunoOrgEnvironment(difficulty=int(difficulty), seed=42)
    obs = env.reset()
    episode_log = []
    belief_accuracy_history = []

    status = f"✅ Episode started | Difficulty: {difficulty} | Phase: {obs.current_phase.value}"
    net_fig = build_network_graph_viz()
    org_fig = build_org_graph_viz()
    obs_text = format_obs(obs)
    return status, net_fig, org_fig, obs_text, "0.00", "0.000"


def take_action(action_type: str, action_name: str, target: str, reasoning: str) -> tuple:
    global episode_log, belief_accuracy_history
    if not env:
        return "❌ Environment not initialized", None, None, "", "0.00", "0.000"

    action = build_action(action_type, action_name, target, reasoning)
    obs, reward, terminated = env.step(action)

    acc = env.belief_map.calculate_belief_accuracy() if env.belief_map else 0.0
    belief_accuracy_history.append(acc)

    episode_log.append({"step": env.state.step_count, "action": action_name, "reward": reward})

    status = f"{'🏁 DONE' if terminated else '▶️ Step'} {env.state.step_count} | Phase: {obs.current_phase.value} | Reward: {reward:+.3f}"
    if terminated:
        status += f" | Reason: {env.state.termination_reason}"

    net_fig = build_network_graph_viz()
    org_fig = build_org_graph_viz()
    obs_text = format_obs(obs)
    threat = f"{obs.threat_level:.2f}"
    cum_reward = f"{env.state.cumulative_reward:.3f}"
    return status, net_fig, org_fig, obs_text, threat, cum_reward


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

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🎮 Control Panel")
                difficulty = gr.Slider(1, 4, value=1, step=1, label="Difficulty Level")
                reset_btn = gr.Button("🔄 Reset Episode", variant="primary")

                action_type = gr.Radio(["tactical", "strategic", "diagnostic"], value="tactical", label="Action Type")
                action_name = gr.Dropdown(all_actions, label="Action", value="scan_logs")
                target = gr.Textbox(label="Target (node/dept ID)", value="")
                reasoning = gr.Textbox(label="Reasoning", lines=2, value="Investigating the situation.")
                step_btn = gr.Button("▶️ Execute Action", variant="primary")

            with gr.Column(scale=2):
                obs_display = gr.Markdown(label="Observation")

        with gr.Row():
            gr.Markdown("### 📊 Metrics")
        with gr.Row():
            belief_plot = gr.Plot(label="Belief Map Accuracy")
            reward_plot = gr.Plot(label="Reward Breakdown")
        metrics_btn = gr.Button("📊 Refresh Metrics")

        # Events
        reset_btn.click(reset_env, inputs=[difficulty],
                       outputs=[status_box, network_plot, org_plot, obs_display, threat_box, reward_box])
        step_btn.click(take_action, inputs=[action_type, action_name, target, reasoning],
                      outputs=[status_box, network_plot, org_plot, obs_display, threat_box, reward_box])
        metrics_btn.click(get_metrics_plots, outputs=[belief_plot, reward_plot])

    return demo


if __name__ == "__main__":
    demo = build_dashboard()
    demo.launch(server_name="0.0.0.0", server_port=7861, share=False)
