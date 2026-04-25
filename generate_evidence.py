import json
from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import ImmunoAction, ActionType, TacticalAction, StrategicAction

def run_demo_episode():
    print("Generating Demo Evidence Episode...")
    env = ImmunoOrgEnvironment(difficulty=1)
    obs = env.reset()
    
    # We simulate a "smart" agent that takes a few strategic and tactical actions
    # to showcase the new features.
    demo_actions = [
        # 1. Initial scan (Diagnostic)
        ImmunoAction(
            action_type=ActionType.DIAGNOSTIC, 
            diagnostic_action="query_belief_map", 
            reasoning="Initial situational awareness check."
        ),
        # 2. Inject a Board Directive to show HITL ( Judge's Console )
        None, 
        # 3. Tactical response to a threat
        ImmunoAction(
            action_type=ActionType.TACTICAL, 
            tactical_action=TacticalAction.ISOLATE_NODE, 
            target="node-1", 
            reasoning="Containment of detected SQL Injection attack based on RAG intel."
        ),
        # 4. Strategic response to a silo
        ImmunoAction(
            action_type=ActionType.STRATEGIC, 
            strategic_action=StrategicAction.MERGE_DEPARTMENTS, 
            target="dept-security", 
            secondary="dept-engineering", 
            reasoning="Reducing organizational friction to accelerate response time."
        ),
        # 5. High-level response
        ImmunoAction(
            action_type=ActionType.TACTICAL, 
            tactical_action=TacticalAction.START_MIGRATION, 
            reasoning="Activating Polymorphic Migration to shift the attack surface."
        ),
    ]
    
    report = []
    report.append("=== IMMUNO-ORG INTELLIGENCE EVIDENCE REPORT ===\n")
    
    for i, action in enumerate(demo_actions):
        if action is None:
            # Simulate Directive Injection
            directive = "CRITICAL: Prioritize system availability over strict isolation."
            env.inject_directive(directive)
            report.append(f"[Step {i}] JUDGE'S CONSOLE: Injected Directive -> {directive}\n")
            continue
            
        obs, reward, done = env.step(action)
        
        # Capture evidence of the feature being used
        report.append(f"[Step {i}] ACTION: {action.reasoning}\n")
        report.append(f"Result: {obs.action_result}\n")
        
        # Evidence of RAG
        rag_alerts = [a for a in obs.alerts if "[RAG" in a]
        if rag_alerts:
            report.append(f"RAG Intelligence: {rag_alerts[0]}\n")
            
        # Evidence of Reasoning
        if env.state.reasoning_traces:
            last_trace = env.state.reasoning_traces[-1]
            report.append(f"Reasoning Trace: {last_trace.decision_trigger} -> {last_trace.rationale}\n")
            
        report.append("-" * 40 + "\n")
        
        if done:
            break

    # Evidence of Co-Evolution
    report.append("\n=== CO-EVOLUTIONARY PROGRESS ===\n")
    report.append(f"Final Adversary Difficulty: {env.attacks.difficulty:.2f}\n")
    report.append(f"Self-Improvement Generation: {env.self_improvement.state.current_generation}\n")
    
    final_report = "".join(report)
    with open("evidence_report.txt", "w", encoding="utf-8") as f:
        f.write(final_report)
    
    print("Evidence generated in evidence_report.txt")

if __name__ == "__main__":
    run_demo_episode()
