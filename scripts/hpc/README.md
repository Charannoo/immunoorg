# HPC training pipeline

Turnkey 4-stage pipeline for running real GRPO training (with optional SFT
warm-start) on an HPC cluster, then auto-pushing every artifact (model,
dataset, evidence PNGs, raw logs) to the Hugging Face Hub.

## Layout

```
scripts/hpc/
├── HANDOFF.md            ← copy-paste-ready instructions for the cluster operator
├── README.md             ← this file (reference for repo viewers)
├── setup_env.sh          ← login-node env setup (uv, no conda, no sudo)
├── run_all.sh            ← submit all 4 stages with SLURM dependencies
├── pipeline/
│   ├── 00_generate_datasets.py   stage 0 — datasets (CPU)
│   ├── 01_sft_warmstart.py       stage 1 — SFT warm-start (1 GPU)
│   ├── 02_grpo_train.py          stage 2 — GRPO training (1+ GPUs)
│   ├── 03_evaluate.py            stage 3 — eval baseline vs trained (1 GPU)
│   └── 04_push_artifacts.py      stage 4 — push to HF Hub (CPU)
└── slurm/
    ├── 00_datasets.sbatch
    ├── 01_sft.sbatch
    ├── 02_grpo.sbatch
    ├── 03_eval.sbatch
    └── 04_push.sbatch
```

## Quick reference

```bash
# One-time on login node
bash scripts/hpc/setup_env.sh

# Submit everything (returns immediately with 5 job IDs)
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
bash scripts/hpc/run_all.sh

# Watch
squeue -u $USER
tail -f logs/stage*-*.out

# Common overrides
bash scripts/hpc/run_all.sh --multigpu 4                    # data-parallel GRPO
bash scripts/hpc/run_all.sh --skip-sft                      # GRPO only
bash scripts/hpc/run_all.sh --partition gpu-a100            # custom partition
export IMMUNOORG_MODEL=Qwen/Qwen2.5-14B-Instruct            # bigger model
export HF_PUSH_REPO=your-org/your-defender-repo             # custom destination
```

## What the pipeline guarantees

- **Stage 0 → 1 → 2 → 3 → 4** runs in order via `--dependency=afterok:`.
  If any stage fails, downstream stages are cancelled automatically.
- **Idempotent**: re-running stages 1-4 reuses cached datasets / adapters.
- **Falls back gracefully**: no Unsloth → plain HF; no flash-attn → SDPA;
  no GPU → CPU mode (slow but works).
- **Auto-detects multi-GPU**: if SLURM gives stage 2 more than 1 GPU, it
  launches via `accelerate launch` for data-parallel GRPO.

## Reading the artifacts after a run

When stage 4 finishes:

| Artifact | Where to find it |
| --- | --- |
| Trained LoRA adapter | `https://huggingface.co/$HF_PUSH_REPO` |
| `evidence_grpo_training.png` | committed to the model repo, also in repo root on the cluster |
| `evidence_eval_*.png` | same |
| `evaluation_results.json` | model repo, full per-policy / per-family numbers |
| `grpo_log.json` | model repo, raw `trainer.state.log_history` |
| Training datasets | `https://huggingface.co/datasets/$HF_DATASET_REPO` |

To pull just the PNGs back to your dev machine:

```bash
huggingface-cli download $HF_PUSH_REPO evidence_grpo_training.png \
    evidence_eval_per_family.png evidence_eval_summary.png \
    --local-dir . --local-dir-use-symlinks False

git add evidence_*.png
git commit -m "evidence: add real GRPO + eval curves from HPC run"
git push origin master
```

That commit is what closes the "Improvement in Rewards" judging gap.

## Default training config (overridable per-stage)

| Stage | Model | Dataset | Time on 1× A100 |
| --- | --- | --- | ---: |
| 0 datasets | (CPU only) | builds 1700+ scenarios + 200 trajectories | ~25 min |
| 1 SFT | Qwen2.5-7B + LoRA r=16 | sft_warmstart.jsonl.gz (~2000 samples) | ~25 min |
| 2 GRPO | Qwen2.5-7B + LoRA (warm-started) | 500 elite-mix prompts × 4 generations | ~90-120 min |
| 3 eval | trained adapter | 100 episodes/family × 3 policies | ~30 min |
| 4 push | (CPU only) | adapter + 6+ PNGs + raw logs | ~10 min |

**Total: ~3-4 hours on a single A100. ~1-1.5 hours with `--multigpu 4`.**
