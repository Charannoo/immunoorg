#!/usr/bin/env bash
# Run training interactively on a GPU node (PBS / LSF / no scheduler).
# Equivalent to slurm_train.sbatch but without sbatch.
#
# Pre-req: you already have an interactive shell on a GPU node, the
#          venv is set up, and HF_TOKEN is exported.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
mkdir -p logs outputs

if [ ! -d ".venv-hpc" ]; then
    echo "ERROR: .venv-hpc not found. Run 'bash scripts/hpc/setup_env.sh' first."
    exit 1
fi
# shellcheck disable=SC1091
source .venv-hpc/bin/activate

if command -v module >/dev/null 2>&1; then
    for mod in "cuda/12.4" "cuda/12.1" "cuda/12.0" "cuda/11.8" "cuda" "CUDA"; do
        module load "$mod" 2>/dev/null && break
    done
fi

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export HF_PUSH_REPO="${HF_PUSH_REPO:-hirann/immunoorg-grpo-defender}"

nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv

LOG="logs/grpo-$(date +%Y%m%d-%H%M%S).out"
echo "logging to $LOG"
python scripts/hpc/train_full.py 2>&1 | tee "$LOG"
