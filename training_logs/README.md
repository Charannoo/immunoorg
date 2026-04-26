# Training log exports

After `python -m training.train_grpo` (or the Colab notebook), TRL writes
`grpo_log_history.json` next to the checkpoint (see `training/train_grpo.py`).

To render **`evidence_grpo_training.png`** at the repo root:

```bash
python scripts/plot_grpo_log_history.py immunoorg-defender/grpo_log_history.json
```

In Colab, the notebook saves `/content/training_logs/grpo_log.json` and can plot
directly (Step 4b). Download that JSON and run the script above to match the
README figure.

Do **not** commit fabricated loss curves — judges expect plots from a real run
(Colab or HPC).
