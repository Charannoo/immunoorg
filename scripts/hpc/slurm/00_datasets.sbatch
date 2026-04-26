#!/usr/bin/env bash
#SBATCH --job-name=immunoorg-stage0-data
#SBATCH --output=logs/stage0-%j.out
#SBATCH --error=logs/stage0-%j.err
#SBATCH --partition=cpu
#SBATCH --time=00:45:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8
#SBATCH --nodes=1
#SBATCH --ntasks=1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 0 — dataset generation (CPU only, ~20-30 min)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
REPO_ROOT="${REPO_ROOT:-$PWD}"
cd "$REPO_ROOT"
mkdir -p logs outputs

echo "===================================================================="
echo "  Stage 0 — datasets  (job $SLURM_JOB_ID, node $(hostname))"
echo "===================================================================="

source .venv-hpc/bin/activate
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export HF_DATASET_REPO="${HF_DATASET_REPO:-hirann/immunoorg-grpo-dataset}"

python scripts/hpc/pipeline/00_generate_datasets.py
