#!/usr/bin/env python3
"""
Stage 3 — Evaluation: baseline vs trained, 100 episodes per agent
==================================================================

This stage produces the chart that judges actually compare against
on the "Improvement in Rewards" criterion: trained-LLM vs random-LLM
vs heuristic across the 5 elite scenario families.

What it does:
1. Loads three policies:
   - Random
   - Heuristic (the gold-standard reward target — same logic as stage 0)
   - Trained LLM (loads the GRPO LoRA from stage 02)
2. Runs each policy for N=20 episodes per scenario family (100 each).
3. Records cumulative reward, win rate (no active threats at end),
   time-to-containment, total downtime.
4. Plots two PNGs in repo root:
   - evidence_eval_per_family.png   bar chart per family per policy
   - evidence_eval_summary.png      overall mean reward + win rate
5. Saves raw results to outputs/evaluation_results.json so the
   numbers can be cited in the README.

Env overrides:
    IMMUNOORG_MODEL              default Qwen/Qwen2.5-7B-Instruct
    IMMUNOORG_GRPO_OUTPUT_DIR    default outputs/grpo-defender
    IMMUNOORG_EVAL_EPISODES_PER_FAMILY  default 20
    IMMUNOORG_EVAL_MAX_STEPS     default 60
    IMMUNOORG_EVAL_RESULTS_PATH  default outputs/evaluation_results.json
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from pathlib import Path
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

MODEL_ID = os.environ.get("IMMUNOORG_MODEL", "Qwen/Qwen2.5-7B-Instruct")
GRPO_DIR = Path(os.environ.get("IMMUNOORG_GRPO_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "grpo-defender")))
EPISODES_PER_FAMILY = int(os.environ.get("IMMUNOORG_EVAL_EPISODES_PER_FAMILY", "20"))
MAX_STEPS = int(os.environ.get("IMMUNOORG_EVAL_MAX_STEPS", "60"))
RESULTS_PATH = Path(os.environ.get("IMMUNOORG_EVAL_RESULTS_PATH", str(REPO_ROOT / "outputs" / "evaluation_results.json")))


def banner(msg: str) -> None:
    print()
    print("=" * 70)
    print(f"  {msg}")
    print("=" * 70)


# ── Policies ────────────────────────────────────────────────────────────────


def random_policy(env, obs, _rng_seed):
    from immunoorg.models import (
        ActionType,
        DiagnosticAction,
        ImmunoAction,
        StrategicAction,
        TacticalAction,
    )
    rng = random.Random(_rng_seed)
    atype = rng.choice([ActionType.TACTICAL, ActionType.STRATEGIC, ActionType.DIAGNOSTIC])
    target = obs.visible_nodes[0].id if obs.visible_nodes else ""
    if atype == ActionType.TACTICAL:
        return ImmunoAction(action_type=atype, tactical_action=rng.choice(list(TacticalAction)),
                            target=target, reasoning="random")
    if atype == ActionType.STRATEGIC:
        return ImmunoAction(action_type=atype, strategic_action=rng.choice(list(StrategicAction)),
                            target="dept-security", reasoning="random")
    return ImmunoAction(action_type=atype, diagnostic_action=rng.choice(list(DiagnosticAction)),
                        reasoning="random")


def heuristic_policy(env, obs, _rng_seed):
    """Same hook-aware heuristic as stage 0."""
    from immunoorg.models import (
        ActionType,
        DiagnosticAction,
        ImmunoAction,
        StrategicAction,
        TacticalAction,
    )

    phase = obs.current_phase.value
    nodes = obs.visible_nodes
    compromised = [n for n in nodes if n.compromised and not n.isolated]
    hooks = getattr(env, "_active_scenario_hooks", {}) or {}

    if hooks.get("inject_rag_best_mitigation") and phase in ("detection", "containment") and compromised:
        return ImmunoAction(action_type=ActionType.TACTICAL,
                            tactical_action=TacticalAction.SNAPSHOT_FORENSICS,
                            target=compromised[0].id, reasoning="RAG forensics")
    if hooks.get("board_uptime_no_isolate") and phase == "containment":
        target = compromised[0].id if compromised else (nodes[0].id if nodes else "")
        return ImmunoAction(action_type=ActionType.TACTICAL,
                            tactical_action=TacticalAction.DEPLOY_PATCH,
                            target=target, reasoning="board: patch")
    if hooks.get("force_denials_on_isolate") and phase in ("containment", "rca", "refactor"):
        return ImmunoAction(action_type=ActionType.STRATEGIC,
                            strategic_action=StrategicAction.ESTABLISH_DEVSECOPS,
                            target="dept-security", secondary_target="dept-engineering",
                            reasoning="silo bypass")
    if hooks.get("stealthy_initial_attack") and phase == "detection":
        return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                            diagnostic_action=DiagnosticAction.VULNERABILITY_SCAN,
                            reasoning="stealth: vuln scan")

    if phase == "detection":
        target = compromised[0].id if compromised else (nodes[0].id if nodes else "")
        return ImmunoAction(action_type=ActionType.TACTICAL,
                            tactical_action=TacticalAction.SCAN_LOGS,
                            target=target, reasoning="detect scan")
    if phase == "containment":
        if compromised:
            return ImmunoAction(action_type=ActionType.TACTICAL,
                                tactical_action=TacticalAction.ISOLATE_NODE,
                                target=compromised[0].id, reasoning="contain")
        return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                            diagnostic_action=DiagnosticAction.TIMELINE_RECONSTRUCT,
                            reasoning="timeline")
    if phase == "rca":
        return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                            diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
                            reasoning="silo")
    if phase == "refactor":
        return ImmunoAction(action_type=ActionType.STRATEGIC,
                            strategic_action=StrategicAction.REDUCE_BUREAUCRACY,
                            target="dept-management", reasoning="reduce")
    return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                        diagnostic_action=DiagnosticAction.MEASURE_ORG_LATENCY,
                        reasoning="validate")


class TrainedLLMPolicy:
    """Loads the GRPO LoRA from stage 02 and parses JSON actions."""

    def __init__(self, model_dir: Path):
        from immunoorg.agents.defender import format_observation_for_llm, get_defender_prompt
        self._format_obs = format_observation_for_llm
        self._sys_prompt = get_defender_prompt()

        try:
            from unsloth import FastLanguageModel
            model, tokenizer = FastLanguageModel.from_pretrained(
                str(model_dir),
                max_seq_length=2048,
                load_in_4bit=True,
            )
            FastLanguageModel.for_inference(model)
            print("  TrainedLLMPolicy: Unsloth inference mode active.")
        except ImportError:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            base = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                device_map="auto" if torch.cuda.is_available() else "cpu",
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            )
            model = PeftModel.from_pretrained(base, str(model_dir))
            model.eval()
            print("  TrainedLLMPolicy: plain transformers + peft active.")

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        self.model = model
        self.tokenizer = tokenizer

    def __call__(self, env, obs, _rng_seed):
        from immunoorg.models import (
            ActionType,
            DiagnosticAction,
            ImmunoAction,
            StrategicAction,
            TacticalAction,
        )

        obs_text = self._format_obs(obs.model_dump())
        prompt = (
            f"{self._sys_prompt}\n\n"
            f"## Current observation\n{obs_text}\n\n"
            f"Respond with a JSON action:"
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            chat = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
        except Exception:
            chat = prompt

        import torch
        inputs = self.tokenizer(chat, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=256, do_sample=True,
                temperature=0.7, top_p=0.9,
            )
        completion = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        # Parse first JSON object out of the completion.
        m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", completion)
        if not m:
            return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                                diagnostic_action=DiagnosticAction.QUERY_BELIEF_MAP,
                                reasoning="(parse fail) fallback")
        try:
            data = json.loads(m.group())
        except Exception:
            return ImmunoAction(action_type=ActionType.DIAGNOSTIC,
                                diagnostic_action=DiagnosticAction.QUERY_BELIEF_MAP,
                                reasoning="(json fail) fallback")

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


# ── Episode runner ──────────────────────────────────────────────────────────


def run_episode(env_factory, scenario, policy_fn, max_steps):
    from training.scenario_hooks import (
        apply_scenario_hooks,
        attach_hooks,
        training_step_penalty,
    )

    env = env_factory(scenario)
    hooks = scenario.get("hooks") or {}
    attach_hooks(env, hooks)
    obs = env.reset()
    apply_scenario_hooks(env, hooks)

    cum_reward = 0.0
    contained_step = None
    for step in range(min(max_steps, env.state.max_steps)):
        action = policy_fn(env, obs, scenario["seed"] + step)
        obs, reward, done = env.step(action)
        cum_reward += float(reward) + float(training_step_penalty(env, action))
        if contained_step is None and not env.attacks.get_active_attacks():
            contained_step = step
        if done:
            break

    win = len(env.attacks.get_active_attacks()) == 0
    return {
        "cumulative_reward": cum_reward,
        "win": bool(win),
        "time_to_containment": contained_step if contained_step is not None else max_steps,
        "downtime": env.state.total_downtime,
    }


def main() -> int:
    banner("ImmunoOrg 2.0 — Stage 3: Evaluation (baseline vs trained)")
    print(f"  model        : {MODEL_ID}")
    print(f"  grpo_dir     : {GRPO_DIR}")
    print(f"  eps/family   : {EPISODES_PER_FAMILY}")
    print(f"  max_steps    : {MAX_STEPS}")
    print(f"  results_path : {RESULTS_PATH}")

    from immunoorg.environment import ImmunoOrgEnvironment
    from training.dataset_generator import DatasetConfig, DatasetGenerator

    families = [
        "basic_containment",
        "rag_grounding",
        "executive_alignment",
        "silo_breaker",
        "stealth_adaptive",
    ]

    n_total = EPISODES_PER_FAMILY * len(families)
    gen = DatasetGenerator(DatasetConfig(
        dataset_type="elite",
        output_dir=str(REPO_ROOT / "outputs" / "_eval_tmp"),
        verbose=False,
        compress_output=False,
    ))
    scenarios = gen.generate_elite_scenario_mix_dataset(total=n_total)
    by_family = {f: [s for s in scenarios if s["family"] == f] for f in families}

    def env_factory(sc):
        return ImmunoOrgEnvironment(difficulty=int(sc["difficulty"]), seed=int(sc["seed"]))

    policies: dict[str, callable] = {
        "random": random_policy,
        "heuristic": heuristic_policy,
    }
    if (GRPO_DIR / "adapter_config.json").exists():
        banner(f"Loading trained LLM from {GRPO_DIR}")
        policies["trained_llm"] = TrainedLLMPolicy(GRPO_DIR)
    else:
        print(f"  WARNING: {GRPO_DIR}/adapter_config.json not found — skipping trained LLM eval.")

    results = {pol: {f: [] for f in families} for pol in policies}

    banner(f"Running {len(policies)} policies × {n_total} scenarios = {len(policies) * n_total} episodes")
    t0 = time.time()
    for pol_name, pol_fn in policies.items():
        print(f"\n  -- {pol_name} --")
        for fam in families:
            for sc in by_family[fam]:
                r = run_episode(env_factory, sc, pol_fn, MAX_STEPS)
                results[pol_name][fam].append(r)
            r_list = results[pol_name][fam]
            print(f"    {fam:22s}  reward={mean(r['cumulative_reward'] for r in r_list):+.2f} "
                  f"± {stdev(r['cumulative_reward'] for r in r_list):.2f}  "
                  f"win_rate={mean(r['win'] for r in r_list):.0%}")
    print(f"\n  total eval time: {(time.time() - t0)/60:.1f} min")

    # Persist raw results
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"  saved raw results -> {RESULTS_PATH}")

    # ── Plot 1: per-family bar chart ───────────────────────────────────
    DARK_BG, CARD_BG = "#0d1117", "#161b22"
    TEXT, GRID = "#c9d1d9", "#30363d"
    palette = {"random": "#f78166", "heuristic": "#3fb950", "trained_llm": "#58a6ff"}

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(CARD_BG)

    width = 0.8 / max(1, len(policies))
    x = list(range(len(families)))
    for i, (pol_name, _) in enumerate(policies.items()):
        means = [mean(r["cumulative_reward"] for r in results[pol_name][f]) for f in families]
        stds = [stdev(r["cumulative_reward"] for r in results[pol_name][f]) for f in families]
        offset = (i - (len(policies) - 1) / 2) * width
        ax.bar([xi + offset for xi in x], means, width, yerr=stds, capsize=4,
               color=palette.get(pol_name, "#888"), alpha=0.85, label=pol_name,
               edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([f.replace("_", "\n") for f in families], color=TEXT, fontsize=9)
    ax.set_ylabel(f"mean reward (over {EPISODES_PER_FAMILY} eps)", color=TEXT)
    ax.set_title("Per-scenario reward — baseline vs trained", color=TEXT, fontsize=12)
    ax.tick_params(colors=TEXT)
    for s in ax.spines.values():
        s.set_edgecolor(GRID)
    ax.grid(True, color=GRID, alpha=0.5, axis="y")
    leg = ax.legend()
    for t in leg.get_texts():
        t.set_color(TEXT)
    leg.get_frame().set_facecolor(CARD_BG)
    plt.tight_layout()
    out1 = REPO_ROOT / "evidence_eval_per_family.png"
    plt.savefig(out1, dpi=160, bbox_inches="tight", facecolor=DARK_BG)
    print(f"  saved -> {out1}")

    # ── Plot 2: overall summary ────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.patch.set_facecolor(DARK_BG)
    for ax in (ax1, ax2):
        ax.set_facecolor(CARD_BG)
        ax.tick_params(colors=TEXT)
        for s in ax.spines.values():
            s.set_edgecolor(GRID)
        ax.grid(True, color=GRID, alpha=0.5, axis="y")

    pol_names = list(policies.keys())
    overall_reward = [
        mean(r["cumulative_reward"]
             for f in families for r in results[p][f])
        for p in pol_names
    ]
    overall_win = [
        mean(r["win"]
             for f in families for r in results[p][f])
        for p in pol_names
    ]
    colors = [palette.get(p, "#888") for p in pol_names]

    ax1.bar(pol_names, overall_reward, color=colors, alpha=0.85,
            edgecolor="white", linewidth=0.5)
    ax1.set_ylabel("mean cumulative reward", color=TEXT)
    ax1.set_title(f"Overall reward (n={EPISODES_PER_FAMILY * len(families)} eps each)",
                  color=TEXT, fontsize=11)

    ax2.bar(pol_names, [w * 100 for w in overall_win], color=colors, alpha=0.85,
            edgecolor="white", linewidth=0.5)
    ax2.set_ylabel("win rate (%)", color=TEXT)
    ax2.set_title("Win rate (no active threats at end)", color=TEXT, fontsize=11)
    ax2.set_ylim(0, 105)

    plt.tight_layout()
    out2 = REPO_ROOT / "evidence_eval_summary.png"
    plt.savefig(out2, dpi=160, bbox_inches="tight", facecolor=DARK_BG)
    print(f"  saved -> {out2}")

    banner("DONE — Stage 3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
