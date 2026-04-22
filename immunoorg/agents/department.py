"""
Department Agents
=================
Siloed department agents with conflicting KPIs that approve/deny/delay
incident response actions based on their own priorities.
"""

from __future__ import annotations

import random
from typing import Any

from immunoorg.models import (
    ApprovalRequest, ApprovalStatus, DepartmentType, OrgNode,
)


# Department behavioral profiles
DEPARTMENT_PROFILES: dict[DepartmentType, dict[str, Any]] = {
    DepartmentType.IT_OPS: {
        "personality": "pragmatic",
        "primary_concern": "system_uptime",
        "resistant_to": ["isolate_node", "quarantine_traffic"],
        "eager_for": ["restore_backup", "deploy_patch"],
        "risk_tolerance": 0.5,
        "prompt": (
            "You are the IT Operations Director. Your primary KPI is system uptime (99.9% target). "
            "You resist actions that take systems offline but support quick fixes. "
            "When threat is high, you'll cooperate but push for minimal disruption."
        ),
    },
    DepartmentType.SECURITY: {
        "personality": "aggressive",
        "primary_concern": "threat_elimination",
        "resistant_to": [],
        "eager_for": ["block_port", "isolate_node", "quarantine_traffic", "rotate_credentials"],
        "risk_tolerance": 0.2,
        "prompt": (
            "You are the CISO. Threats must be eliminated immediately. You favor aggressive "
            "containment even at the cost of downtime. You approve most security actions quickly "
            "and push for stronger policies."
        ),
    },
    DepartmentType.ENGINEERING: {
        "personality": "resistant",
        "primary_concern": "feature_velocity",
        "resistant_to": ["rewrite_policy", "update_approval_protocol", "reduce_bureaucracy"],
        "eager_for": ["deploy_patch"],
        "risk_tolerance": 0.6,
        "prompt": (
            "You are the VP of Engineering. Your team ships features and meeting deadlines is critical. "
            "Security measures that slow deployment are unwelcome. You cooperate only when the threat "
            "is clearly severe and well-documented."
        ),
    },
    DepartmentType.DEVOPS: {
        "personality": "pragmatic",
        "primary_concern": "deployment_speed",
        "resistant_to": ["update_approval_protocol"],
        "eager_for": ["deploy_patch", "restore_backup", "enable_ids"],
        "risk_tolerance": 0.4,
        "prompt": (
            "You are the DevOps Lead. You value fast deployments and reliable pipelines. "
            "You support automated fixes but resist adding approval gates that slow things down."
        ),
    },
    DepartmentType.MANAGEMENT: {
        "personality": "cautious",
        "primary_concern": "cost_efficiency",
        "resistant_to": ["merge_departments", "add_cross_functional_team"],
        "eager_for": ["reduce_bureaucracy"],
        "risk_tolerance": 0.5,
        "prompt": (
            "You are the CEO. You care about the bottom line and risk management. "
            "Expensive responses need strong justification. You approve structural changes "
            "only when the risk-cost analysis is compelling."
        ),
    },
    DepartmentType.LEGAL: {
        "personality": "conservative",
        "primary_concern": "compliance",
        "resistant_to": ["reduce_bureaucracy"],
        "eager_for": ["rewrite_policy", "snapshot_forensics"],
        "risk_tolerance": 0.7,
        "prompt": (
            "You are the General Counsel. Every action must be documented and compliant. "
            "You demand justification before approving and insist on forensic evidence. "
            "You add delay but ensure legal protection."
        ),
    },
    DepartmentType.HR: {
        "personality": "protective",
        "primary_concern": "employee_satisfaction",
        "resistant_to": ["merge_departments", "split_department"],
        "eager_for": [],
        "risk_tolerance": 0.5,
        "prompt": (
            "You are the HR Director. Organizational changes affect employee morale. "
            "You resist rapid restructuring and advocate for change management processes. "
            "You cooperate on security but want employee impact minimized."
        ),
    },
    DepartmentType.FINANCE: {
        "personality": "analytical",
        "primary_concern": "budget_utilization",
        "resistant_to": ["add_cross_functional_team"],
        "eager_for": ["reduce_bureaucracy"],
        "risk_tolerance": 0.6,
        "prompt": (
            "You are the CFO. Every action has a cost. You support cost-effective responses "
            "but resist expensive measures unless the ROI is clear. You want data before decisions."
        ),
    },
}


class DepartmentAgent:
    """Simulates a department head's decision-making for approval requests."""

    def __init__(self, org_node: OrgNode, seed: int | None = None):
        self.node = org_node
        self.profile = DEPARTMENT_PROFILES.get(org_node.department_type, {})
        self.rng = random.Random(seed)
        self.approval_history: list[dict[str, Any]] = []

    def evaluate_request(self, request: ApprovalRequest, threat_level: float) -> ApprovalStatus:
        """Evaluate an approval request based on department KPIs and personality."""
        score = 0.5  # Base

        # Threat level influence
        score += threat_level * 0.3

        # Urgency influence
        score += request.urgency * 0.2

        # Trust influence
        score += self.node.trust_score * 0.1

        # Action preference
        if request.action_name in self.profile.get("eager_for", []):
            score += 0.2
        if request.action_name in self.profile.get("resistant_to", []):
            score -= 0.3

        # Risk tolerance
        risk_tol = self.profile.get("risk_tolerance", 0.5)
        if threat_level > risk_tol:
            score += 0.15  # High threat overrides resistance

        # Add some noise
        score += self.rng.uniform(-0.05, 0.05)

        # Decision
        if score >= self.node.cooperation_threshold:
            decision = ApprovalStatus.APPROVED
        elif score >= self.node.cooperation_threshold * 0.6:
            decision = ApprovalStatus.DELAYED
        else:
            decision = ApprovalStatus.DENIED

        self.approval_history.append({
            "request_id": request.id,
            "action": request.action_name,
            "score": score,
            "decision": decision.value,
            "threat_level": threat_level,
        })

        return decision

    def get_prompt(self) -> str:
        """Get the LLM prompt for this department agent."""
        return self.profile.get("prompt", f"You are the head of {self.node.name}.")

    def get_cooperation_rate(self) -> float:
        """Get historical cooperation rate."""
        if not self.approval_history:
            return 0.5
        approved = sum(1 for h in self.approval_history if h["decision"] == "approved")
        return approved / len(self.approval_history)


class DepartmentAgentPool:
    """Manages all department agents."""

    def __init__(self, org_nodes: list[OrgNode], seed: int | None = None):
        self.agents: dict[str, DepartmentAgent] = {}
        for node in org_nodes:
            self.agents[node.id] = DepartmentAgent(node, seed=seed)

    def get_agent(self, dept_id: str) -> DepartmentAgent | None:
        return self.agents.get(dept_id)

    def evaluate_all_pending(
        self, requests: list[ApprovalRequest], threat_level: float
    ) -> list[tuple[ApprovalRequest, ApprovalStatus]]:
        """Have all relevant department agents evaluate pending requests."""
        results = []
        for req in requests:
            agent = self.agents.get(req.approver)
            if agent:
                decision = agent.evaluate_request(req, threat_level)
                results.append((req, decision))
            else:
                results.append((req, ApprovalStatus.DENIED))
        return results

    def get_all_prompts(self) -> dict[str, str]:
        """Get prompts for all department agents."""
        return {dept_id: agent.get_prompt() for dept_id, agent in self.agents.items()}
