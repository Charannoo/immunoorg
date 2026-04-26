#!/usr/bin/env python3
"""
Stage 4 — Push artifacts to the HF Hub
======================================

Final stage. Pushes:

  - GRPO LoRA adapter        -> $HF_PUSH_REPO         (model repo)
  - SFT warmstart adapter    -> $HF_PUSH_REPO/sft-warmstart/  (subfolder)
  - All evidence_*.png files -> $HF_PUSH_REPO         (model repo)
  - evaluation_results.json  -> $HF_PUSH_REPO         (model repo)
  - grpo_log.json            -> $HF_PUSH_REPO         (model repo)
  - dataset bundle           -> $HF_DATASET_REPO      (dataset repo, only if
                                                       not already pushed by stage 0)

Env overrides:
    HF_TOKEN              required
    HF_PUSH_REPO          default hirann/immunoorg-grpo-defender
    HF_DATASET_REPO       default hirann/immunoorg-grpo-dataset
    IMMUNOORG_GRPO_OUTPUT_DIR    default outputs/grpo-defender
    IMMUNOORG_SFT_OUTPUT_DIR     default outputs/sft-warmstart
    IMMUNOORG_DATA_DIR           default outputs/datasets
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

HF_TOKEN = os.environ.get("HF_TOKEN", "").strip() or None
PUSH_REPO = os.environ.get("HF_PUSH_REPO", "hirann/immunoorg-grpo-defender")
DATASET_REPO = os.environ.get("HF_DATASET_REPO", "hirann/immunoorg-grpo-dataset")
GRPO_DIR = Path(os.environ.get("IMMUNOORG_GRPO_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "grpo-defender")))
SFT_DIR = Path(os.environ.get("IMMUNOORG_SFT_OUTPUT_DIR", str(REPO_ROOT / "outputs" / "sft-warmstart")))
DATA_DIR = Path(os.environ.get("IMMUNOORG_DATA_DIR", str(REPO_ROOT / "outputs" / "datasets")))


def banner(msg: str) -> None:
    print()
    print("=" * 70)
    print(f"  {msg}")
    print("=" * 70)


def main() -> int:
    banner("ImmunoOrg 2.0 — Stage 4: Push artifacts to HF Hub")

    if not HF_TOKEN:
        print("HF_TOKEN missing; nothing to push. Files remain on disk:")
        print(f"  GRPO  : {GRPO_DIR}")
        print(f"  SFT   : {SFT_DIR}")
        print(f"  data  : {DATA_DIR}")
        return 1

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=HF_TOKEN)

    # ── Model repo (GRPO adapter + evidence + logs) ─────────────────────
    create_repo(repo_id=PUSH_REPO, repo_type="model", token=HF_TOKEN, exist_ok=True)
    print(f"\n[1/3] uploading GRPO adapter -> {PUSH_REPO}")
    if GRPO_DIR.exists():
        api.upload_folder(
            folder_path=str(GRPO_DIR),
            repo_id=PUSH_REPO,
            repo_type="model",
            commit_message="HPC pipeline stage 02 — GRPO adapter",
        )
        print(f"  -> https://huggingface.co/{PUSH_REPO}")
    else:
        print(f"  WARNING: {GRPO_DIR} missing")

    # ── SFT adapter as subfolder ────────────────────────────────────────
    if SFT_DIR.exists() and (SFT_DIR / "adapter_config.json").exists():
        print(f"\n[2/3] uploading SFT warmstart adapter -> {PUSH_REPO}/sft-warmstart/")
        api.upload_folder(
            folder_path=str(SFT_DIR),
            repo_id=PUSH_REPO,
            repo_type="model",
            path_in_repo="sft-warmstart",
            commit_message="HPC pipeline stage 01 — SFT warmstart adapter",
        )
    else:
        print("\n[2/3] no SFT adapter to upload (skipped)")

    # ── Evidence PNGs from repo root ────────────────────────────────────
    evidence_pngs = sorted(REPO_ROOT.glob("evidence_*.png"))
    if evidence_pngs:
        print(f"\n[3/3] uploading {len(evidence_pngs)} evidence PNGs:")
        for png in evidence_pngs:
            print(f"  - {png.name}")
            api.upload_file(
                path_or_fileobj=str(png),
                path_in_repo=png.name,
                repo_id=PUSH_REPO,
                repo_type="model",
                commit_message=f"add {png.name}",
            )
    else:
        print("\n[3/3] no evidence PNGs found in repo root")

    # ── eval results / logs ─────────────────────────────────────────────
    extras = {
        "evaluation_results.json": REPO_ROOT / "outputs" / "evaluation_results.json",
        "grpo_log.json": GRPO_DIR / "grpo_log.json",
        "sft_log.json": SFT_DIR / "sft_log.json",
    }
    for name, p in extras.items():
        if p.exists():
            api.upload_file(
                path_or_fileobj=str(p),
                path_in_repo=name,
                repo_id=PUSH_REPO,
                repo_type="model",
                commit_message=f"add {name}",
            )
            print(f"  uploaded extra: {name}")

    # ── Dataset repo (only if stage 0 didn't push) ──────────────────────
    if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
        try:
            api.repo_info(repo_id=DATASET_REPO, repo_type="dataset")
            print(f"\n  dataset repo {DATASET_REPO} already exists — skipping re-upload")
        except Exception:
            print(f"\n  uploading dataset bundle -> {DATASET_REPO}")
            create_repo(repo_id=DATASET_REPO, repo_type="dataset",
                        token=HF_TOKEN, exist_ok=True)
            api.upload_folder(
                folder_path=str(DATA_DIR),
                repo_id=DATASET_REPO,
                repo_type="dataset",
                commit_message="HPC pipeline final dataset bundle",
                ignore_patterns=["_tmp/*", "_tmp/**"],
            )

    banner("DONE — Stage 4")
    print(f"  model repo   : https://huggingface.co/{PUSH_REPO}")
    print(f"  dataset repo : https://huggingface.co/datasets/{DATASET_REPO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
