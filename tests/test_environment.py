"""Tests for the ImmunoOrg environment."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import (
    ImmunoAction, ActionType, TacticalAction, DiagnosticAction,
    StrategicAction, IncidentPhase,
)
from immunoorg.network_graph import NetworkGraph
from immunoorg.org_graph import OrgGraph
from immunoorg.reward import RewardCalculator
from immunoorg.belief_map import BeliefMap
from immunoorg.curriculum import CurriculumEngine


def test_network_graph_generation():
    """Test network graph generates valid topology."""
    for diff in [1, 2, 3, 4]:
        ng = NetworkGraph(difficulty=diff, seed=42)
        ng.generate_topology()
        nodes = ng.get_all_nodes()
        edges = ng.get_all_edges()
        assert len(nodes) > 0, f"No nodes at difficulty {diff}"
        assert len(edges) > 0, f"No edges at difficulty {diff}"
        assert all(n.health == 1.0 for n in nodes), "Initial health should be 1.0"
        print(f"  ✅ Difficulty {diff}: {len(nodes)} nodes, {len(edges)} edges")


def test_org_graph_generation():
    """Test org graph generates valid structure."""
    ng = NetworkGraph(difficulty=2, seed=42)
    ng.generate_topology()
    og = OrgGraph(difficulty=2, seed=42)
    og.generate_org_structure(list(ng.nodes.keys()))
    nodes = og.get_all_nodes()
    edges = og.get_all_edges()
    assert len(nodes) > 0
    assert len(edges) > 0
    efficiency = og.calculate_org_efficiency()
    assert 0.0 <= efficiency <= 1.0
    print(f"  ✅ {len(nodes)} departments, {len(edges)} channels, efficiency={efficiency:.2f}")


def test_environment_reset():
    """Test environment reset returns valid observation."""
    env = ImmunoOrgEnvironment(difficulty=1, seed=42)
    obs = env.reset()
    assert obs.current_phase == IncidentPhase.DETECTION
    assert obs.step_count == 0
    assert len(obs.visible_nodes) > 0
    assert len(obs.org_nodes) > 0
    assert obs.threat_level > 0  # Attack was launched
    print(f"  ✅ Reset OK: {len(obs.visible_nodes)} nodes, threat={obs.threat_level:.2f}")


def test_environment_step_tactical():
    """Test tactical actions execute correctly."""
    env = ImmunoOrgEnvironment(difficulty=1, seed=42)
    obs = env.reset()

    # Scan logs
    action = ImmunoAction(
        action_type=ActionType.TACTICAL,
        tactical_action=TacticalAction.SCAN_LOGS,
        target=obs.visible_nodes[0].id,
        reasoning="Scanning for attack indicators.",
    )
    obs2, reward, done = env.step(action)
    assert obs2.step_count == 1
    assert "Scanned" in obs2.action_result or "scan" in obs2.action_result.lower()
    print(f"  ✅ Scan logs: reward={reward:.3f}, result={obs2.action_result[:60]}")


def test_environment_step_diagnostic():
    """Test diagnostic actions."""
    env = ImmunoOrgEnvironment(difficulty=1, seed=42)
    obs = env.reset()

    action = ImmunoAction(
        action_type=ActionType.DIAGNOSTIC,
        diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
        target="",
        reasoning="Looking for organizational silos.",
    )
    obs2, reward, done = env.step(action)
    assert obs2.action_success
    print(f"  ✅ Identify silo: {obs2.action_result[:60]}")


def test_full_episode_level1():
    """Test a full episode at level 1."""
    env = ImmunoOrgEnvironment(difficulty=1, seed=42)
    obs = env.reset()

    actions = [
        ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.SCAN_LOGS,
                     target=obs.visible_nodes[0].id, reasoning="Scanning logs."),
        ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.TRACE_ATTACK_PATH,
                     target="", reasoning="Tracing attack."),
    ]

    # Find compromised node and isolate it
    for node in obs.visible_nodes:
        if node.compromised:
            actions.append(ImmunoAction(
                action_type=ActionType.TACTICAL, tactical_action=TacticalAction.ISOLATE_NODE,
                target=node.id, reasoning="Isolating compromised node.",
            ))
            break

    # RCA
    actions.append(ImmunoAction(
        action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.CORRELATE_FAILURE,
        target="", parameters={"technical_indicator": "attack", "organizational_flaw": "no_devsecops", "confidence": 0.7},
        reasoning="Correlating failure.",
    ))
    actions.append(ImmunoAction(
        action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
        target="", reasoning="Finding silos.",
    ))

    # Refactor
    actions.append(ImmunoAction(
        action_type=ActionType.STRATEGIC, strategic_action=StrategicAction.ESTABLISH_DEVSECOPS,
        target="dept-security", reasoning="Establishing DevSecOps.",
    ))

    # Validation
    actions.append(ImmunoAction(
        action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.MEASURE_ORG_LATENCY,
        target="", reasoning="Validating improvements.",
    ))

    total_reward = 0.0
    for i, action in enumerate(actions):
        obs, reward, done = env.step(action)
        total_reward += reward
        if done:
            break

    print(f"  ✅ Full episode: {env.state.step_count} steps, reward={total_reward:.3f}, "
          f"phase={obs.current_phase.value}, terminated={done}")


def test_curriculum_advancement():
    """Test curriculum level advancement."""
    ce = CurriculumEngine(start_level=1)
    # Simulate 3 successes
    for _ in range(3):
        result = ce.record_episode_result({
            "threats_contained_ratio": 1.0, "total_downtime": 5.0, "total_reward": 1.0
        })
    assert ce.current_level == 2, f"Should advance to level 2, got {ce.current_level}"
    print(f"  ✅ Curriculum advanced to level {ce.current_level}")


def test_belief_map_accuracy():
    """Test belief map scoring."""
    bm = BeliefMap()
    bm.set_ground_truth([{"vector": "sql_injection", "target": "db-01"}])

    # Agent guesses correctly
    bm.agent_correlate("sql_injection_on_db-01", "no_devsecops", 0.8, ["evidence"], 1.0)
    accuracy = bm.calculate_belief_accuracy()
    assert accuracy > 0, f"Accuracy should be > 0, got {accuracy}"
    print(f"  ✅ Belief accuracy: {accuracy:.2f}")


def test_reward_calculator():
    """Test reward computation."""
    rc = RewardCalculator()
    state = ImmunoOrgEnvironment(difficulty=1, seed=42)
    state.reset()
    action = ImmunoAction(
        action_type=ActionType.TACTICAL, tactical_action=TacticalAction.SCAN_LOGS,
        target="test", reasoning="Testing the reward function with a scan action.",
    )
    reward = rc.compute_step_reward(
        state=state.state, action=action, action_success=True,
        threats_before=1, threats_after=1, belief_accuracy=0.0,
        org_chaos=0.0, downtime_delta=0.0,
    )
    assert isinstance(reward, float)
    print(f"  ✅ Reward computed: {reward:.3f}")


def run_all_tests():
    print("=" * 60)
    print("ImmunoOrg Test Suite")
    print("=" * 60)

    tests = [
        ("Network Graph Generation", test_network_graph_generation),
        ("Org Graph Generation", test_org_graph_generation),
        ("Environment Reset", test_environment_reset),
        ("Tactical Actions", test_environment_step_tactical),
        ("Diagnostic Actions", test_environment_step_diagnostic),
        ("Full Episode Level 1", test_full_episode_level1),
        ("Curriculum Advancement", test_curriculum_advancement),
        ("Belief Map Accuracy", test_belief_map_accuracy),
        ("Reward Calculator", test_reward_calculator),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        print(f"\n🧪 {name}")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
