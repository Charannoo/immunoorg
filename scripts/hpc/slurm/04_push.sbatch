#!/usr/bin/env bash
#SBATCH --job-name=immunoorg-stage4-push
#SBATCH --output=logs/stage4-%j.out
#SBATCH --error=logs/stage4-%j.err
#SBATCH --partition=cpu
#SBATCH --time=00:20:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --nodes=1
#SBATCH --ntasks=1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — push everything to the HF Hub (CPU only)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
REPO_ROOT="${REPO_ROOT:-$PWD}"
cd "$REPO_ROOT"
mkdir -p logs

echo "===================================================================="
echo "  Stage 4 — push  (job $SLURM_JOB_ID, node $(hostname))"
echo "===================================================================="

source .venv-hpc/bin/activate
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

python scripts/hpc/pipeline/04_push_artifacts.py
