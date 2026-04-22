"""
ImmunoOrg EnvClient
====================
OpenEnv client for interacting with the ImmunoOrg environment.
Install: pip install git+https://huggingface.co/spaces/YOUR_SPACE/immunoorg
Usage:
    from immunoorg_client import ImmunoOrgAction, ImmunoOrgEnv
    with ImmunoOrgEnv(base_url="https://YOUR_SPACE.hf.space").sync() as client:
        obs = client.reset()
        obs = client.step(ImmunoOrgAction(action_type="tactical", tactical_action="scan_logs", target="web-server-00"))
"""

from __future__ import annotations
from typing import Any

from openenv.core import EnvClient
from server.main import ImmunoOrgAction, ImmunoOrgObservation


class ImmunoOrgEnv(EnvClient[ImmunoOrgAction, ImmunoOrgObservation]):
    """OpenEnv client for ImmunoOrg."""

    action_type = ImmunoOrgAction
    observation_type = ImmunoOrgObservation


# Re-export for convenience
__all__ = ["ImmunoOrgEnv", "ImmunoOrgAction", "ImmunoOrgObservation"]
