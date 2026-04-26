#!/usr/bin/env python3
"""
Render ``evidence_grpo_training.png`` from a TRL ``trainer.state.log_history`` export.

After ``python -m training.train_grpo`` (or Colab), you will have
``<output_dir>/grpo_log_history.json``. Run:

  python scripts/plot_grpo_log_history.py immunoorg-defender/grpo_log_history.json

Or default path:

  python scripts/plot_grpo_log_history.py

Requires matplotlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    default_json = REPO_ROOT / "immunoorg-defender" / "grpo_log_history.json"
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_json
    out_png = REPO_ROOT / "evidence_grpo_training.png"

    if not in_path.is_file():
        print(f"Missing {in_path} — run training first (see README / Colab).")
        sys.exit(1)

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("Expected a JSON list (log_history).")
        sys.exit(1)

    steps: list[int] = []
    loss: list[float] = []
    reward: list[float] = []

    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        step = row.get("step")
        if step is None:
            step = i
        steps.append(int(step))
        if "loss" in row and row["loss"] is not None:
            loss.append(float(row["loss"]))
        if "reward" in row and row["reward"] is not None:
            reward.append(float(row["reward"]))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=120)
    fig.suptitle("GRPO training (ImmunoOrg defender) — exported log history", fontsize=12)

    if len(loss) >= 2 and len(steps) >= len(loss):
        sx = steps[: len(loss)]
        axes[0].plot(sx, loss, "b-o", markersize=4)
        axes[0].set_xlabel("Optimization step")
        axes[0].set_ylabel("Loss")
        axes[0].set_title("Training loss")
        axes[0].grid(True, alpha=0.3)
    else:
        axes[0].text(
            0.5,
            0.5,
            "No loss entries in log_history.\n(Re-run with TRL that logs `loss`.)",
            ha="center",
            va="center",
            transform=axes[0].transAxes,
        )

    if len(reward) >= 2:
        sr = steps[: len(reward)] if len(steps) >= len(reward) else list(range(len(reward)))
        axes[1].plot(sr, reward, "g-s", markersize=4)
        axes[1].set_xlabel("Optimization step")
        axes[1].set_ylabel("Reward (logged)")
        axes[1].set_title("Logged reward signal")
        axes[1].grid(True, alpha=0.3)
    else:
        axes[1].text(
            0.5,
            0.5,
            "No reward entries in log_history.\n(OK — loss-only runs are common.)",
            ha="center",
            va="center",
            transform=axes[1].transAxes,
        )

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()
