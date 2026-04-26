#!/usr/bin/env python3
"""
ImmunoOrg 2.0 — Full GRPO training driver (HPC version)
========================================================

Runs end-to-end on a single GPU (A100 / H100 / V100):

1. Load Qwen2.5-7B-Instruct in 4-bit + LoRA via Unsloth.
2. Build a 500-prompt training set from the elite scenario mix
   (20% each of basic / RAG / executive-alignment / silo-breaker / stealth).
3. Train with TRL GRPOTrainer using THREE independent verifiable rewards.
4. Save the trainer log, plot loss + per-reward curves -> evidence_grpo_training.png.
5. Save the LoRA adapter to outputs/immunoorg-defender/.
6. Push everything (adapter + PNG + log + auto-generated model card) to
   $HF_PUSH_REPO so the rest of the team can pull from one place.

Override defaults via env vars:
    IMMUNOORG_MODEL              default Qwen/Qwen2.5-7B-Instruct
    IMMUNOORG_NUM_PROMPTS        default 500
    IMMUNOORG_EPOCHS             default 1
    IMMUNOORG_BATCH_SIZE         default 4
    IMMUNOORG_NUM_GENERATIONS    default 4
    IMMUNOORG_MAX_COMPLETION     default 384
    IMMUNOORG_LR                 default 5e-6
    IMMUNOORG_OUTPUT_DIR         default outputs/immunoorg-defender
    HF_PUSH_REPO                 default hirann/immunoorg-grpo-defender
    HF_TOKEN                     required for the Hub push (job runs anyway if missing)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ── Config ───────────────────────────────────────────────────────────────────


MODEL_ID = os.environ.get("IMMUNOORG_MODEL", "Qwen/Qwen2.5-7B-Instruct")
NUM_PROMPTS = int(os.environ.get("IMMUNOORG_NUM_PROMPTS", "500"))
EPOCHS = int(os.environ.get("IMMUNOORG_EPOCHS", "1"))
BATCH_SIZE = int(os.environ.get("IMMUNOORG_BATCH_SIZE", "4"))
NUM_GENERATIONS = int(os.environ.get("IMMUNOORG_NUM_GENERATIONS", "4"))
MAX_COMPLETION = int(os.environ.get("IMMUNOORG_MAX_COMPLETION", "384"))
LR = float(os.environ.get("IMMUNOORG_LR", "5e-6"))
OUTPUT_DIR = Path(os.environ.get("IMMUNOORG_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "immunoorg-defender")))
PUSH_REPO = os.environ.get("HF_PUSH_REPO", "hirann/immunoorg-grpo-defender")
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip() or None

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def banner(msg: str) -> None:
    print()
    print("=" * 70)
    print(f"  {msg}")
    print("=" * 70)


# ── 1. Model load ────────────────────────────────────────────────────────────


def load_model_and_tokenizer():
    banner(f"[1/5] Loading model: {MODEL_ID}")

    try:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            MODEL_ID,
            max_seq_length=2048,
            load_in_4bit=True,
            dtype=None,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            lora_alpha=32,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            bias="none",
            use_gradient_checkpointing=True,
            random_state=42,
        )
        print("Unsloth + 4-bit LoRA active.")
    except ImportError:
        print("Unsloth not installed; falling back to plain transformers + peft.")
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        device_map = "auto" if torch.cuda.is_available() else "cpu"
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            device_map=device_map,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
        model = get_peft_model(
            model,
            LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", bias="none"),
        )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


# ── 2. Dataset (elite scenario mix) ──────────────────────────────────────────


def build_dataset():
    banner(f"[2/5] Building elite scenario dataset ({NUM_PROMPTS} prompts)")
    from datasets import Dataset

    from immunoorg.agents.defender import format_observation_for_llm, get_defender_prompt
    from immunoorg.environment import ImmunoOrgEnvironment
    from training.dataset_generator import DatasetConfig, DatasetGenerator
    from training.scenario_hooks import apply_scenario_hooks, attach_hooks

    # Round NUM_PROMPTS down to a multiple of 5 so the mix stays balanced.
    n = (NUM_PROMPTS // 5) * 5
    gen = DatasetGenerator(DatasetConfig(
        dataset_type="elite",
        output_dir=str(OUTPUT_DIR / "datasets"),
        verbose=False,
        compress_output=False,
    ))
    scenarios = gen.generate_elite_scenario_mix_dataset(total=n)

    system = get_defender_prompt()
    samples = []
    for sc in scenarios:
        try:
            env = ImmunoOrgEnvironment(
                difficulty=int(sc["difficulty"]),
                seed=int(sc["seed"]),
            )
            attach_hooks(env, sc.get("hooks") or {})
            obs = env.reset()
            apply_scenario_hooks(env, sc.get("hooks") or {})

            obs_text = format_observation_for_llm(obs.model_dump())
            prompt = (
                f"{system}\n\n"
                f"## Scenario family: {sc['family']}\n"
                f"## Current observation\n{obs_text}\n\n"
                f"Respond with a JSON action:"
            )
            samples.append({"prompt": prompt, "family": sc["family"]})
        except Exception as e:
            print(f"  skipped scenario {sc.get('scenario_id')}: {e}")
            continue

    dataset = Dataset.from_list(samples)
    families = sorted({s["family"] for s in samples})
    counts = {f: sum(1 for s in samples if s["family"] == f) for f in families}
    print(f"  built {len(dataset)} prompts across {len(families)} families: {counts}")
    return dataset


# ── 3. Train ─────────────────────────────────────────────────────────────────


def train(model, tokenizer, dataset):
    banner("[3/5] GRPO training")
    import torch
    from trl import GRPOConfig, GRPOTrainer

    from training.train_grpo import (
        format_reward,
        phase_appropriate_reward,
        reasoning_quality_reward,
    )

    on_cpu = not torch.cuda.is_available()
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    use_fp16 = torch.cuda.is_available() and not use_bf16
    print(f"  cuda      : {torch.cuda.is_available()}")
    print(f"  bf16/fp16 : {use_bf16} / {use_fp16}")

    grpo_kwargs = dict(
        output_dir=str(OUTPUT_DIR),
        num_generations=NUM_GENERATIONS,
        max_completion_length=MAX_COMPLETION,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=1,
        learning_rate=LR,
        num_train_epochs=EPOCHS,
        beta=0.04,
        logging_steps=1,
        save_steps=200,
        save_total_limit=1,
        report_to="none",
        warmup_ratio=0.05,
        max_grad_norm=1.0,
    )
    if on_cpu:
        grpo_kwargs.update(use_cpu=True, bf16=False, fp16=False)
    else:
        grpo_kwargs.update(bf16=use_bf16, fp16=use_fp16)

    config = GRPOConfig(**grpo_kwargs)

    trainer_kwargs = dict(
        model=model,
        reward_funcs=[
            format_reward,
            reasoning_quality_reward,
            phase_appropriate_reward,
        ],
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    try:
        trainer = GRPOTrainer(args=config, **trainer_kwargs)
    except TypeError:
        trainer = GRPOTrainer(config=config, **trainer_kwargs)

    print(f"  starting training for {EPOCHS} epoch(s)...")
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0
    print(f"  training finished in {elapsed/60:.1f} min")

    # Persist trainer state for plotting + push.
    log_path = OUTPUT_DIR / "grpo_log.json"
    log_path.write_text(
        json.dumps(getattr(trainer.state, "log_history", []), indent=2),
        encoding="utf-8",
    )
    print(f"  trainer log -> {log_path}")

    # Save the LoRA adapter (NOT the full upcast — that's the hackathon
    # warning #16: "do not upcast 4-bit -> 16-bit and naively merge LoRA").
    adapter_dir = OUTPUT_DIR
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"  adapter   -> {adapter_dir}")

    return log_path


# ── 4. Plot ─────────────────────────────────────────────────────────────────


def plot_curves(log_path: Path) -> Path:
    banner("[4/5] Plotting reward + loss curves")
    log = json.loads(log_path.read_text(encoding="utf-8"))

    steps, loss, reward_total = [], [], []
    reward_cols = {
        "rewards/format_reward": [],
        "rewards/reasoning_quality_reward": [],
        "rewards/phase_appropriate_reward": [],
    }
    for r in log:
        if "step" not in r:
            continue
        steps.append(r["step"])
        loss.append(r.get("loss"))
        reward_total.append(r.get("reward"))
        for k in reward_cols:
            reward_cols[k].append(r.get(k))

    if not steps:
        print("  WARNING: no logged steps; skipping plot")
        return Path()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.8))
    fig.suptitle(
        f"GRPO training on ImmunoOrg 2.0 (model={MODEL_ID})",
        fontsize=12, fontweight="bold",
    )

    # Loss
    ax1.plot(steps, loss, color="#FF6B6B", linewidth=2, label="GRPO loss")
    ax1.set_xlabel("training step")
    ax1.set_ylabel("loss")
    ax1.set_title("Training loss")
    ax1.grid(alpha=0.3)
    ax1.legend()

    # Rewards
    ax2.plot(steps, reward_total, color="#4ECDC4", linewidth=2.5, label="total reward")
    palette = {
        "rewards/format_reward": "#FFD166",
        "rewards/reasoning_quality_reward": "#A78BFA",
        "rewards/phase_appropriate_reward": "#3FB950",
    }
    for k, vals in reward_cols.items():
        if any(v is not None for v in vals):
            ax2.plot(steps, vals, linewidth=1.4, alpha=0.85, color=palette[k],
                     label=k.split("/")[-1])
    ax2.set_xlabel("training step")
    ax2.set_ylabel("reward")
    ax2.set_title("Reward curves (3 verifiable signals)")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=8, loc="lower right")

    plt.tight_layout()
    out = REPO_ROOT / "evidence_grpo_training.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  saved -> {out}")
    return out


# ── 5. Push to HF Hub ────────────────────────────────────────────────────────


def push_to_hub(adapter_dir: Path, log_path: Path, png_path: Path) -> None:
    banner(f"[5/5] Push to HF Hub: {PUSH_REPO}")

    if not HF_TOKEN:
        print("  HF_TOKEN missing; skipping upload. Files are still on disk:")
        print(f"    adapter : {adapter_dir}")
        print(f"    log     : {log_path}")
        print(f"    png     : {png_path}")
        return

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=HF_TOKEN)
    create_repo(
        repo_id=PUSH_REPO,
        repo_type="model",
        token=HF_TOKEN,
        exist_ok=True,
    )

    # Auto-generate a model card.
    card = f"""---
license: apache-2.0
library_name: peft
base_model: {MODEL_ID}
tags:
  - reinforcement-learning
  - grpo
  - openenv
  - cybersecurity
  - immunoorg
---

# ImmunoOrg 2.0 — GRPO defender (LoRA)

LoRA adapter trained with GRPO (TRL) against the
[ImmunoOrg 2.0](https://huggingface.co/spaces/hirann/immunoorg-v3) OpenEnv
environment for the OpenEnv Hackathon (India 2026).

- **Base model**: `{MODEL_ID}`
- **Algorithm**: GRPO (TRL) with 3 independent verifiable reward functions
  (`format_reward`, `reasoning_quality_reward`, `phase_appropriate_reward`).
- **Training data**: 20% / 20% / 20% / 20% / 20% mix of the 5 elite
  conflict scenarios (basic containment, RAG-grounding, executive
  alignment, silo-breaker, stealth-adaptive).
- **Reward curves**: see `evidence_grpo_training.png` in this repo.

## Files

- `adapter_config.json`, `adapter_model.safetensors` — the LoRA weights
- `evidence_grpo_training.png` — loss + per-reward curves (judge evidence)
- `grpo_log.json` — raw `trainer.state.log_history` for reproducibility

## Reproduce

```bash
git clone https://github.com/Charannoo/immunoorg.git
cd immunoorg
bash scripts/hpc/setup_env.sh
sbatch scripts/hpc/slurm_train.sbatch
```
"""
    (adapter_dir / "README.md").write_text(card, encoding="utf-8")

    print("  uploading adapter folder...")
    api.upload_folder(
        folder_path=str(adapter_dir),
        repo_id=PUSH_REPO,
        repo_type="model",
        commit_message="GRPO training run from HPC",
    )

    if png_path.exists():
        print("  uploading evidence_grpo_training.png...")
        api.upload_file(
            path_or_fileobj=str(png_path),
            path_in_repo="evidence_grpo_training.png",
            repo_id=PUSH_REPO,
            repo_type="model",
            commit_message="add GRPO loss + reward curves",
        )

    if log_path.exists():
        print("  uploading grpo_log.json...")
        api.upload_file(
            path_or_fileobj=str(log_path),
            path_in_repo="grpo_log.json",
            repo_id=PUSH_REPO,
            repo_type="model",
            commit_message="add raw trainer log",
        )

    print()
    print("  ALL UPLOADED.")
    print(f"  pull on the other side with:")
    print(f"    huggingface-cli download {PUSH_REPO} evidence_grpo_training.png")
    print(f"    huggingface-cli download {PUSH_REPO}")
    print()


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    banner("ImmunoOrg 2.0 GRPO training (HPC driver)")
    print(f"  model           : {MODEL_ID}")
    print(f"  prompts         : {NUM_PROMPTS}")
    print(f"  epochs          : {EPOCHS}")
    print(f"  batch_size      : {BATCH_SIZE}")
    print(f"  num_generations : {NUM_GENERATIONS}")
    print(f"  max_completion  : {MAX_COMPLETION}")
    print(f"  lr              : {LR}")
    print(f"  output_dir      : {OUTPUT_DIR}")
    print(f"  push_repo       : {PUSH_REPO}")
    print(f"  HF_TOKEN set    : {bool(HF_TOKEN)}")

    model, tokenizer = load_model_and_tokenizer()
    dataset = build_dataset()
    log_path = train(model, tokenizer, dataset)
    png_path = plot_curves(log_path)
    push_to_hub(OUTPUT_DIR, log_path, png_path)

    banner("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
