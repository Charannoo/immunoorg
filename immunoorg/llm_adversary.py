"""
LLM-Driven Adversary Engine
===========================
ImmunoOrg 2.0 - Phase 1: Adversarial Evolution

Upgrades the AttackEngine from template-based attacks to a reasoning-based adversary
that analyzes the network graph and adapts strategy based on observed defender actions.

The LLM adversary:
- Analyzes the network topology to identify crown jewels (data, management nodes)
- Plans multi-stage attack paths considering node compromise status
- Adapts tactics based on defender response patterns
- Generates novel attack combinations not in fixed templates
"""

from __future__ import annotations

import random
import json
from typing import Any
from dataclasses import dataclass

from immunoorg.models import (
    Attack, AttackVector, NetworkNode,
)
from immunoorg.network_graph import NetworkGraph


@dataclass
class AttackPlan:
    """A reasoned multi-stage attack plan."""
    attack_id: str
    primary_vector: AttackVector
    target_path: list[str]  # Chain of nodes to compromise
    estimated_success_rate: float
    stages: list[dict[str, Any]]  # Multi-stage breakdown
    rationale: str  # Why this plan is effective


class LLMAdversaryReasoner:
    """
    Simulates an LLM-driven adversary that reasons about network topology
    and generates adaptive attack plans.
    
    This is a *simulated* LLM (using heuristics) rather than calling
    a real LLM API, to keep the environment fast and deterministic.
    """

    def __init__(self, network: NetworkGraph, seed: int | None = None):
        self.network = network
        self.rng = random.Random(seed)
        self.attack_history: list[dict[str, Any]] = []
        self.observed_defenses: list[str] = []
        self.last_planned_attacks: list[AttackPlan] = []

    def identify_high_value_targets(self) -> list[NetworkNode]:
        """
        Identify the crown jewels in the network.
        High-value = data nodes, management nodes, high-criticality services.
        """
        nodes = self.network.get_all_nodes()
        scored = []
        
        for node in nodes:
            score = 0.0
            
            # Data tier is most valuable
            if node.tier == "data":
                score += 0.9
            # Management/control is also valuable
            elif node.tier == "management":
                score += 0.8
            # Compromised nodes are less valuable
            elif node.compromised:
                score -= 0.5
            # Isolated nodes are hard to reach
            elif node.isolated:
                score -= 0.3
            
            # Add service criticality
            critical_services = ["database", "auth", "admin", "backup"]
            for service in node.ports:
                if any(crit in service.service.lower() for crit in critical_services):
                    score += 0.2
            
            scored.append((node, score))
        
        # Sort by score, return top targets
        scored.sort(key=lambda x: x[1], reverse=True)
        return [node for node, score in scored if score > 0][:5]

    def plan_attack_path(self, target: NetworkNode) -> list[str]:
        """
        Plan an efficient path from external entry point to target.
        Considers already-compromised nodes as jumping points.
        """
        nodes = self.network.get_all_nodes()
        
        # Find compromised nodes (already in network)
        compromised = [n for n in nodes if n.compromised]
        
        # If we have compromised nodes, try to use them
        if compromised:
            closest = min(compromised, key=lambda n: abs(hash(n.tier) - hash(target.tier)))
            return [closest.id, target.id]
        
        # Otherwise, find entry point based on tier proximity
        dmz_nodes = [n for n in nodes if n.tier == "dmz" and not n.isolated]
        if dmz_nodes and target.tier != "dmz":
            entry = self.rng.choice(dmz_nodes)
            return [entry.id, target.id]
        
        return [target.id]

    def generate_attack_plan(
        self,
        difficulty: int,
        observed_defenses: list[str] | None = None,
    ) -> AttackPlan:
        """
        Generate a multi-stage attack plan based on network analysis.
        Adapts to observed defender patterns.
        """
        observed_defenses = observed_defenses or []
        
        # Identify targets
        targets = self.identify_high_value_targets()
        if not targets:
            # Fallback: any available node
            targets = [self.network.get_all_nodes()[0]] if self.network.get_all_nodes() else []
        
        if not targets:
            raise ValueError("No targets available in network")
        
        primary_target = targets[0]
        attack_path = self.plan_attack_path(primary_target)
        
        # Adapt vector based on observed defenses
        vector = self._select_vector_against_defenses(observed_defenses, difficulty)
        
        # Build multi-stage plan
        stages = self._plan_stages(vector, attack_path, difficulty)
        
        # Estimate success
        success_rate = self._estimate_success(vector, attack_path, observed_defenses)
        
        plan = AttackPlan(
            attack_id=f"plan-{self.rng.randint(10000, 99999)}",
            primary_vector=vector,
            target_path=attack_path,
            estimated_success_rate=success_rate,
            stages=stages,
            rationale=self._generate_rationale(vector, attack_path, observed_defenses),
        )
        
        self.last_planned_attacks.append(plan)
        return plan

    def _select_vector_against_defenses(self, observed_defenses: list[str], difficulty: int) -> AttackVector:
        """
        Choose attack vector that exploits gaps in observed defenses.
        If defender is blocking ports, use credential attacks.
        If defender is isolating nodes, use lateral movement.
        """
        defense_counter = {
            "block_port": [AttackVector.CREDENTIAL_STUFFING, AttackVector.PHISHING, AttackVector.SUPPLY_CHAIN],
            "isolate_node": [AttackVector.LATERAL_MOVEMENT, AttackVector.PRIVILEGE_ESCALATION],
            "deploy_ids": [AttackVector.APT_BACKDOOR, AttackVector.ZERO_DAY],
            "rotate_credentials": [AttackVector.RANSOMWARE, AttackVector.DDOS],
        }
        
        # If we've seen specific defenses, exploit gaps
        for defense in observed_defenses:
            if defense in defense_counter:
                return self.rng.choice(defense_counter[defense])
        
        # Default: choose vector for difficulty
        vectors_by_difficulty = {
            1: [AttackVector.SQL_INJECTION, AttackVector.XSS],
            2: [AttackVector.LATERAL_MOVEMENT, AttackVector.PRIVILEGE_ESCALATION],
            3: [AttackVector.RANSOMWARE, AttackVector.SUPPLY_CHAIN],
            4: [AttackVector.APT_BACKDOOR, AttackVector.ZERO_DAY],
        }
        candidates = vectors_by_difficulty.get(difficulty, [AttackVector.APT_BACKDOOR])
        return self.rng.choice(candidates)

    def _plan_stages(self, vector: AttackVector, target_path: list[str], difficulty: int) -> list[dict[str, Any]]:
        """
        Break down the attack into stages for multi-step exploitation.
        """
        stages = []
        
        # Stage 1: Reconnaissance
        stages.append({
            "name": "Reconnaissance",
            "description": "Scan target network for vulnerabilities",
            "duration": 1,
            "success_rate": 0.95,
        })
        
        # Stage 2: Initial Access
        stages.append({
            "name": "Initial Access",
            "description": f"Exploit {vector.value} to gain initial foothold",
            "duration": 2,
            "success_rate": 0.7 + (difficulty * 0.05),
            "vector": vector.value,
        })
        
        # Stage 3: Lateral Movement (if multi-hop path)
        if len(target_path) > 1:
            stages.append({
                "name": "Lateral Movement",
                "description": f"Pivot through {len(target_path) - 1} nodes to reach target",
                "duration": len(target_path),
                "success_rate": 0.6 + (difficulty * 0.08),
            })
        
        # Stage 4: Persistence
        if difficulty >= 3:
            stages.append({
                "name": "Persistence",
                "description": "Establish backdoor/C2 channel",
                "duration": 2,
                "success_rate": 0.8,
            })
        
        # Stage 5: Exfiltration
        stages.append({
            "name": "Data Exfiltration",
            "description": "Exfiltrate sensitive data",
            "duration": 1,
            "success_rate": 0.5 + (difficulty * 0.1),
        })
        
        return stages

    def _estimate_success(
        self,
        vector: AttackVector,
        target_path: list[str],
        observed_defenses: list[str],
    ) -> float:
        """
        Estimate likelihood of success based on path length and defenses.
        """
        # Base success: harder with longer paths
        base_success = 0.8 - (len(target_path) * 0.1)
        
        # Reduce for observed defenses
        defense_impact = len(observed_defenses) * 0.05
        
        return max(0.1, min(1.0, base_success - defense_impact))

    def _generate_rationale(self, vector: AttackVector, target_path: list[str], observed_defenses: list[str]) -> str:
        """
        Generate a human-readable explanation of the attack plan.
        """
        if len(target_path) == 1:
            return f"Direct exploit of {vector.value} on single target. No lateral movement required."
        else:
            hops = " → ".join(target_path)
            return f"Multi-stage attack: {vector.value} followed by lateral movement ({hops}). Observed defenses suggest this vector has lower coverage."

    def adapt_to_defender_action(self, action: str) -> None:
        """
        Learn from defender actions to improve future plans.
        """
        self.observed_defenses.append(action)
        
        # Bonus: increase stealth/difficulty of future attacks
        # (This would be reflected in next call to generate_attack_plan)


class LLMAdversary:
    """
    Wrapper that uses the LLMAdversaryReasoner to generate smarter attacks.
    Maintains compatibility with the original AttackEngine interface.
    """

    def __init__(self, network: NetworkGraph, difficulty: int = 1, seed: int | None = None):
        self.network = network
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.reasoner = LLMAdversaryReasoner(network, seed)
        self.current_plan: AttackPlan | None = None

    def generate_next_attack(self, sim_time: float) -> Attack:
        """
        Generate an attack using the LLM reasoner's plan.
        """
        # Generate a new plan if we don't have one
        if not self.current_plan:
            try:
                self.current_plan = self.reasoner.generate_attack_plan(
                    self.difficulty,
                    self.reasoner.observed_defenses,
                )
            except (ValueError, IndexError):
                # Fallback if network is empty
                raise ValueError("Cannot generate attack: empty network")
        
        plan = self.current_plan
        target = plan.target_path[-1] if plan.target_path else None
        
        attack = Attack(
            vector=plan.primary_vector,
            source_node="external",
            target_node=target or "",
            entry_point=f"{plan.primary_vector.value}",
            severity=min(1.0, 0.4 + (self.difficulty * 0.15)),
            started_at=sim_time,
            stealth=min(1.0, 0.3 + (self.difficulty * 0.15)),
            lateral_path=plan.target_path,
            metadata={
                "plan_id": plan.attack_id,
                "rationale": plan.rationale,
                "success_probability": plan.estimated_success_rate,
                "stages": [s["name"] for s in plan.stages],
            }
        )
        
        # Clear plan so next call generates a new one
        self.current_plan = None
        
        return attack

    def observe_defender_action(self, action: str) -> None:
        """
        Record defender action for adaptation.
        """
        self.reasoner.adapt_to_defender_action(action)

    def get_attack_rationale(self) -> str:
        """
        Get the reasoning behind the current/last attack plan.
        Useful for debugging and analysis.
        """
        if self.current_plan:
            return self.current_plan.rationale
        elif self.reasoner.last_planned_attacks:
            return self.reasoner.last_planned_attacks[-1].rationale
        return "No attack plan generated yet"
