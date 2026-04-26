# HPC training package

Turnkey scripts to run real GRPO training on an HPC GPU (typically 1× A100/H100)
and ship the results back as a Hugging Face model repo.

| File | What it does |
| --- | --- |
| [`HANDOFF.md`](./HANDOFF.md) | One-page copy-paste-ready instructions to send to whoever has the cluster. |
| [`setup_env.sh`](./setup_env.sh) | Login-node env setup with `uv` (no conda, no sudo). Creates `.venv-hpc`. |
| [`slurm_train.sbatch`](./slurm_train.sbatch) | SLURM batch script (1 GPU, 1 hr walltime). Submit with `sbatch`. |
| [`run_interactive.sh`](./run_interactive.sh) | Same but without SLURM (PBS/LSF, or interactive GPU shell). |
| [`train_full.py`](./train_full.py) | Python training driver — Unsloth + TRL GRPO + plot + HF push. |

## Quick reference

```bash
# Login node (one-time, ~5 min)
bash scripts/hpc/setup_env.sh

# Submit training (returns immediately)
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
sbatch scripts/hpc/slurm_train.sbatch

# Watch
squeue -u $USER
tail -f logs/grpo-*.out
```

When done, the run pushes:
- LoRA adapter (`adapter_model.safetensors`)
- `evidence_grpo_training.png`
- raw `grpo_log.json`

to `hirann/immunoorg-grpo-defender` on the HF Hub. Override the destination
with `export HF_PUSH_REPO=your-org/your-repo` before `sbatch`.

## Pulling results on the dev side

```bash
huggingface-cli download hirann/immunoorg-grpo-defender evidence_grpo_training.png \
    --local-dir . --local-dir-use-symlinks False

git add evidence_grpo_training.png
git commit -m "Add real GRPO loss + reward curves from HPC run"
git push origin master
```

That's the missing piece for the "Improvement in Rewards" judging criterion.

## Defaults you can override

| Env var | Default | Notes |
| --- | --- | --- |
| `IMMUNOORG_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | Smaller (3B/1.5B) for V100 32GB |
| `IMMUNOORG_NUM_PROMPTS` | `500` | Multiple of 5 keeps the elite mix balanced |
| `IMMUNOORG_EPOCHS` | `1` | 2 epochs ≈ 70 min on A100 |
| `IMMUNOORG_BATCH_SIZE` | `4` | Drop to 2 for V100 |
| `IMMUNOORG_NUM_GENERATIONS` | `4` | Must divide `BATCH_SIZE * gradient_accum` |
| `IMMUNOORG_MAX_COMPLETION` | `384` | 256 if you're memory-tight |
| `IMMUNOORG_LR` | `5e-6` | GRPO is sensitive to LR; 5e-6 is conservative |
| `HF_PUSH_REPO` | `hirann/immunoorg-grpo-defender` | Where the LoRA + PNG land |
| `HF_TOKEN` | _(none)_ | Required for the upload step |
