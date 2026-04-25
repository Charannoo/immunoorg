"""
Belief Map — World Model
=========================
Correlates technical failures to organizational flaws.
Tracks the agent's internal model accuracy against ground truth.

ImmunoOrg 2.0 - Phase 4: Integrated with MITRE ATT&CK TTP framework
for improved root cause analysis.
"""

from __future__ import annotations

from immunoorg.models import (
    AttackVector, BeliefMapState, TechOrgCorrelation,
)
from immunoorg.mitre_ttp import MITRETTPEngine


# Ground truth correlation library — what org flaws cause what tech failures
GROUND_TRUTH_LIBRARY: dict[str, list[dict[str, str]]] = {
    AttackVector.SQL_INJECTION.value: [
        {"flaw": "no_devsecops", "description": "No DevSecOps integration — code not security-reviewed"},
        {"flaw": "weak_db_access_control", "description": "Insufficient database access controls"},
    ],
    AttackVector.XSS.value: [
        {"flaw": "no_devsecops", "description": "No DevSecOps pipeline for frontend security"},
        {"flaw": "silo_security_engineering", "description": "Security and Engineering don't communicate"},
    ],
    AttackVector.PRIVILEGE_ESCALATION.value: [
        {"flaw": "excessive_trust", "description": "Over-permissive access policies"},
        {"flaw": "weak_monitoring", "description": "Insufficient privilege monitoring"},
    ],
    AttackVector.LATERAL_MOVEMENT.value: [
        {"flaw": "flat_network", "description": "Insufficient network segmentation"},
        {"flaw": "silo_security_engineering", "description": "Security can't coordinate with Engineering"},
    ],
    AttackVector.PHISHING.value: [
        {"flaw": "no_security_training", "description": "HR doesn't run security awareness training"},
        {"flaw": "silo_hr_security", "description": "HR and Security not coordinated"},
    ],
    AttackVector.RANSOMWARE.value: [
        {"flaw": "slow_approval", "description": "Incident response approval too slow"},
        {"flaw": "no_backup_policy", "description": "No automated backup and recovery policy"},
    ],
    AttackVector.APT_BACKDOOR.value: [
        {"flaw": "weak_monitoring", "description": "No continuous threat monitoring"},
        {"flaw": "excessive_trust", "description": "Management endpoints too trusted"},
        {"flaw": "no_zero_trust", "description": "No zero-trust architecture"},
    ],
    AttackVector.DDOS.value: [
        {"flaw": "no_rate_limiting", "description": "No rate limiting or traffic shaping"},
        {"flaw": "single_point_failure", "description": "Single point of failure in DMZ"},
    ],
    AttackVector.CREDENTIAL_STUFFING.value: [
        {"flaw": "weak_auth", "description": "No MFA or weak password policies"},
        {"flaw": "silo_it_security", "description": "IT and Security not sharing credential intelligence"},
    ],
    AttackVector.SUPPLY_CHAIN.value: [
        {"flaw": "no_devsecops", "description": "No supply chain security scanning"},
        {"flaw": "no_sbom", "description": "No Software Bill of Materials tracking"},
    ],
    AttackVector.ZERO_DAY.value: [
        {"flaw": "slow_patching", "description": "Slow patch deployment pipeline"},
        {"flaw": "weak_monitoring", "description": "No behavioral anomaly detection"},
    ],
}


class BeliefMap:
    """Manages the agent's world model — correlating technical failures to org flaws.
    
    Phase 4: Integrated with MITRE ATT&CK framework for improved TTP-based correlation.
    """

    def __init__(self):
        self.state = BeliefMapState()
        self.ground_truth: list[TechOrgCorrelation] = []
        self.ttp_engine = MITRETTPEngine()  # Phase 4 integration

    def set_ground_truth(self, attacks: list[dict]) -> None:
        """Set ground truth correlations based on active attacks."""
        self.ground_truth = []
        for attack_info in attacks:
            vector = attack_info.get("vector", "")
            if vector in GROUND_TRUTH_LIBRARY:
                for flaw_info in GROUND_TRUTH_LIBRARY[vector]:
                    corr = TechOrgCorrelation(
                        technical_indicator=f"{vector}_on_{attack_info.get('target', 'unknown')}",
                        organizational_flaw=flaw_info["flaw"],
                        confidence=1.0,
                        evidence=[flaw_info["description"]],
                        ground_truth=True,
                    )
                    self.ground_truth.append(corr)

    def agent_correlate(self, technical_indicator: str, org_flaw: str,
                        confidence: float, evidence: list[str], sim_time: float) -> TechOrgCorrelation:
        """Agent submits a correlation hypothesis."""
        corr = TechOrgCorrelation(
            technical_indicator=technical_indicator,
            organizational_flaw=org_flaw,
            confidence=confidence,
            evidence=evidence,
            discovered_at=sim_time,
        )
        self.state.correlations.append(corr)
        return corr

    def calculate_belief_accuracy(self) -> float:
        """Score the agent's belief map against ground truth (0-1)."""
        if not self.ground_truth:
            return 0.0

        gt_flaws = {c.organizational_flaw for c in self.ground_truth}
        agent_flaws = {c.organizational_flaw for c in self.state.correlations if c.confidence >= 0.5}

        if not gt_flaws:
            return 1.0

        correct = gt_flaws & agent_flaws
        precision = len(correct) / max(1, len(agent_flaws)) if agent_flaws else 0.0
        recall = len(correct) / len(gt_flaws)

        # F1 score
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def get_unidentified_flaws(self) -> list[str]:
        """Get ground truth flaws the agent hasn't identified yet."""
        gt_flaws = {c.organizational_flaw for c in self.ground_truth}
        agent_flaws = {c.organizational_flaw for c in self.state.correlations if c.confidence >= 0.5}
        return list(gt_flaws - agent_flaws)

    def get_false_positives(self) -> list[str]:
        """Get flaws the agent identified that aren't in ground truth."""
        gt_flaws = {c.organizational_flaw for c in self.ground_truth}
        agent_flaws = {c.organizational_flaw for c in self.state.correlations if c.confidence >= 0.5}
        return list(agent_flaws - gt_flaws)

    def add_timeline_event(self, event: dict) -> None:
        """Add an event to the attack timeline."""
        self.state.attack_timeline.append(event)

    def update_silo_identification(self, silos: list[tuple[str, str]]) -> None:
        """Agent identifies organizational silos."""
        self.state.identified_silos = silos

    def update_bottlenecks(self, bottlenecks: list[str]) -> None:
        """Agent identifies bottleneck departments."""
        self.state.bottleneck_departments = bottlenecks

    def get_org_weaknesses(self) -> list[str]:
        """Get all identified organizational weaknesses."""
        return [c.organizational_flaw for c in self.state.correlations if c.confidence >= 0.5]

    def generate_feedback(self) -> str:
        """Generate feedback on belief map accuracy for the agent."""
        accuracy = self.calculate_belief_accuracy()
        unidentified = self.get_unidentified_flaws()
        false_pos = self.get_false_positives()

        feedback_parts = [f"Belief map accuracy: {accuracy:.1%}"]
        if unidentified:
            feedback_parts.append(f"Unidentified flaws remaining: {len(unidentified)}")
        if false_pos:
            feedback_parts.append(f"False positives: {len(false_pos)}")
        if accuracy >= 0.8:
            feedback_parts.append("World model is highly accurate — ready for org refactoring")
        elif accuracy >= 0.5:
            feedback_parts.append("World model partially accurate — more diagnosis needed")
        else:
            feedback_parts.append("World model needs significant improvement — investigate further")

        return " | ".join(feedback_parts)
    
    # Phase 4: MITRE TTP Integration
    def correlate_attack_to_ttp(self, technical_indicators: list[str]) -> dict:
        """
        Correlate observed technical indicators to MITRE ATT&CK TTPs.
        Returns likely techniques and tactics.
        """
        return self.ttp_engine.correlate_indicators_to_ttp(technical_indicators)
    
    def get_mitre_context(self) -> dict:
        """Get overview of MITRE TTP framework."""
        return self.ttp_engine.get_mitre_overview()
    
    def suggest_defensive_strategy_from_ttp(self, observed_techniques: list[str]) -> dict:
        """
        Suggest organizational changes and technical mitigations
        based on observed MITRE techniques.
        """
        technique_to_mitigation = {
            "T1566": "Implement email security gateway and user training",
            "T1110": "Enable MFA, enforce strong password policies",
            "T1021": "Implement network segmentation, disable unnecessary remote services",
            "T1548": "Reduce privilege scope, implement privilege access management",
            "T1027": "Deploy EDR (Endpoint Detection & Response)",
            "T1486": "Implement automated backup with immutable snapshots",
            "T1190": "Apply security patches, conduct code review, enable WAF",
            "T1047": "Disable WMI, monitor WMI usage, implement application whitelisting",
        }
        
        mitigations = []
        for technique in observed_techniques:
            if technique in technique_to_mitigation:
                mitigations.append({
                    "technique": technique,
                    "mitigation": technique_to_mitigation[technique]
                })
        
        return {
            "observed_techniques": observed_techniques,
            "recommended_mitigations": mitigations,
            "confidence": min(1.0, len(observed_techniques) * 0.3),
        }
