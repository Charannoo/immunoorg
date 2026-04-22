"""
Golden Trajectory Extraction
=============================
Extract optimal trajectories from environment rollouts for SFT warm-start.
"""

from __future__ import annotations
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import ImmunoAction, TacticalAction, DiagnosticAction, StrategicAction, ActionType


# Hand-crafted golden trajectories for each difficulty level
GOLDEN_TRAJECTORIES = {
    1: [
        {"action_type": "tactical", "tactical_action": "scan_logs", "reasoning": "Step 1: Scan logs on the first compromised node to identify attack vector and confirm the threat before taking containment action."},
        {"action_type": "diagnostic", "diagnostic_action": "trace_attack_path", "reasoning": "Step 2: Trace the attack path to understand scope. Need to know if lateral movement occurred."},
        {"action_type": "tactical", "tactical_action": "isolate_node", "reasoning": "Step 3: Isolate the compromised node to stop the attack. This is the fastest containment action."},
        {"action_type": "diagnostic", "diagnostic_action": "correlate_failure", "reasoning": "Step 4: Correlate the technical failure to organizational root cause. The attack vector indicates a gap in security practices."},
        {"action_type": "diagnostic", "diagnostic_action": "identify_silo", "reasoning": "Step 5: Check for organizational silos that may have slowed response."},
        {"action_type": "diagnostic", "diagnostic_action": "measure_org_latency", "reasoning": "Step 6: Validate organizational improvements by measuring current efficiency metrics."},
    ],
    2: [
        {"action_type": "tactical", "tactical_action": "scan_logs", "reasoning": "Phase 1 Detection: Scanning logs to identify initial compromise point and attack vector."},
        {"action_type": "diagnostic", "diagnostic_action": "trace_attack_path", "reasoning": "Tracing lateral movement path to understand the full kill chain before containment."},
        {"action_type": "diagnostic", "diagnostic_action": "timeline_reconstruct", "reasoning": "Reconstructing timeline to identify sequence of compromises for targeted containment."},
        {"action_type": "tactical", "tactical_action": "isolate_node", "reasoning": "Isolating the source node first to cut off the attacker's entry point."},
        {"action_type": "tactical", "tactical_action": "deploy_patch", "reasoning": "Patching the initially compromised node to close the vulnerability."},
        {"action_type": "diagnostic", "diagnostic_action": "correlate_failure", "reasoning": "Correlating the lateral movement success to flat network segmentation and security-engineering silo."},
        {"action_type": "diagnostic", "diagnostic_action": "identify_silo", "reasoning": "Identifying silos that delayed incident response."},
        {"action_type": "strategic", "strategic_action": "create_shortcut_edge", "reasoning": "Creating fast communication channel between security and engineering to improve future response."},
        {"action_type": "diagnostic", "diagnostic_action": "measure_org_latency", "reasoning": "Validating that the organizational change improved efficiency."},
    ],
}


def extract_golden_trajectories(num_episodes: int = 10, difficulty: int = 1) -> list[dict]:
    """Run episodes and extract the best trajectories."""
    best_trajectories = []

    for ep in range(num_episodes):
        env = ImmunoOrgEnvironment(difficulty=difficulty, seed=ep)
        obs = env.reset()

        trajectory = []
        golden = GOLDEN_TRAJECTORIES.get(difficulty, GOLDEN_TRAJECTORIES[1])

        total_reward = 0.0
        for i, action_template in enumerate(golden):
            action = ImmunoAction(
                action_type=ActionType(action_template["action_type"]),
                tactical_action=TacticalAction(action_template["tactical_action"]) if action_template.get("tactical_action") else None,
                strategic_action=StrategicAction(action_template["strategic_action"]) if action_template.get("strategic_action") else None,
                diagnostic_action=DiagnosticAction(action_template["diagnostic_action"]) if action_template.get("diagnostic_action") else None,
                target=_get_target(obs, action_template),
                reasoning=action_template["reasoning"],
            )

            obs_obj, reward, terminated = env.step(action)
            total_reward += reward
            obs = obs_obj

            trajectory.append({
                "step": i,
                "action": action.model_dump(),
                "reward": reward,
                "observation_summary": f"phase={obs.current_phase.value} threat={obs.threat_level:.2f}",
            })

            if terminated:
                break

        best_trajectories.append({
            "episode": ep,
            "difficulty": difficulty,
            "total_reward": total_reward,
            "steps": len(trajectory),
            "trajectory": trajectory,
        })

    # Sort by reward and return top trajectories
    best_trajectories.sort(key=lambda t: t["total_reward"], reverse=True)
    return best_trajectories[:max(1, num_episodes // 2)]


def _get_target(obs, action_template: dict) -> str:
    """Pick an appropriate target from the observation."""
    action_type = action_template.get("action_type", "")
    if action_type == "tactical":
        nodes = obs.visible_nodes if hasattr(obs, 'visible_nodes') else []
        compromised = [n for n in nodes if n.compromised]
        if compromised:
            return compromised[0].id
        if nodes:
            return nodes[0].id
    elif action_type == "strategic":
        return "dept-security"
    return ""


def save_golden_trajectories(output_path: str = "golden_trajectories.json"):
    """Generate and save golden trajectories for all difficulty levels."""
    all_trajectories = {}
    for diff in [1, 2]:
        print(f"Extracting golden trajectories for difficulty {diff}...")
        trajectories = extract_golden_trajectories(num_episodes=5, difficulty=diff)
        all_trajectories[f"level_{diff}"] = trajectories
        print(f"  Found {len(trajectories)} good trajectories (best reward: {trajectories[0]['total_reward']:.3f})")

    with open(output_path, "w") as f:
        json.dump(all_trajectories, f, indent=2, default=str)
    print(f"\n💾 Saved to {output_path}")


if __name__ == "__main__":
    save_golden_trajectories()
