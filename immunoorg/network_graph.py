"""
Network Graph Engine
====================
Simulates the technical infrastructure layer with servers, APIs, ports,
cascading failures, and attack propagation.
"""

from __future__ import annotations

import random
from typing import Any

import networkx as nx

from immunoorg.models import (
    Attack, AttackVector, LogEntry, LogSeverity, NetworkEdge,
    NetworkNode, NodeType, PortState, PortStatus,
)


class NetworkGraph:
    """Manages the technical network topology and simulates infrastructure behavior."""

    def __init__(self, difficulty: int = 1, seed: int | None = None):
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.graph = nx.DiGraph()
        self.nodes: dict[str, NetworkNode] = {}
        self.edges: list[NetworkEdge] = []
        self.sim_time: float = 0.0

    def generate_topology(self) -> None:
        """Generate a realistic enterprise network topology based on difficulty."""
        tier_configs = {
            1: {"web": 2, "app": 2, "data": 1, "management": 1, "dmz": 1},
            2: {"web": 3, "app": 4, "data": 2, "management": 2, "dmz": 1},
            3: {"web": 4, "app": 6, "data": 3, "management": 3, "dmz": 2},
            4: {"web": 5, "app": 8, "data": 4, "management": 4, "dmz": 2},
        }
        config = tier_configs.get(self.difficulty, tier_configs[1])

        tier_type_map = {
            "web": [NodeType.SERVER, NodeType.LOAD_BALANCER],
            "app": [NodeType.SERVER, NodeType.API],
            "data": [NodeType.DATABASE, NodeType.SERVER],
            "management": [NodeType.SERVER, NodeType.ENDPOINT],
            "dmz": [NodeType.FIREWALL, NodeType.SERVER],
        }

        service_map = {
            NodeType.SERVER: ["nginx", "apache", "node"],
            NodeType.API: ["rest-api", "graphql", "grpc"],
            NodeType.DATABASE: ["mysql", "postgres", "redis", "mongodb"],
            NodeType.FIREWALL: ["iptables", "pfsense"],
            NodeType.LOAD_BALANCER: ["haproxy", "nginx-lb"],
            NodeType.ENDPOINT: ["workstation", "admin-console"],
        }

        port_map = {
            "nginx": [80, 443],
            "apache": [80, 443, 8080],
            "node": [3000, 8080],
            "rest-api": [8080, 8443],
            "graphql": [4000],
            "grpc": [50051],
            "mysql": [3306],
            "postgres": [5432],
            "redis": [6379],
            "mongodb": [27017],
            "iptables": [22],
            "pfsense": [443, 8443],
            "haproxy": [80, 443, 8404],
            "nginx-lb": [80, 443],
            "workstation": [3389, 22],
            "admin-console": [443, 8443],
        }

        node_counter = 0
        tier_nodes: dict[str, list[str]] = {}

        for tier, count in config.items():
            tier_nodes[tier] = []
            types = tier_type_map[tier]
            for i in range(count):
                node_type = types[i % len(types)]
                service = self.rng.choice(service_map[node_type])
                ports_for_service = port_map.get(service, [8080])

                node_id = f"{tier}-{node_type.value}-{node_counter:02d}"
                node_counter += 1

                ports = [
                    PortState(
                        port_number=p,
                        service=service,
                        status=PortStatus.OPEN,
                        vulnerability_score=self.rng.uniform(0.0, 0.4),
                    )
                    for p in ports_for_service
                ]

                criticality = {"data": 0.9, "management": 0.7, "app": 0.6, "web": 0.5, "dmz": 0.8}

                node = NetworkNode(
                    id=node_id,
                    name=f"{service}-{tier}-{i}",
                    type=node_type,
                    tier=tier,
                    ports=ports,
                    health=1.0,
                    services=[service],
                    criticality=criticality.get(tier, 0.5),
                )
                self.nodes[node_id] = node
                self.graph.add_node(node_id, tier=tier, type=node_type.value)
                tier_nodes[tier].append(node_id)

        # Create edges: dmz → web → app → data, management connects to all
        tier_order = ["dmz", "web", "app", "data"]
        for i in range(len(tier_order) - 1):
            src_tier = tier_order[i]
            dst_tier = tier_order[i + 1]
            for src in tier_nodes.get(src_tier, []):
                for dst in tier_nodes.get(dst_tier, []):
                    if self.rng.random() < 0.6:
                        edge = NetworkEdge(
                            source=src, target=dst,
                            bandwidth=self.rng.uniform(100, 10000),
                            latency=self.rng.uniform(0.1, 5.0),
                            encrypted=self.rng.random() > 0.2,
                        )
                        self.edges.append(edge)
                        self.graph.add_edge(src, dst, weight=edge.latency)

        # Management connects to a subset of all nodes
        for mgmt_node in tier_nodes.get("management", []):
            all_other = [n for n in self.nodes if n != mgmt_node]
            targets = self.rng.sample(all_other, min(len(all_other), 4 + self.difficulty))
            for t in targets:
                edge = NetworkEdge(
                    source=mgmt_node, target=t,
                    bandwidth=1000, latency=1.0, encrypted=True,
                )
                self.edges.append(edge)
                self.graph.add_edge(mgmt_node, t, weight=1.0)

    def get_node(self, node_id: str) -> NetworkNode | None:
        return self.nodes.get(node_id)

    def get_all_nodes(self) -> list[NetworkNode]:
        return list(self.nodes.values())

    def get_all_node_ids(self) -> list[str]:
        """Convenience helper: return all node IDs.
        
        Some higher-level modules/tests operate on IDs rather than full node objects.
        """
        return list(self.nodes.keys())

    def get_all_edges(self) -> list[NetworkEdge]:
        return list(self.edges)

    def compromise_node(self, node_id: str, vector: AttackVector, sim_time: float) -> bool:
        """Compromise a node with a given attack vector."""
        node = self.nodes.get(node_id)
        if not node or node.compromised or node.isolated:
            return False

        node.compromised = True
        node.compromised_at = sim_time
        node.attack_vector = vector
        node.health = max(0.0, node.health - self.rng.uniform(0.3, 0.7))

        # Generate attack log
        node.logs.append(LogEntry(
            timestamp=sim_time,
            severity=LogSeverity.CRITICAL,
            source=node_id,
            message=f"Compromised via {vector.value}",
            attack_indicator=True,
            indicator_confidence=0.3 + self.rng.uniform(0, 0.5),
        ))
        return True

    def propagate_attack(self, source_id: str, attack: Attack, sim_time: float) -> list[str]:
        """Propagate an attack from a compromised node to neighbors (cascading failure)."""
        newly_compromised = []
        neighbors = list(self.graph.successors(source_id))
        self.rng.shuffle(neighbors)

        propagation_chance = {1: 0.1, 2: 0.25, 3: 0.4, 4: 0.6}
        chance = propagation_chance.get(self.difficulty, 0.2)

        for neighbor in neighbors:
            target_node = self.nodes.get(neighbor)
            if not target_node or target_node.compromised or target_node.isolated:
                continue
            if self.rng.random() < chance:
                if self.compromise_node(neighbor, AttackVector.LATERAL_MOVEMENT, sim_time):
                    newly_compromised.append(neighbor)
                    # Add to attack lateral path
                    attack.lateral_path.append(neighbor)

        return newly_compromised

    def apply_damage_tick(self, sim_time: float) -> float:
        """Apply ongoing damage from compromised nodes. Returns total damage this tick."""
        damage = 0.0
        for node in self.nodes.values():
            if node.compromised and not node.isolated:
                dmg = node.criticality * 0.05
                node.health = max(0.0, node.health - dmg)
                damage += dmg
                # Generate warning logs with some noise
                if self.rng.random() < 0.3:
                    node.logs.append(LogEntry(
                        timestamp=sim_time,
                        severity=LogSeverity.WARNING,
                        source=node.id,
                        message=f"Anomalous activity detected on {node.services[0] if node.services else 'unknown'}",
                        attack_indicator=True,
                        indicator_confidence=self.rng.uniform(0.1, 0.6),
                    ))
            # Generate normal noise logs
            if self.rng.random() < 0.1:
                node.logs.append(LogEntry(
                    timestamp=sim_time,
                    severity=LogSeverity.INFO,
                    source=node.id,
                    message=self.rng.choice([
                        "Health check OK", "Routine maintenance log",
                        "Connection pool refresh", "Cache cleared",
                        "Backup checkpoint created",
                    ]),
                ))
        return damage

    def isolate_node(self, node_id: str) -> bool:
        """Isolate a node from the network."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        node.isolated = True
        return True

    def block_port(self, node_id: str, port_number: int) -> bool:
        """Block a specific port on a node."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        for port in node.ports:
            if port.port_number == port_number:
                port.status = PortStatus.BLOCKED
                return True
        return False

    def deploy_patch(self, node_id: str) -> bool:
        """Patch a node, reducing vulnerability scores."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        node.patched = True
        for port in node.ports:
            port.vulnerability_score = max(0.0, port.vulnerability_score - 0.3)
        if node.compromised:
            node.compromised = False
            node.attack_vector = None
            node.health = min(1.0, node.health + 0.3)
        return True

    def restore_backup(self, node_id: str) -> bool:
        """Restore a node from backup."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        node.health = 1.0
        node.compromised = False
        node.attack_vector = None
        node.isolated = False
        return True

    def rotate_credentials(self, node_id: str) -> bool:
        """Rotate credentials on a node."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        # Reduces effectiveness of credential-based attacks
        if node.attack_vector in (AttackVector.CREDENTIAL_STUFFING, AttackVector.PHISHING):
            node.compromised = False
            node.attack_vector = None
            node.health = min(1.0, node.health + 0.2)
        return True

    def scan_logs(self, node_id: str) -> list[LogEntry]:
        """Return logs for a node, including attack indicators."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return list(node.logs[-20:])  # Last 20 entries

    def get_network_health(self) -> dict[str, float]:
        """Get health summary by tier."""
        tier_health: dict[str, list[float]] = {}
        for node in self.nodes.values():
            if node.tier not in tier_health:
                tier_health[node.tier] = []
            tier_health[node.tier].append(node.health)

        return {
            tier: sum(healths) / len(healths) if healths else 1.0
            for tier, healths in tier_health.items()
        }

    def get_compromised_nodes(self) -> list[NetworkNode]:
        return [n for n in self.nodes.values() if n.compromised]

    def find_attack_path(self, source: str, target: str) -> list[str] | None:
        """Find shortest path between two nodes."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_vulnerable_nodes(self, threshold: float = 0.3) -> list[NetworkNode]:
        """Find nodes with high vulnerability scores."""
        vulnerable = []
        for node in self.nodes.values():
            max_vuln = max((p.vulnerability_score for p in node.ports), default=0.0)
            if max_vuln >= threshold:
                vulnerable.append(node)
        return vulnerable
