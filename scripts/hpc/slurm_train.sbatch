#!/usr/bin/env bash
#SBATCH --job-name=immunoorg-grpo
#SBATCH --output=logs/grpo-%j.out
#SBATCH --error=logs/grpo-%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --nodes=1
#SBATCH --ntasks=1
# ─────────────────────────────────────────────────────────────────────────────
# ImmunoOrg 2.0 GRPO training job
#
# Submit with:    sbatch scripts/hpc/slurm_train.sbatch
# Watch with:     squeue -u $USER  &&  tail -f logs/grpo-*.out
#
# Override the partition/GPU at submit time without editing this file:
#   sbatch --partition=h100 --gres=gpu:h100:1 scripts/hpc/slurm_train.sbatch
#
# Override training params via env vars before sbatch:
#   export IMMUNOORG_MODEL="Qwen/Qwen2.5-3B-Instruct"
#   export IMMUNOORG_NUM_PROMPTS=200
#   export IMMUNOORG_EPOCHS=2
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$(scontrol show job "$SLURM_JOB_ID" | grep -oP 'Command=\K[^ ]+')")/../.." 2>/dev/null && pwd)" || REPO_ROOT="$PWD"
cd "$REPO_ROOT"
mkdir -p logs outputs

echo "===================================================================="
echo "  ImmunoOrg 2.0 GRPO training (SLURM job $SLURM_JOB_ID)"
echo "  Node     : $(hostname)"
echo "  GPU      : $CUDA_VISIBLE_DEVICES"
echo "  Started  : $(date -Iseconds)"
echo "  Repo     : $REPO_ROOT"
echo "===================================================================="

# Re-load the CUDA module inside the job allocation
if command -v module >/dev/null 2>&1; then
    module purge 2>/dev/null || true
    for mod in "cuda/12.4" "cuda/12.1" "cuda/12.0" "cuda/11.8" "cuda" "CUDA"; do
        if module load "$mod" 2>/dev/null; then
            echo "loaded module: $mod"
            break
        fi
    done
fi

# Activate env (created by scripts/hpc/setup_env.sh)
if [ ! -d ".venv-hpc" ]; then
    echo "ERROR: .venv-hpc not found. Run 'bash scripts/hpc/setup_env.sh' on the login node first."
    exit 1
fi
# shellcheck disable=SC1091
source .venv-hpc/bin/activate
python -V
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv

# Sanity check token (job will still run if missing — just won't push results)
if [ -z "${HF_TOKEN:-}" ]; then
    echo "WARNING: HF_TOKEN not set — results will not be uploaded to the Hub."
    echo "         export HF_TOKEN=hf_... before sbatch to enable upload."
fi

# Run the training driver
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export HF_PUSH_REPO="${HF_PUSH_REPO:-hirann/immunoorg-grpo-defender}"

python scripts/hpc/train_full.py 2>&1

echo "===================================================================="
echo "  finished: $(date -Iseconds)"
echo "===================================================================="
