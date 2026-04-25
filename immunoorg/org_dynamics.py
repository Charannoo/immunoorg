"""
Dynamic Organizational Dynamics Engine
======================================
ImmunoOrg 2.0 - Phase 2: Dynamic Org Dynamics

Implements trust decay between departments based on:
- Denial of approval requests (trust decreases)
- Successful cooperation (trust increases)
- Time-based trust recovery
- Cascading trust effects in the network

This creates emergent organizational silos where:
- Repeated denials erode trust
- Trust loss increases latency and cooperation thresholds
- Agents must strategically rebuild trust to function effectively
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from immunoorg.models import OrgEdge, OrgNode


@dataclass
class TrustEvent:
    """Tracks a trust-affecting interaction between departments."""
    timestamp: float
    source_dept: str
    target_dept: str
    event_type: str  # "approval_granted", "approval_denied", "cooperation_successful", "recovery"
    severity: float  # 0-1, how much this event affects trust
    reason: str  # Why the event occurred


@dataclass
class DynamicTrustMetrics:
    """Metrics tracking trust dynamics."""
    trust_history: list[TrustEvent] = field(default_factory=list)
    denial_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    cooperation_successes: dict[tuple[str, str], int] = field(default_factory=dict)
    last_interaction: dict[tuple[str, str], float] = field(default_factory=dict)


class DynamicOrgDynamicsEngine:
    """
    Manages trust decay and recovery between departments over time.
    
    Trust equations:
    - Initial trust: 0.5-0.8 (from org_graph)
    - Denial impact: -0.05 * severity
    - Cooperation boost: +0.03 per successful interaction
    - Time decay: -0.02 per 10 simulation steps of inactivity
    - Recovery: Natural drift toward neutral (0.5) over long periods
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.metrics = DynamicTrustMetrics()
        self.trust_decay_rate = 0.02  # Per 10 simulation steps
        self.trust_recovery_rate = 0.01  # Per 10 simulation steps
        self.last_update_time = 0.0

    def record_approval_granted(
        self,
        source_dept: str,
        target_dept: str,
        severity: float = 1.0,
        sim_time: float = 0.0,
    ) -> None:
        """Record a successful approval."""
        event = TrustEvent(
            timestamp=sim_time,
            source_dept=source_dept,
            target_dept=target_dept,
            event_type="approval_granted",
            severity=severity,
            reason="Request approved successfully",
        )
        self.metrics.trust_history.append(event)
        self.metrics.last_interaction[(source_dept, target_dept)] = sim_time
        
        key = (source_dept, target_dept)
        self.metrics.cooperation_successes[key] = self.metrics.cooperation_successes.get(key, 0) + 1

    def record_approval_denied(
        self,
        source_dept: str,
        target_dept: str,
        reason: str = "Request denied",
        severity: float = 1.0,
        sim_time: float = 0.0,
    ) -> None:
        """
        Record a denied approval.
        Denials have stronger impact on trust than approvals.
        """
        event = TrustEvent(
            timestamp=sim_time,
            source_dept=source_dept,
            target_dept=target_dept,
            event_type="approval_denied",
            severity=severity,
            reason=reason,
        )
        self.metrics.trust_history.append(event)
        self.metrics.last_interaction[(source_dept, target_dept)] = sim_time
        
        key = (source_dept, target_dept)
        self.metrics.denial_counts[key] = self.metrics.denial_counts.get(key, 0) + 1

    def apply_trust_dynamics(
        self,
        edges: list[OrgEdge],
        nodes: dict[str, OrgNode],
        sim_time: float,
    ) -> None:
        """
        Apply trust decay, recovery, and cascading effects to the org graph.
        Called every step (or every N steps for efficiency).
        """
        time_delta = sim_time - self.last_update_time
        if time_delta < 1.0:  # Only update every 1.0 sim time units
            return
        
        update_cycles = int(time_delta / 1.0)
        
        for edge in edges:
            key = (edge.source, edge.target)
            
            # Count interactions
            denials = self.metrics.denial_counts.get(key, 0)
            successes = self.metrics.cooperation_successes.get(key, 0)
            last_interaction = self.metrics.last_interaction.get(key, sim_time)
            time_since_interaction = sim_time - last_interaction
            
            # Calculate trust delta
            trust_delta = 0.0
            
            # Denial-based decay
            if denials > 0:
                trust_delta -= min(0.15, denials * 0.05)  # Cap at -15%
            
            # Cooperation-based recovery
            if successes > 0:
                trust_delta += successes * 0.03
            
            # Time-based decay for inactive relationships
            inactivity_cycles = int(time_since_interaction / 1.0)
            if inactivity_cycles > 5:  # After 5 cycles of no interaction
                # Slow drift toward neutral
                neutral_value = 0.5
                trust_delta += (neutral_value - edge.trust) * 0.001 * update_cycles
            
            # Apply delta (bounded to [0, 1])
            new_trust = max(0.1, min(1.0, edge.trust + trust_delta))
            edge.trust = new_trust
            
            # Increase latency when trust is low
            # Low trust = more bureaucratic delays
            if edge.trust < 0.3:
                edge.latency *= 1.5
            elif edge.trust > 0.7:
                edge.latency *= 0.85
        
        self.last_update_time = sim_time

    def identify_trust_breakdown(self, edges: list[OrgEdge], threshold: float = 0.3) -> list[tuple[str, str]]:
        """Identify department pairs where trust has collapsed."""
        breakdown_pairs = []
        for edge in edges:
            if edge.trust < threshold and edge.active:
                breakdown_pairs.append((edge.source, edge.target))
        return breakdown_pairs

    def calculate_cascading_impact(
        self,
        source: str,
        target: str,
        nodes: dict[str, OrgNode],
        edges: list[OrgEdge],
    ) -> dict[str, Any]:
        """
        Calculate how a trust breakdown between two departments
        affects the broader org.
        """
        # Find all paths affected by this edge
        affected_paths = 0
        affected_departments = set()
        
        for edge in edges:
            if (edge.source == source and edge.target == target) or \
               (edge.source == target and edge.target == source):
                # This is one of the affected edges
                affected_paths += 1
                affected_departments.add(edge.source)
                affected_departments.add(edge.target)
        
        return {
            "affected_paths": affected_paths,
            "affected_departments": list(affected_departments),
            "cascade_severity": min(1.0, affected_paths * 0.1),
        }

    def get_trust_report(self) -> dict[str, Any]:
        """Generate a comprehensive trust dynamics report."""
        return {
            "total_events": len(self.metrics.trust_history),
            "total_denials": sum(self.metrics.denial_counts.values()),
            "total_successes": sum(self.metrics.cooperation_successes.values()),
            "denial_counts": dict(self.metrics.denial_counts),
            "cooperation_counts": dict(self.metrics.cooperation_successes),
        }
