#!/usr/bin/env bash
# ImmunoOrg HPC env setup (4-stage pipeline edition)
# ===================================================
#
# Run ONCE on the *login node* (not inside a SLURM job).
# Idempotent: re-running just verifies the env exists.
#
# Installs:
#   - uv (single-binary Python package manager, no conda needed)
#   - Python 3.11 venv at .venv-hpc/
#   - PyTorch 2.4 + CUDA 12 wheels (broad cluster compat)
#   - TRL >= 0.15, transformers >= 4.45, peft, accelerate, datasets
#   - Unsloth (single-GPU 2-3x speedup for <13B)
#   - bitsandbytes (4-bit quantisation), safetensors, sentencepiece
#   - matplotlib, pyyaml, networkx, pydantic, fastapi (for env package)
#
# Optional flags:
#   --no-flash-attn   skip flash-attention install (some clusters lack the headers)
#   --no-deepspeed    skip deepspeed install (only matters for >2x GPU runs)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

INSTALL_FLASH_ATTN=1
INSTALL_DEEPSPEED=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-flash-attn) INSTALL_FLASH_ATTN=0; shift ;;
        --no-deepspeed)  INSTALL_DEEPSPEED=0; shift ;;
        -h|--help)       grep '^# ' "$0" | sed 's/^# //'; exit 0 ;;
        *) echo "unknown flag: $1"; exit 1 ;;
    esac
done

echo "===================================================================="
echo "  ImmunoOrg 2.0 HPC env setup (4-stage pipeline edition)"
echo "  Repo: $REPO_ROOT"
echo "===================================================================="

# ── 1. Install uv if missing (no sudo, single binary) ────────────────────
if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "[1/5] installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
echo "[1/5] uv: $(uv --version)"

# ── 2. Try to load CUDA + GCC modules if Lmod is present ────────────────
echo
echo "[2/5] looking for CUDA / GCC modules..."
if command -v module >/dev/null 2>&1; then
    module purge 2>/dev/null || true
    for mod in cuda/12.4 cuda/12.1 cuda/12.0 cuda/11.8 cuda CUDA; do
        if module load "$mod" 2>/dev/null; then echo "    loaded: $mod"; break; fi
    done
    for mod in gcc/11 gcc/10 gcc; do
        if module load "$mod" 2>/dev/null; then echo "    loaded: $mod"; break; fi
    done
    nvcc --version 2>/dev/null || echo "    (no nvcc on login node - GPU node will have it)"
else
    echo "    (no Lmod - assuming system CUDA / GCC)"
fi

# ── 3. Create venv ───────────────────────────────────────────────────────
echo
echo "[3/5] creating venv at .venv-hpc with Python 3.11..."
if [ ! -d ".venv-hpc" ]; then
    uv venv --python 3.11 .venv-hpc
fi
# shellcheck disable=SC1091
source .venv-hpc/bin/activate
python -V

# ── 4. Install training stack ────────────────────────────────────────────
echo
echo "[4/5] installing GRPO / SFT training stack (~5 min)..."
uv pip install --upgrade pip wheel setuptools

# Pinned baseline
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

# Unsloth (single-GPU speedup; pulls in xformers / triton matching torch)
uv pip install --no-cache "unsloth"

# Flash-attention 2 (optional; fails on some older clusters / non-Ampere GPUs)
if [ "$INSTALL_FLASH_ATTN" -eq 1 ]; then
    echo
    echo "    installing flash-attn (skip with --no-flash-attn if it fails)..."
    uv pip install --no-cache "flash-attn>=2.5" --no-build-isolation || \
        echo "    flash-attn install failed (not fatal — Unsloth has its own kernels)"
fi

# DeepSpeed for multi-GPU GRPO (optional; only used when --multigpu N > 1)
if [ "$INSTALL_DEEPSPEED" -eq 1 ]; then
    echo
    echo "    installing deepspeed (only used for multi-GPU runs)..."
    uv pip install --no-cache "deepspeed>=0.14" || \
        echo "    deepspeed install failed (not fatal — single-GPU still works)"
fi

# ── 5. Sanity check ──────────────────────────────────────────────────────
echo
echo "[5/5] sanity check..."
python - <<'PY'
import importlib
mods = ["torch", "transformers", "trl", "peft", "datasets", "accelerate", "bitsandbytes", "huggingface_hub"]
for m in mods:
    try:
        v = getattr(importlib.import_module(m), "__version__", "?")
        print(f"  {m:18s} {v}")
    except Exception as e:
        print(f"  {m:18s} FAILED ({e})")
try:
    import unsloth
    print(f"  unsloth            {unsloth.__version__}")
except Exception:
    print("  unsloth            (not installed - single-GPU will fall back to plain HF)")
PY

mkdir -p logs outputs

echo
echo "===================================================================="
echo "  ENV READY"
echo "===================================================================="
echo "  next:"
echo "    export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
echo "    bash scripts/hpc/run_all.sh"
echo "===================================================================="
