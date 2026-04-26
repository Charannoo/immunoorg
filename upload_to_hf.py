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


def scrub_hub_token(raw: str) -> str:
    """Strip BOM, quotes, accidental KEY= prefixes, and outer whitespace."""
    t = raw.strip().strip("\ufeff")
    if "\n" in t:
        t = t.splitlines()[0].strip()
    if t.upper().startswith("HF_TOKEN="):
        t = t.split("=", 1)[1].strip()
    if t.upper().startswith("HUGGINGFACE_HUB_TOKEN="):
        t = t.split("=", 1)[1].strip()
    return t.strip().strip('"').strip("'")


def resolve_hf_token(explicit: str | None) -> str | None:
    """CLI --token, then .hf_token (if present), then HF_TOKEN / HUGGINGFACE_HUB_TOKEN.

    File wins over env so a correct `.hf_token` is not overridden by a stale HF_TOKEN
    in the shell profile.
    """
    if explicit and explicit.strip():
        return scrub_hub_token(explicit)
    p = Path(".hf_token")
    if p.is_file():
        v = p.read_text(encoding="utf-8")
        if v.strip():
            return scrub_hub_token(v)
    for key in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        v = os.environ.get(key, "").strip()
        if v:
            return scrub_hub_token(v)
    return None


def preflight_hub_auth(token: str, repo_owner: str) -> None:
    """One whoami + owner check so 401 is explained before 50 upload errors."""
    from huggingface_hub import HfApi

    try:
        from huggingface_hub.errors import HfHubHTTPError
    except ImportError:
        from huggingface_hub.utils import HfHubHTTPError  # type: ignore

    api = HfApi(token=token)
    try:
        try:
            info = api.whoami(cache=True)
        except TypeError:
            info = api.whoami()
    except HfHubHTTPError as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        err_l = str(e).lower()
        if code == 401 or "401" in err_l or "invalid username or password" in err_l:
            print("ERROR: Hugging Face rejected this token (401).")
            print(f"  (Scrubbed token length: {len(token)} — typical Hub tokens are ~37+ chars; copy the full value.)")
            print("  - Regenerate: https://huggingface.co/settings/tokens")
            print("  - Use a token with write access (classic: repo scope; fine-grained: Repositories write).")
            print("  - Paste only the token in .hf_token (no quotes, no HF_TOKEN= prefix).")
            sys.exit(1)
        if code == 429 or "429" in err_l or "rate limit" in err_l:
            print(
                "NOTE: /whoami is rate-limited right now; skipping username preflight.\n"
                "      Upload will still run — if you get 401 on upload, fix token or --username.\n"
            )
            return
        raise

    name = (info or {}).get("name") or ""
    orgs = [o.get("name") for o in (info or {}).get("orgs", []) if isinstance(o, dict)]
    if repo_owner != name and repo_owner not in orgs:
        print(
            f"WARNING: You are pushing to '{repo_owner}/…' but this token is for user '{name}'."
        )
        if orgs:
            print(f"  Token has org access: {orgs}")
        print("  Fix: pass --username that matches your HF username, or use an org where you have write access.")
        print("  Otherwise uploads will return 401 / repository not found.\n")

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
        err = str(e)
        print(f"  Space already exists or error: {e}")
        if "401" in err or "Unauthorized" in err or "invalid username or password" in err.lower():
            print("\nAborting: Hub rejected credentials when creating the Space (check token + --username).")
            sys.exit(1)

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
        'server/main.py', 'server/config.py', 'server/demo_ui.py',
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
    parser.add_argument("--token",    default=None, help="HuggingFace API token (or HF_TOKEN / .hf_token)")
    parser.add_argument("--username", default=os.environ.get("HF_USERNAME"), help="HuggingFace username")
    parser.add_argument("--space",    default="immunoorg-2",                  help="Space name (default: immunoorg-2)")
    args = parser.parse_args()

    token = resolve_hf_token(args.token)
    if not token:
        print("ERROR: No Hugging Face Hub token found.")
        print("  Use one of: --token, HF_TOKEN env, or a one-line token in .hf_token")
        print("  (Do not use TRAINING_SECRET / .training_secret for Hub uploads.)")
        print("  Create a token: https://huggingface.co/settings/tokens")
        sys.exit(1)
    if not args.username:
        print("ERROR: Provide HF username via --username or HF_USERNAME env var")
        sys.exit(1)

    preflight_hub_auth(token, args.username)
    url = upload_to_hf(token, args.username, args.space)
