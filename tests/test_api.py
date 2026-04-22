"""End-to-end API test."""
import requests
import json

BASE = "http://localhost:7860"

# Test health
r = requests.get(f"{BASE}/health")
print("HEALTH:", r.json())

# Test reset
r = requests.post(f"{BASE}/reset", json={"task": "level1_single_attack", "difficulty": 1, "seed": 42})
data = r.json()
obs = data["observation"]
phase = obs["current_phase"]
n_nodes = len(obs["visible_nodes"])
threat = obs["threat_level"]
print(f"RESET: phase={phase}, nodes={n_nodes}, threat={threat:.2f}")

# Test step - scan logs
target_id = obs["visible_nodes"][0]["id"]
action = {"action": {"action_type": "tactical", "tactical_action": "scan_logs", "target": target_id, "reasoning": "Scanning for threats."}}
r = requests.post(f"{BASE}/step", json=action)
data = r.json()
print(f"STEP 1: reward={data['reward']:.3f}, result={data['observation']['action_result'][:60]}")

# Test step - isolate compromised
compromised = [n for n in data["observation"]["visible_nodes"] if n.get("compromised")]
if compromised:
    action = {"action": {"action_type": "tactical", "tactical_action": "isolate_node", "target": compromised[0]["id"], "reasoning": "Isolating."}}
    r = requests.post(f"{BASE}/step", json=action)
    data = r.json()
    print(f"STEP 2: reward={data['reward']:.3f}, result={data['observation']['action_result'][:60]}")

# Test diagnostic
action = {"action": {"action_type": "diagnostic", "diagnostic_action": "identify_silo", "target": "", "reasoning": "Finding silos."}}
r = requests.post(f"{BASE}/step", json=action)
data = r.json()
print(f"STEP 3: reward={data['reward']:.3f}, phase={data['info']['phase']}")

# Test state
r = requests.get(f"{BASE}/state")
state = r.json()
print(f"STATE: steps={state['step_count']}, cumulative_reward={state['cumulative_reward']:.3f}")

print("\nALL API TESTS PASSED")
