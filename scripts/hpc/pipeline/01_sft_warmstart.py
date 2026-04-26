#!/usr/bin/env python3
"""
Stage 1 — SFT warm-start
========================

The hackathon guide explicitly recommends "a little SFT first, then RL"
(section #3). This stage trains the base model on the heuristic
trajectories from stage 0 so the model already speaks the env's JSON
action format before GRPO begins. That gives GRPO a non-zero starting
reward and dramatically reduces the number of GRPO steps needed.

Output: a LoRA adapter at outputs/sft-warmstart/ that stage 02
(GRPO) loads as its starting point.

Env overrides:
    IMMUNOORG_MODEL          default Qwen/Qwen2.5-7B-Instruct
    IMMUNOORG_DATA_DIR       default outputs/datasets
    IMMUNOORG_SFT_OUTPUT_DIR default outputs/sft-warmstart
    IMMUNOORG_SFT_EPOCHS     default 1
    IMMUNOORG_SFT_BATCH_SIZE default 4
    IMMUNOORG_SFT_LR         default 2e-4   (higher than GRPO; OK for SFT)
    IMMUNOORG_SFT_MAX_LEN    default 2048
    IMMUNOORG_SFT_MAX_SAMPLES  default 0    (0 = use all available)
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

MODEL_ID = os.environ.get("IMMUNOORG_MODEL", "Qwen/Qwen2.5-7B-Instruct")
DATA_DIR = Path(os.environ.get("IMMUNOORG_DATA_DIR", str(REPO_ROOT / "outputs" / "datasets")))
OUTPUT_DIR = Path(os.environ.get("IMMUNOORG_SFT_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "sft-warmstart")))
EPOCHS = int(os.environ.get("IMMUNOORG_SFT_EPOCHS", "1"))
BATCH_SIZE = int(os.environ.get("IMMUNOORG_SFT_BATCH_SIZE", "4"))
LR = float(os.environ.get("IMMUNOORG_SFT_LR", "2e-4"))
MAX_LEN = int(os.environ.get("IMMUNOORG_SFT_MAX_LEN", "2048"))
MAX_SAMPLES = int(os.environ.get("IMMUNOORG_SFT_MAX_SAMPLES", "0"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def banner(msg: str) -> None:
    print()
    print("=" * 70)
    print(f"  {msg}")
    print("=" * 70)


def load_sft_dataset():
    """Load (prompt, completion) pairs that stage 0 produced."""
    from datasets import Dataset

    path = DATA_DIR / "sft_warmstart.jsonl.gz"
    if not path.exists():
        raise FileNotFoundError(
            f"SFT data not found at {path}. Run stage 0 first."
        )

    samples = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))

    if MAX_SAMPLES > 0:
        samples = samples[:MAX_SAMPLES]
    print(f"  loaded {len(samples)} SFT samples from {path}")

    # TRL SFTTrainer expects a `text` column with the chat-formatted full
    # turn; we'll build it via the model's tokenizer chat template inside
    # main(). For now stash the raw fields.
    return Dataset.from_list(samples)


def main() -> int:
    banner("ImmunoOrg 2.0 — Stage 1: SFT warm-start")
    print(f"  model       : {MODEL_ID}")
    print(f"  data_dir    : {DATA_DIR}")
    print(f"  output_dir  : {OUTPUT_DIR}")
    print(f"  epochs      : {EPOCHS}")
    print(f"  batch_size  : {BATCH_SIZE}")
    print(f"  lr          : {LR}")
    print(f"  max_len     : {MAX_LEN}")

    raw = load_sft_dataset()

    banner("Loading model")
    import torch

    use_unsloth = True
    try:
        from unsloth import FastLanguageModel
        model, tokenizer = FastLanguageModel.from_pretrained(
            MODEL_ID,
            max_seq_length=MAX_LEN,
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
        print("  Unsloth + 4-bit LoRA loaded.")
    except ImportError:
        use_unsloth = False
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
        print("  Plain transformers + peft loaded (no Unsloth).")

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Convert (prompt, completion) -> text using the model's chat template.
    def to_text(example):
        msgs = [
            {"role": "user", "content": example["prompt"]},
            {"role": "assistant", "content": example["completion"]},
        ]
        return {"text": tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=False,
        )}

    dataset = raw.map(to_text, remove_columns=raw.column_names)
    print(f"  formatted dataset: {len(dataset)} rows")

    banner("Configuring SFTTrainer")
    from trl import SFTConfig, SFTTrainer

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    use_fp16 = torch.cuda.is_available() and not use_bf16
    on_cpu = not torch.cuda.is_available()

    sft_kwargs = dict(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=2,
        learning_rate=LR,
        warmup_ratio=0.05,
        logging_steps=5,
        save_steps=200,
        save_total_limit=1,
        max_grad_norm=1.0,
        report_to="none",
        max_length=MAX_LEN,
        dataset_text_field="text",
        packing=False,
    )
    if on_cpu:
        sft_kwargs.update(use_cpu=True, bf16=False, fp16=False)
    else:
        sft_kwargs.update(bf16=use_bf16, fp16=use_fp16)

    config = SFTConfig(**sft_kwargs)

    trainer_kwargs = dict(
        model=model,
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    try:
        trainer = SFTTrainer(args=config, **trainer_kwargs)
    except TypeError:
        trainer = SFTTrainer(config=config, **trainer_kwargs)

    banner(f"Training SFT for {EPOCHS} epoch(s) on {len(dataset)} samples")
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0
    print(f"  SFT done in {elapsed/60:.1f} min")

    banner(f"Saving adapter -> {OUTPUT_DIR}")
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    log_path = OUTPUT_DIR / "sft_log.json"
    log_path.write_text(
        json.dumps(getattr(trainer.state, "log_history", []), indent=2),
        encoding="utf-8",
    )
    print(f"  trainer log -> {log_path}")

    banner("DONE — Stage 1")
    print(f"  Stage 02 (GRPO) will load this adapter as its starting point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
