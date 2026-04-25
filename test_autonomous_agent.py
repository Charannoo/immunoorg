from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.agents.llm_agent import ImmunoDefenderAgent

def test_agent_autonomy():
    print("Testing Autonomous LLM Agent...")
    env = ImmunoOrgEnvironment(difficulty=1)
    agent = ImmunoDefenderAgent()
    
    obs = env.reset()
    
    # 1. Test Detection Phase (Heuristic)
    print("\n--- Phase: Detection ---")
    action = agent.act(obs)
    print(f"Agent reasoning: {action.reasoning}")
    print(f"Agent action: {action.action_type} - {action.diagnostic_action if action.action_type.name == 'DIAGNOSTIC' else 'N/A'}")
    obs, reward, done = env.step(action)

    # 2. Test RAG Influence
    print("\n--- Injecting RAG Signal ---")
    from immunoorg.models import Attack, AttackVector
    atk = Attack(vector=AttackVector.SQL_INJECTION, target_node="node-1", severity=0.8, stealth=0.0)
    env.attacks.active_attacks = [atk]

    
    # Step to update observation
    action = agent.act(obs)
    # We might need to step once to get the RAG alerts into the observation
    obs, reward, done = env.step(action)
    
    # Now act on the observation that contains RAG alerts
    action = agent.act(obs)
    print(f"RAG-driven reasoning: {action.reasoning}")
    print(f"RAG-driven action: {action.tactical_action if action.action_type.name == 'TACTICAL' else 'N/A'}")

    # 3. Test Board Directive Influence
    print("\n--- Injecting Board Directive ---")
    env.inject_directive("CRITICAL: Prioritize system availability over strict isolation.")
    
    # Update observation
    action = agent.act(obs)
    obs, reward, done = env.step(action)
    
    action = agent.act(obs)
    print(f"Directive-driven reasoning: {action.reasoning}")
    print(f"Directive-driven action: {action.tactical_action if action.action_type.name == 'TACTICAL' else 'N/A'}")

if __name__ == "__main__":
    test_agent_autonomy()
