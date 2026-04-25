"""
ImmunoOrg OpenEnv client
=========================

Thin OpenEnv ``EnvClient`` binding for the ImmunoOrg environment.
This module is intentionally **server-free**: it only imports the
shared wire schemas from ``immunoorg.api_models`` so it can be
installed (or vendored) by external training code without dragging
in the FastAPI server, the simulator, or any of the heavy
``immunoorg`` engines.

Usage
-----
.. code-block:: python

    from client import ImmunoOrgEnv, ImmunoOrgAction

    with ImmunoOrgEnv(base_url="https://hirann-immunoorg-2.hf.space").sync() as env:
        obs = env.reset()
        obs = env.step(ImmunoOrgAction(
            action_type="tactical",
            tactical_action="scan_logs",
            target="web-server-00",
            reasoning="Detection phase scan.",
        ))

If the ``openenv`` package is unavailable (e.g. inside a minimal
container), the module still exposes the wire schemas so callers can
talk to the FastAPI endpoints with plain ``requests``.
"""

from __future__ import annotations

from immunoorg.api_models import ImmunoOrgAction, ImmunoOrgObservation

try:
    from openenv.core import EnvClient

    class ImmunoOrgEnv(EnvClient[ImmunoOrgAction, ImmunoOrgObservation, dict]):
        """OpenEnv client for ImmunoOrg."""

        action_type = ImmunoOrgAction
        observation_type = ImmunoOrgObservation
except ImportError:  # pragma: no cover - openenv is an optional dep here
    ImmunoOrgEnv = None  # type: ignore[assignment]


__all__ = ["ImmunoOrgEnv", "ImmunoOrgAction", "ImmunoOrgObservation"]
