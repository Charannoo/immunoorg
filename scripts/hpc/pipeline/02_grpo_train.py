#!/usr/bin/env python3
"""
Stage 2 — GRPO training
=======================

Loads the SFT-warm-started LoRA adapter from stage 01 (or the base
model directly if SFT was skipped), then runs full GRPO training on
the elite-scenario prompt set built in stage 00.

Multi-GPU note: TRL's GRPOTrainer auto-shards via Accelerate when
launched with `accelerate launch` or `torchrun`. The SLURM script
slurm/02_grpo.sbatch handles that — invoke this script via that
sbatch file rather than `python` directly when you want multi-GPU.

Output:
    outputs/grpo-defender/        LoRA adapter
    outputs/grpo-defender/grpo_log.json
    evidence_grpo_training.png    loss + per-reward curves (repo root)

Env overrides:
    IMMUNOORG_MODEL              default Qwen/Qwen2.5-7B-Instruct
    IMMUNOORG_SFT_OUTPUT_DIR     default outputs/sft-warmstart  (used as start)
    IMMUNOORG_SKIP_SFT           if set, ignore the warmstart adapter
    IMMUNOORG_GRPO_OUTPUT_DIR    default outputs/grpo-defender
    IMMUNOORG_DATA_DIR           default outputs/datasets
    IMMUNOORG_GRPO_EPOCHS        default 1
    IMMUNOORG_GRPO_BATCH_SIZE    default 4
    IMMUNOORG_GRPO_NUM_GENERATIONS  default 4
    IMMUNOORG_GRPO_MAX_COMPLETION   default 384
    IMMUNOORG_GRPO_LR            default 5e-6
    IMMUNOORG_GRPO_MAX_PROMPTS   default 0  (0 = use all)
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

MODEL_ID = os.environ.get("IMMUNOORG_MODEL", "Qwen/Qwen2.5-7B-Instruct")
SFT_DIR = Path(os.environ.get("IMMUNOORG_SFT_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "sft-warmstart")))
SKIP_SFT = bool(int(os.environ.get("IMMUNOORG_SKIP_SFT", "0")))
OUTPUT_DIR = Path(os.environ.get("IMMUNOORG_GRPO_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "grpo-defender")))
DATA_DIR = Path(os.environ.get("IMMUNOORG_DATA_DIR", str(REPO_ROOT / "outputs" / "datasets")))
EPOCHS = int(os.environ.get("IMMUNOORG_GRPO_EPOCHS", "1"))
BATCH_SIZE = int(os.environ.get("IMMUNOORG_GRPO_BATCH_SIZE", "4"))
NUM_GENERATIONS = int(os.environ.get("IMMUNOORG_GRPO_NUM_GENERATIONS", "4"))
MAX_COMPLETION = int(os.environ.get("IMMUNOORG_GRPO_MAX_COMPLETION", "384"))
LR = float(os.environ.get("IMMUNOORG_GRPO_LR", "5e-6"))
MAX_PROMPTS = int(os.environ.get("IMMUNOORG_GRPO_MAX_PROMPTS", "0"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def banner(msg: str) -> None:
    print()
    print("=" * 70)
    print(f"  {msg}")
    print("=" * 70)


def load_grpo_dataset():
    from datasets import Dataset

    path = DATA_DIR / "grpo_prompts.jsonl.gz"
    if not path.exists():
        raise FileNotFoundError(
            f"GRPO prompts not found at {path}. Run stage 0 first."
        )
    samples = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))
    if MAX_PROMPTS > 0:
        samples = samples[:MAX_PROMPTS]
    print(f"  loaded {len(samples)} GRPO prompts from {path}")
    families = sorted({s["family"] for s in samples})
    counts = {f: sum(1 for s in samples if s["family"] == f) for f in families}
    print(f"  family distribution: {counts}")
    return Dataset.from_list(samples)


def load_model_and_tokenizer():
    banner(f"[1/4] Loading model: {MODEL_ID}")
    print(f"  SFT warmstart: {SFT_DIR if (SFT_DIR / 'adapter_config.json').exists() and not SKIP_SFT else '(skipped)'}")

    use_unsloth = True
    try:
        from unsloth import FastLanguageModel
        from_path = str(SFT_DIR) if (SFT_DIR / "adapter_config.json").exists() and not SKIP_SFT else MODEL_ID
        model, tokenizer = FastLanguageModel.from_pretrained(
            from_path,
            max_seq_length=2048,
            load_in_4bit=True,
            dtype=None,
        )
        # If we loaded from MODEL_ID we still need to attach LoRA;
        # if we loaded from SFT_DIR the adapter is already attached.
        if from_path == MODEL_ID:
            model = FastLanguageModel.get_peft_model(
                model,
                r=16, lora_alpha=32,
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
                bias="none",
                use_gradient_checkpointing=True,
                random_state=42,
            )
        print("  Unsloth + 4-bit LoRA active.")
    except ImportError:
        use_unsloth = False
        import torch
        from peft import LoraConfig, PeftModel, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        device_map = "auto" if torch.cuda.is_available() else "cpu"
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            device_map=device_map,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
        if (SFT_DIR / "adapter_config.json").exists() and not SKIP_SFT:
            model = PeftModel.from_pretrained(base, str(SFT_DIR), is_trainable=True)
            print("  Loaded SFT adapter as starting point.")
        else:
            model = get_peft_model(
                base,
                LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", bias="none"),
            )
        print("  Plain transformers + peft active (no Unsloth).")

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


def train(model, tokenizer, dataset):
    banner(f"[2/4] GRPO training")
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
    n_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
    print(f"  cuda      : {torch.cuda.is_available()} (n_gpus={n_gpus})")
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

    print(f"  starting training for {EPOCHS} epoch(s) on {len(dataset)} prompts...")
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0
    print(f"  training finished in {elapsed/60:.1f} min")

    log_path = OUTPUT_DIR / "grpo_log.json"
    log_path.write_text(
        json.dumps(getattr(trainer.state, "log_history", []), indent=2),
        encoding="utf-8",
    )
    print(f"  trainer log -> {log_path}")

    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"  adapter   -> {OUTPUT_DIR}")
    return log_path


def plot_curves(log_path: Path) -> Path:
    banner(f"[3/4] Plotting reward + loss curves")
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
        print("  WARNING: empty log; skipping plot")
        return Path()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.8))
    fig.suptitle(
        f"GRPO training on ImmunoOrg 2.0 (model={MODEL_ID})",
        fontsize=12, fontweight="bold",
    )

    ax1.plot(steps, loss, color="#FF6B6B", linewidth=2, label="GRPO loss")
    ax1.set_xlabel("training step")
    ax1.set_ylabel("loss")
    ax1.set_title("Training loss")
    ax1.grid(alpha=0.3)
    ax1.legend()

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


def main() -> int:
    banner("ImmunoOrg 2.0 — Stage 2: GRPO training")
    print(f"  model           : {MODEL_ID}")
    print(f"  sft_warmstart   : {SFT_DIR if not SKIP_SFT else '(skipped)'}")
    print(f"  output_dir      : {OUTPUT_DIR}")
    print(f"  data_dir        : {DATA_DIR}")
    print(f"  epochs          : {EPOCHS}")
    print(f"  batch_size      : {BATCH_SIZE}")
    print(f"  num_generations : {NUM_GENERATIONS}")
    print(f"  max_completion  : {MAX_COMPLETION}")
    print(f"  lr              : {LR}")

    model, tokenizer = load_model_and_tokenizer()
    dataset = load_grpo_dataset()
    log_path = train(model, tokenizer, dataset)
    plot_curves(log_path)

    banner("DONE — Stage 2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
