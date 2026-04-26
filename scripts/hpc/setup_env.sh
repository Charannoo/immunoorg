#!/usr/bin/env bash
# ImmunoOrg HPC env setup
# =======================
# Installs Python deps for GRPO training on a SLURM-allocated GPU node.
# Uses `uv` (10x faster than pip, single-file install, no conda needed).
#
# Run once on the *login node* (not inside the SLURM job).
# Idempotent: re-running just verifies the env.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "===================================================================="
echo "  ImmunoOrg 2.0 HPC env setup"
echo "  Repo: $REPO_ROOT"
echo "===================================================================="

# ── 1. Install `uv` if missing (no sudo, drops binary into ~/.local/bin) ──
if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "[1/4] installing uv (single static binary, ~10s)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
echo "[1/4] uv: $(uv --version)"

# ── 2. Try to load a recent CUDA module if the cluster uses Lmod ──
echo
echo "[2/4] looking for CUDA module..."
if command -v module >/dev/null 2>&1; then
    module purge 2>/dev/null || true
    # Try common CUDA modules in priority order
    for mod in "cuda/12.4" "cuda/12.1" "cuda/12.0" "cuda/11.8" "cuda" "CUDA"; do
        if module load "$mod" 2>/dev/null; then
            echo "    loaded: $mod"
            break
        fi
    done
    nvcc --version 2>/dev/null || echo "    (no nvcc on login node — that's fine, GPU node will have it)"
else
    echo "    (no Lmod / module command — assuming system CUDA)"
fi

# ── 3. Create a venv pinned to Python 3.11 (needed for PEP 604 unions) ──
echo
echo "[3/4] creating venv at .venv-hpc with Python 3.11..."
if [ ! -d ".venv-hpc" ]; then
    uv venv --python 3.11 .venv-hpc
fi
# shellcheck disable=SC1091
source .venv-hpc/bin/activate
python -V

# ── 4. Install training stack ──
echo
echo "[4/4] installing GRPO training stack (~3-5 min)..."
# Use uv pip for the install — much faster than plain pip and resolves cleanly.
uv pip install --upgrade pip wheel setuptools

# Pinned versions known to work together as of April 2026:
#  - torch 2.4 / cu121 (broadest cluster compat — A100/H100/V100 all OK)
#  - trl 0.15.x (the version the repo was developed against)
#  - unsloth latest (single-GPU 2-3x speedup for <13B models)
uv pip install --no-cache \
    "torch==2.4.*" \
    "transformers>=4.45,<5.0" \
    "trl>=0.15.0,<1.0" \
    "datasets>=2.19" \
    "accelerate>=0.30" \
    "peft>=0.11" \
    "bitsandbytes>=0.43" \
    "sentencepiece" \
    "safetensors" \
    "huggingface_hub>=0.24" \
    "matplotlib>=3.7" \
    "numpy<2.0" \
    "pandas" \
    "fastapi" \
    "uvicorn[standard]" \
    "pydantic>=2.6" \
    "networkx>=3.2" \
    "pyyaml" \
    "rich"

# Unsloth pulls in xformers / triton; install last so it picks the matching torch.
uv pip install --no-cache "unsloth"

echo
echo "===================================================================="
echo "  ENV READY"
echo "===================================================================="
echo "  activate with:  source $REPO_ROOT/.venv-hpc/bin/activate"
echo "  next step    :  sbatch scripts/hpc/slurm_train.sbatch"
echo "===================================================================="
