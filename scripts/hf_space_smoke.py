
import requests

BASE_URL = "https://hirann-immunoorg-v3.hf.space"

def test_endpoint(name, method, path, payload=None):
    print(f"Testing {name} ({method} {path})...")
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url)
        else:
            r = requests.post(url, json=payload)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}\n")
        return r.status_code == 200
    except Exception as e:
        print(f"Error: {e}\n")
        return False

if __name__ == "__main__":
    # 1. Health Check
    test_endpoint("Health", "GET", "/health")

    # 2. Reset
    reset_success = test_endpoint("Reset", "POST", "/reset", {"difficulty": 1})

    if reset_success:
        # 3. Step
        action_payload = {
            "action": {
                "action_type": "tactical",
                "tactical_action": "scan_logs",
                "target": "web-server-00",
                "reasoning": "Initial scan"
            }
        }
        test_endpoint("Step", "POST", "/step", action_payload)

        # 4. State
        test_endpoint("State", "GET", "/state")
