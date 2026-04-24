"""
Self-Improvement Loop
=====================
Recursive cycle: contain → analyze → mutate org → generate harder attack → repeat.
Tracks generational improvement toward "Immunological Equilibrium".
"""

from __future__ import annotations

import copy
import random
from typing import Any

from immunoorg.models import (
    GenerationRecord, OrgEdge, OrgNode, SelfImprovementState, PatchCandidate,
)
from immunoorg.org_graph import OrgGraph


class SelfImprovementEngine:
    """Manages the recursive self-improvement loop."""

    def __init__(self, seed: int | None = None):
        self.state = SelfImprovementState()
        self.rng = random.Random(seed)
        self.equilibrium_threshold = 0.05  # Improvement rate below this = equilibrium

    def record_generation(
        self,
        org_graph: OrgGraph,
        attack_complexity: float,
        time_to_containment: float,
        total_reward: float,
        mutations: list[str],
        attack_vector: str | None = None,
    ) -> GenerationRecord:
        """Record the results of a generation."""
        record = GenerationRecord(
            generation=self.state.current_generation,
            org_graph_snapshot=[n.model_copy() for n in org_graph.get_all_nodes()],
            org_edges_snapshot=[e.model_copy() for e in org_graph.get_all_edges()],
            attack_complexity=attack_complexity,
            time_to_containment=time_to_containment,
            org_efficiency=org_graph.calculate_org_efficiency(),
            total_reward=total_reward,
            mutations_applied=mutations,
        )
        self.state.generations.append(record)

        # Track best configuration
        if total_reward > self.state.best_reward:
            self.state.best_reward = total_reward
            self.state.best_org_config = [n.model_copy() for n in org_graph.get_all_nodes()]
            self.state.best_org_edges = [e.model_copy() for e in org_graph.get_all_edges()]

        # Check for equilibrium
        self._check_equilibrium()

        self.state.current_generation += 1
        return record

    def _check_equilibrium(self) -> None:
        """Check if the system has reached immunological equilibrium."""
        if len(self.state.generations) < 3:
            return

        recent = self.state.generations[-3:]
        improvements = []
        for i in range(1, len(recent)):
            prev_reward = recent[i - 1].total_reward
            curr_reward = recent[i].total_reward
            if prev_reward != 0:
                improvement = (curr_reward - prev_reward) / abs(prev_reward)
            else:
                improvement = curr_reward
            improvements.append(improvement)

        avg_improvement = sum(improvements) / len(improvements)
        self.state.improvement_rate = avg_improvement

        if abs(avg_improvement) < self.equilibrium_threshold:
            self.state.equilibrium_reached = True

    def suggest_org_mutations(self, org_graph: OrgGraph, weaknesses: list[str]) -> list[dict[str, Any]]:
        """Suggest org graph mutations based on identified weaknesses."""
        mutations = []

        # Identify silos and suggest connections
        silos = org_graph.identify_silos()
        for silo_a, silo_b in silos:
            mutations.append({
                "type": "create_shortcut_edge",
                "source": silo_a,
                "target": silo_b,
                "reason": f"Bridge silo between {silo_a} and {silo_b}",
            })

        # Address specific weaknesses
        weakness_mutations = {
            "slow_approval": {"type": "reduce_bureaucracy", "reason": "Reduce approval latency"},
            "no_devsecops": {"type": "establish_devsecops", "reason": "Integrate security into dev pipeline"},
            "silo_security_engineering": {
                "type": "create_shortcut_edge",
                "source": "dept-security",
                "target": "dept-engineering",
                "reason": "Connect Security and Engineering",
            },
            "excessive_trust": {"type": "update_approval_protocol", "reason": "Tighten access controls"},
            "weak_monitoring": {"type": "create_incident_channel", "reason": "Add monitoring capability"},
        }

        for weakness in weaknesses:
            if weakness in weakness_mutations:
                mutations.append(weakness_mutations[weakness])

        return mutations

    def apply_mutations(self, org_graph: OrgGraph, mutations: list[dict[str, Any]]) -> list[str]:
        """Apply suggested mutations to the org graph."""
        applied = []
        for mutation in mutations:
            mut_type = mutation.get("type", "")
            if mut_type == "create_shortcut_edge":
                src = mutation.get("source", "")
                dst = mutation.get("target", "")
                if src and dst:
                    result = org_graph.create_shortcut_edge(src, dst)
                    if result:
                        applied.append(f"Created shortcut: {src} → {dst}")
            elif mut_type == "reduce_bureaucracy":
                for node in org_graph.get_all_nodes():
                    if node.active:
                        org_graph.reduce_bureaucracy(node.id)
                        applied.append(f"Reduced bureaucracy: {node.id}")
                        break
            elif mut_type == "establish_devsecops":
                # Create a cross-functional team bridging security and engineering
                sec = org_graph.get_node("dept-security")
                eng = org_graph.get_node("dept-engineering")
                if sec and eng:
                    org_graph.create_shortcut_edge(sec.id, eng.id)
                    org_graph.create_shortcut_edge(eng.id, sec.id)
                    applied.append("Established DevSecOps bridge")
            elif mut_type == "create_incident_channel":
                # Connect security to all departments with fast channels
                sec = org_graph.get_node("dept-security")
                if sec:
                    for node in org_graph.get_all_nodes():
                        if node.id != sec.id and node.active:
                            org_graph.create_shortcut_edge(sec.id, node.id)
                    applied.append("Created incident response channels")
            elif mut_type == "update_approval_protocol":
                for node in org_graph.get_all_nodes():
                    if node.active:
                        node.cooperation_threshold = max(0.2, node.cooperation_threshold - 0.1)
                applied.append("Updated approval protocols — lowered thresholds")

        return applied

    def get_improvement_trajectory(self) -> list[dict[str, float]]:
        """Get the improvement trajectory across generations."""
        return [
            {
                "generation": g.generation,
                "time_to_containment": g.time_to_containment,
                "org_efficiency": g.org_efficiency,
                "total_reward": g.total_reward,
                "attack_complexity": g.attack_complexity,
            }
            for g in self.state.generations
        ]

    def get_summary(self) -> dict[str, Any]:
        return {
            "current_generation": self.state.current_generation,
            "total_generations": len(self.state.generations),
            "equilibrium_reached": self.state.equilibrium_reached,
            "improvement_rate": self.state.improvement_rate,
            "best_reward": self.state.best_reward,
            "trajectory": self.get_improvement_trajectory(),
        }


# ── Time-Travel Forensics & Auto-Patch (Theme 4: Self-Improving Agents) ──────

class TimeTravelForensics:
    """
    ImmunoOrg 2.0 — Theme 4: Self-Improving Agent Systems
    Bonus Prize: Mercor — Scaling Token Output Rewards

    After an incident is contained, reconstructs the full kill chain,
    generates a minimal code patch, validates it adversarially, and
    submits it as a PR. Patches are added to the training dataset,
    closing the self-improvement loop.
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.patch_history: list[PatchCandidate] = []
        self.training_dataset: list[dict[str, Any]] = []  # Patches ready for fine-tuning

    def reconstruct_kill_chain(self, attack_history: list[Any], sim_time: float) -> dict[str, Any]:
        """
        Replay event log to build complete attack timeline.
        Returns kill chain with confidence scores.
        """
        if not attack_history:
            return {"stages": [], "confidence": 0.0, "root_cause": "unknown"}

        stages = []
        for i, event in enumerate(attack_history[-10:]):  # Last 10 events
            stage = {
                "order": i + 1,
                "event": str(event)[:100],
                "ttp": self._infer_ttp(str(event)),
                "confidence": self.rng.uniform(0.65, 0.95),
            }
            stages.append(stage)

        root_cause = self._identify_root_cause(stages)
        return {
            "stages": stages,
            "confidence": sum(s["confidence"] for s in stages) / max(1, len(stages)),
            "root_cause": root_cause,
            "reconstructed_at": sim_time,
        }

    def _infer_ttp(self, event_str: str) -> str:
        ttp_map = {
            "sql": "T1190 — Exploit Public-Facing Application",
            "lateral": "T1021 — Remote Services (Lateral Movement)",
            "credential": "T1078 — Valid Accounts",
            "privilege": "T1068 — Exploitation for Privilege Escalation",
            "ransomware": "T1486 — Data Encrypted for Impact",
            "phish": "T1566 — Phishing",
        }
        event_lower = event_str.lower()
        for key, ttp in ttp_map.items():
            if key in event_lower:
                return ttp
        return "T1059 — Command and Scripting Interpreter"

    def _identify_root_cause(self, stages: list[dict]) -> str:
        causes = [
            "Missing input validation on API endpoint",
            "Hardcoded credentials in source code",
            "Overly permissive IAM policy (AdministratorAccess)",
            "Unpatched dependency with known CVE",
            "Missing authentication middleware on admin endpoint",
            "S3 bucket publicly accessible due to IaC misconfiguration",
        ]
        return self.rng.choice(causes)

    def generate_patch_candidate(
        self,
        root_cause: str,
        vulnerability_id: str,
        sim_time: float,
    ) -> PatchCandidate:
        """
        Generate a minimal code patch for the identified root cause.
        Mercor bonus: token_count is tracked; quality = 1/log2(tokens) * test_pass_rate.
        """
        # Simulate patch generation — in production this calls an LLM
        patch_templates = {
            "Missing input validation": (
                "- def process_input(data):\n-     return db.query(data)\n"
                "+ def process_input(data):\n+     data = sanitize(data)\n"
                "+     if not validate_schema(data):\n+         raise ValueError('Invalid input')\n"
                "+     return db.query(data)",
                18,  # token count (concise = high Mercor reward)
            ),
            "Hardcoded credentials": (
                "- API_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
                "+ API_KEY = os.environ.get('API_KEY')\n"
                "+ if not API_KEY:\n+     raise EnvironmentError('API_KEY not set')",
                12,
            ),
            "Overly permissive IAM": (
                "- Effect: Allow\n-   Action: '*'\n-   Resource: '*'\n"
                "+ Effect: Allow\n+   Action:\n+     - s3:GetObject\n+     - s3:PutObject\n"
                "+   Resource: 'arn:aws:s3:::app-bucket/*'",
                20,
            ),
            "Missing authentication": (
                "- @app.route('/admin')\n- def admin():\n"
                "+ @app.route('/admin')\n+ @requires_auth\n+ def admin():\n",
                8,
            ),
        }
        # Find best matching template
        diff, token_count = "# Generic patch", 50
        for key, (template_diff, tokens) in patch_templates.items():
            if any(word in root_cause for word in key.split()):
                diff, token_count = template_diff, tokens
                break

        # Simulate test results
        test_cases = self.rng.randint(3, 12)
        test_pass_rate = self.rng.uniform(0.85, 1.0)
        regressions = 0 if test_pass_rate > 0.95 else self.rng.randint(0, 1)

        from immunoorg.reward import RewardCalculator
        quality = RewardCalculator.compute_patch_quality_score(
            token_count, test_pass_rate, regressions
        )

        patch = PatchCandidate(
            vulnerability_id=vulnerability_id,
            cve_reference=f"CVE-2024-{self.rng.randint(10000, 99999)}",
            patch_diff=diff,
            token_count=token_count,
            lines_changed=token_count // 4,
            test_cases_generated=test_cases,
            test_pass_rate=test_pass_rate,
            regression_count=regressions,
            pr_submitted=True,
            quality_score=quality,
            generated_at=sim_time,
        )
        self.patch_history.append(patch)
        return patch

    def add_to_training_dataset(self, patch: PatchCandidate, kill_chain: dict) -> None:
        """
        Closes the self-improvement loop: successful patches become
        training examples for the next model fine-tuning run.
        """
        if patch.quality_score >= 0.3 and patch.test_pass_rate >= 0.85:
            record = {
                "patch_id": patch.patch_id,
                "root_cause": kill_chain.get("root_cause", ""),
                "patch_diff": patch.patch_diff,
                "quality_score": patch.quality_score,
                "token_count": patch.token_count,
                "test_pass_rate": patch.test_pass_rate,
                "cve": patch.cve_reference,
                "training_label": "patch_generation",
            }
            self.training_dataset.append(record)
            patch.added_to_training = True

    def get_patch_summary(self) -> dict[str, Any]:
        if not self.patch_history:
            return {"total_patches": 0, "avg_quality": 0.0, "training_examples": 0}
        return {
            "total_patches": len(self.patch_history),
            "avg_quality": sum(p.quality_score for p in self.patch_history) / len(self.patch_history),
            "avg_token_count": sum(p.token_count for p in self.patch_history) / len(self.patch_history),
            "training_examples": len(self.training_dataset),
            "best_patch": max(self.patch_history, key=lambda p: p.quality_score).patch_id,
        }
