# ImmunoOrg 2.0 — Supercomputer Run Handoff (4-stage pipeline)

Hi! Thanks for running this. The whole thing is **two commands** and the cluster
does the rest unattended. Total wall-clock: **~3-4 hours** for the full 4-stage
pipeline on a single A100/H100, or **~1-1.5 hours** if you skip SFT.

What the pipeline produces:
- A trained LoRA defender (Qwen2.5-7B by default, configurable up to 14B/32B)
- 6+ evidence PNG charts (loss curves, baseline-vs-trained comparisons)
- A reusable training dataset on the HF Hub
- All artifacts auto-pushed to my HF account

---

## What you'll need

- **HF write token** (sender will give you one, will look like `hf_xxx...`).
- **GPU**: A100 / H100 / V100 (32GB+). If you have multiple, even better.
- **SLURM** (most US clusters). PBS/Torque also works — see "Non-SLURM" below.
- **Internet on GPU node** for model download. Most clusters allow this. If not,
  see "Air-gapped" below.

---

## Steps (literal copy-paste)

```bash
# 1. Clone the repo (~3 sec)
git clone https://github.com/Charannoo/immunoorg.git
cd immunoorg

# 2. One-time env setup (~5-8 min, downloads PyTorch + Unsloth + TRL + flash-attn)
bash scripts/hpc/setup_env.sh

# 3. Export the HF token
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 4. Submit the entire 4-stage pipeline (returns immediately with 5 job IDs)
bash scripts/hpc/run_all.sh
```

That's it. SLURM will run all 4 stages in dependency order (each stage waits
for the previous via `--dependency=afterok:`). When stage 4 finishes, every
artifact is on the HF Hub and the sender can pull it from there.

---

## What the pipeline actually does

| Stage | Job | Resources | Time | What it produces |
| ---: | --- | --- | ---: | --- |
| 0 | datasets | CPU only, 32G RAM | ~25 min | 1700+ scenarios + 200 heuristic trajectories + SFT data + GRPO prompt set, pushed to `<user>/immunoorg-grpo-dataset` |
| 1 | SFT warm-start | 1 GPU, 64G RAM | ~25 min | LoRA adapter trained on heuristic trajectories so the model already speaks the env's JSON format before GRPO starts |
| 2 | GRPO training | 1+ GPU, 96G RAM | ~90-120 min | Final LoRA adapter, `evidence_grpo_training.png` (loss + per-reward curves) |
| 3 | evaluation | 1 GPU, 64G RAM | ~30 min | 100 episodes per family × 3 policies (random/heuristic/trained), produces `evidence_eval_per_family.png` and `evidence_eval_summary.png` |
| 4 | push artifacts | CPU only | ~10 min | Pushes adapter + 6+ PNGs + raw logs to `<user>/immunoorg-grpo-defender` model repo |

You can watch live with:

```bash
squeue -u $USER                       # job states
tail -f logs/stage*-*.out             # live training log
```

---

## Customising

### Want to use multiple GPUs (recommended if you have them)?

```bash
bash scripts/hpc/run_all.sh --multigpu 4
```

Stage 2 (GRPO) will be data-parallel across 4 GPUs via `accelerate launch`.
Roughly cuts stage 2 time from 90 min to 25 min.

### Want a bigger model (14B / 32B)?

Override before submitting:

```bash
export IMMUNOORG_MODEL="Qwen/Qwen2.5-14B-Instruct"      # needs A100 80GB or 2x A100 40GB
# or
export IMMUNOORG_MODEL="Qwen/Qwen2.5-32B-Instruct"      # needs 2x A100 80GB or 4x A100 40GB

bash scripts/hpc/run_all.sh --multigpu 2
```

### Skip SFT (saves ~30 min, slightly weaker results)

```bash
bash scripts/hpc/run_all.sh --skip-sft
```

### Custom partition / queue names

If your partition isn't called `gpu` and `cpu`:

```bash
bash scripts/hpc/run_all.sh --partition gpu-a100 --partition-cpu compute
```

Or set env vars: `IMMUNOORG_PARTITION=gpu-a100 IMMUNOORG_PARTITION_CPU=compute`.

### Push to a different HF account

```bash
export HF_PUSH_REPO="your-username/immunoorg-defender"
export HF_DATASET_REPO="your-username/immunoorg-dataset"
bash scripts/hpc/run_all.sh
```

### Common partition names by cluster

| Cluster | GPU partition | CPU partition |
| --- | --- | --- |
| TACC (Frontera/Lonestar) | `rtx`, `v100` | `normal`, `development` |
| NCSA Delta | `gpuA100x4`, `gpuA40x4` | `cpu` |
| NERSC Perlmutter | `gpu`, `gpu_a100` | `regular_milan_ss11` |
| Most universities | `gpu`, `a100`, `h100` | `cpu`, `compute`, `general` |

Run `sinfo -o '%P %G %D'` if you're not sure.

---

## Troubleshooting

### `sbatch: error: Invalid partition specified`
→ `sinfo -o '%P %G'` shows real partition names. Pass `--partition <name>`.

### Out of memory on GPU
→ Smaller model: `export IMMUNOORG_MODEL="Qwen/Qwen2.5-3B-Instruct"`.
→ Smaller batch: `export IMMUNOORG_GRPO_BATCH_SIZE=2 IMMUNOORG_SFT_BATCH_SIZE=2`.

### "RuntimeError: bf16 requires Ampere or newer"
→ V100 (Volta) detected. The pipeline auto-falls back to fp16 — should just work.
   If it doesn't, edit `scripts/hpc/pipeline/02_grpo_train.py` and force `bf16=False, fp16=True`.

### Stage 0 / 4 want a CPU partition but cluster only has GPU
→ Submit them to GPU too: `bash scripts/hpc/run_all.sh --partition-cpu gpu`.

### Air-gapped GPU node (no internet)
1. On the login node:
   ```bash
   bash scripts/hpc/setup_env.sh
   source .venv-hpc/bin/activate
   python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; \
              AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B-Instruct'); \
              AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct')"
   ```
2. The model is now in `~/.cache/huggingface/`. SLURM jobs reuse the cache.

### Non-SLURM cluster (PBS/Torque, LSF, single-node interactive)
You can still run each stage manually inside an interactive GPU shell:

```bash
# Get an interactive GPU shell first (cluster-specific, e.g. PBS):
qsub -I -l select=1:ngpus=1:walltime=04:00:00

# Then:
source .venv-hpc/bin/activate
export HF_TOKEN="..."
python scripts/hpc/pipeline/00_generate_datasets.py
python scripts/hpc/pipeline/01_sft_warmstart.py
python scripts/hpc/pipeline/02_grpo_train.py
python scripts/hpc/pipeline/03_evaluate.py
python scripts/hpc/pipeline/04_push_artifacts.py
```

---

## When it's done

Just message back:
- The five SLURM job IDs (`run_all.sh` prints them)
- Confirmation that the model + dataset URLs above contain the artifacts

Sender pulls everything from those URLs and re-deploys the HF Space.

Thanks again — this run is the missing piece for the hackathon submission. 🙏
