"""
ImmunoOrg 2.0 — HuggingFace Spaces Upload Script
=================================================
Run this script to create the HF Space and upload all files.

Usage:
    python upload_to_hf.py --token YOUR_HF_TOKEN --username YOUR_HF_USERNAME

Or set environment variables:
    set HF_TOKEN=your_token
    set HF_USERNAME=your_username
    python upload_to_hf.py
"""

import os
import sys
import argparse
from pathlib import Path

def upload_to_hf(token: str, username: str, space_name: str = "immunoorg-2"):
    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=token)
    repo_id = f"{username}/{space_name}"

    print(f"Creating HF Space: {repo_id}")
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
            token=token,
            exist_ok=True,
        )
        print(f"  Space created: https://huggingface.co/spaces/{repo_id}")
    except Exception as e:
        print(f"  Space already exists or error: {e}")

    # Files to upload
    SKIP = {
        '.git', '__pycache__', '.pyc', '.planning',
        'node_modules', '.env', '*.egg-info',
        'ImmunoOrg_Training_Colab.ipynb',  # too large for space
        '.pytest_cache', '.venv', 'training_runs',
    }

    root = Path('.')
    upload_count = 0

    # Core files list (ordered by importance)
    core_patterns = [
        'Dockerfile', 'requirements.txt', 'openenv.yaml', 'README.md',
        'BLOG_POST.md', 'JUDGING_GUIDE.md', 'RESEARCH.md',
        'demo_runner.py', 'generate_evidence.py',
        'evidence_*.png',
        'server/main.py', 'server/config.py',
        'immunoorg/*.py',
        'immunoorg/agents/*.py',
        'visualization/dashboard.py',
        'visualization/metrics.py',
        'training/train_grpo.py',
        'training/scenario_hooks.py',
        'training/grpo_training_pipeline.py',
    ]

    # Collect files
    files_to_upload = []
    for pattern in core_patterns:
        files_to_upload.extend(root.glob(pattern))

    print(f"\nUploading {len(files_to_upload)} files...")
    for fpath in files_to_upload:
        if fpath.is_dir():
            continue
        if any(skip in str(fpath) for skip in SKIP):
            continue
        try:
            api.upload_file(
                path_or_fileobj=str(fpath),
                path_in_repo=str(fpath).replace('\\', '/'),
                repo_id=repo_id,
                repo_type="space",
                token=token,
            )
            print(f"  UPLOADED: {fpath}")
            upload_count += 1
        except Exception as e:
            print(f"  SKIP (error): {fpath} — {e}")

    print(f"\nDone! {upload_count} files uploaded.")
    print(f"\nYour Space URL: https://huggingface.co/spaces/{repo_id}")
    print(f"It will take ~5 minutes to build the Docker container.")
    print(f"\nNext: Update README.md with this URL:")
    print(f"  HF_SPACE_URL = https://huggingface.co/spaces/{repo_id}")
    return f"https://huggingface.co/spaces/{repo_id}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload ImmunoOrg 2.0 to HuggingFace Spaces")
    parser.add_argument("--token",    default=os.environ.get("HF_TOKEN"),    help="HuggingFace API token")
    parser.add_argument("--username", default=os.environ.get("HF_USERNAME"), help="HuggingFace username")
    parser.add_argument("--space",    default="immunoorg-2",                  help="Space name (default: immunoorg-2)")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: Provide HF token via --token or HF_TOKEN env var")
        print("  Get token from: https://huggingface.co/settings/tokens")
        sys.exit(1)
    if not args.username:
        print("ERROR: Provide HF username via --username or HF_USERNAME env var")
        sys.exit(1)

    url = upload_to_hf(args.token, args.username, args.space)
