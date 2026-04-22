"""
Permission Flow Engine
======================
The critical linkage between Technical and Organizational layers.
Every tactical action requires authorization flowing through the Org Graph.
"""

from __future__ import annotations

import random
from typing import Any

from immunoorg.models import (
    ActionType, ApprovalRequest, ApprovalStatus, OrgNode, TacticalAction, StrategicAction,
)
from immunoorg.org_graph import OrgGraph


# Maps actions to the authority name used in department configs
ACTION_AUTHORITY_MAP: dict[str, str] = {
    TacticalAction.BLOCK_PORT.value: "block_port",
    TacticalAction.ISOLATE_NODE.value: "isolate_node",
    TacticalAction.SCAN_LOGS.value: "scan_logs",  # No approval needed
    TacticalAction.DEPLOY_PATCH.value: "deploy_patch",
    TacticalAction.QUARANTINE_TRAFFIC.value: "quarantine_traffic",
    TacticalAction.ESCALATE_ALERT.value: "escalate_alert",  # No approval needed
    TacticalAction.RESTORE_BACKUP.value: "restore_backup",
    TacticalAction.ROTATE_CREDENTIALS.value: "rotate_credentials",
    TacticalAction.ENABLE_IDS.value: "enable_ids",
    TacticalAction.SNAPSHOT_FORENSICS.value: "snapshot_forensics",
    StrategicAction.MERGE_DEPARTMENTS.value: "merge_departments",
    StrategicAction.CREATE_SHORTCUT_EDGE.value: "create_shortcut_edge",
    StrategicAction.UPDATE_APPROVAL_PROTOCOL.value: "update_approval_protocol",
    StrategicAction.SPLIT_DEPARTMENT.value: "split_department",
    StrategicAction.REASSIGN_AUTHORITY.value: "reassign_authority",
    StrategicAction.ADD_CROSS_FUNCTIONAL_TEAM.value: "add_cross_functional_team",
    StrategicAction.REDUCE_BUREAUCRACY.value: "reduce_bureaucracy",
    StrategicAction.CREATE_INCIDENT_CHANNEL.value: "create_incident_channel",
    StrategicAction.REWRITE_POLICY.value: "rewrite_policy",
    StrategicAction.ESTABLISH_DEVSECOPS.value: "establish_devsecops",
}

# Actions that don't need approval
NO_APPROVAL_ACTIONS = {"scan_logs", "escalate_alert", "query_belief_map", "correlate_failure",
                       "trace_attack_path", "audit_permissions", "measure_org_latency",
                       "identify_silo", "timeline_reconstruct", "vulnerability_scan"}


class PermissionFlowEngine:
    """Routes approval requests through the org graph and simulates bureaucratic delays."""

    def __init__(self, org_graph: OrgGraph, seed: int | None = None):
        self.org = org_graph
        self.rng = random.Random(seed)
        self.pending: list[ApprovalRequest] = []
        self.completed: list[ApprovalRequest] = []

    def needs_approval(self, action_name: str) -> bool:
        """Check if an action needs organizational approval."""
        return action_name not in NO_APPROVAL_ACTIONS

    def request_approval(
        self,
        action_name: str,
        action_type: ActionType,
        requester_dept: str,
        target: str,
        urgency: float,
        sim_time: float,
        justification: str = "",
    ) -> ApprovalRequest:
        """Create and route an approval request through the org graph."""
        authority = ACTION_AUTHORITY_MAP.get(action_name, action_name)
        path = self.org.find_approval_path(requester_dept, authority)

        if not path:
            # No path found — action might be self-approved by requester
            node = self.org.get_node(requester_dept)
            if node and authority in node.approval_authority:
                path = [requester_dept]
            else:
                # Denied — no authority path exists
                req = ApprovalRequest(
                    action_type=action_type,
                    action_name=action_name,
                    requester=requester_dept,
                    approver="none",
                    target=target,
                    status=ApprovalStatus.DENIED,
                    submitted_at=sim_time,
                    resolved_at=sim_time,
                    approval_path=[],
                    urgency=urgency,
                    justification=justification,
                )
                self.completed.append(req)
                return req

        approver = path[-1] if path else requester_dept
        latency = self.org.calculate_approval_latency(path)

        req = ApprovalRequest(
            action_type=action_type,
            action_name=action_name,
            requester=requester_dept,
            approver=approver,
            target=target,
            status=ApprovalStatus.PENDING,
            submitted_at=sim_time,
            approval_path=path,
            urgency=urgency,
            justification=justification,
        )
        self.pending.append(req)
        return req

    def process_pending(self, sim_time: float, threat_level: float) -> list[ApprovalRequest]:
        """Process all pending approvals. Returns newly resolved requests."""
        resolved = []
        still_pending = []

        for req in self.pending:
            latency = self.org.calculate_approval_latency(req.approval_path)

            # Urgency and threat level reduce effective latency
            effective_latency = latency * (1.0 - req.urgency * 0.3) * (1.0 - threat_level * 0.2)
            effective_latency = max(0.1, effective_latency)

            elapsed = sim_time - req.submitted_at
            if elapsed >= effective_latency:
                # Check if approver department cooperates
                approver_node = self.org.get_node(req.approver)
                decision = self._evaluate_approval(approver_node, req, threat_level)
                req.status = decision
                req.resolved_at = sim_time
                resolved.append(req)
                self.completed.append(req)
            else:
                still_pending.append(req)

        self.pending = still_pending
        return resolved

    def _evaluate_approval(
        self, approver: OrgNode | None, req: ApprovalRequest, threat_level: float
    ) -> ApprovalStatus:
        """Department agent decides whether to approve based on KPIs and trust."""
        if not approver:
            return ApprovalStatus.DENIED

        # High urgency + high threat = easier approval
        approval_score = req.urgency * 0.4 + threat_level * 0.3 + approver.trust_score * 0.3

        # KPI impact check — some actions hurt specific departments
        kpi_penalty = self._estimate_kpi_impact(approver, req.action_name)
        approval_score -= kpi_penalty

        # Check cooperation threshold
        if approval_score >= approver.cooperation_threshold:
            return ApprovalStatus.APPROVED
        elif approval_score >= approver.cooperation_threshold * 0.7:
            return ApprovalStatus.DELAYED
        else:
            return ApprovalStatus.DENIED

    def _estimate_kpi_impact(self, dept: OrgNode, action_name: str) -> float:
        """Estimate how much an action hurts a department's KPIs."""
        impact_map: dict[str, dict[str, float]] = {
            "isolate_node": {"system_uptime": 0.3, "feature_velocity": 0.2},
            "block_port": {"system_uptime": 0.1, "deployment_speed": 0.1},
            "quarantine_traffic": {"system_uptime": 0.2, "feature_velocity": 0.15},
            "merge_departments": {"employee_satisfaction": 0.3, "cost_efficiency": -0.1},
            "split_department": {"cost_efficiency": 0.2, "employee_satisfaction": 0.1},
            "reduce_bureaucracy": {"compliance_score": 0.2, "audit_readiness": 0.1},
            "rewrite_policy": {"deployment_speed": 0.15, "feature_velocity": 0.1},
        }

        impacts = impact_map.get(action_name, {})
        total_penalty = 0.0
        for kpi in dept.kpis:
            if kpi.name in impacts:
                total_penalty += impacts[kpi.name] * kpi.weight
        return total_penalty

    def get_average_approval_latency(self) -> float:
        """Get average latency across all completed approvals."""
        approved = [r for r in self.completed if r.status == ApprovalStatus.APPROVED and r.resolved_at]
        if not approved:
            return 0.0
        return sum(r.resolved_at - r.submitted_at for r in approved) / len(approved)

    def get_denial_rate(self) -> float:
        """Get the fraction of requests that were denied."""
        if not self.completed:
            return 0.0
        denied = sum(1 for r in self.completed if r.status == ApprovalStatus.DENIED)
        return denied / len(self.completed)
