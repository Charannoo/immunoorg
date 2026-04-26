#!/usr/bin/env bash
# Submit the full ImmunoOrg HPC pipeline as a chain of SLURM jobs with
# `--dependency=afterok:` between stages. One command, then walk away.
#
# Usage:
#   export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#   bash scripts/hpc/run_all.sh                          # default settings
#   bash scripts/hpc/run_all.sh --skip-sft               # GRPO only (no warmstart)
#   bash scripts/hpc/run_all.sh --multigpu 4             # GRPO on 4 GPUs
#   bash scripts/hpc/run_all.sh --partition gpu-h100     # custom partition
#
# Pre-req: bash scripts/hpc/setup_env.sh has been run on the login node.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# ── Defaults (override via flags) ───────────────────────────────────────────
PARTITION="${IMMUNOORG_PARTITION:-gpu}"
PARTITION_CPU="${IMMUNOORG_PARTITION_CPU:-cpu}"
GPU_COUNT=1
SKIP_SFT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-sft)    SKIP_SFT=1; shift ;;
        --multigpu)    GPU_COUNT="$2"; shift 2 ;;
        --partition)   PARTITION="$2"; shift 2 ;;
        --partition-cpu) PARTITION_CPU="$2"; shift 2 ;;
        -h|--help)
            grep '^# ' "$0" | sed 's/^# //'
            exit 0 ;;
        *) echo "unknown flag: $1"; exit 1 ;;
    esac
done

if [ -z "${HF_TOKEN:-}" ]; then
    echo "WARNING: HF_TOKEN not set — datasets, model, and evidence will NOT be pushed to the Hub."
fi

mkdir -p logs

echo "===================================================================="
echo "  ImmunoOrg HPC pipeline submission"
echo "===================================================================="
echo "  partition (gpu) : $PARTITION"
echo "  partition (cpu) : $PARTITION_CPU"
echo "  GPUs / job       : $GPU_COUNT"
echo "  skip SFT?        : $SKIP_SFT"
echo "  HF_TOKEN set?    : ${HF_TOKEN:+yes}"
echo "===================================================================="
echo

# ── Stage 0: datasets (CPU) ─────────────────────────────────────────────────
JOB0=$(sbatch --parsable \
    --partition="$PARTITION_CPU" \
    --export=ALL,REPO_ROOT="$REPO_ROOT" \
    scripts/hpc/slurm/00_datasets.sbatch)
echo "[stage 0] datasets        -> job $JOB0  (partition=$PARTITION_CPU)"

# ── Stage 1: SFT (depends on stage 0) ───────────────────────────────────────
if [ "$SKIP_SFT" -eq 1 ]; then
    echo "[stage 1] SFT warmstart   -> SKIPPED"
    SFT_DEP=""
    JOB1=""
else
    JOB1=$(sbatch --parsable \
        --partition="$PARTITION" \
        --dependency=afterok:"$JOB0" \
        --export=ALL,REPO_ROOT="$REPO_ROOT" \
        scripts/hpc/slurm/01_sft.sbatch)
    echo "[stage 1] SFT warmstart   -> job $JOB1  (after $JOB0, partition=$PARTITION)"
    SFT_DEP=":$JOB1"
fi

# ── Stage 2: GRPO (depends on stage 0 + stage 1 if present) ────────────────
GRPO_DEP="afterok:$JOB0$SFT_DEP"
GRPO_GRES="gpu:$GPU_COUNT"
GRPO_NTASKS="$GPU_COUNT"

JOB2=$(sbatch --parsable \
    --partition="$PARTITION" \
    --dependency="$GRPO_DEP" \
    --gres="$GRPO_GRES" \
    --ntasks-per-node="$GRPO_NTASKS" \
    --export=ALL,REPO_ROOT="$REPO_ROOT",IMMUNOORG_SKIP_SFT="$SKIP_SFT" \
    scripts/hpc/slurm/02_grpo.sbatch)
echo "[stage 2] GRPO training   -> job $JOB2  (after $GRPO_DEP, $GRPO_GRES)"

# ── Stage 3: evaluation (depends on GRPO) ──────────────────────────────────
JOB3=$(sbatch --parsable \
    --partition="$PARTITION" \
    --dependency=afterok:"$JOB2" \
    --export=ALL,REPO_ROOT="$REPO_ROOT" \
    scripts/hpc/slurm/03_eval.sbatch)
echo "[stage 3] evaluation      -> job $JOB3  (after $JOB2)"

# ── Stage 4: push (depends on eval) ────────────────────────────────────────
JOB4=$(sbatch --parsable \
    --partition="$PARTITION_CPU" \
    --dependency=afterok:"$JOB3" \
    --export=ALL,REPO_ROOT="$REPO_ROOT" \
    scripts/hpc/slurm/04_push.sbatch)
echo "[stage 4] push artifacts  -> job $JOB4  (after $JOB3, partition=$PARTITION_CPU)"

echo
echo "===================================================================="
echo "  All 5 jobs submitted. Watch with:"
echo "    squeue -u \$USER"
echo "    tail -f logs/stage*-*.out"
echo "===================================================================="
echo
echo "When the chain finishes, results land at:"
echo "  https://huggingface.co/${HF_PUSH_REPO:-hirann/immunoorg-grpo-defender}"
echo "  https://huggingface.co/datasets/${HF_DATASET_REPO:-hirann/immunoorg-grpo-dataset}"
