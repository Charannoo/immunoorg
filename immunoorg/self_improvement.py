"""
Self-Improvement Loop
=====================
Recursive cycle: contain → analyze → mutate org → generate harder attack → repeat.
Tracks generational improvement toward "Immunological Equilibrium".
"""

from __future__ import annotations

import copy
import random
from typing import Any

from immunoorg.models import (
    GenerationRecord, OrgEdge, OrgNode, SelfImprovementState,
)
from immunoorg.org_graph import OrgGraph


class SelfImprovementEngine:
    """Manages the recursive self-improvement loop."""

    def __init__(self, seed: int | None = None):
        self.state = SelfImprovementState()
        self.rng = random.Random(seed)
        self.equilibrium_threshold = 0.05  # Improvement rate below this = equilibrium

    def record_generation(
        self,
        org_graph: OrgGraph,
        attack_complexity: float,
        time_to_containment: float,
        total_reward: float,
        mutations: list[str],
        attack_vector: str | None = None,
    ) -> GenerationRecord:
        """Record the results of a generation."""
        record = GenerationRecord(
            generation=self.state.current_generation,
            org_graph_snapshot=[n.model_copy() for n in org_graph.get_all_nodes()],
            org_edges_snapshot=[e.model_copy() for e in org_graph.get_all_edges()],
            attack_complexity=attack_complexity,
            time_to_containment=time_to_containment,
            org_efficiency=org_graph.calculate_org_efficiency(),
            total_reward=total_reward,
            mutations_applied=mutations,
        )
        self.state.generations.append(record)

        # Track best configuration
        if total_reward > self.state.best_reward:
            self.state.best_reward = total_reward
            self.state.best_org_config = [n.model_copy() for n in org_graph.get_all_nodes()]
            self.state.best_org_edges = [e.model_copy() for e in org_graph.get_all_edges()]

        # Check for equilibrium
        self._check_equilibrium()

        self.state.current_generation += 1
        return record

    def _check_equilibrium(self) -> None:
        """Check if the system has reached immunological equilibrium."""
        if len(self.state.generations) < 3:
            return

        recent = self.state.generations[-3:]
        improvements = []
        for i in range(1, len(recent)):
            prev_reward = recent[i - 1].total_reward
            curr_reward = recent[i].total_reward
            if prev_reward != 0:
                improvement = (curr_reward - prev_reward) / abs(prev_reward)
            else:
                improvement = curr_reward
            improvements.append(improvement)

        avg_improvement = sum(improvements) / len(improvements)
        self.state.improvement_rate = avg_improvement

        if abs(avg_improvement) < self.equilibrium_threshold:
            self.state.equilibrium_reached = True

    def suggest_org_mutations(self, org_graph: OrgGraph, weaknesses: list[str]) -> list[dict[str, Any]]:
        """Suggest org graph mutations based on identified weaknesses."""
        mutations = []

        # Identify silos and suggest connections
        silos = org_graph.identify_silos()
        for silo_a, silo_b in silos:
            mutations.append({
                "type": "create_shortcut_edge",
                "source": silo_a,
                "target": silo_b,
                "reason": f"Bridge silo between {silo_a} and {silo_b}",
            })

        # Address specific weaknesses
        weakness_mutations = {
            "slow_approval": {"type": "reduce_bureaucracy", "reason": "Reduce approval latency"},
            "no_devsecops": {"type": "establish_devsecops", "reason": "Integrate security into dev pipeline"},
            "silo_security_engineering": {
                "type": "create_shortcut_edge",
                "source": "dept-security",
                "target": "dept-engineering",
                "reason": "Connect Security and Engineering",
            },
            "excessive_trust": {"type": "update_approval_protocol", "reason": "Tighten access controls"},
            "weak_monitoring": {"type": "create_incident_channel", "reason": "Add monitoring capability"},
        }

        for weakness in weaknesses:
            if weakness in weakness_mutations:
                mutations.append(weakness_mutations[weakness])

        return mutations

    def apply_mutations(self, org_graph: OrgGraph, mutations: list[dict[str, Any]]) -> list[str]:
        """Apply suggested mutations to the org graph."""
        applied = []
        for mutation in mutations:
            mut_type = mutation.get("type", "")
            if mut_type == "create_shortcut_edge":
                src = mutation.get("source", "")
                dst = mutation.get("target", "")
                if src and dst:
                    result = org_graph.create_shortcut_edge(src, dst)
                    if result:
                        applied.append(f"Created shortcut: {src} → {dst}")
            elif mut_type == "reduce_bureaucracy":
                for node in org_graph.get_all_nodes():
                    if node.active:
                        org_graph.reduce_bureaucracy(node.id)
                        applied.append(f"Reduced bureaucracy: {node.id}")
                        break
            elif mut_type == "establish_devsecops":
                # Create a cross-functional team bridging security and engineering
                sec = org_graph.get_node("dept-security")
                eng = org_graph.get_node("dept-engineering")
                if sec and eng:
                    org_graph.create_shortcut_edge(sec.id, eng.id)
                    org_graph.create_shortcut_edge(eng.id, sec.id)
                    applied.append("Established DevSecOps bridge")
            elif mut_type == "create_incident_channel":
                # Connect security to all departments with fast channels
                sec = org_graph.get_node("dept-security")
                if sec:
                    for node in org_graph.get_all_nodes():
                        if node.id != sec.id and node.active:
                            org_graph.create_shortcut_edge(sec.id, node.id)
                    applied.append("Created incident response channels")
            elif mut_type == "update_approval_protocol":
                for node in org_graph.get_all_nodes():
                    if node.active:
                        node.cooperation_threshold = max(0.2, node.cooperation_threshold - 0.1)
                applied.append("Updated approval protocols — lowered thresholds")

        return applied

    def get_improvement_trajectory(self) -> list[dict[str, float]]:
        """Get the improvement trajectory across generations."""
        return [
            {
                "generation": g.generation,
                "time_to_containment": g.time_to_containment,
                "org_efficiency": g.org_efficiency,
                "total_reward": g.total_reward,
                "attack_complexity": g.attack_complexity,
            }
            for g in self.state.generations
        ]

    def get_summary(self) -> dict[str, Any]:
        return {
            "current_generation": self.state.current_generation,
            "total_generations": len(self.state.generations),
            "equilibrium_reached": self.state.equilibrium_reached,
            "improvement_rate": self.state.improvement_rate,
            "best_reward": self.state.best_reward,
            "trajectory": self.get_improvement_trajectory(),
        }
