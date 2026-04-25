"""
Baseline Agents for Benchmarking
=================================
Implements Random and Heuristic agents for performance comparison.
"""

from __future__ import annotations
import random
from immunoorg.models import (
    ImmunoAction, ImmunoObservation, ActionType,
    TacticalAction, StrategicAction, DiagnosticAction
)


class RandomAgent:
    """Takes uniformly random actions."""
    
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.action_history: list[ImmunoAction] = []
    
    def act(self, obs: ImmunoObservation) -> ImmunoAction:
        """Select a random action."""
        action_types = [ActionType.TACTICAL, ActionType.STRATEGIC, ActionType.DIAGNOSTIC]
        action_type = self.rng.choice(action_types)
        
        if action_type == ActionType.TACTICAL:
            tactical_actions = [a for a in TacticalAction]
            action = ImmunoAction(
                action_type=action_type,
                tactical_action=self.rng.choice(tactical_actions),
                target=f"node-{self.rng.randint(1, 5)}",
                reasoning="Random action"
            )
        elif action_type == ActionType.STRATEGIC:
            strategic_actions = [a for a in StrategicAction]
            action = ImmunoAction(
                action_type=action_type,
                strategic_action=self.rng.choice(strategic_actions),
                target=f"dept-{self.rng.choice(['security', 'engineering', 'devops', 'ops'])}",
                secondary_target=f"dept-{self.rng.choice(['security', 'engineering', 'devops', 'ops'])}",
                reasoning="Random action"
            )
        else:
            diagnostic_actions = [a for a in DiagnosticAction]
            action = ImmunoAction(
                action_type=action_type,
                diagnostic_action=self.rng.choice(diagnostic_actions),
                reasoning="Random action"
            )
        
        self.action_history.append(action)
        return action


class HeuristicAgent:
    """Uses simple heuristic rules based on phase and threat level."""
    
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.action_history: list[ImmunoAction] = []
    
    def act(self, obs: ImmunoObservation) -> ImmunoAction:
        """Select an action based on simple heuristics."""
        phase = obs.current_phase.value
        threat = obs.threat_level
        
        # Phase-based heuristics
        if phase == "detection":
            action = ImmunoAction(
                action_type=ActionType.DIAGNOSTIC,
                diagnostic_action=DiagnosticAction.QUERY_BELIEF_MAP,
                reasoning="Detection phase: gather information"
            )
        elif phase == "containment":
            # High threat → aggressive containment
            if threat > 0.6:
                action = ImmunoAction(
                    action_type=ActionType.TACTICAL,
                    tactical_action=TacticalAction.ISOLATE_NODE,
                    target="node-1",
                    reasoning="High threat: isolating"
                )
            else:
                action = ImmunoAction(
                    action_type=ActionType.TACTICAL,
                    tactical_action=TacticalAction.SCAN_LOGS,
                    target="node-1",
                    reasoning="Medium threat: scanning for details"
                )
        elif phase == "rca":
            action = ImmunoAction(
                action_type=ActionType.DIAGNOSTIC,
                diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
                reasoning="RCA phase: identifying organizational bottlenecks"
            )
        elif phase == "refactor":
            action = ImmunoAction(
                action_type=ActionType.STRATEGIC,
                strategic_action=StrategicAction.MERGE_DEPARTMENTS,
                target="dept-security",
                secondary_target="dept-engineering",
                reasoning="Refactor phase: restructuring org"
            )
        else:
            # Default: diagnostics
            action = ImmunoAction(
                action_type=ActionType.DIAGNOSTIC,
                diagnostic_action=DiagnosticAction.QUERY_BELIEF_MAP,
                reasoning="Default: gathering system state"
            )
        
        self.action_history.append(action)
        return action
