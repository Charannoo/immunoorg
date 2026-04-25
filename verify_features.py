from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import ImmunoAction, ActionType, TacticalAction

def test_features():
    print("Starting feature verification...")
    
    # 1. Test Environment Logic
    env = ImmunoOrgEnvironment(difficulty=1)
    obs = env.reset()
    
    # Force a detected attack to check RAG
    from immunoorg.models import Attack, AttackVector
    atk = Attack(vector=AttackVector.SQL_INJECTION, target_node="node-1", severity=0.5)
    env.attacks.active_attacks = [atk]
    
    # Step once to trigger observation build
    rag_found = False
    for _ in range(10):
        action = ImmunoAction(
            action_type=ActionType.DIAGNOSTIC, 
            diagnostic_action="query_belief_map", 
            reasoning="checking system state"
        )
        obs, reward, done = env.step(action)
        if any("[RAG RETRIEVAL" in alert for alert in obs.alerts):
            rag_found = True
            break
    
    print(f"RAG Integration: {'PASSED' if rag_found else 'FAILED'}")
    
    # Test Reasoning Traces
    trace_found = len(env.state.reasoning_traces) > 0
    print(f"Reasoning Traces: {'PASSED' if trace_found else 'FAILED'}")
    
    # Test Board Directives
    env.inject_directive("Prioritize Uptime")
    directive_found = "Prioritize Uptime" in env.state.directives
    print(f"Board Directives: {'PASSED' if directive_found else 'FAILED'}")
    
    # Test Adversary Evolution
    # Mock a high improvement rate
    env.self_improvement.state.improvement_rate = 0.2
    old_diff = env.attacks.difficulty
    env.attacks.evolve_adversary_complexity(0.2)
    evolved = env.attacks.difficulty > old_diff
    print(f"Adversary Evolution: {'PASSED' if evolved else 'FAILED'}")

if __name__ == "__main__":
    test_features()
