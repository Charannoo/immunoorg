"""End-to-end API smoke test against a running ImmunoOrg server.

This test is intentionally written so it skips silently when no server
is reachable on ``localhost:7860`` — that way ``pytest tests`` still
passes in CI / local dev where you haven't booted ``uvicorn server.main:app``
yourself. To actually exercise it, run::

    uvicorn server.main:app --port 7860 &
    pytest tests/test_api.py -v
"""

from __future__ import annotations

import pytest
import requests

BASE = "http://localhost:7860"


def _server_alive() -> bool:
    try:
        r = requests.get(f"{BASE}/health", timeout=1.5)
        return r.status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(
    not _server_alive(),
    reason="ImmunoOrg server not running on localhost:7860 (start uvicorn server.main:app)",
)


def test_health_reset_step_state():
    """One round-trip through /health -> /reset -> /step -> /state."""
    # /health
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "healthy"

    # /reset
    r = requests.post(
        f"{BASE}/reset",
        json={"task": "level1_single_attack", "difficulty": 1, "seed": 42},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    obs = r.json()["observation"]
    assert obs["current_phase"] in {
        "detection",
        "containment",
        "rca",
        "refactor",
        "validation",
    }
    assert len(obs["visible_nodes"]) > 0
    assert obs["threat_level"] >= 0.0

    # /step  (scan logs on first visible node)
    target_id = obs["visible_nodes"][0]["id"]
    payload = {
        "action": {
            "action_type": "tactical",
            "tactical_action": "scan_logs",
            "target": target_id,
            "reasoning": "Smoke-test scan from pytest.",
        }
    }
    r = requests.post(f"{BASE}/step", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "reward" in data
    assert "observation" in data

    # /step (diagnostic)
    r = requests.post(
        f"{BASE}/step",
        json={
            "action": {
                "action_type": "diagnostic",
                "diagnostic_action": "identify_silo",
                "target": "",
                "reasoning": "Smoke-test silo lookup.",
            }
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text

    # /state
    r = requests.get(f"{BASE}/state", timeout=5)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["step_count"] >= 2
    assert "cumulative_reward" in state


if __name__ == "__main__":
    if not _server_alive():
        print(f"No ImmunoOrg server on {BASE} — start uvicorn server.main:app first.")
    else:
        test_health_reset_step_state()
        print("API smoke test passed.")
