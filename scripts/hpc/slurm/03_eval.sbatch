#!/usr/bin/env bash
#SBATCH --job-name=immunoorg-stage3-eval
#SBATCH --output=logs/stage3-%j.out
#SBATCH --error=logs/stage3-%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --time=00:45:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --nodes=1
#SBATCH --ntasks=1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — evaluation: random vs heuristic vs trained_llm, 100 episodes each
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
REPO_ROOT="${REPO_ROOT:-$PWD}"
cd "$REPO_ROOT"
mkdir -p logs outputs

echo "===================================================================="
echo "  Stage 3 — eval  (job $SLURM_JOB_ID, node $(hostname))"
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

python scripts/hpc/pipeline/03_evaluate.py
