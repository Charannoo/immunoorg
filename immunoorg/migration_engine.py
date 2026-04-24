"""
Polymorphic Migration Engine (Moving Target Defense)
=====================================================
ImmunoOrg 2.0 — Theme 2: Long-Horizon Planning
Bonus Prize: Scale AI — Long Horizon IT Workflows

50-step infrastructure migration as a background state machine.
Constraint propagation: constraints set in Phase 1 (Recon) are
validated in Phase 4 (Real Asset Migration) — forgetting them fails the step.
"""

from __future__ import annotations
import random
from typing import Any
from immunoorg.models import (
    MigrationPhase, MigrationStep, MigrationWorkflowState,
    HoneytokenActivation, HoneytokenType,
)

PHASE_STEP_COUNTS = {
    MigrationPhase.RECONNAISSANCE: 5,
    MigrationPhase.DECOY_DEPLOYMENT: 7,
    MigrationPhase.TRAFFIC_REROUTING: 10,
    MigrationPhase.REAL_ASSET_MIGRATION: 13,
    MigrationPhase.HONEYTOKEN_ACTIVATION: 7,
    MigrationPhase.FORENSIC_CAPTURE: 5,
    MigrationPhase.SECURE_CUTOVER: 3,
}

PHASE_DESCRIPTIONS = {
    MigrationPhase.RECONNAISSANCE: [
        "Map network topology and identify attacker footholds",
        "Build complete attack graph from telemetry",
        "Identify active C2 channels",
        "Catalogue data assets and residency requirements [SETS: data_residency]",
        "Map tenant-specific compliance constraints [SETS: tenant_compliance]",
    ],
    MigrationPhase.DECOY_DEPLOYMENT: [
        "Provision EC2 honeypot instances with realistic fake data",
        "Clone production DB schema with synthetic PII",
        "Configure realistic service responses on honeypot endpoints",
        "Deploy honeytoken credentials in accessible locations",
        "Validate attacker pivot probability to decoy >80%",
        "Activate canary token monitoring with geo-attribution",
        "Verify honeypot isolation from real production data",
    ],
    MigrationPhase.TRAFFIC_REROUTING: [
        "Update DNS records to route real users from compromised nodes",
        "Reconfigure load balancer for seamless user redirect",
        "Update CDN edge configurations to new clean origin",
        "Verify zero dropped connections during migration",
        "Redirect attacker traffic to honeypot via BGP",
        "Activate session persistence for in-flight transactions",
        "Monitor traffic split between clean and honeypot nodes",
        "Validate SLA compliance during rerouting",
        "Enable adaptive rate limiting on honeypot",
        "Confirm email MX records updated to clean infra",
    ],
    MigrationPhase.REAL_ASSET_MIGRATION: [
        "Deploy fresh application stack in isolated VPC",
        "Validate data residency constraint from recon [REQUIRES: data_residency]",
        "Migrate application state with integrity checksums",
        "Transfer encrypted DB backups to clean environment",
        "Rotate all API keys and secrets in new environment",
        "Deploy new TLS certificates on clean endpoints",
        "Run integration test suite against clean environment",
        "Validate tenant compliance in new environment [REQUIRES: tenant_compliance]",
        "Confirm data integrity hash matches pre-migration baseline",
        "Canary deploy with 1% of real traffic",
        "Confirm no lateral channels from old to new environment",
        "Document migration steps for audit trail",
        "Validate monitoring and alerting active",
    ],
    MigrationPhase.HONEYTOKEN_ACTIVATION: [
        "Activate fake AWS access keys with beacon callbacks",
        "Seed fake PII employee records with unique identifiers",
        "Deploy poisoned credentials to credential stores",
        "Plant trapdoor documents with embedded tracking pixels",
        "Activate cross-referencing between honeytoken activations",
        "Detect first honeytoken activation",
        "Build attacker attribution profile from token data",
    ],
    MigrationPhase.FORENSIC_CAPTURE: [
        "Capture complete honeytoken interaction logs",
        "Reconstruct attacker kill chain from honeypot telemetry",
        "Document full TTPs (Tactics, Techniques, Procedures)",
        "Correlate attacker IP with geolocation data",
        "Extract attacker tooling signatures for IOC database",
    ],
    MigrationPhase.SECURE_CUTOVER: [
        "Finalize 100% traffic migration to clean environment",
        "Deactivate all compromised infrastructure",
        "Generate incident report and verify 100% uptime maintained",
    ],
}

ATTACKER_GEOS = [
    "Unknown (Tor Exit Node)", "Moscow, RU", "Beijing, CN",
    "Frankfurt, DE (VPN)", "Amsterdam, NL (Proxy)", "Unknown (VPN)",
]
ATTACKER_IPS = ["185.220.101.47", "103.75.190.12", "91.240.118.22", "195.154.175.43"]
HONEYTOKEN_DATA = {
    HoneytokenType.CANARY_TOKEN: "AWS key used to list S3 buckets",
    HoneytokenType.FAKE_PII: "Employee record 'John Canary' SSN:000-00-0000 exfiltrated",
    HoneytokenType.POISONED_CREDENTIAL: "Login to fake HR portal with poisoned creds",
    HoneytokenType.TRAPDOOR_DOCUMENT: "Q3 Financials (FAKE).docx opened — tracking pixel fired",
}


class MigrationEngine:
    """
    Executes the 50-step Moving Target Defense migration as a background
    state machine. Advances one step per episode tick.
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self._state: MigrationWorkflowState | None = None
        self._checkpoints: dict[str, int] = {}
        self._constraint_store: dict[str, Any] = {}

    @property
    def state(self) -> MigrationWorkflowState | None:
        return self._state

    @property
    def is_active(self) -> bool:
        return (self._state is not None
                and self._state.current_phase != MigrationPhase.COMPLETE)

    def start(self, sim_time: float, constraints: dict[str, Any] | None = None) -> MigrationWorkflowState:
        steps: list[MigrationStep] = []
        step_num = 0
        phase_order = list(PHASE_STEP_COUNTS.keys())
        for phase in phase_order:
            self._checkpoints[phase.value] = step_num
            descs = PHASE_DESCRIPTIONS.get(phase, [])
            for i in range(PHASE_STEP_COUNTS[phase]):
                desc = descs[i] if i < len(descs) else f"Step {step_num}"
                requires = ""
                sets_constraint = ""
                if "[REQUIRES:" in desc:
                    requires = desc.split("[REQUIRES:")[1].rstrip("]").strip()
                if "[SETS:" in desc:
                    sets_constraint = desc.split("[SETS:")[1].rstrip("]").strip()
                step = MigrationStep(
                    step_number=step_num,
                    description=desc.split("[")[0].strip(),
                    phase=phase,
                    constraint_ids=[requires] if requires else [],
                    success_metric=f"step_{step_num}_success",
                    required_success_threshold=0.85,
                )
                if sets_constraint:
                    step.constraint_values[sets_constraint] = "pending"
                steps.append(step)
                step_num += 1

        self._state = MigrationWorkflowState(
            current_phase=phase_order[0],
            total_steps=step_num,
            steps=steps,
            constraints=constraints or {"data_residency": "us-east-1", "tenant_compliance": "HIPAA"},
            started_at=sim_time,
        )
        self._constraint_store = dict(self._state.constraints)
        return self._state

    def advance(self, sim_time: float) -> dict[str, Any]:
        if not self._state or not self.is_active:
            return {"status": "inactive"}
        idx = self._state.current_step
        if idx >= len(self._state.steps):
            self._state.current_phase = MigrationPhase.COMPLETE
            self._state.completed_at = sim_time
            return {"status": "complete", "step": idx}

        step = self._state.steps[idx]
        result: dict[str, Any] = {
            "step": idx, "phase": step.phase.value,
            "description": step.description,
            "constraint_violation": False, "honeytoken_activation": None,
        }

        # Scale AI: constraint validation
        for cid in step.constraint_ids:
            if cid not in self._constraint_store:
                # Rollback to REAL_ASSET_MIGRATION checkpoint
                rollback = self._checkpoints.get(MigrationPhase.REAL_ASSET_MIGRATION.value, 0)
                self._state.current_step = rollback
                self._state.current_phase = MigrationPhase.REAL_ASSET_MIGRATION
                for s in self._state.steps[rollback:idx]:
                    s.completed = False
                result["constraint_violation"] = True
                result["message"] = (
                    f"CONSTRAINT VIOLATION at step {idx}: '{cid}' not established in Recon. "
                    f"Rolling back to Phase 4 start."
                )
                return result

        # Execute step
        val = min(1.0, self.rng.uniform(0.75, 1.05))
        step.success_value = val
        step.completed = val >= step.required_success_threshold

        # Set constraints for steps that define them
        for key in step.constraint_values:
            self._constraint_store[key] = self._state.constraints.get(key, "us-east-1")
            step.constraint_values[key] = self._constraint_store[key]

        # Honeytoken activations
        if step.phase in (MigrationPhase.HONEYTOKEN_ACTIVATION, MigrationPhase.FORENSIC_CAPTURE):
            if self.rng.random() < 0.35:
                token_type = self.rng.choice(list(HoneytokenType))
                activation = HoneytokenActivation(
                    token_type=token_type,
                    activated_at=sim_time,
                    attacker_ip=self.rng.choice(ATTACKER_IPS),
                    attacker_geo=self.rng.choice(ATTACKER_GEOS),
                    data_accessed=HONEYTOKEN_DATA.get(token_type, "Unknown asset"),
                    attribution_confidence=self.rng.uniform(0.6, 0.95),
                )
                self._state.honeytoken_activations.append(activation)
                result["honeytoken_activation"] = activation.model_dump()

        if step.phase == MigrationPhase.TRAFFIC_REROUTING and not step.completed:
            self._state.zero_downtime = False

        self._state.current_step += 1
        self._advance_phase()
        result["success_value"] = val
        result["step_completed"] = step.completed
        result["status"] = "advancing"
        return result

    def _advance_phase(self) -> None:
        if not self._state:
            return
        phase_steps = [s for s in self._state.steps if s.phase == self._state.current_phase]
        if phase_steps and all(s.completed for s in phase_steps):
            order = list(PHASE_STEP_COUNTS.keys())
            try:
                cur = order.index(self._state.current_phase)
                if cur + 1 < len(order):
                    self._state.current_phase = order[cur + 1]
            except ValueError:
                pass

    def get_progress(self) -> dict[str, Any]:
        if not self._state:
            return {"active": False}
        completed = sum(1 for s in self._state.steps if s.completed)
        total = len(self._state.steps)
        return {
            "active": self.is_active,
            "current_phase": self._state.current_phase.value,
            "current_step": self._state.current_step,
            "total_steps": total,
            "completed_steps": completed,
            "progress_pct": completed / max(1, total),
            "zero_downtime": self._state.zero_downtime,
            "honeytoken_activations": len(self._state.honeytoken_activations),
            "active_honeypots": self._state.active_honeypots,
        }

    def get_honeytoken_map_data(self) -> list[dict[str, Any]]:
        if not self._state:
            return []
        return [
            {"token_id": a.token_id, "type": a.token_type.value,
             "geo": a.attacker_geo, "ip": a.attacker_ip,
             "confidence": a.attribution_confidence, "data": a.data_accessed}
            for a in self._state.honeytoken_activations
        ]
