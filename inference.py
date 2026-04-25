"""
ImmunoOrg Inference Script
==========================
OpenEnv-compatible inference with [START], [STEP], [END] logging.
Demonstrates agent interaction with the environment.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import requests

BASE_URL = os.environ.get("IMMUNOORG_URL", "http://localhost:7860")


def log_start(task_id: str, config: dict[str, Any]) -> None:
    print(f"[START] task={task_id} config={json.dumps(config)}")


def log_step(step: int, action: dict, observation_summary: str, reward: float) -> None:
    print(f"[STEP] step={step} action={json.dumps(action)} obs={observation_summary} reward={reward:.4f}")


def log_end(task_id: str, total_reward: float, metrics: dict[str, Any]) -> None:
    print(f"[END] task={task_id} total_reward={total_reward:.4f} metrics={json.dumps(metrics)}")


def run_episode(task_id: str = "level1_single_attack", difficulty: int = 1) -> dict[str, Any]:
    """Run a single episode with a rule-based baseline agent."""
    config = {"task": task_id, "difficulty": difficulty}
    log_start(task_id, config)

    # Reset
    resp = requests.post(f"{BASE_URL}/reset", json={"task": task_id, "difficulty": difficulty})
    resp.raise_for_status()
    data = resp.json()
    obs = data["observation"]

    total_reward = 0.0
    step = 0
    done = False

    while not done and step < 200:
        # Simple rule-based agent
        action = decide_action(obs, step)

        # Step
        resp = requests.post(f"{BASE_URL}/step", json={"action": action})
        resp.raise_for_status()
        result = resp.json()

        obs = result["observation"]
        reward = result["reward"]
        done = result.get("done", result.get("terminated", False))
        total_reward += reward
        step += 1

        obs_summary = f"phase={obs.get('current_phase', '?')} threat={obs.get('threat_level', 0):.2f}"
        log_step(step, action, obs_summary, reward)

    metrics = {
        "steps": step,
        "total_reward": total_reward,
        "final_phase": obs.get("current_phase", "unknown"),
        "threat_level": obs.get("threat_level", 0),
        "downtime": obs.get("system_downtime", 0),
    }
    log_end(task_id, total_reward, metrics)
    return metrics


def decide_action(obs: dict, step: int) -> dict[str, Any]:
    """Rule-based baseline agent for demonstration."""
    phase = obs.get("current_phase", "detection")
    attacks = obs.get("detected_attacks", [])
    nodes = obs.get("visible_nodes", [])

    if phase == "detection":
        # Scan logs on first available node
        compromised = [n for n in nodes if n.get("compromised")]
        if compromised:
            return {
                "action_type": "tactical",
                "tactical_action": "scan_logs",
                "target": compromised[0]["id"],
                "reasoning": f"Scanning logs on compromised node {compromised[0]['id']} for attack indicators.",
            }
        # Scan a random node
        if nodes:
            return {
                "action_type": "tactical",
                "tactical_action": "scan_logs",
                "target": nodes[0]["id"],
                "reasoning": "Scanning logs for initial threat detection.",
            }

    elif phase == "containment":
        # Isolate compromised nodes
        compromised = [n for n in nodes if n.get("compromised") and not n.get("isolated")]
        if compromised:
            return {
                "action_type": "tactical",
                "tactical_action": "isolate_node",
                "target": compromised[0]["id"],
                "reasoning": f"Isolating compromised node {compromised[0]['id']} to prevent lateral movement.",
            }

    elif phase == "rca":
        # Try to identify silos
        if step % 3 == 0:
            return {
                "action_type": "diagnostic",
                "diagnostic_action": "identify_silo",
                "target": "",
                "reasoning": "Identifying organizational silos that may have delayed incident response.",
            }
        # Correlate failures
        if attacks:
            vector = attacks[0].get("vector", "unknown")
            return {
                "action_type": "diagnostic",
                "diagnostic_action": "correlate_failure",
                "target": attacks[0].get("target_node", ""),
                "parameters": {
                    "technical_indicator": f"{vector}_attack",
                    "organizational_flaw": "no_devsecops",
                    "confidence": 0.7,
                },
                "reasoning": f"Correlating {vector} attack to potential DevSecOps gap.",
            }

    elif phase == "refactor":
        # Create shortcut between security and engineering
        return {
            "action_type": "strategic",
            "strategic_action": "establish_devsecops",
            "target": "dept-security",
            "secondary_target": "dept-engineering",
            "reasoning": "Establishing DevSecOps integration to prevent future code-level vulnerabilities.",
        }

    elif phase == "validation":
        return {
            "action_type": "diagnostic",
            "diagnostic_action": "measure_org_latency",
            "target": "",
            "reasoning": "Validating that organizational changes improved response efficiency.",
        }

    # Default: escalate
    return {
        "action_type": "tactical",
        "tactical_action": "escalate_alert",
        "target": "",
        "reasoning": "Escalating alert to increase threat awareness.",
    }


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "level1_single_attack"
    difficulty = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    run_episode(task, difficulty)
