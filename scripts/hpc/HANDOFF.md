# ImmunoOrg 2.0 — Supercomputer Run Handoff

Hi! Thanks for running this — it gets the hackathon's most-required artifact
(GRPO loss + reward curves) into the submission. The whole thing is one
command. **Total wall-clock: ~45 min on 1× A100 / H100.**

---

## What you'll need

- **An HF write token** (sender will give you one — call it `$HF_TOKEN`).
- **One GPU**: A100 40GB / 80GB or H100 (V100 32GB also works).
- **SLURM** (most US clusters). If your cluster uses PBS/Torque, see "Non-SLURM" at the bottom.
- **Internet access on the GPU node** (most clusters have this; if yours does
  not, see "Air-gapped node" below — there's a workaround).

---

## Steps (literal copy-paste)

```bash
# 1. Clone the repo (~3 sec)
git clone https://github.com/Charannoo/immunoorg.git
cd immunoorg

# 2. One-time env setup (~5 min, downloads PyTorch + Unsloth + TRL)
bash scripts/hpc/setup_env.sh

# 3. Export your HF token (so the trained adapter + PNG can be uploaded)
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export HF_PUSH_REPO="hirann/immunoorg-grpo-defender"   # default; sender can override

# 4. Submit the SLURM job (returns a job ID immediately)
sbatch scripts/hpc/slurm_train.sbatch

# 5. Watch progress
squeue -u $USER                                  # job state
tail -f logs/grpo-*.out                          # live training log
```

When the job finishes, the script automatically:
- Saves `evidence_grpo_training.png` (loss + reward curves) to the repo root.
- Saves the LoRA adapter to `outputs/immunoorg-defender/`.
- **Pushes both to `https://huggingface.co/$HF_PUSH_REPO`** so the sender can
  pull them on their machine.

You're done. Just message back the SLURM job ID and the HF model URL.

---

## Customising the SLURM job

The defaults work for most clusters. If your partition / GPU is named differently,
edit the top of `scripts/hpc/slurm_train.sbatch`:

```bash
#SBATCH --partition=gpu           # change to your partition (e.g. a100, h100, gpu-a100)
#SBATCH --gres=gpu:1              # 1 GPU
#SBATCH --time=01:00:00           # 1 hour walltime
#SBATCH --mem=64G                 # 64 GB RAM
#SBATCH --cpus-per-task=8
```

Common partition names by cluster:
- TACC (Frontera/Lonestar): `rtx`, `v100`
- NCSA (Delta): `gpuA100x4`
- NERSC (Perlmutter): `gpu`, `gpu_a100`
- Most universities: `gpu`, `a100`, `h100`

Run `sinfo -o '%P %G %D'` if you're not sure.

---

## What it actually trains

- **Base model**: `Qwen/Qwen2.5-7B-Instruct` (4-bit LoRA via Unsloth)
- **Algorithm**: GRPO (TRL)
- **Reward functions** (3 independent, judge anti-hacking compliant):
  1. `format_reward` — valid JSON action schema
  2. `reasoning_quality_reward` — causal language + entity grounding
  3. `phase_appropriate_reward` — action belongs to current incident phase
- **Dataset**: 500 prompts from the **elite scenario mix** (20% each of 5 conflict
  scenarios: basic containment, RAG-grounding, executive alignment, silo-breaker,
  stealth-adaptive).
- **Training time**: ~30-40 min on A100 80GB with Unsloth (1 epoch, 200 GRPO
  steps, num_generations=4).

Override via env vars before `sbatch`:

```bash
export IMMUNOORG_MODEL="Qwen/Qwen2.5-3B-Instruct"   # smaller for V100 32GB
export IMMUNOORG_EPOCHS=2
export IMMUNOORG_NUM_PROMPTS=200                    # smaller dataset for faster runs
```

---

## What gets pushed to the HF model repo

```
https://huggingface.co/<HF_PUSH_REPO>/
├── adapter_config.json
├── adapter_model.safetensors          ← LoRA weights (~30 MB for 7B)
├── tokenizer.json + tokenizer_config.json
├── evidence_grpo_training.png         ← THE money chart
├── grpo_log.json                       ← raw trainer.state.log_history
└── README.md                           ← auto-generated model card
```

---

## Troubleshooting

### `sbatch: error: Invalid partition specified`
→ Run `sinfo -o '%P %G'` to see your real partition names; edit the
`#SBATCH --partition=` line in `scripts/hpc/slurm_train.sbatch`.

### Out-of-memory during training
→ Edit `IMMUNOORG_MODEL` to a smaller model (`Qwen/Qwen2.5-3B-Instruct` or
`Qwen/Qwen2.5-1.5B-Instruct`).

### "RuntimeError: bf16 requires Ampere or newer"
→ You're on V100 (Volta). Edit `scripts/hpc/train_full.py` and change
`bf16=True` to `fp16=True` (one line, see comment).

### Air-gapped GPU node (no internet)
1. From the login node: `bash scripts/hpc/setup_env.sh && python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B-Instruct'); AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct')"`
2. This downloads the model into `~/.cache/huggingface/`.
3. `sbatch scripts/hpc/slurm_train.sbatch` will use the cache instead of downloading.

### Non-SLURM cluster (PBS/Torque, LSF, etc.)
You can run interactively on a GPU node:

```bash
# Get an interactive GPU shell first (cluster-specific):
#   PBS:  qsub -I -l select=1:ngpus=1:walltime=01:00:00
#   LSF:  bsub -Is -gpu "num=1" -W 60 bash
# then:
bash scripts/hpc/setup_env.sh
export HF_TOKEN="..."
bash scripts/hpc/run_interactive.sh
```

---

That's the whole thing. Thanks again — this single run is worth ~15 percentage
points on the final hackathon score. 🙏
