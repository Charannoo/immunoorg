#!/usr/bin/env bash
#SBATCH --job-name=immunoorg-stage2-grpo
#SBATCH --output=logs/stage2-%j.out
#SBATCH --error=logs/stage2-%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --ntasks=1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — GRPO training
#
# Single-GPU default. For multi-GPU, override at submit time:
#
#   sbatch --gres=gpu:4 --ntasks-per-node=4 scripts/hpc/slurm/02_grpo.sbatch
#
# When ntasks > 1 we launch via `accelerate launch` for data-parallel
# DDP. TRL's GRPOTrainer handles the rest.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
REPO_ROOT="${REPO_ROOT:-$PWD}"
cd "$REPO_ROOT"
mkdir -p logs outputs

echo "===================================================================="
echo "  Stage 2 — GRPO  (job $SLURM_JOB_ID, node $(hostname))"
echo "  GPUs requested: ${SLURM_GPUS:-${SLURM_GRES:-1}}"
echo "===================================================================="

if command -v module >/dev/null 2>&1; then
    for mod in cuda/12.4 cuda/12.1 cuda/12.0 cuda/11.8 cuda CUDA; do
        module load "$mod" 2>/dev/null && break
    done
fi

source .venv-hpc/bin/activate
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false

# Detect if multi-GPU was requested.
N_GPUS="$(nvidia-smi --list-gpus | wc -l)"
if [ "$N_GPUS" -gt 1 ]; then
    echo "  detected $N_GPUS GPUs — launching via accelerate"
    accelerate launch --num_processes "$N_GPUS" --mixed_precision bf16 \
        scripts/hpc/pipeline/02_grpo_train.py
else
    echo "  single GPU — launching directly"
    python scripts/hpc/pipeline/02_grpo_train.py
fi
