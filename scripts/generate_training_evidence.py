"""
Generate the "training-evidence" reward chart without a GPU.

This script runs the Random and Heuristic policies through the 5
elite scenario families implemented in ``training/scenario_hooks.py``
(basic_containment / rag_grounding / executive_alignment /
silo_breaker / stealth_adaptive) and renders a single PNG showing:

- Per-family mean episode reward (Random vs Heuristic), with error bars.
- A "lift" annotation showing how much the heuristic policy beats
  random in each family — i.e. the reward signal the GRPO trainer
  has to climb.

The PNG is saved as ``evidence_scenario_rewards.png`` at repo root.
The README references it as an honest reward-curve substitute when
no GPU run is available.

Run:
    python scripts/generate_training_evidence.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Make repo root importable (script is run as `python scripts/...`).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from immunoorg.environment import ImmunoOrgEnvironment  # noqa: E402
from immunoorg.models import (  # noqa: E402
    ActionType,
    DiagnosticAction,
    ImmunoAction,
    StrategicAction,
    TacticalAction,
)
from training.dataset_generator import DatasetConfig, DatasetGenerator  # noqa: E402
from training.scenario_hooks import (  # noqa: E402
    apply_scenario_hooks,
    attach_hooks,
    training_step_penalty,
)


# ─── Policies ─────────────────────────────────────────────────────────────────


def random_policy(rng, obs, env):
    import random as _r
    rng_ = _r.Random(rng)
    atype = rng_.choice([ActionType.TACTICAL, ActionType.STRATEGIC, ActionType.DIAGNOSTIC])
    target = obs.visible_nodes[0].id if obs.visible_nodes else ""
    if atype == ActionType.TACTICAL:
        return ImmunoAction(
            action_type=atype,
            tactical_action=rng_.choice(list(TacticalAction)),
            target=target,
            reasoning="random",
        )
    if atype == ActionType.STRATEGIC:
        return ImmunoAction(
            action_type=atype,
            strategic_action=rng_.choice(list(StrategicAction)),
            target="dept-security",
            reasoning="random",
        )
    return ImmunoAction(
        action_type=atype,
        diagnostic_action=rng_.choice(list(DiagnosticAction)),
        reasoning="random",
    )


def heuristic_policy(_rng, obs, env):
    """Phase-aware heuristic that exercises the right "winning-tier" feature
    for each scenario family (RAG forensics, no-isolate alignment, etc.)."""
    phase = obs.current_phase.value
    nodes = obs.visible_nodes
    compromised = [n for n in nodes if n.compromised and not n.isolated]
    hooks = getattr(env, "_active_scenario_hooks", {}) or {}

    # RAG-grounding family: prefer SNAPSHOT_FORENSICS -> DEPLOY_PATCH chain.
    if hooks.get("inject_rag_best_mitigation") and phase in ("detection", "containment"):
        if compromised:
            return ImmunoAction(
                action_type=ActionType.TACTICAL,
                tactical_action=TacticalAction.SNAPSHOT_FORENSICS,
                target=compromised[0].id,
                reasoning="RAG: capture forensic snapshot before patching the rootkit.",
            )

    # Executive alignment: never isolate; deploy IDS / patches instead.
    if hooks.get("board_uptime_no_isolate") and phase == "containment":
        target = compromised[0].id if compromised else (nodes[0].id if nodes else "")
        return ImmunoAction(
            action_type=ActionType.TACTICAL,
            tactical_action=TacticalAction.DEPLOY_PATCH,
            target=target,
            reasoning="Board uptime directive: patch instead of isolating.",
        )

    # Silo-breaker: stop trying to isolate; do org refactor.
    if hooks.get("force_denials_on_isolate") and phase in ("containment", "rca", "refactor"):
        return ImmunoAction(
            action_type=ActionType.STRATEGIC,
            strategic_action=StrategicAction.ESTABLISH_DEVSECOPS,
            target="dept-security",
            secondary_target="dept-engineering",
            reasoning="Approver keeps denying; restructure org to remove the bottleneck.",
        )

    # Stealth: prefer multi-step investigation (vuln scan + trace).
    if hooks.get("stealthy_initial_attack") and phase == "detection":
        return ImmunoAction(
            action_type=ActionType.DIAGNOSTIC,
            diagnostic_action=DiagnosticAction.VULNERABILITY_SCAN,
            reasoning="Stealth attack: deeper scan before tactical action.",
        )

    # Default phase-appropriate heuristic.
    if phase == "detection":
        target = compromised[0].id if compromised else (nodes[0].id if nodes else "")
        return ImmunoAction(
            action_type=ActionType.TACTICAL,
            tactical_action=TacticalAction.SCAN_LOGS,
            target=target,
            reasoning="Detection: scan for indicators.",
        )
    if phase == "containment":
        if compromised:
            return ImmunoAction(
                action_type=ActionType.TACTICAL,
                tactical_action=TacticalAction.ISOLATE_NODE,
                target=compromised[0].id,
                reasoning="Isolate the compromised node.",
            )
        return ImmunoAction(
            action_type=ActionType.DIAGNOSTIC,
            diagnostic_action=DiagnosticAction.TIMELINE_RECONSTRUCT,
            reasoning="Reconstruct timeline.",
        )
    if phase == "rca":
        return ImmunoAction(
            action_type=ActionType.DIAGNOSTIC,
            diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
            reasoning="Find the org silo behind the failure.",
        )
    if phase == "refactor":
        return ImmunoAction(
            action_type=ActionType.STRATEGIC,
            strategic_action=StrategicAction.REDUCE_BUREAUCRACY,
            target="dept-management",
            reasoning="Reduce approval latency.",
        )
    return ImmunoAction(
        action_type=ActionType.DIAGNOSTIC,
        diagnostic_action=DiagnosticAction.MEASURE_ORG_LATENCY,
        reasoning="Validate org improvements.",
    )


# ─── Scenario rollouts ────────────────────────────────────────────────────────


def run_scenario(scenario, policy_fn, max_steps=60):
    env = ImmunoOrgEnvironment(
        difficulty=int(scenario["difficulty"]),
        seed=int(scenario["seed"]),
    )
    hooks = scenario.get("hooks") or {}
    attach_hooks(env, hooks)
    obs = env.reset()
    apply_scenario_hooks(env, hooks)

    total_reward = 0.0
    for step in range(min(max_steps, env.state.max_steps)):
        action = policy_fn(scenario["seed"] + step, obs, env)
        obs, reward, done = env.step(action)
        total_reward += float(reward) + float(training_step_penalty(env, action))
        if done:
            break
    return total_reward


def main():
    print("Generating elite scenario mix (50 scenarios = 10 per family)...")
    gen = DatasetGenerator(
        DatasetConfig(
            dataset_type="elite",
            output_dir="training_runs/_evidence",
            verbose=False,
            compress_output=False,
        )
    )
    scenarios = gen.generate_elite_scenario_mix_dataset(total=50)

    families = [
        "basic_containment",
        "rag_grounding",
        "executive_alignment",
        "silo_breaker",
        "stealth_adaptive",
    ]
    by_family = {f: [s for s in scenarios if s["family"] == f] for f in families}

    rewards = {pol: {f: [] for f in families} for pol in ("random", "heuristic")}

    for fam, scs in by_family.items():
        print(f"\n--- {fam} ({len(scs)} scenarios) ---")
        for sc in scs:
            r_rand = run_scenario(sc, random_policy)
            r_heur = run_scenario(sc, heuristic_policy)
            rewards["random"][fam].append(r_rand)
            rewards["heuristic"][fam].append(r_heur)
        print(
            f"  random   mean={mean(rewards['random'][fam]):+.2f} ± {stdev(rewards['random'][fam]):.2f}"
        )
        print(
            f"  heuristic mean={mean(rewards['heuristic'][fam]):+.2f} ± {stdev(rewards['heuristic'][fam]):.2f}"
        )

    # ─── Plot ─────────────────────────────────────────────────────────────
    DARK_BG, CARD_BG = "#0d1117", "#161b22"
    TEXT, GRID = "#c9d1d9", "#30363d"
    COLOR_RAND, COLOR_HEUR = "#f78166", "#3fb950"

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(CARD_BG)

    x = list(range(len(families)))
    width = 0.36

    rand_means = [mean(rewards["random"][f]) for f in families]
    rand_stds = [stdev(rewards["random"][f]) for f in families]
    heur_means = [mean(rewards["heuristic"][f]) for f in families]
    heur_stds = [stdev(rewards["heuristic"][f]) for f in families]

    bars1 = ax.bar(
        [i - width / 2 for i in x],
        rand_means,
        width,
        yerr=rand_stds,
        capsize=4,
        color=COLOR_RAND,
        alpha=0.85,
        label="Random policy (untrained baseline)",
        edgecolor="white",
        linewidth=0.6,
    )
    bars2 = ax.bar(
        [i + width / 2 for i in x],
        heur_means,
        width,
        yerr=heur_stds,
        capsize=4,
        color=COLOR_HEUR,
        alpha=0.85,
        label="Heuristic policy (gold standard target for GRPO)",
        edgecolor="white",
        linewidth=0.6,
    )

    # Lift annotations
    for i, fam in enumerate(families):
        lift = heur_means[i] - rand_means[i]
        y_top = max(heur_means[i] + heur_stds[i], rand_means[i] + rand_stds[i]) + 0.4
        ax.annotate(
            f"+{lift:.2f}" if lift >= 0 else f"{lift:.2f}",
            xy=(i, y_top),
            ha="center",
            color=COLOR_HEUR if lift >= 0 else COLOR_RAND,
            fontsize=10,
            fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f.replace("_", "\n") for f in families], color=TEXT, fontsize=9
    )
    ax.set_ylabel("mean episode reward (over 10 scenarios)", color=TEXT, fontsize=10)
    ax.set_title(
        "Reward signal across the 5 elite scenarios\n"
        "(each pair shows the lift the GRPO trainer has to climb)",
        color=TEXT,
        fontsize=12,
    )
    ax.tick_params(colors=TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.grid(True, color=GRID, linewidth=0.6, linestyle="--", alpha=0.6, axis="y")
    leg = ax.legend(loc="lower right", fontsize=9)
    for txt in leg.get_texts():
        txt.set_color(TEXT)
    leg.get_frame().set_facecolor(CARD_BG)
    leg.get_frame().set_edgecolor(GRID)

    plt.tight_layout()
    out = REPO_ROOT / "evidence_scenario_rewards.png"
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=DARK_BG)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
