"""
One-shot deploy of the cleaned ImmunoOrg 2.0 repo to a fresh HF Space.

Reads token from the HF_TOKEN env var (or D:\\scaler-r2\\.hf_token if env
is missing), creates the Space if it doesn't exist, sets the
TRAINING_SECRET space secret, and uploads the whole repo as a single
commit using ``HfApi.upload_folder``.

Usage::

    python scripts/deploy_to_hf_space.py \\
        --repo-id hirann/immunoorg-v3 \\
        --training-secret auto      # or "skip" or a literal value
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_token() -> str:
    tok = os.environ.get("HF_TOKEN", "").strip()
    if tok:
        return tok
    fp = REPO_ROOT / ".hf_token"
    if fp.exists():
        return fp.read_text(encoding="utf-8").strip()
    raise SystemExit("HF_TOKEN missing; set env var or write to .hf_token first.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True, help="e.g. hirann/immunoorg-v3")
    parser.add_argument(
        "--training-secret",
        default="skip",
        help="auto | skip | <literal string>",
    )
    args = parser.parse_args()

    token = _load_token()

    # Late import so the script can still print a useful message if HF lib is missing.
    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=token)

    # 1. Confirm token works and print the account so the user sees who is deploying.
    me = api.whoami(token=token)
    print(f"[1/4] authenticated as {me['name']} ({me.get('type')})")

    # 2. Create (or accept existing) Space.
    print(f"[2/4] creating Space {args.repo_id} (Docker SDK)...")
    create_repo(
        repo_id=args.repo_id,
        repo_type="space",
        space_sdk="docker",
        private=False,
        token=token,
        exist_ok=True,
    )
    print(f"    -> https://huggingface.co/spaces/{args.repo_id}")

    # 3. Optionally store TRAINING_SECRET so /admin/training/* endpoints work.
    if args.training_secret == "skip":
        print("[3/4] training-secret: SKIPPED (admin/training endpoints stay disabled)")
        secret_value = None
    else:
        secret_value = (
            secrets.token_urlsafe(32)
            if args.training_secret == "auto"
            else args.training_secret
        )
        api.add_space_secret(
            repo_id=args.repo_id,
            key="TRAINING_SECRET",
            value=secret_value,
            description="Gate token for /admin/training/start (auto-generated)",
        )
        print(f"[3/4] training-secret: stored as TRAINING_SECRET on the Space")

    # 4. Upload the whole repo as a single commit.
    print(f"[4/4] uploading repo from {REPO_ROOT}")
    ignore = [
        ".git/*",
        ".git/**",
        "__pycache__/*",
        "**/__pycache__/**",
        "*.pyc",
        ".venv/*",
        ".venv/**",
        ".pytest_cache/*",
        ".pytest_cache/**",
        "training_runs/*",
        "training_runs/**",
        ".hf_token",
        "*.log",
        ".idea/**",
        ".vscode/**",
        "training/datasets/**",
        "training/grpo_data/**",
        "training/output/**",
        "training/trajectories/**",
    ]
    commit = api.upload_folder(
        folder_path=str(REPO_ROOT),
        repo_id=args.repo_id,
        repo_type="space",
        ignore_patterns=ignore,
        commit_message=(
            "Initial deploy of cleaned ImmunoOrg 2.0 repo "
            "(elite scenario mix + 6 evidence PNGs + 3-reward GRPO pipeline)"
        ),
    )
    print(f"    commit: {commit}")
    print()
    print("Done. Space will start a Docker build now (~3-5 min).")
    print(f"   Live URL : https://hirann-{args.repo_id.split('/')[-1]}.hf.space")
    print(f"   Build log: https://huggingface.co/spaces/{args.repo_id}?logs=build")
    if secret_value is not None:
        print()
        print("== SAVE THIS TRAINING_SECRET (shown ONCE) ==")
        print(secret_value)
        print("============================================")
        print("To start training from your laptop:")
        print(
            f"  curl 'https://hirann-{args.repo_id.split('/')[-1]}.hf.space"
            f"/admin/training/start?token={secret_value}&smoke_test=true'"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
