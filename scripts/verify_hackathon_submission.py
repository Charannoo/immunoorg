#!/usr/bin/env python3
"""
Pre-flight check for OpenEnv Hackathon (India 2026) non-negotiables.

Run from repo root:
  python scripts/verify_hackathon_submission.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _fail(msg: str) -> None:
    print(f"FAIL  {msg}")


def _ok(msg: str) -> None:
    print(f"OK    {msg}")


def main() -> int:
    code = 0

    req = REPO / "requirements.txt"
    if req.is_file() and "openenv-core" in req.read_text(encoding="utf-8"):
        _ok("requirements.txt includes openenv-core (Space Docker installs OpenEnv).")
    else:
        _fail("requirements.txt should include openenv-core>=0.3.0")
        code = 1

    if (REPO / "openenv.yaml").is_file():
        _ok("openenv.yaml present.")
    else:
        _fail("openenv.yaml missing")
        code = 1

    readme = REPO / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if "huggingface.co/spaces/" in text:
            _ok("README links a Hugging Face Space.")
        else:
            _fail("README should link huggingface.co/spaces/...")
            code = 1
        if "ImmunoOrg_Training_Colab.ipynb" in text:
            _ok("README links Colab notebook.")
        else:
            _fail("README should link ImmunoOrg_Training_Colab.ipynb")
            code = 1
        if "docs.google.com/document" in text or "HF_MINI_BLOG" in text or "youtube.com" in text.lower():
            _ok("README mentions judges doc and/or HF blog / YouTube placeholders.")
        else:
            _fail("Add judges doc URL + HF blog / YouTube URLs (see README resource table).")
            code = 1
    else:
        _fail("README.md missing")
        code = 1

    pngs = list(REPO.glob("evidence*.png"))
    if len(pngs) >= 4:
        _ok(f"Found {len(pngs)} evidence*.png files.")
    else:
        _fail("Expected several evidence*.png files at repo root.")
        code = 1

    grpo_png = REPO / "evidence_grpo_training.png"
    if grpo_png.is_file():
        _ok("evidence_grpo_training.png exists (GRPO plot).")
    else:
        print(
            "WARN  evidence_grpo_training.png missing — after any GRPO run:\n"
            "       python scripts/plot_grpo_log_history.py immunoorg-defender/grpo_log_history.json\n"
            "       (Judges expect training loss/reward plots from a real run; Colab is fine.)"
        )

    if (REPO / "BLOG_POST.md").is_file():
        _ok("BLOG_POST.md present (paste into HF post).")
    else:
        _fail("BLOG_POST.md missing")
        code = 1

    if (REPO / "PUBLISH_HACKATHON.md").is_file():
        _ok("PUBLISH_HACKATHON.md present.")
    else:
        _fail("PUBLISH_HACKATHON.md missing")
        code = 1

    print()
    if code == 0:
        print("All automated checks passed. Still manually: publish HF post or YouTube, fill URLs in README, push Space.")
    else:
        print("Fix the items above before submitting.")
    return code


if __name__ == "__main__":
    sys.exit(main())
