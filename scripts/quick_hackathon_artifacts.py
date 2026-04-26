#!/usr/bin/env python3
"""
Fastest path to hackathon numbers + training figure (~15–35s total).

  python scripts/quick_hackathon_artifacts.py

Runs: benchmark_suite --quick → benchmark_results.json
      make_hackathon_training_figure.py → evidence_grpo_training.png
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    t0 = time.perf_counter()
    subprocess.run(
        [sys.executable, str(ROOT / "benchmark_suite.py"), "--quick"],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "make_hackathon_training_figure.py")],
        cwd=str(ROOT),
        check=True,
    )
    dt = time.perf_counter() - t0
    print(f"\n✓ benchmark_results.json + evidence_grpo_training.png ({dt:.1f}s)")


if __name__ == "__main__":
    main()
