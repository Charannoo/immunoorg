"""
ImmunoOrg Core Environment
==========================
OpenEnv Environment subclass orchestrating the dual-layer simulation.
"""

from __future__ import annotations
import json
import random
from typing import Any

from immunoorg.models import (
    ActionType, ApprovalStatus, Attack, AttackVector,
    ImmunoAction, ImmunoObservation, ImmunoState, IncidentPhase,
    TacticalAction, StrategicAction, DiagnosticAction,
)
from immunoorg.network_graph import NetworkGraph
from immunoorg.org_graph import OrgGraph
from immunoorg.permission_flow import PermissionFlowEngine
from immunoorg.attack_engine import AttackEngine
from immunoorg.belief_map import BeliefMap
from immunoorg.curriculum import CurriculumEngine
from immunoorg.reward import RewardCalculator
from immunoorg.agents.department import DepartmentAgentPool
from immunoorg.self_improvement import SelfImprovementEngine


class ImmunoOrgEnvironment:
    """The Self-Healing Autonomous Enterprise environment."""

    def __init__(self, difficulty: int = 1, seed: int | None = None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.curriculum = CurriculumEngine(start_level=difficulty)
        self.self_improvement = SelfImprovementEngine(seed=seed)
        self._state = ImmunoState()
        # Sub-engines initialized on reset
        self.network: NetworkGraph | None = None
        self.org: OrgGraph | None = None
        self.permissions: PermissionFlowEngine | None = None
        self.attacks: AttackEngine | None = None
        self.belief_map: BeliefMap | None = None
        self.reward_calc: RewardCalculator | None = None
        self.dept_agents: DepartmentAgentPool | None = None
        self._pending_actions: dict[str, ImmunoAction] = {}  # approval_id -> action

    @property
    def state(self) -> ImmunoState:
        return self._state

    def reset(self, task: str | None = None) -> ImmunoObservation:
        """Initialize a new episode."""
        config = self.curriculum.get_current_config()
        s = self.rng.randint(0, 999999) if self.seed is None else self.seed

        # Initialize sub-engines
        self.network = NetworkGraph(difficulty=config.level, seed=s)
        self.network.generate_topology()

        self.org = OrgGraph(difficulty=config.level, seed=s)
        self.org.generate_org_structure(list(self.network.nodes.keys()))

        self.permissions = PermissionFlowEngine(self.org, seed=s)
        self.attacks = AttackEngine(self.network, difficulty=config.level, seed=s)
        self.belief_map = BeliefMap()
        self.reward_calc = RewardCalculator(config.reward_coefficients)
        self.dept_agents = DepartmentAgentPool(self.org.get_all_nodes(), seed=s)

        # Reset state
        self._state = ImmunoState(
            max_steps=config.max_steps,
            difficulty_level=config.level,
            network_nodes=self.network.get_all_nodes(),
            network_edges=self.network.get_all_edges(),
            org_nodes=self.org.get_all_nodes(),
            org_edges=self.org.get_all_edges(),
            current_phase=IncidentPhase.DETECTION,
            self_improvement_generation=self.self_improvement.state.current_generation,
        )

        # Generate initial attack
        initial_attack = self.attacks.generate_initial_attack(sim_time=0.0)
        self._state.active_attacks = [initial_attack]
        self._state.threat_level = initial_attack.severity

        # Set ground truth correlations
        self.belief_map.set_ground_truth([{
            "vector": initial_attack.vector.value,
            "target": initial_attack.target_node,
        }])
        self._state.ground_truth_correlations = self.belief_map.ground_truth

        # Record phase
        self._state.phase_history.append({"phase": IncidentPhase.DETECTION.value, "step": 0})

        return self._build_observation("Episode started. Threat detected.", True)

    def step(self, action: ImmunoAction) -> tuple[ImmunoObservation, float, bool]:
        """Process one step."""
        self._state.step_count += 1
        self._state.sim_time += 1.0
        threats_before = len(self.attacks.get_active_attacks())

        # 1. Process the action
        result, success = self._execute_action(action)

        # 2. Adversary reacts
        self.attacks.adversary_tick(self._state.sim_time)
        action_name = self._get_action_name(action)
        self.attacks.observe_defender_action(action_name)

        # 3. Apply damage tick
        damage = self.network.apply_damage_tick(self._state.sim_time)
        self._state.total_damage += damage
        if damage > 0:
            self._state.total_downtime += 1.0

        # 4. Process pending approvals — execute approved actions
        resolved = self.permissions.process_pending(self._state.sim_time, self._state.threat_level)
        for req in resolved:
            self._state.completed_approvals.append(req)
            if req.status == ApprovalStatus.APPROVED and req.id in self._pending_actions:
                pending_action = self._pending_actions.pop(req.id)
                self._execute_direct(pending_action)

        # 5. Update state
        self._state.network_nodes = self.network.get_all_nodes()
        self._state.active_attacks = self.attacks.active_attacks
        self._state.contained_attacks = self.attacks.contained_attacks
        self._state.org_nodes = self.org.get_all_nodes()
        self._state.org_edges = self.org.get_all_edges()
        self._state.pending_approvals = self.permissions.pending
        self._state.agent_belief_map = self.belief_map.state

        # Update threat level
        active = self.attacks.get_active_attacks()
        self._state.threat_level = max((a.severity for a in active), default=0.0)

        # Update org chaos
        self._state.org_chaos_score = self.org.calculate_org_chaos()

        # 6. Phase transitions
        self._check_phase_transition()

        # 7. Calculate reward
        threats_after = len(self.attacks.get_active_attacks())
        belief_accuracy = self.belief_map.calculate_belief_accuracy()
        reward = self.reward_calc.compute_step_reward(
            state=self._state, action=action, action_success=success,
            threats_before=threats_before, threats_after=threats_after,
            belief_accuracy=belief_accuracy,
            org_chaos=self._state.org_chaos_score,
            downtime_delta=1.0 if damage > 0 else 0.0,
        )
        self._state.cumulative_reward += reward

        # 8. Check termination
        terminated = self._check_termination()
        if terminated:
            episode_reward = self.reward_calc.compute_episode_reward(
                self._state, belief_accuracy, self.org.calculate_org_efficiency()
            )
            reward += episode_reward
            self._state.cumulative_reward += episode_reward

            # Record in curriculum
            metrics = {
                "threats_contained_ratio": len(self._state.contained_attacks) / max(1, len(self._state.contained_attacks) + len(self.attacks.get_active_attacks())),
                "total_downtime": self._state.total_downtime,
                "total_reward": self._state.cumulative_reward,
                "belief_accuracy": belief_accuracy,
                "org_efficiency": self.org.calculate_org_efficiency(),
            }
            self.curriculum.record_episode_result(metrics)

            # Record in self-improvement
            self.self_improvement.record_generation(
                org_graph=self.org,
                attack_complexity=self._state.threat_level,
                time_to_containment=self._state.sim_time,
                total_reward=self._state.cumulative_reward,
                mutations=[],
            )

        obs = self._build_observation(result, success)
        return obs, reward, terminated

    def _execute_action(self, action: ImmunoAction) -> tuple[str, bool]:
        """Execute the agent's action and return (result_description, success)."""
        action_name = self._get_action_name(action)

        # Diagnostic actions don't need approval
        if action.action_type == ActionType.DIAGNOSTIC:
            return self._execute_diagnostic(action)

        # Check if approval needed
        if not self.permissions.needs_approval(action_name):
            return self._execute_direct(action)

        # Find requesting department — pick the dept that owns the target node, or security
        requester = "dept-security"
        for dept in self.org.get_all_nodes():
            if dept.active and action.target in dept.technical_nodes_owned:
                requester = dept.id
                break

        req = self.permissions.request_approval(
            action_name=action_name,
            action_type=action.action_type,
            requester_dept=requester,
            target=action.target,
            urgency=min(1.0, self._state.threat_level + 0.3),
            sim_time=self._state.sim_time,
            justification=action.reasoning,
        )

        # Immediate check — also try processing pending right away at high threat
        if req.status == ApprovalStatus.APPROVED:
            return self._execute_direct(action)
        elif req.status == ApprovalStatus.DENIED:
            # At high threat levels, security overrides denial
            if self._state.threat_level >= 0.5:
                return self._execute_direct(action)
            return f"Action '{action_name}' DENIED by {req.approver}.", False
        else:
            # Store pending action for execution when approved
            self._pending_actions[req.id] = action
            # At high urgency, fast-track: execute immediately with delay penalty
            if self._state.threat_level >= 0.4:
                return self._execute_direct(action)
            return f"Action '{action_name}' submitted for approval. Waiting...", False

    def _execute_direct(self, action: ImmunoAction) -> tuple[str, bool]:
        """Execute an action that has been approved or doesn't need approval."""
        if action.action_type == ActionType.TACTICAL:
            return self._execute_tactical(action)
        elif action.action_type == ActionType.STRATEGIC:
            return self._execute_strategic(action)
        return "Unknown action type", False

    def _execute_tactical(self, action: ImmunoAction) -> tuple[str, bool]:
        t = action.tactical_action
        target = action.target
        if t == TacticalAction.BLOCK_PORT:
            port = action.parameters.get("port_number", 0)
            ok = self.network.block_port(target, port)
            # Check if this contains an attack
            for atk in self.attacks.get_active_attacks():
                if atk.target_node == target and str(port) in atk.entry_point:
                    self.attacks.contain_attack(atk.id, self._state.sim_time)
            return f"Port {port} blocked on {target}" if ok else f"Failed to block port on {target}", ok
        elif t == TacticalAction.ISOLATE_NODE:
            ok = self.network.isolate_node(target)
            for atk in self.attacks.get_active_attacks():
                if atk.target_node == target or target in atk.lateral_path:
                    self.attacks.contain_attack(atk.id, self._state.sim_time)
                    self._state.correct_identifications += 1
            return f"Node {target} isolated" if ok else f"Failed to isolate {target}", ok
        elif t == TacticalAction.SCAN_LOGS:
            logs = self.network.scan_logs(target)
            attack_logs = [l for l in logs if l.attack_indicator]
            return f"Scanned {len(logs)} logs on {target}. Found {len(attack_logs)} attack indicators.", True
        elif t == TacticalAction.DEPLOY_PATCH:
            ok = self.network.deploy_patch(target)
            return f"Patch deployed on {target}" if ok else f"Failed to patch {target}", ok
        elif t == TacticalAction.RESTORE_BACKUP:
            ok = self.network.restore_backup(target)
            return f"Backup restored on {target}" if ok else f"Failed to restore {target}", ok
        elif t == TacticalAction.ROTATE_CREDENTIALS:
            ok = self.network.rotate_credentials(target)
            return f"Credentials rotated on {target}" if ok else f"Failed to rotate on {target}", ok
        elif t == TacticalAction.QUARANTINE_TRAFFIC:
            ok = self.network.isolate_node(target)
            return f"Traffic quarantined on {target}" if ok else f"Failed to quarantine {target}", ok
        elif t == TacticalAction.ESCALATE_ALERT:
            self._state.threat_level = min(1.0, self._state.threat_level + 0.1)
            return f"Alert escalated. Threat level increased to {self._state.threat_level:.2f}", True
        elif t == TacticalAction.ENABLE_IDS:
            return f"IDS enabled on {target}. Enhanced detection active.", True
        elif t == TacticalAction.SNAPSHOT_FORENSICS:
            return f"Forensic snapshot captured for {target}.", True
        return "Unknown tactical action", False

    def _execute_strategic(self, action: ImmunoAction) -> tuple[str, bool]:
        s = action.strategic_action
        target = action.target
        secondary = action.secondary_target
        self._state.org_changes_made += 1
        if s == StrategicAction.MERGE_DEPARTMENTS:
            result = self.org.merge_departments(target, secondary or "")
            return (f"Merged {target} and {secondary}" if result else "Merge failed"), result is not None
        elif s == StrategicAction.CREATE_SHORTCUT_EDGE:
            result = self.org.create_shortcut_edge(target, secondary or "")
            return (f"Shortcut created: {target} → {secondary}" if result else "Shortcut failed"), result is not None
        elif s == StrategicAction.REDUCE_BUREAUCRACY:
            ok = self.org.reduce_bureaucracy(target)
            return f"Bureaucracy reduced for {target}" if ok else "Failed", ok
        elif s == StrategicAction.UPDATE_APPROVAL_PROTOCOL:
            auths = action.parameters.get("new_authorities", [])
            ok = self.org.update_approval_protocol(target, auths)
            return f"Approval protocol updated for {target}" if ok else "Failed", ok
        elif s == StrategicAction.CREATE_INCIDENT_CHANNEL:
            self.org.create_shortcut_edge("dept-security", target)
            return f"Incident channel created: security → {target}", True
        elif s == StrategicAction.ESTABLISH_DEVSECOPS:
            self.org.create_shortcut_edge("dept-security", "dept-engineering")
            self.org.create_shortcut_edge("dept-engineering", "dept-security")
            return "DevSecOps integration established", True
        elif s == StrategicAction.REWRITE_POLICY:
            for node in self.org.get_all_nodes():
                if node.active:
                    node.cooperation_threshold = max(0.2, node.cooperation_threshold - 0.1)
            return "Company policies rewritten — cooperation thresholds lowered", True
        elif s == StrategicAction.ADD_CROSS_FUNCTIONAL_TEAM:
            return "Cross-functional incident response team created", True
        elif s == StrategicAction.SPLIT_DEPARTMENT:
            return f"Department {target} split", True
        elif s == StrategicAction.REASSIGN_AUTHORITY:
            return f"Authority reassigned for {target}", True
        return "Unknown strategic action", False

    def _execute_diagnostic(self, action: ImmunoAction) -> tuple[str, bool]:
        d = action.diagnostic_action
        if d == DiagnosticAction.QUERY_BELIEF_MAP:
            feedback = self.belief_map.generate_feedback()
            return f"Belief Map: {feedback}", True
        elif d == DiagnosticAction.CORRELATE_FAILURE:
            tech = action.parameters.get("technical_indicator", action.target)
            org_flaw = action.parameters.get("organizational_flaw", "")
            confidence = action.parameters.get("confidence", 0.5)
            evidence = action.parameters.get("evidence", [action.reasoning])
            self.belief_map.agent_correlate(tech, org_flaw, confidence, evidence, self._state.sim_time)
            accuracy = self.belief_map.calculate_belief_accuracy()
            return f"Correlation recorded. Belief accuracy: {accuracy:.1%}", True
        elif d == DiagnosticAction.TRACE_ATTACK_PATH:
            active = self.attacks.get_active_attacks()
            paths = []
            for atk in active:
                paths.append(f"{atk.vector.value}: {' → '.join(atk.lateral_path)}")
            return f"Attack paths: {'; '.join(paths) if paths else 'No active attacks'}", True
        elif d == DiagnosticAction.IDENTIFY_SILO:
            silos = self.org.identify_silos()
            self.belief_map.update_silo_identification(silos)
            silo_strs = [f"{a}↔{b}" for a, b in silos]
            return f"Silos identified: {', '.join(silo_strs) if silo_strs else 'None found'}", True
        elif d == DiagnosticAction.MEASURE_ORG_LATENCY:
            efficiency = self.org.calculate_org_efficiency()
            avg_latency = self.permissions.get_average_approval_latency()
            return f"Org efficiency: {efficiency:.1%}, Avg approval latency: {avg_latency:.1f}", True
        elif d == DiagnosticAction.AUDIT_PERMISSIONS:
            denial_rate = self.permissions.get_denial_rate()
            return f"Permission audit: {denial_rate:.0%} denial rate", True
        elif d == DiagnosticAction.TIMELINE_RECONSTRUCT:
            history = self.attacks.attack_history
            return f"Timeline: {json.dumps(history[-10:], default=str)}", True
        elif d == DiagnosticAction.VULNERABILITY_SCAN:
            vulns = self.network.get_vulnerable_nodes()
            vuln_strs = [f"{n.id} (max_vuln={max((p.vulnerability_score for p in n.ports), default=0):.2f})" for n in vulns]
            return f"Vulnerable nodes: {', '.join(vuln_strs) if vuln_strs else 'None'}", True
        return "Unknown diagnostic action", False

    def _get_action_name(self, action: ImmunoAction) -> str:
        if action.tactical_action:
            return action.tactical_action.value
        if action.strategic_action:
            return action.strategic_action.value
        if action.diagnostic_action:
            return action.diagnostic_action.value
        return ""

    def _check_phase_transition(self) -> None:
        """Auto-transition between incident phases based on state and progress."""
        phase = self._state.current_phase
        active_attacks = self.attacks.get_active_attacks()
        step = self._state.step_count

        if phase == IncidentPhase.DETECTION:
            # Move to containment when: attack contained OR enough detection steps done
            if len(self._state.contained_attacks) > 0 or step >= 3:
                self._transition_phase(IncidentPhase.CONTAINMENT)
        elif phase == IncidentPhase.CONTAINMENT:
            # Move to RCA when: all attacks contained OR enough containment effort
            if len(active_attacks) == 0 or self._state.correct_identifications > 0:
                self._transition_phase(IncidentPhase.ROOT_CAUSE_ANALYSIS)
        elif phase == IncidentPhase.ROOT_CAUSE_ANALYSIS:
            # Move to refactor when belief map has some accuracy OR correlations exist
            if (self.belief_map.calculate_belief_accuracy() >= 0.3
                    or len(self.belief_map.state.correlations) >= 1):
                self._transition_phase(IncidentPhase.ORG_REFACTOR)
        elif phase == IncidentPhase.ORG_REFACTOR:
            if self._state.org_changes_made >= 1:
                self._transition_phase(IncidentPhase.VALIDATION)

    def _transition_phase(self, new_phase: IncidentPhase) -> None:
        if new_phase != self._state.current_phase:
            self._state.current_phase = new_phase
            self._state.phase_history.append({"phase": new_phase.value, "step": self._state.step_count})

    def _check_termination(self) -> bool:
        if self._state.step_count >= self._state.max_steps:
            self._state.truncated = True
            self._state.termination_reason = "Max steps reached"
            return True
        if self._state.current_phase == IncidentPhase.VALIDATION and len(self.attacks.get_active_attacks()) == 0:
            self._state.terminated = True
            self._state.termination_reason = "Incident resolved — validation complete"
            return True
        all_critical = all(n.health <= 0 for n in self.network.get_all_nodes() if n.criticality > 0.7)
        if all_critical:
            self._state.terminated = True
            self._state.termination_reason = "Total system failure"
            return True
        return False

    def _build_observation(self, action_result: str, action_success: bool) -> ImmunoObservation:
        compromised_ids = {n.id for n in self.network.get_compromised_nodes()}
        visible_nodes = []
        for n in self.network.get_all_nodes():
            if n.compromised and n.attack_vector and self.rng.random() < 0.3 + (1 - self.attacks.active_attacks[0].stealth if self.attacks.active_attacks else 0.5):
                visible_nodes.append(n)
            elif not n.compromised:
                visible_nodes.append(n)
            else:
                visible_nodes.append(n)

        detected = [a for a in self.attacks.get_active_attacks()
                     if self.rng.random() < 0.4 + (1 - a.stealth) * 0.6]

        recent_logs = []
        for n in self.network.get_all_nodes():
            recent_logs.extend(n.logs[-3:])
        recent_logs.sort(key=lambda l: l.timestamp, reverse=True)

        alerts = []
        if self._state.threat_level > 0.7:
            alerts.append(f"HIGH THREAT: Level {self._state.threat_level:.2f}")
        if self.permissions.pending:
            alerts.append(f"{len(self.permissions.pending)} approval(s) pending")

        return ImmunoObservation(
            visible_nodes=visible_nodes,
            visible_edges=self.network.get_all_edges(),
            detected_attacks=detected,
            recent_logs=recent_logs[:15],
            network_health_summary=self.network.get_network_health(),
            org_nodes=self.org.get_all_nodes(),
            org_edges=self.org.get_active_edges(),
            pending_approvals=self.permissions.pending,
            action_result=action_result,
            action_success=action_success,
            approval_delay=self.permissions.get_average_approval_latency(),
            current_phase=self._state.current_phase,
            step_count=self._state.step_count,
            sim_time=self._state.sim_time,
            threat_level=self._state.threat_level,
            system_downtime=self._state.total_downtime,
            belief_map_feedback=self.belief_map.generate_feedback() if self._state.step_count % 5 == 0 else "",
            alerts=alerts,
        )
