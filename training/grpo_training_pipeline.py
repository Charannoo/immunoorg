"""
GRPO training entrypoint for HF Spaces / background jobs.

- Prefers persistent HF volume at ``/data`` when writable.
- Writes ``status.json`` + ``training.log`` under that root.
- Invoked by the FastAPI training trigger via ``python -m training.grpo_training_pipeline run ...``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path


def training_root() -> Path:
    """HF persistent disk is typically ``/data`` when enabled for the Space."""
    data = Path("/data")
    try:
        if data.is_dir() and os.access(data, os.W_OK):
            return data / "immunoorg-training"
    except OSError:
        pass
    repo = Path(__file__).resolve().parent.parent
    return repo / "outputs" / "training"


def status_file() -> Path:
    return training_root() / "status.json"


def log_file() -> Path:
    return training_root() / "training.log"


def _write_status(payload: dict) -> None:
    root = training_root()
    root.mkdir(parents=True, exist_ok=True)
    p = status_file()
    cur: dict = {}
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cur = {}
    cur.update(payload)
    cur["updated_at"] = time.time()
    p.write_text(json.dumps(cur, indent=2), encoding="utf-8")


def run_training(argv: list[str] | None = None) -> int:
    """CLI: ``python -m training.grpo_training_pipeline run [train_grpo args...]``"""
    parser = argparse.ArgumentParser(description="ImmunoOrg GRPO background pipeline")
    parser.add_argument(
        "command",
        choices=["run"],
        help="run = execute GRPO training (delegates to training.train_grpo)",
    )
    known, rest = parser.parse_known_args(argv)
    if known.command != "run":
        return 1

    root = training_root()
    root.mkdir(parents=True, exist_ok=True)
    log_path = log_file()

    _write_status(
        {
            "state": "starting",
            "pid": os.getpid(),
            "training_root": str(root),
            "log_file": str(log_path),
        }
    )

    # Tee stdout/stderr to log file for Space container logs + file audit.
    class _Tee:
        def __init__(self, *streams):
            self._streams = streams

        def write(self, data: str) -> int:
            for s in self._streams:
                s.write(data)
                s.flush()
            return len(data)

        def flush(self) -> None:
            for s in self._streams:
                s.flush()

    log_f = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = _Tee(sys.__stdout__, log_f)  # type: ignore[method-assign]
    sys.stderr = _Tee(sys.__stderr__, log_f)  # type: ignore[method-assign]

    try:
        _write_status({"state": "running", "started_at": time.time()})
        # Ensure HF cache / outputs land on persistent volume when available
        os.environ.setdefault("HF_HOME", str(root / "hf_home"))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(root / "hf_home" / "transformers"))
        os.environ.setdefault("HF_DATASETS_CACHE", str(root / "hf_home" / "datasets"))

        from training.train_grpo import parse_train_args, run_grpo_training

        args = parse_train_args(rest)
        if not args.output_dir or args.output_dir == "./immunoorg-defender":
            args.output_dir = str(root / "checkpoints" / "immunoorg-defender")
        run_grpo_training(args)
        _write_status({"state": "finished", "finished_at": time.time(), "output_dir": args.output_dir})
        return 0
    except SystemExit as e:
        code = int(e.code) if isinstance(e.code, int) else 1
        _write_status({"state": "failed", "exit_code": code, "error": "SystemExit"})
        return code
    except Exception as e:
        _write_status(
            {
                "state": "failed",
                "error": repr(e),
                "traceback": traceback.format_exc(),
            }
        )
        return 1
    finally:
        try:
            log_f.close()
        except Exception:
            pass


def main() -> None:
    raise SystemExit(run_training(sys.argv[1:]))


if __name__ == "__main__":
    main()
