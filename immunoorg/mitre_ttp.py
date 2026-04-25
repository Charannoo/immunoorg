"""
MITRE ATT&CK TTP Integration Engine
===================================
ImmunoOrg 2.0 - Phase 4: TTP Expansion

Integrates the MITRE ATT&CK framework into ImmunoOrg, mapping:
- Adversary Tactics (Reconnaissance, Execution, Defense Evasion, etc.)
- Techniques (Sub-techniques of each tactic)
- Procedures (How each technique is implemented)

This enables:
- More realistic attack chains (ATT&CK techniques → ImmunoOrg attacks)
- Better belief mapping (correlating technical failures to specific TTPs)
- Agent learning of TTP-specific defenses
- Adversary reasoning based on TTP availability
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Any
import random


class MITREtactic(Enum):
    """MITRE ATT&CK Tactics (high-level adversary goals)."""
    RECONNAISSANCE = "reconnaissance"
    RESOURCE_DEVELOPMENT = "resource_development"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command_and_control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


@dataclass
class MITREtechnique:
    """A MITRE ATT&CK technique with sub-techniques."""
    id: str  # e.g., "T1566" (Phishing)
    name: str
    tactic: MITREtactic
    description: str
    platforms: list[str]  # Windows, Linux, macOS, Cloud, etc.
    sub_techniques: list[str] | None = None  # e.g., ["T1566.001", "T1566.002"]
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, MITREtechnique):
            return self.id == other.id
        return False


# Comprehensive MITRE ATT&CK Technique Library
MITRE_TECHNIQUES: dict[str, MITREtechnique] = {
    "T1566": MITREtechnique(
        id="T1566",
        name="Phishing",
        tactic=MITREtactic.INITIAL_ACCESS,
        description="Send phishing emails to gain initial access",
        platforms=["Windows", "Linux", "macOS"],
        sub_techniques=["T1566.001", "T1566.002", "T1566.003"],
    ),
    "T1199": MITREtechnique(
        id="T1199",
        name="Trusted Relationship",
        tactic=MITREtactic.INITIAL_ACCESS,
        description="Exploit trusted relationships to gain access",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1190": MITREtechnique(
        id="T1190",
        name="Exploit Public-Facing Application",
        tactic=MITREtactic.INITIAL_ACCESS,
        description="Exploit vulnerabilities in public-facing applications",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1598": MITREtechnique(
        id="T1598",
        name="Phishing for Information",
        tactic=MITREtactic.RECONNAISSANCE,
        description="Phishing for information gathering",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1589": MITREtechnique(
        id="T1589",
        name="Gather Victim Identity Information",
        tactic=MITREtactic.RECONNAISSANCE,
        description="Gather information about target identities",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1087": MITREtechnique(
        id="T1087",
        name="Account Discovery",
        tactic=MITREtactic.DISCOVERY,
        description="Discover accounts in the environment",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1110": MITREtechnique(
        id="T1110",
        name="Brute Force",
        tactic=MITREtactic.CREDENTIAL_ACCESS,
        description="Brute force credential access",
        platforms=["Windows", "Linux", "macOS"],
        sub_techniques=["T1110.001", "T1110.002", "T1110.003"],
    ),
    "T1555": MITREtechnique(
        id="T1555",
        name="Credentials from Password Stores",
        tactic=MITREtactic.CREDENTIAL_ACCESS,
        description="Extract credentials from password managers",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1021": MITREtechnique(
        id="T1021",
        name="Remote Services",
        tactic=MITREtactic.LATERAL_MOVEMENT,
        description="Use remote services for lateral movement",
        platforms=["Windows", "Linux", "macOS"],
        sub_techniques=["T1021.001", "T1021.002", "T1021.003"],
    ),
    "T1570": MITREtechnique(
        id="T1570",
        name="Lateral Tool Transfer",
        tactic=MITREtactic.LATERAL_MOVEMENT,
        description="Transfer tools laterally within network",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1047": MITREtechnique(
        id="T1047",
        name="Windows Management Instrumentation",
        tactic=MITREtactic.EXECUTION,
        description="Use WMI for command execution",
        platforms=["Windows"],
    ),
    "T1059": MITREtechnique(
        id="T1059",
        name="Command and Scripting Interpreter",
        tactic=MITREtactic.EXECUTION,
        description="Execute commands via scripting",
        platforms=["Windows", "Linux", "macOS"],
        sub_techniques=["T1059.001", "T1059.002", "T1059.008"],
    ),
    "T1548": MITREtechnique(
        id="T1548",
        name="Abuse Elevation Control Mechanism",
        tactic=MITREtactic.PRIVILEGE_ESCALATION,
        description="Escalate privileges through misconfigurations",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1134": MITREtechnique(
        id="T1134",
        name="Access Token Manipulation",
        tactic=MITREtactic.PRIVILEGE_ESCALATION,
        description="Manipulate access tokens for privilege escalation",
        platforms=["Windows"],
    ),
    "T1027": MITREtechnique(
        id="T1027",
        name="Obfuscated Files or Information",
        tactic=MITREtactic.DEFENSE_EVASION,
        description="Obfuscate malicious code",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1140": MITREtechnique(
        id="T1140",
        name="Deobfuscate/Decode Files or Information",
        tactic=MITREtactic.DEFENSE_EVASION,
        description="Decode obfuscated payloads",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1048": MITREtechnique(
        id="T1048",
        name="Exfiltration Over Alternative Protocol",
        tactic=MITREtactic.EXFILTRATION,
        description="Exfiltrate data over non-standard protocols",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1041": MITREtechnique(
        id="T1041",
        name="Exfiltration Over C2 Channel",
        tactic=MITREtactic.EXFILTRATION,
        description="Exfiltrate data through command & control",
        platforms=["Windows", "Linux", "macOS"],
    ),
    "T1561": MITREtechnique(
        id="T1561",
        name="Disk Wipe",
        tactic=MITREtactic.IMPACT,
        description="Wipe disks as part of attack",
        platforms=["Windows", "Linux"],
    ),
    "T1486": MITREtechnique(
        id="T1486",
        name="Encrypt Sensitive Information",
        tactic=MITREtactic.IMPACT,
        description="Encrypt data for ransom (ransomware)",
        platforms=["Windows", "Linux"],
    ),
}


@dataclass
class AttackChain:
    """A multi-step attack chain using MITRE TTPs."""
    id: str
    name: str
    tactics: list[MITREtactic]
    techniques: list[MITREtechnique]
    description: str
    difficulty: int  # 1-4 (novice to elite)


# Pre-defined attack chains
ATTACK_CHAINS: dict[str, AttackChain] = {
    "spear_phishing_to_lateral_movement": AttackChain(
        id="chain_001",
        name="Spear Phishing → Lateral Movement",
        tactics=[MITREtactic.INITIAL_ACCESS, MITREtactic.LATERAL_MOVEMENT],
        techniques=[MITRE_TECHNIQUES["T1566"], MITRE_TECHNIQUES["T1021"]],
        description="Phish for credentials, then move laterally using remote services",
        difficulty=2,
    ),
    "supply_chain_to_persistence": AttackChain(
        id="chain_002",
        name="Supply Chain Compromise → Persistence",
        tactics=[
            MITREtactic.INITIAL_ACCESS,
            MITREtactic.PERSISTENCE,
            MITREtactic.PRIVILEGE_ESCALATION,
        ],
        techniques=[
            MITRE_TECHNIQUES["T1199"],
            MITRE_TECHNIQUES["T1548"],
            MITRE_TECHNIQUES["T1027"],
        ],
        description="Exploit supply chain trust to establish persistence and escalate privileges",
        difficulty=3,
    ),
    "zero_day_to_exfiltration": AttackChain(
        id="chain_003",
        name="Zero-Day Exploit → Exfiltration",
        tactics=[
            MITREtactic.INITIAL_ACCESS,
            MITREtactic.EXECUTION,
            MITREtactic.EXFILTRATION,
        ],
        techniques=[
            MITRE_TECHNIQUES["T1190"],
            MITRE_TECHNIQUES["T1059"],
            MITRE_TECHNIQUES["T1048"],
        ],
        description="Exploit zero-day to execute code and exfiltrate data",
        difficulty=4,
    ),
}


class MITRETTPEngine:
    """
    Manages MITRE ATT&CK techniques and generates attacks based on TTPs.
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.techniques = MITRE_TECHNIQUES
        self.chains = ATTACK_CHAINS

    def get_techniques_by_tactic(self, tactic: MITREtactic) -> list[MITREtechnique]:
        """Get all techniques for a specific tactic."""
        return [t for t in self.techniques.values() if t.tactic == tactic]

    def get_techniques_by_platform(self, platform: str) -> list[MITREtechnique]:
        """Get all techniques for a specific platform."""
        return [t for t in self.techniques.values() if platform in t.platforms]

    def get_chain_by_difficulty(self, difficulty: int) -> AttackChain | None:
        """Get a random attack chain for a given difficulty level."""
        candidates = [c for c in self.chains.values() if c.difficulty == difficulty]
        return self.rng.choice(candidates) if candidates else None

    def generate_ttp_based_attack(self, difficulty: int) -> dict[str, Any]:
        """
        Generate an attack based on MITRE TTPs for a given difficulty.
        """
        chain = self.get_chain_by_difficulty(difficulty)
        if not chain:
            # Fallback: pick random techniques
            all_techs = list(self.techniques.values())
            techniques = self.rng.sample(all_techs, min(3, len(all_techs)))
            return {
                "techniques": [t.id for t in techniques],
                "tactic_sequence": [t.tactic.value for t in techniques],
                "description": "Random technique combination",
            }

        return {
            "chain_id": chain.id,
            "chain_name": chain.name,
            "techniques": [t.id for t in chain.techniques],
            "technique_names": [t.name for t in chain.techniques],
            "tactics": [t.value for t in chain.tactics],
            "description": chain.description,
            "difficulty": chain.difficulty,
        }

    def correlate_indicators_to_ttp(
        self,
        indicators: list[str],
    ) -> dict[str, Any]:
        """
        Given a list of observed indicators (e.g., "command_execution", "lateral_movement"),
        correlate them to likely MITRE TTPs.
        
        Used by BeliefMap for improved root cause analysis.
        """
        indicator_to_tactic = {
            "reconnaissance": MITREtactic.RECONNAISSANCE,
            "phishing": MITREtactic.INITIAL_ACCESS,
            "credential_access": MITREtactic.CREDENTIAL_ACCESS,
            "command_execution": MITREtactic.EXECUTION,
            "privilege_escalation": MITREtactic.PRIVILEGE_ESCALATION,
            "defense_evasion": MITREtactic.DEFENSE_EVASION,
            "lateral_movement": MITREtactic.LATERAL_MOVEMENT,
            "persistence": MITREtactic.PERSISTENCE,
            "exfiltration": MITREtactic.EXFILTRATION,
            "impact": MITREtactic.IMPACT,
        }

        likely_tactics = set()
        likely_techniques = []

        for indicator in indicators:
            if indicator in indicator_to_tactic:
                tactic = indicator_to_tactic[indicator]
                likely_tactics.add(tactic)
                techniques = self.get_techniques_by_tactic(tactic)
                likely_techniques.extend(techniques)

        return {
            "indicators": indicators,
            "likely_tactics": [t.value for t in likely_tactics],
            "likely_techniques": [
                {"id": t.id, "name": t.name} for t in set(likely_techniques)
            ][:5],  # Top 5
            "confidence": min(1.0, len(likely_tactics) * 0.25),
        }

    def get_mitre_overview(self) -> dict[str, Any]:
        """Get overview statistics about loaded MITRE TTPs."""
        tactics_used = set(t.tactic for t in self.techniques.values())
        return {
            "total_techniques": len(self.techniques),
            "total_tactics": len(tactics_used),
            "tactics": [t.value for t in tactics_used],
            "total_chains": len(self.chains),
            "max_difficulty": max((c.difficulty for c in self.chains.values()), default=1),
        }
