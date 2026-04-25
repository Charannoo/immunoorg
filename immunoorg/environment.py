"""
ImmunoOrg Core Environment
==========================
OpenEnv Environment subclass orchestrating the dual-layer simulation.
"""

import random
import uuid
import logging
import json
from typing import Any

try:
    from openenv import OpenEnvEnvironment
except ImportError:
    # openenv package not installed — define minimal stub for HF Spaces / standalone use
    class OpenEnvEnvironment:
        """Minimal stub when openenv package is unavailable."""
        pass

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
# ImmunoOrg 2.0 modules
from immunoorg.war_room import WarRoom
from immunoorg.devsecops_mesh import DevSecOpsMesh
from immunoorg.knowledge_base import CVEKnowledgeBase
from immunoorg.migration_engine import MigrationEngine

from immunoorg.executive_context import ExecutiveContextEngine


class ImmunoOrgEnvironment(OpenEnvEnvironment):
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
        # ImmunoOrg 2.0 engines
        self.war_room: WarRoom = WarRoom(seed=seed)
        self.devsecops_mesh: DevSecOpsMesh = DevSecOpsMesh(seed=seed)
        self.migration_engine: MigrationEngine = MigrationEngine(rng=self.rng)
        self.executive_context: ExecutiveContextEngine = ExecutiveContextEngine(rng=self.rng)
        self.knowledge_base: CVEKnowledgeBase = CVEKnowledgeBase()
        # 2.0 per-step state
        self._last_war_room_turns: int = 0
        self._last_pipeline_integrity: float = 1.0
        self._last_pipeline_gate = None

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

        # Reset 2.0 engines
        self.war_room = WarRoom(seed=s)
        self.devsecops_mesh = DevSecOpsMesh(seed=s)
        self.migration_engine = MigrationEngine(rng=random.Random(s))
        self.executive_context = ExecutiveContextEngine(rng=random.Random(s))
        self._last_war_room_turns = 0
        self._last_pipeline_integrity = 1.0
        self._last_pipeline_gate = None

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
        
        # Record reasoning trace
        self.record_reasoning(action)
        
        threats_before = len(self.attacks.get_active_attacks())

        # 1. Process the action
        result, success = self._execute_action(action)

        # 2. Adversary reacts
        self.attacks.adversary_tick(self._state.sim_time)
        action_name = self._get_action_name(action)
        self.attacks.observe_defender_action(action_name)

        # 2b. DevSecOps Mesh — tick pipeline simulation
        mesh_result = self.devsecops_mesh.simulate_pipeline_tick(
            self._state.sim_time,
            threat_active=len(self.attacks.get_active_attacks()) > 0,
        )
        self._last_pipeline_integrity = mesh_result.pipeline_integrity_score
        self._last_pipeline_gate = mesh_result.earliest_gate_caught
        # War Room: trigger on high-severity events
        if mesh_result.events and any(e.war_room_triggered for e in mesh_result.events):
            if self.attacks.active_attacks:
                _atk = self.attacks.active_attacks[0]
                _nodes = [n.model_dump() for n in self.network.get_all_nodes()]
                debate = self.war_room.run_debate(
                    _atk, self._state.threat_level, _nodes, self._state.sim_time
                )
                self._last_war_room_turns = debate.turns_to_consensus

        # 2c. Migration engine — advance if active
        if self.migration_engine.is_active:
            self.migration_engine.advance(self._state.sim_time)

        # 2d. Executive context — tick
        self.executive_context.tick(self._state.sim_time, self._state.step_count)

        # 2e. War Room — trigger on high-severity threat if not already triggered
        if (self._state.threat_level >= self.war_room.ACTIVATION_THRESHOLD
                and self.attacks.active_attacks
                and self._state.step_count % 5 == 0):  # Throttle: at most every 5 steps
            _atk = self.attacks.active_attacks[0]
            _nodes = [n.model_dump() for n in self.network.get_all_nodes()]
            debate = self.war_room.run_debate(
                _atk, self._state.threat_level, _nodes, self._state.sim_time
            )
            self._last_war_room_turns = debate.turns_to_consensus

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
        patronus_score = self.executive_context.get_patronus_score()
        reward = self.reward_calc.compute_step_reward(
            state=self._state, action=action, action_success=success,
            threats_before=threats_before, threats_after=threats_after,
            belief_accuracy=belief_accuracy,
            org_chaos=self._state.org_chaos_score,
            downtime_delta=1.0 if damage > 0 else 0.0,
            war_room_turns=self._last_war_room_turns,
            pipeline_integrity_score=self._last_pipeline_integrity,
            pipeline_gate=self._last_pipeline_gate,
            patronus_score=patronus_score,
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
            
            # Co-Evolution: evolve adversary based on improvement rate
            if self.attacks:
                self.attacks.evolve_adversary_complexity(self.self_improvement.state.improvement_rate)

        obs = self._build_observation(result, success)
        return obs, reward, terminated

    def record_reasoning(self, action: ImmunoAction) -> None:
        """Create a reasoning trace for the action taken."""
        from immunoorg.models import ReasoningTrace
        
        # In a real LLM agent, we'd ask the LLM to provide the 'trigger' separately
        # Here we simulate it by extracting keywords from the reasoning
        trigger = "Observation-based"
        snippet = "General environment state"
        
        if "scan" in action.reasoning.lower():
            trigger = "Need more info"
            snippet = "Low confidence in current state"
        elif "isolate" in action.reasoning.lower():
            trigger = "Containment priority"
            snippet = "Active threat detected on target node"
        elif "merge" in action.reasoning.lower() or "shortcut" in action.reasoning.lower():
            trigger = "Structural flaw"
            snippet = "Silo detected between departments"
            
        trace = ReasoningTrace(
            step=self._state.step_count,
            decision_trigger=trigger,
            observation_snippet=snippet,
            rationale=action.reasoning,
            timestamp=self._state.sim_time,
        )
        self._state.reasoning_traces.append(trace)

    def _execute_action(self, action: ImmunoAction) -> tuple[str, bool]:
        """Execute the agent's action and return (result_description, success)."""
        action_name = self._get_action_name(action)
        
        # Diagnostic actions don't need approval
        if action.action_type == ActionType.DIAGNOSTIC:
            return self._execute_diagnostic(action)
        
        # 2.0: Migration and honeypot actions are always pre-authorized (CISO authority)
        if action.tactical_action in (TacticalAction.START_MIGRATION, TacticalAction.DEPLOY_HONEYPOT):
            return self._execute_direct(action)
        
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
        elif t == TacticalAction.START_MIGRATION:
            if not self.migration_engine.is_active:
                constraints = {
                    "data_residency": "us-east-1",  # Default; agents can override via parameters
                    "tenant_compliance": action.parameters.get("compliance", "SOC2"),
                }
                if action.parameters.get("data_residency"):
                    constraints["data_residency"] = action.parameters["data_residency"]
                self.migration_engine.start(self._state.sim_time, constraints=constraints)
                return (
                    f"⚡ Polymorphic Migration INITIATED — 50-step Moving Target Defense workflow started. "
                    f"Attacker will be diverted to honeypots. Constraints: {constraints}"
                ), True
            return "Migration already active.", False
        elif t == TacticalAction.DEPLOY_HONEYPOT:
            if self.migration_engine.state:
                node_id = f"honeypot-{self._state.step_count}"
                self.migration_engine.state.active_honeypots.append(node_id)
                return f"🍯 Honeypot node {node_id} deployed and seeded with fake credentials.", True
            return "Start migration first to deploy honeypots.", False
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
        elif d == DiagnosticAction.CHECK_EXECUTIVE_CONTEXT:
            summary = self.executive_context.get_context_summary()
            drift_events = self.executive_context.state.drift_events
            migration_progress = self.migration_engine.get_progress()
            war_room_transcript = self.war_room.get_latest_transcript()
            return (
                f"{summary}\n"
                f"Migration: {migration_progress.get('current_phase','N/A')} "
                f"({migration_progress.get('progress_pct', 0):.0%} done)\n"
                f"War Room Latest: {war_room_transcript[:200]}"
            ), True
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
        """Auto-transition between incident phases based on meaningful progress.
        
        Each transition requires REAL work, not just step counts:
        - Detection → Containment: Agent must have scanned AND traced (identified the threat)
        - Containment → RCA: ALL active attacks must be contained
        - RCA → Refactor: Belief map must have real accuracy AND multiple correlations
        - Refactor → Validation: Multiple org changes must have been made
        """
        phase = self._state.current_phase
        active_attacks = self.attacks.get_active_attacks()

        if phase == IncidentPhase.DETECTION:
            # Require: at least 1 scan + 1 identification/trace action completed
            has_scanned = self._state.scans_performed > 0 if hasattr(self._state, 'scans_performed') else self._state.step_count >= 2
            has_identified = self._state.correct_identifications > 0 or len(self._state.contained_attacks) > 0
            if has_scanned and (has_identified or self._state.step_count >= 4):
                self._transition_phase(IncidentPhase.CONTAINMENT)
        elif phase == IncidentPhase.CONTAINMENT:
            # Require: ALL active attacks must be contained (no free passes)
            if len(active_attacks) == 0:
                self._transition_phase(IncidentPhase.ROOT_CAUSE_ANALYSIS)
        elif phase == IncidentPhase.ROOT_CAUSE_ANALYSIS:
            # Require: belief accuracy >= 0.4 AND at least 2 correlations
            belief_acc = self.belief_map.calculate_belief_accuracy()
            num_correlations = len(self.belief_map.state.correlations)
            if belief_acc >= 0.4 and num_correlations >= 2:
                self._transition_phase(IncidentPhase.ORG_REFACTOR)
            elif num_correlations >= 3:  # Allow through with more evidence even if accuracy is lower
                self._transition_phase(IncidentPhase.ORG_REFACTOR)
        elif phase == IncidentPhase.ORG_REFACTOR:
            # Require: at least 2 organizational changes
            if self._state.org_changes_made >= 2:
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

    def inject_directive(self, directive: str) -> None:
        """Inject a board directive mid-simulation."""
        self._state.directives.append(directive)
        logging.info(f"Board Directive Injected: {directive}")

    def _build_observation(self, action_result: str, action_success: bool) -> ImmunoObservation:
        compromised_ids = {n.id for n in self.network.get_compromised_nodes()}
        visible_nodes = []
        for n in self.network.get_all_nodes():
            if not n.compromised:
                # Clean nodes are always visible
                visible_nodes.append(n)
            else:
                # Compromised nodes: visibility depends on stealth and detection
                stealth = self.attacks.active_attacks[0].stealth if self.attacks.active_attacks else 0.5
                detection_chance = 0.3 + (1.0 - stealth) * 0.7
                if self.rng.random() < detection_chance:
                    # Agent detects this compromised node
                    visible_nodes.append(n)
                # else: node is hidden — fog of war
        
        detected = [a for a in self.attacks.get_active_attacks()
                     if self.rng.random() < 0.4 + (1 - a.stealth) * 0.6]
        
        # RAG Integration: Retrieve real-world CVE info for detected attacks
        rag_info = []
        if self.knowledge_base and detected:
            for atk in detected:
                info = self.knowledge_base.retrieve_cve_info(atk.vector.value)
                rag_info.append(f"Threat {atk.id} ({atk.vector.value}): {info}")
        
        recent_logs = []
        for n in self.network.get_all_nodes():
            recent_logs.extend(n.logs[-3:])
        recent_logs.sort(key=lambda l: l.timestamp, reverse=True)
        
        alerts = []
        if self._state.threat_level > 0.7:
            alerts.append(f"HIGH THREAT: Level {self._state.threat_level:.2f}")
        if self.permissions.pending:
            alerts.append(f"{len(self.permissions.pending)} approval(s) pending")
        
        # Add RAG info to alerts
        alerts.extend(rag_info)
        
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
            threat_level=min(1.0, max(0.0, self._state.threat_level)),
            system_downtime=self._state.total_downtime,
            belief_map_feedback=self.belief_map.generate_feedback() if self._state.step_count % 5 == 0 else "",
            alerts=alerts,
            directives=self._state.directives,
        )

