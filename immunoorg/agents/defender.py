"""
Defender Agent
==============
The primary LLM-driven agent that detects, contains, analyzes, and restructures.
"""

from __future__ import annotations

DEFENDER_SYSTEM_PROMPT = """You are the Chief Incident Response Officer of a simulated enterprise called ImmunoOrg.

You observe network telemetry and organizational structure in real-time. Your mission spans five phases:

1. **DETECTION**: Analyze logs, traffic patterns, and anomalies to identify active cyber-attacks.
2. **CONTAINMENT**: Take tactical actions (block ports, isolate nodes, quarantine traffic) to stop the attack from spreading.
3. **ROOT CAUSE ANALYSIS**: Correlate technical failures (e.g., SQL injection on a database) to organizational weaknesses (e.g., no DevSecOps integration, siloed departments).
4. **ORG REFACTOR**: Restructure the organizational graph to eliminate systemic vulnerabilities — merge departments, create shortcut communication channels, reduce bureaucracy.
5. **VALIDATION**: Verify that your changes improved resilience and the system is secure.

## CRITICAL CONSTRAINTS
- Every tactical action (block_port, isolate_node, etc.) requires APPROVAL from department heads.
- Department heads have CONFLICTING priorities (IT wants uptime, Security wants lockdown, Engineering wants velocity).
- Approval flows through the organizational graph — if there are silos (missing connections), approvals are SLOW or IMPOSSIBLE.
- The adversary ADAPTS to your actions. If you block one vector, they'll pivot.

## OUTPUT FORMAT
Respond with a JSON object:
```json
{
    "action_type": "tactical|strategic|diagnostic",
    "tactical_action": "block_port|isolate_node|scan_logs|...",
    "strategic_action": "merge_departments|create_shortcut_edge|...",
    "diagnostic_action": "correlate_failure|identify_silo|...",
    "target": "<node_id or department_id>",
    "secondary_target": "<optional, for merge/link operations>",
    "parameters": {},
    "reasoning": "<Your detailed chain-of-thought reasoning>"
}
```

## STRATEGY TIPS
- In DETECTION phase: Use scan_logs and trace_attack_path to understand the situation
- In CONTAINMENT: Prioritize isolating compromised nodes, but be aware of downtime costs
- In RCA: Use correlate_failure and identify_silo to build your world model
- In REFACTOR: Address root causes — if security and engineering are siloed, create a shortcut edge
- Think about BOTH technical AND organizational dimensions simultaneously
- Your reasoning quality is scored — explain WHY you take each action
"""

DEFENDER_FEW_SHOT_EXAMPLES = [
    {
        "observation_summary": "Web server web-server-01 shows anomalous SQL query patterns on port 3306. Threat level: 0.4. Phase: DETECTION.",
        "response": {
            "action_type": "diagnostic",
            "diagnostic_action": "scan_logs",
            "target": "web-server-01",
            "reasoning": "The anomalous SQL patterns on port 3306 suggest a potential SQL injection attack. I need to scan the logs first to confirm the attack vector and understand the scope before taking containment action. Premature containment without evidence could cause unnecessary downtime."
        }
    },
    {
        "observation_summary": "Confirmed SQL injection on db-server-01 via port 3306. Lateral movement detected to app-server-02. Threat level: 0.7. Phase: CONTAINMENT.",
        "response": {
            "action_type": "tactical",
            "tactical_action": "isolate_node",
            "target": "db-server-01",
            "reasoning": "The SQL injection on db-server-01 is confirmed and has already spread laterally to app-server-02. Priority is to isolate the source node (db-server-01) immediately to prevent further lateral movement. The data tier is critical, but the active breach poses a greater risk than temporary downtime. I'll address app-server-02 in the next step."
        }
    },
    {
        "observation_summary": "Attack contained. Belief map shows SQL injection correlated with missing DevSecOps. Security and Engineering departments have no direct communication channel (SILO). Phase: RCA.",
        "response": {
            "action_type": "diagnostic",
            "diagnostic_action": "identify_silo",
            "target": "dept-security",
            "reasoning": "The SQL injection succeeded because there's no DevSecOps integration — Security can't review Engineering's code before deployment. The root cause is organizational: Security and Engineering are siloed with no direct communication channel. I need to confirm this silo before proposing a structural fix."
        }
    },
]


def get_defender_prompt() -> str:
    """Get the full defender system prompt."""
    return DEFENDER_SYSTEM_PROMPT


def get_few_shot_examples() -> list[dict]:
    """Get few-shot examples for the defender agent."""
    return DEFENDER_FEW_SHOT_EXAMPLES


def format_observation_for_llm(observation: dict) -> str:
    """Format an observation into a human-readable prompt for the LLM."""
    parts = []

    parts.append(f"## Current Phase: {observation.get('current_phase', 'unknown').upper()}")
    parts.append(f"Step: {observation.get('step_count', 0)} | Sim Time: {observation.get('sim_time', 0):.1f}")
    parts.append(f"Threat Level: {observation.get('threat_level', 0):.2f}")
    parts.append(f"System Downtime: {observation.get('system_downtime', 0):.1f}")

    # Network health
    health = observation.get("network_health_summary", {})
    if health:
        parts.append("\n## Network Health")
        for tier, h in health.items():
            status = "🟢" if h > 0.8 else "🟡" if h > 0.5 else "🔴"
            parts.append(f"  {status} {tier}: {h:.0%}")

    # Detected attacks
    attacks = observation.get("detected_attacks", [])
    if attacks:
        parts.append(f"\n## Active Threats ({len(attacks)})")
        for atk in attacks:
            parts.append(f"  ⚠️ {atk.get('vector', '?')} on {atk.get('target_node', '?')} "
                        f"(severity: {atk.get('severity', 0):.2f})")

    # Recent logs
    logs = observation.get("recent_logs", [])
    if logs:
        parts.append(f"\n## Recent Logs ({len(logs)})")
        for log in logs[-5:]:
            indicator = "🚨" if log.get("attack_indicator") else "📋"
            parts.append(f"  {indicator} [{log.get('severity', 'info')}] {log.get('message', '')}")

    # Org structure
    org_nodes = observation.get("org_nodes", [])
    if org_nodes:
        parts.append(f"\n## Organization ({len(org_nodes)} departments)")
        for dept in org_nodes:
            parts.append(f"  🏢 {dept.get('name', '?')} — trust: {dept.get('trust_score', 0):.2f}, "
                        f"latency: {dept.get('response_latency', 0):.1f}")

    # Pending approvals
    approvals = observation.get("pending_approvals", [])
    if approvals:
        parts.append(f"\n## Pending Approvals ({len(approvals)})")
        for apr in approvals:
            parts.append(f"  ⏳ {apr.get('action_name', '?')} → {apr.get('approver', '?')} "
                        f"(status: {apr.get('status', '?')})")

    # Action result
    result = observation.get("action_result", "")
    if result:
        success = "✅" if observation.get("action_success") else "❌"
        parts.append(f"\n## Last Action Result: {success} {result}")

    # Belief map feedback
    feedback = observation.get("belief_map_feedback", "")
    if feedback:
        parts.append(f"\n## World Model Feedback: {feedback}")

    # Alerts
    alerts = observation.get("alerts", [])
    if alerts:
        parts.append("\n## Alerts & Intelligence")
        for alert in alerts:
            parts.append(f"  🔔 {alert}")
    
    # Board Directives
    directives = observation.get("directives", [])
    if directives:
        parts.append("\n## 👔 Board Directives (MUST FOLLOW)")
        for d in directives:
            parts.append(f"  📌 {d}")
    
    return "\n".join(parts)

