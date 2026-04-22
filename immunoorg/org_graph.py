"""
Organizational Graph Engine
============================
Simulates the company's departmental structure with communication channels,
trust weights, KPI conflicts, and bureaucracy latencies.
"""

from __future__ import annotations

import random
from typing import Any

import networkx as nx

from immunoorg.models import (
    DepartmentType, KPI, OrgEdge, OrgNode,
)


# Default department configurations
DEPARTMENT_CONFIGS: dict[DepartmentType, dict[str, Any]] = {
    DepartmentType.IT_OPS: {
        "name": "IT Operations",
        "kpis": [
            KPI(name="system_uptime", target_value=99.9, current_value=99.5, weight=1.0, direction="maximize"),
            KPI(name="mttr", target_value=15.0, current_value=30.0, weight=0.7, direction="minimize"),
        ],
        "approval_authority": ["isolate_node", "restore_backup", "deploy_patch", "enable_ids"],
        "response_latency": 1.0,
        "cooperation_threshold": 0.4,
        "budget": 150.0,
        "headcount": 15,
    },
    DepartmentType.SECURITY: {
        "name": "Cybersecurity",
        "kpis": [
            KPI(name="threats_neutralized", target_value=100.0, current_value=85.0, weight=1.0, direction="maximize"),
            KPI(name="false_positive_rate", target_value=5.0, current_value=12.0, weight=0.8, direction="minimize"),
        ],
        "approval_authority": ["block_port", "quarantine_traffic", "rotate_credentials", "snapshot_forensics"],
        "response_latency": 0.5,
        "cooperation_threshold": 0.3,
        "budget": 200.0,
        "headcount": 12,
    },
    DepartmentType.ENGINEERING: {
        "name": "Software Engineering",
        "kpis": [
            KPI(name="feature_velocity", target_value=20.0, current_value=18.0, weight=1.0, direction="maximize"),
            KPI(name="deploy_frequency", target_value=10.0, current_value=8.0, weight=0.6, direction="maximize"),
        ],
        "approval_authority": ["deploy_patch"],
        "response_latency": 2.0,
        "cooperation_threshold": 0.6,
        "budget": 300.0,
        "headcount": 40,
    },
    DepartmentType.DEVOPS: {
        "name": "DevOps",
        "kpis": [
            KPI(name="deployment_speed", target_value=5.0, current_value=8.0, weight=1.0, direction="minimize"),
            KPI(name="pipeline_reliability", target_value=99.0, current_value=96.0, weight=0.8, direction="maximize"),
        ],
        "approval_authority": ["deploy_patch", "restore_backup", "isolate_node"],
        "response_latency": 1.0,
        "cooperation_threshold": 0.4,
        "budget": 120.0,
        "headcount": 10,
    },
    DepartmentType.MANAGEMENT: {
        "name": "Executive Management",
        "kpis": [
            KPI(name="cost_efficiency", target_value=0.8, current_value=0.7, weight=1.0, direction="maximize"),
            KPI(name="risk_score", target_value=0.2, current_value=0.4, weight=0.9, direction="minimize"),
        ],
        "approval_authority": [
            "merge_departments", "split_department", "reassign_authority",
            "rewrite_policy", "add_cross_functional_team",
        ],
        "response_latency": 3.0,
        "cooperation_threshold": 0.5,
        "budget": 500.0,
        "headcount": 5,
    },
    DepartmentType.LEGAL: {
        "name": "Legal & Compliance",
        "kpis": [
            KPI(name="compliance_score", target_value=100.0, current_value=92.0, weight=1.0, direction="maximize"),
            KPI(name="audit_readiness", target_value=1.0, current_value=0.8, weight=0.7, direction="maximize"),
        ],
        "approval_authority": ["rewrite_policy", "update_approval_protocol"],
        "response_latency": 4.0,
        "cooperation_threshold": 0.7,
        "budget": 80.0,
        "headcount": 8,
    },
    DepartmentType.HR: {
        "name": "Human Resources",
        "kpis": [
            KPI(name="employee_satisfaction", target_value=85.0, current_value=72.0, weight=1.0, direction="maximize"),
            KPI(name="turnover_rate", target_value=5.0, current_value=12.0, weight=0.8, direction="minimize"),
        ],
        "approval_authority": ["merge_departments", "split_department"],
        "response_latency": 3.0,
        "cooperation_threshold": 0.5,
        "budget": 90.0,
        "headcount": 8,
    },
    DepartmentType.FINANCE: {
        "name": "Finance",
        "kpis": [
            KPI(name="budget_utilization", target_value=0.9, current_value=0.85, weight=1.0, direction="maximize"),
            KPI(name="cost_overrun", target_value=0.0, current_value=0.05, weight=0.9, direction="minimize"),
        ],
        "approval_authority": ["update_approval_protocol"],
        "response_latency": 2.5,
        "cooperation_threshold": 0.6,
        "budget": 100.0,
        "headcount": 10,
    },
}


class OrgGraph:
    """Manages the organizational structure with departments, communication channels, and trust."""

    def __init__(self, difficulty: int = 1, seed: int | None = None):
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.graph = nx.DiGraph()
        self.nodes: dict[str, OrgNode] = {}
        self.edges: list[OrgEdge] = []
        self._initial_edges_snapshot: list[OrgEdge] = []

    def generate_org_structure(self, network_node_ids: list[str]) -> None:
        """Generate the organizational structure and assign network nodes to departments."""
        # Departments to include based on difficulty
        dept_sets = {
            1: [DepartmentType.IT_OPS, DepartmentType.SECURITY, DepartmentType.MANAGEMENT],
            2: [DepartmentType.IT_OPS, DepartmentType.SECURITY, DepartmentType.ENGINEERING,
                DepartmentType.MANAGEMENT],
            3: [DepartmentType.IT_OPS, DepartmentType.SECURITY, DepartmentType.ENGINEERING,
                DepartmentType.DEVOPS, DepartmentType.MANAGEMENT, DepartmentType.LEGAL],
            4: list(DepartmentType),  # All departments
        }
        active_depts = dept_sets.get(self.difficulty, dept_sets[1])

        # Create department nodes
        for dept_type in active_depts:
            config = DEPARTMENT_CONFIGS[dept_type]
            node = OrgNode(
                id=f"dept-{dept_type.value}",
                name=config["name"],
                department_type=dept_type,
                trust_score=0.7 + self.rng.uniform(-0.1, 0.1),
                response_latency=config["response_latency"] * (1.0 + (self.difficulty - 1) * 0.3),
                cooperation_threshold=config["cooperation_threshold"],
                kpis=config["kpis"],
                approval_authority=config["approval_authority"],
                budget=config["budget"],
                headcount=config["headcount"],
            )
            self.nodes[node.id] = node
            self.graph.add_node(node.id, dept_type=dept_type.value)

        # Assign network nodes to departments
        self._assign_network_nodes(network_node_ids)

        # Create communication channels
        self._create_channels()
        self._initial_edges_snapshot = [e.model_copy() for e in self.edges]

    def _assign_network_nodes(self, network_node_ids: list[str]) -> None:
        """Assign network nodes to departments based on tier mappings."""
        tier_dept_map = {
            "web": DepartmentType.ENGINEERING,
            "app": DepartmentType.ENGINEERING,
            "data": DepartmentType.IT_OPS,
            "management": DepartmentType.IT_OPS,
            "dmz": DepartmentType.SECURITY,
        }
        for net_id in network_node_ids:
            parts = net_id.split("-")
            tier = parts[0] if parts else "app"
            dept_type = tier_dept_map.get(tier, DepartmentType.IT_OPS)
            dept_id = f"dept-{dept_type.value}"
            if dept_id in self.nodes:
                self.nodes[dept_id].technical_nodes_owned.append(net_id)
            else:
                # Fallback to IT ops
                fallback = f"dept-{DepartmentType.IT_OPS.value}"
                if fallback in self.nodes:
                    self.nodes[fallback].technical_nodes_owned.append(net_id)

    def _create_channels(self) -> None:
        """Create communication channels between departments."""
        node_ids = list(self.nodes.keys())
        # Standard channels based on organizational reality
        standard_channels = [
            (DepartmentType.IT_OPS, DepartmentType.SECURITY, 1.0, 0.7),
            (DepartmentType.IT_OPS, DepartmentType.DEVOPS, 0.5, 0.8),
            (DepartmentType.SECURITY, DepartmentType.MANAGEMENT, 2.0, 0.5),
            (DepartmentType.ENGINEERING, DepartmentType.DEVOPS, 0.5, 0.8),
            (DepartmentType.ENGINEERING, DepartmentType.MANAGEMENT, 2.5, 0.4),
            (DepartmentType.MANAGEMENT, DepartmentType.LEGAL, 1.5, 0.6),
            (DepartmentType.MANAGEMENT, DepartmentType.HR, 1.5, 0.6),
            (DepartmentType.MANAGEMENT, DepartmentType.FINANCE, 1.0, 0.7),
            (DepartmentType.LEGAL, DepartmentType.HR, 2.0, 0.5),
        ]

        for src_type, dst_type, base_latency, base_trust in standard_channels:
            src_id = f"dept-{src_type.value}"
            dst_id = f"dept-{dst_type.value}"
            if src_id in self.nodes and dst_id in self.nodes:
                latency = base_latency * (1.0 + (self.difficulty - 1) * 0.5)
                edge = OrgEdge(
                    source=src_id, target=dst_id,
                    latency=latency,
                    trust=base_trust + self.rng.uniform(-0.1, 0.1),
                    bandwidth=1.0,
                    formal=True,
                )
                self.edges.append(edge)
                self.graph.add_edge(src_id, dst_id, weight=latency)
                # Add reverse edge (bidirectional communication) with slightly more latency
                rev_edge = OrgEdge(
                    source=dst_id, target=src_id,
                    latency=latency * 1.2,
                    trust=base_trust + self.rng.uniform(-0.1, 0.1),
                    bandwidth=1.0,
                    formal=True,
                )
                self.edges.append(rev_edge)
                self.graph.add_edge(dst_id, src_id, weight=latency * 1.2)

        # At higher difficulty, intentionally create "silos" by removing some channels
        if self.difficulty >= 3:
            removable = [e for e in self.edges
                         if "security" in e.source and "engineering" in e.target
                         or "engineering" in e.source and "security" in e.target]
            for e in removable[:1]:
                e.active = False

    def get_node(self, node_id: str) -> OrgNode | None:
        return self.nodes.get(node_id)

    def get_all_nodes(self) -> list[OrgNode]:
        return list(self.nodes.values())

    def get_all_edges(self) -> list[OrgEdge]:
        return list(self.edges)

    def get_active_edges(self) -> list[OrgEdge]:
        return [e for e in self.edges if e.active]

    def find_approval_path(self, requester_id: str, action_name: str) -> list[str]:
        """Find the shortest approval path for an action through the org graph."""
        # Find which department can approve this action
        approvers = []
        for node in self.nodes.values():
            if action_name in node.approval_authority:
                approvers.append(node.id)

        if not approvers:
            return []

        # Build active-only graph
        active_graph = nx.DiGraph()
        for e in self.edges:
            if e.active:
                active_graph.add_edge(e.source, e.target, weight=e.latency)

        # Find shortest path to any approver
        best_path: list[str] = []
        best_cost = float("inf")
        for approver in approvers:
            try:
                path = nx.shortest_path(active_graph, requester_id, approver, weight="weight")
                cost = nx.shortest_path_length(active_graph, requester_id, approver, weight="weight")
                if cost < best_cost:
                    best_cost = cost
                    best_path = path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        return best_path

    def calculate_approval_latency(self, path: list[str]) -> float:
        """Calculate total latency for an approval path."""
        if len(path) < 2:
            return 0.0
        total = 0.0
        for i in range(len(path) - 1):
            for edge in self.edges:
                if edge.source == path[i] and edge.target == path[i + 1] and edge.active:
                    total += edge.latency
                    # Add node processing time
                    node = self.nodes.get(path[i + 1])
                    if node:
                        total += node.response_latency
                    break
        return total

    def merge_departments(self, dept_a_id: str, dept_b_id: str) -> OrgNode | None:
        """Merge two departments into one."""
        a = self.nodes.get(dept_a_id)
        b = self.nodes.get(dept_b_id)
        if not a or not b:
            return None

        merged = OrgNode(
            id=f"dept-merged-{a.department_type.value}-{b.department_type.value}",
            name=f"{a.name} + {b.name}",
            department_type=a.department_type,
            trust_score=(a.trust_score + b.trust_score) / 2,
            response_latency=min(a.response_latency, b.response_latency),
            cooperation_threshold=min(a.cooperation_threshold, b.cooperation_threshold),
            kpis=a.kpis + b.kpis,
            approval_authority=list(set(a.approval_authority + b.approval_authority)),
            budget=a.budget + b.budget,
            headcount=a.headcount + b.headcount,
            technical_nodes_owned=a.technical_nodes_owned + b.technical_nodes_owned,
        )

        # Deactivate old departments
        a.active = False
        b.active = False

        # Add merged dept
        self.nodes[merged.id] = merged
        self.graph.add_node(merged.id)

        # Rewire edges
        for edge in self.edges:
            if edge.source in (dept_a_id, dept_b_id):
                if edge.target not in (dept_a_id, dept_b_id):
                    new_edge = OrgEdge(
                        source=merged.id, target=edge.target,
                        latency=edge.latency * 0.7, trust=edge.trust, formal=True,
                    )
                    self.edges.append(new_edge)
                    self.graph.add_edge(merged.id, edge.target, weight=new_edge.latency)
            if edge.target in (dept_a_id, dept_b_id):
                if edge.source not in (dept_a_id, dept_b_id):
                    new_edge = OrgEdge(
                        source=edge.source, target=merged.id,
                        latency=edge.latency * 0.7, trust=edge.trust, formal=True,
                    )
                    self.edges.append(new_edge)
                    self.graph.add_edge(edge.source, merged.id, weight=new_edge.latency)

        return merged

    def create_shortcut_edge(self, src_id: str, dst_id: str) -> OrgEdge | None:
        """Create a new fast communication channel between departments."""
        if src_id not in self.nodes or dst_id not in self.nodes:
            return None
        edge = OrgEdge(
            source=src_id, target=dst_id,
            latency=0.5, trust=0.6, bandwidth=2.0,
            formal=False,
        )
        self.edges.append(edge)
        self.graph.add_edge(src_id, dst_id, weight=0.5)
        return edge

    def reduce_bureaucracy(self, dept_id: str) -> bool:
        """Reduce latency on all edges connected to a department."""
        node = self.nodes.get(dept_id)
        if not node:
            return False
        node.response_latency *= 0.6
        for edge in self.edges:
            if edge.source == dept_id or edge.target == dept_id:
                edge.latency *= 0.7
        return True

    def update_approval_protocol(self, dept_id: str, new_authorities: list[str]) -> bool:
        """Update what a department can approve."""
        node = self.nodes.get(dept_id)
        if not node:
            return False
        node.approval_authority = list(set(node.approval_authority + new_authorities))
        return True

    def calculate_org_efficiency(self) -> float:
        """Calculate overall organizational efficiency (0-1). Higher = better."""
        if not self.nodes:
            return 0.0

        active_nodes = [n for n in self.nodes.values() if n.active]
        if not active_nodes:
            return 0.0

        avg_latency = sum(n.response_latency for n in active_nodes) / len(active_nodes)
        avg_trust = sum(n.trust_score for n in active_nodes) / len(active_nodes)

        active_edges = self.get_active_edges()
        connectivity = len(active_edges) / max(1, len(active_nodes) * (len(active_nodes) - 1))

        # Efficiency: high trust, low latency, good connectivity
        latency_score = max(0.0, 1.0 - avg_latency / 10.0)
        efficiency = (avg_trust * 0.4 + latency_score * 0.4 + min(1.0, connectivity * 2) * 0.2)
        return min(1.0, max(0.0, efficiency))

    def calculate_org_chaos(self) -> float:
        """Calculate how much the org has changed from initial state (0=unchanged, 1=total chaos)."""
        if not self._initial_edges_snapshot:
            return 0.0
        initial_set = {(e.source, e.target) for e in self._initial_edges_snapshot}
        current_set = {(e.source, e.target) for e in self.edges if e.active}
        added = current_set - initial_set
        removed = initial_set - current_set
        total_changes = len(added) + len(removed)
        max_possible = max(1, len(initial_set) * 2)
        return min(1.0, total_changes / max_possible)

    def identify_silos(self) -> list[tuple[str, str]]:
        """Identify department pairs that should be connected but aren't."""
        silos = []
        critical_pairs = [
            (DepartmentType.SECURITY, DepartmentType.ENGINEERING),
            (DepartmentType.SECURITY, DepartmentType.DEVOPS),
            (DepartmentType.IT_OPS, DepartmentType.ENGINEERING),
        ]
        active_edges_set = {(e.source, e.target) for e in self.edges if e.active}
        for dept_a, dept_b in critical_pairs:
            id_a = f"dept-{dept_a.value}"
            id_b = f"dept-{dept_b.value}"
            if id_a in self.nodes and id_b in self.nodes:
                if (id_a, id_b) not in active_edges_set and (id_b, id_a) not in active_edges_set:
                    silos.append((id_a, id_b))
        return silos
