"""
Proof-of-Improvement Metrics
=============================
Plotting functions for Time-to-Containment, Org-Efficiency, and training curves.
"""

from __future__ import annotations
import json
from typing import Any

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def plot_improvement_trajectory(generations: list[dict[str, float]]) -> Any:
    """Plot Time-to-Containment vs Org-Efficiency across self-improvement generations."""
    if not HAS_PLOTLY or not generations:
        return None

    gens = [g["generation"] for g in generations]
    ttc = [g["time_to_containment"] for g in generations]
    eff = [g["org_efficiency"] for g in generations]
    reward = [g["total_reward"] for g in generations]
    complexity = [g["attack_complexity"] for g in generations]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Time-to-Containment (↓ better)",
            "Org Efficiency (↑ better)",
            "Total Reward (↑ better)",
            "Attack Complexity Handled (↑ better)",
        ),
    )

    fig.add_trace(go.Scatter(x=gens, y=ttc, mode="lines+markers", name="TTC",
                             line=dict(color="#ef4444", width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=gens, y=eff, mode="lines+markers", name="Efficiency",
                             line=dict(color="#22c55e", width=3)), row=1, col=2)
    fig.add_trace(go.Scatter(x=gens, y=reward, mode="lines+markers", name="Reward",
                             line=dict(color="#3b82f6", width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=gens, y=complexity, mode="lines+markers", name="Complexity",
                             line=dict(color="#f59e0b", width=3)), row=2, col=2)

    fig.update_layout(
        title="ImmunoOrg Self-Improvement Trajectory",
        template="plotly_dark",
        height=600,
        showlegend=False,
    )
    fig.update_xaxes(title_text="Generation")
    return fig


def plot_curriculum_progress(level_stats: dict[int, dict]) -> Any:
    """Plot curriculum progression with success rates per level."""
    if not HAS_PLOTLY:
        return None

    levels = list(level_stats.keys())
    episodes = [level_stats[l]["episodes"] for l in levels]
    success_rates = [level_stats[l]["success_rate"] * 100 for l in levels]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"Level {l}" for l in levels], y=episodes,
        name="Episodes", marker_color="#6366f1",
    ))
    fig.add_trace(go.Scatter(
        x=[f"Level {l}" for l in levels], y=success_rates,
        mode="lines+markers", name="Success Rate %",
        yaxis="y2", line=dict(color="#f59e0b", width=3),
    ))

    fig.update_layout(
        title="Curriculum Progress",
        template="plotly_dark",
        yaxis=dict(title="Episodes"),
        yaxis2=dict(title="Success Rate %", overlaying="y", side="right", range=[0, 100]),
        height=400,
    )
    return fig


def plot_belief_accuracy_convergence(accuracy_history: list[float]) -> Any:
    """Plot how belief map accuracy converges over steps."""
    if not HAS_PLOTLY or not accuracy_history:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=accuracy_history, mode="lines",
        fill="tozeroy", fillcolor="rgba(59, 130, 246, 0.2)",
        line=dict(color="#3b82f6", width=2),
    ))
    fig.add_hline(y=0.8, line_dash="dash", line_color="#22c55e",
                  annotation_text="Target: 80%")

    fig.update_layout(
        title="Belief Map Accuracy Convergence",
        template="plotly_dark",
        xaxis_title="Step",
        yaxis_title="Accuracy",
        yaxis=dict(range=[0, 1]),
        height=350,
    )
    return fig


def plot_reward_breakdown(partial_rewards: dict[str, float]) -> Any:
    """Plot breakdown of reward components."""
    if not HAS_PLOTLY or not partial_rewards:
        return None

    labels = list(partial_rewards.keys())
    values = list(partial_rewards.values())
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=colors,
    ))
    fig.update_layout(
        title="Reward Component Breakdown",
        template="plotly_dark",
        xaxis_title="Reward",
        height=350,
    )
    return fig


def generate_proof_of_improvement_report(
    trajectory: list[dict], curriculum: dict, partial_rewards: dict
) -> str:
    """Generate a text summary for the proof-of-improvement."""
    lines = ["# ImmunoOrg — Proof of Improvement Report\n"]

    if trajectory:
        first = trajectory[0]
        last = trajectory[-1]
        ttc_improvement = ((first.get("time_to_containment", 1) - last.get("time_to_containment", 1))
                          / max(0.01, first.get("time_to_containment", 1))) * 100
        eff_improvement = ((last.get("org_efficiency", 0) - first.get("org_efficiency", 0))
                          / max(0.01, first.get("org_efficiency", 1))) * 100

        lines.append(f"## Self-Improvement: {len(trajectory)} Generations")
        lines.append(f"- Time-to-Containment: **{ttc_improvement:+.1f}%** improvement")
        lines.append(f"- Org Efficiency: **{eff_improvement:+.1f}%** improvement")
        lines.append(f"- Best Reward: **{max(g.get('total_reward', 0) for g in trajectory):.3f}**\n")

    if curriculum:
        lines.append(f"## Curriculum: Level {curriculum.get('current_level', '?')}")
        lines.append(f"- Total Episodes: {curriculum.get('total_episodes', 0)}")
        lines.append(f"- Consecutive Successes: {curriculum.get('consecutive_successes', 0)}\n")

    if partial_rewards:
        lines.append("## Reward Breakdown")
        for k, v in sorted(partial_rewards.items(), key=lambda x: x[1], reverse=True):
            sign = "+" if v >= 0 else ""
            lines.append(f"- {k}: {sign}{v:.3f}")

    return "\n".join(lines)
