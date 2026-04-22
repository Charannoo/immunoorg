"""
ImmunoOrg Data Models
=====================
Complete Pydantic models for the dual-layer environment.
"""

from __future__ import annotations
import uuid
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


# === ENUMS ===

class NodeType(str, Enum):
    SERVER = "server"
    API = "api"
    DATABASE = "database"
    FIREWALL = "firewall"
    ENDPOINT = "endpoint"
    LOAD_BALANCER = "load_balancer"

class AttackVector(str, Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"
    PHISHING = "phishing"
    RANSOMWARE = "ransomware"
    APT_BACKDOOR = "apt_backdoor"
    DDOS = "ddos"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SUPPLY_CHAIN = "supply_chain"
    ZERO_DAY = "zero_day"

class PortStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    BLOCKED = "blocked"

class DepartmentType(str, Enum):
    IT_OPS = "it_ops"
    SECURITY = "security"
    ENGINEERING = "engineering"
    DEVOPS = "devops"
    MANAGEMENT = "management"
    LEGAL = "legal"
    HR = "hr"
    FINANCE = "finance"

class IncidentPhase(str, Enum):
    DETECTION = "detection"
    CONTAINMENT = "containment"
    ROOT_CAUSE_ANALYSIS = "rca"
    ORG_REFACTOR = "refactor"
    VALIDATION = "validation"

class ActionType(str, Enum):
    TACTICAL = "tactical"
    STRATEGIC = "strategic"
    DIAGNOSTIC = "diagnostic"

class TacticalAction(str, Enum):
    BLOCK_PORT = "block_port"
    ISOLATE_NODE = "isolate_node"
    SCAN_LOGS = "scan_logs"
    DEPLOY_PATCH = "deploy_patch"
    QUARANTINE_TRAFFIC = "quarantine_traffic"
    ESCALATE_ALERT = "escalate_alert"
    RESTORE_BACKUP = "restore_backup"
    ROTATE_CREDENTIALS = "rotate_credentials"
    ENABLE_IDS = "enable_ids"
    SNAPSHOT_FORENSICS = "snapshot_forensics"

class StrategicAction(str, Enum):
    MERGE_DEPARTMENTS = "merge_departments"
    CREATE_SHORTCUT_EDGE = "create_shortcut_edge"
    UPDATE_APPROVAL_PROTOCOL = "update_approval_protocol"
    SPLIT_DEPARTMENT = "split_department"
    REASSIGN_AUTHORITY = "reassign_authority"
    ADD_CROSS_FUNCTIONAL_TEAM = "add_cross_functional_team"
    REDUCE_BUREAUCRACY = "reduce_bureaucracy"
    CREATE_INCIDENT_CHANNEL = "create_incident_channel"
    REWRITE_POLICY = "rewrite_policy"
    ESTABLISH_DEVSECOPS = "establish_devsecops"

class DiagnosticAction(str, Enum):
    QUERY_BELIEF_MAP = "query_belief_map"
    CORRELATE_FAILURE = "correlate_failure"
    TRACE_ATTACK_PATH = "trace_attack_path"
    AUDIT_PERMISSIONS = "audit_permissions"
    MEASURE_ORG_LATENCY = "measure_org_latency"
    IDENTIFY_SILO = "identify_silo"
    TIMELINE_RECONSTRUCT = "timeline_reconstruct"
    VULNERABILITY_SCAN = "vulnerability_scan"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    DELAYED = "delayed"
    ESCALATED = "escalated"

class LogSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"


# === TECHNICAL LAYER ===

class PortState(BaseModel):
    port_number: int = Field(..., ge=1, le=65535)
    protocol: Literal["tcp", "udp"] = "tcp"
    service: str = ""
    status: PortStatus = PortStatus.OPEN
    vulnerability_score: float = Field(0.0, ge=0.0, le=1.0)

class LogEntry(BaseModel):
    timestamp: float = 0.0
    severity: LogSeverity = LogSeverity.INFO
    source: str = ""
    message: str = ""
    attack_indicator: bool = False
    indicator_confidence: float = Field(0.0, ge=0.0, le=1.0)

class NetworkEdge(BaseModel):
    source: str
    target: str
    bandwidth: float = 1000.0
    latency: float = 1.0
    encrypted: bool = True
    traffic_volume: float = 0.0
    anomaly_score: float = Field(0.0, ge=0.0, le=1.0)

class NetworkNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    type: NodeType = NodeType.SERVER
    tier: Literal["web", "app", "data", "management", "dmz"] = "app"
    ports: list[PortState] = Field(default_factory=list)
    health: float = Field(1.0, ge=0.0, le=1.0)
    compromised: bool = False
    compromised_at: float | None = None
    attack_vector: AttackVector | None = None
    logs: list[LogEntry] = Field(default_factory=list)
    patched: bool = False
    isolated: bool = False
    services: list[str] = Field(default_factory=list)
    criticality: float = Field(0.5, ge=0.0, le=1.0)

class Attack(BaseModel):
    id: str = Field(default_factory=lambda: f"ATK-{uuid.uuid4().hex[:6].upper()}")
    vector: AttackVector = AttackVector.SQL_INJECTION
    source_node: str = ""
    target_node: str = ""
    entry_point: str = ""
    severity: float = Field(0.5, ge=0.0, le=1.0)
    started_at: float = 0.0
    contained: bool = False
    contained_at: float | None = None
    lateral_path: list[str] = Field(default_factory=list)
    damage_dealt: float = 0.0
    stealth: float = Field(0.5, ge=0.0, le=1.0)


# === ORGANIZATIONAL LAYER ===

class OrgEdge(BaseModel):
    source: str
    target: str
    latency: float = Field(1.0, ge=0.0)
    trust: float = Field(0.5, ge=0.0, le=1.0)
    bandwidth: float = Field(1.0, ge=0.0)
    formal: bool = True
    active: bool = True

class KPI(BaseModel):
    name: str
    target_value: float
    current_value: float
    weight: float = Field(1.0, ge=0.0)
    direction: Literal["maximize", "minimize"] = "maximize"

class OrgNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    department_type: DepartmentType = DepartmentType.IT_OPS
    trust_score: float = Field(0.7, ge=0.0, le=1.0)
    response_latency: float = Field(1.0, ge=0.0)
    cooperation_threshold: float = Field(0.5, ge=0.0, le=1.0)
    kpis: list[KPI] = Field(default_factory=list)
    approval_authority: list[str] = Field(default_factory=list)
    budget: float = 100.0
    headcount: int = 10
    technical_nodes_owned: list[str] = Field(default_factory=list)
    active: bool = True

class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"APR-{uuid.uuid4().hex[:6].upper()}")
    action_type: ActionType = ActionType.TACTICAL
    action_name: str = ""
    requester: str = ""
    approver: str = ""
    target: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    submitted_at: float = 0.0
    resolved_at: float | None = None
    approval_path: list[str] = Field(default_factory=list)
    urgency: float = Field(0.5, ge=0.0, le=1.0)
    justification: str = ""


# === BELIEF MAP ===

class TechOrgCorrelation(BaseModel):
    technical_indicator: str = ""
    organizational_flaw: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    discovered_at: float = 0.0
    ground_truth: bool | None = None

class BeliefMapState(BaseModel):
    correlations: list[TechOrgCorrelation] = Field(default_factory=list)
    attack_timeline: list[dict[str, Any]] = Field(default_factory=list)
    identified_silos: list[tuple[str, str]] = Field(default_factory=list)
    bottleneck_departments: list[str] = Field(default_factory=list)
    predicted_next_attack: AttackVector | None = None
    model_confidence: float = Field(0.0, ge=0.0, le=1.0)


# === OPENENV INTERFACE MODELS ===

class ImmunoAction(BaseModel):
    """The agent's action."""
    action_type: ActionType = ActionType.TACTICAL
    tactical_action: TacticalAction | None = None
    strategic_action: StrategicAction | None = None
    diagnostic_action: DiagnosticAction | None = None
    target: str = ""
    secondary_target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""

class ImmunoObservation(BaseModel):
    """What the agent observes after an action."""
    visible_nodes: list[NetworkNode] = Field(default_factory=list)
    visible_edges: list[NetworkEdge] = Field(default_factory=list)
    detected_attacks: list[Attack] = Field(default_factory=list)
    recent_logs: list[LogEntry] = Field(default_factory=list)
    network_health_summary: dict[str, float] = Field(default_factory=dict)
    org_nodes: list[OrgNode] = Field(default_factory=list)
    org_edges: list[OrgEdge] = Field(default_factory=list)
    pending_approvals: list[ApprovalRequest] = Field(default_factory=list)
    action_result: str = ""
    action_success: bool = True
    approval_delay: float = 0.0
    current_phase: IncidentPhase = IncidentPhase.DETECTION
    step_count: int = 0
    sim_time: float = 0.0
    threat_level: float = Field(0.0, ge=0.0, le=1.0)
    system_downtime: float = 0.0
    belief_map_feedback: str = ""
    alerts: list[str] = Field(default_factory=list)

class ImmunoState(BaseModel):
    """Full environment state (server-side)."""
    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_count: int = 0
    sim_time: float = 0.0
    max_steps: int = 200
    network_nodes: list[NetworkNode] = Field(default_factory=list)
    network_edges: list[NetworkEdge] = Field(default_factory=list)
    active_attacks: list[Attack] = Field(default_factory=list)
    contained_attacks: list[Attack] = Field(default_factory=list)
    org_nodes: list[OrgNode] = Field(default_factory=list)
    org_edges: list[OrgEdge] = Field(default_factory=list)
    pending_approvals: list[ApprovalRequest] = Field(default_factory=list)
    completed_approvals: list[ApprovalRequest] = Field(default_factory=list)
    ground_truth_correlations: list[TechOrgCorrelation] = Field(default_factory=list)
    agent_belief_map: BeliefMapState = Field(default_factory=BeliefMapState)
    current_phase: IncidentPhase = IncidentPhase.DETECTION
    phase_history: list[dict[str, Any]] = Field(default_factory=list)
    total_downtime: float = 0.0
    threat_level: float = Field(0.0, ge=0.0, le=1.0)
    total_damage: float = 0.0
    false_positives: int = 0
    correct_identifications: int = 0
    org_changes_made: int = 0
    org_chaos_score: float = Field(0.0, ge=0.0, le=1.0)
    difficulty_level: int = Field(1, ge=1, le=4)
    self_improvement_generation: int = 0
    cumulative_reward: float = 0.0
    partial_rewards: list[dict[str, float]] = Field(default_factory=list)
    terminated: bool = False
    truncated: bool = False
    termination_reason: str = ""


# === SELF-IMPROVEMENT ===

class GenerationRecord(BaseModel):
    generation: int = 0
    org_graph_snapshot: list[OrgNode] = Field(default_factory=list)
    org_edges_snapshot: list[OrgEdge] = Field(default_factory=list)
    attack_complexity: float = 0.0
    time_to_containment: float = 0.0
    org_efficiency: float = 0.0
    total_reward: float = 0.0
    mutations_applied: list[str] = Field(default_factory=list)
    attack_used: AttackVector | None = None

class SelfImprovementState(BaseModel):
    generations: list[GenerationRecord] = Field(default_factory=list)
    current_generation: int = 0
    equilibrium_reached: bool = False
    improvement_rate: float = 0.0
    best_org_config: list[OrgNode] | None = None
    best_org_edges: list[OrgEdge] | None = None
    best_reward: float = float("-inf")
