"""
Trained-agent loader
====================

Lazy, fail-soft loader for a GRPO-trained LoRA adapter sitting on the
Hugging Face Hub. Designed so the live Space (and the demo UI) can
serve a *trained* agent the moment the HPC pipeline pushes a fresh
adapter, without us having to redeploy code.

Behaviour
---------
- ``IMMUNOORG_TRAINED_REPO`` env var (default ``hirann/immunoorg-grpo-defender``)
  is the model repo to load from.
- ``IMMUNOORG_BASE_MODEL`` env var (default ``Qwen/Qwen2.5-7B-Instruct``)
  is the base model the LoRA sits on top of.
- If torch / transformers / peft are not installed, or if the repo
  doesn't exist yet, ``TrainedDefender.is_available()`` returns False
  and ``predict_action()`` raises ``TrainedAgentUnavailable``.
- Loading happens on first call, not at import time, so the Space
  can boot in seconds even if the model isn't ready.

Used by
-------
- ``server/main.py``      → ``GET /trained_status`` and the demo UI
- ``server/demo_ui.py``   → "Run trained agent" button
"""

from __future__ import annotations

import json
import os
import re
from threading import Lock
from typing import Any, Optional


class TrainedAgentUnavailable(RuntimeError):
    """Raised when the trained adapter can't be loaded (deps / repo missing)."""


_DEFAULT_REPO = "hirann/immunoorg-grpo-defender"
_DEFAULT_BASE = "Qwen/Qwen2.5-7B-Instruct"


class TrainedDefender:
    """Singleton-ish wrapper around the GRPO-trained LoRA adapter."""

    _instance: Optional["TrainedDefender"] = None
    _lock = Lock()

    @classmethod
    def get(cls) -> "TrainedDefender":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self.repo_id = os.environ.get("IMMUNOORG_TRAINED_REPO", _DEFAULT_REPO)
        self.base_model = os.environ.get("IMMUNOORG_BASE_MODEL", _DEFAULT_BASE)
        self.model = None
        self.tokenizer = None
        self._load_error: Optional[str] = None
        self._load_attempted = False

    # ── Public API ──────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Probe HF Hub for the adapter without downloading anything heavy."""
        try:
            from huggingface_hub import HfApi  # type: ignore

            api = HfApi()
            api.repo_info(repo_id=self.repo_id, repo_type="model")
            return True
        except Exception as e:
            self._load_error = str(e)
            return False

    def status(self) -> dict[str, Any]:
        """Used by the /trained_status endpoint and the demo UI badge."""
        out: dict[str, Any] = {
            "repo_id": self.repo_id,
            "base_model": self.base_model,
            "loaded": self.model is not None,
            "load_attempted": self._load_attempted,
            "load_error": self._load_error,
        }
        try:
            from huggingface_hub import HfApi  # type: ignore

            info = HfApi().repo_info(repo_id=self.repo_id, repo_type="model")
            out["repo_exists"] = True
            out["last_modified"] = str(getattr(info, "last_modified", ""))
            out["sha"] = getattr(info, "sha", None)
        except Exception as e:
            out["repo_exists"] = False
            out["repo_check_error"] = str(e)
        return out

    def predict_action(self, observation_text: str, system_prompt: str) -> dict[str, Any]:
        """Run one inference step.

        Returns the parsed JSON action dict. Raises TrainedAgentUnavailable
        on any failure so the caller can fall back to the heuristic policy.
        """
        self._lazy_load()
        assert self.model is not None and self.tokenizer is not None

        prompt = (
            f"{system_prompt}\n\n## Current observation\n{observation_text}\n\n"
            f"Respond with a JSON action:"
        )
        try:
            chat = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            chat = prompt

        import torch  # type: ignore

        inputs = self.tokenizer(
            chat,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
        completion = self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )

        m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", completion)
        if not m:
            raise TrainedAgentUnavailable(
                f"could not parse JSON from model output: {completion[:200]!r}"
            )
        try:
            return json.loads(m.group())
        except Exception as e:  # pragma: no cover
            raise TrainedAgentUnavailable(f"json parse failed: {e}") from e

    # ── Internal ────────────────────────────────────────────────────────

    def _lazy_load(self) -> None:
        if self.model is not None:
            return
        if self._load_attempted and self._load_error:
            raise TrainedAgentUnavailable(self._load_error)

        self._load_attempted = True
        try:
            self._do_load()
        except Exception as e:
            self._load_error = f"{type(e).__name__}: {e}"
            raise TrainedAgentUnavailable(self._load_error) from e

    def _do_load(self) -> None:
        # Try Unsloth first for speed; fall back to plain transformers + peft.
        try:
            from unsloth import FastLanguageModel  # type: ignore

            model, tokenizer = FastLanguageModel.from_pretrained(
                self.repo_id,
                max_seq_length=2048,
                load_in_4bit=True,
            )
            FastLanguageModel.for_inference(model)
        except Exception:
            import torch  # type: ignore
            from peft import PeftModel  # type: ignore
            from transformers import (  # type: ignore
                AutoModelForCausalLM,
                AutoTokenizer,
            )

            tokenizer = AutoTokenizer.from_pretrained(self.repo_id)
            base = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                device_map="auto" if torch.cuda.is_available() else "cpu",
                torch_dtype=torch.bfloat16
                if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
                else torch.float32,
            )
            model = PeftModel.from_pretrained(base, self.repo_id)
            model.eval()

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        self.model = model
        self.tokenizer = tokenizer


__all__ = ["TrainedDefender", "TrainedAgentUnavailable"]
