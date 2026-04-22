"""
Curriculum Engine
=================
4-tier difficulty curriculum that progressively increases attack complexity
and organizational challenge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CurriculumLevel:
    """Definition of a curriculum difficulty level."""
    level: int
    name: str
    description: str
    max_steps: int
    attack_count: int
    lateral_movement: bool
    cascading_failures: bool
    org_refactor_required: bool
    apt_campaign: bool
    department_count: int
    silo_count: int
    adversary_adaptation_rate: float  # How fast adversary adapts (0-1)
    reward_coefficients: dict[str, float] = field(default_factory=dict)
    success_criteria: dict[str, float] = field(default_factory=dict)


CURRICULUM_LEVELS: dict[int, CurriculumLevel] = {
    1: CurriculumLevel(
        level=1,
        name="Novice — Single-Point Attack",
        description="Single attack vector targeting one node. Simple identification and blocking.",
        max_steps=50,
        attack_count=1,
        lateral_movement=False,
        cascading_failures=False,
        org_refactor_required=False,
        apt_campaign=False,
        department_count=3,
        silo_count=0,
        adversary_adaptation_rate=0.0,
        reward_coefficients={"alpha": 1.0, "beta": 0.3, "gamma": 0.1, "delta": 0.2, "epsilon": 0.1},
        success_criteria={"threats_contained": 1.0, "max_downtime": 20.0, "min_reward": 0.5},
    ),
    2: CurriculumLevel(
        level=2,
        name="Intermediate — Lateral Movement",
        description="Multi-node attack with lateral movement. Requires timeline reconstruction.",
        max_steps=100,
        attack_count=2,
        lateral_movement=True,
        cascading_failures=False,
        org_refactor_required=False,
        apt_campaign=False,
        department_count=4,
        silo_count=0,
        adversary_adaptation_rate=0.2,
        reward_coefficients={"alpha": 1.0, "beta": 0.5, "gamma": 0.2, "delta": 0.4, "epsilon": 0.2},
        success_criteria={"threats_contained": 1.0, "max_downtime": 30.0, "min_reward": 0.4},
    ),
    3: CurriculumLevel(
        level=3,
        name="Advanced — Cascading Breach + Org Refactor",
        description="Cascading failures exploiting organizational silos. Requires identifying the silo and performing basic org refactoring.",
        max_steps=150,
        attack_count=3,
        lateral_movement=True,
        cascading_failures=True,
        org_refactor_required=True,
        apt_campaign=False,
        department_count=6,
        silo_count=2,
        adversary_adaptation_rate=0.4,
        reward_coefficients={"alpha": 1.0, "beta": 0.7, "gamma": 0.5, "delta": 0.6, "epsilon": 0.3},
        success_criteria={"threats_contained": 0.9, "max_downtime": 50.0, "min_reward": 0.3},
    ),
    4: CurriculumLevel(
        level=4,
        name="Elite — APT Campaign + Total Restructure",
        description="Advanced Persistent Threat campaign requiring total org restructuring and protocol rewriting to reach Immunological Equilibrium.",
        max_steps=200,
        attack_count=5,
        lateral_movement=True,
        cascading_failures=True,
        org_refactor_required=True,
        apt_campaign=True,
        department_count=8,
        silo_count=3,
        adversary_adaptation_rate=0.6,
        reward_coefficients={"alpha": 1.0, "beta": 1.0, "gamma": 0.8, "delta": 0.8, "epsilon": 0.5},
        success_criteria={"threats_contained": 0.8, "max_downtime": 80.0, "min_reward": 0.2},
    ),
}


class CurriculumEngine:
    """Manages difficulty progression and auto-advancement."""

    def __init__(self, start_level: int = 1):
        self.current_level = max(1, min(4, start_level))
        self.episode_history: list[dict[str, Any]] = []
        self.consecutive_successes: int = 0
        self.consecutive_failures: int = 0
        self.auto_advance: bool = True

    def get_current_config(self) -> CurriculumLevel:
        return CURRICULUM_LEVELS[self.current_level]

    def get_reward_coefficients(self) -> dict[str, float]:
        return self.get_current_config().reward_coefficients

    def record_episode_result(self, metrics: dict[str, float]) -> dict[str, Any]:
        """Record episode result and potentially advance/regress difficulty."""
        config = self.get_current_config()
        criteria = config.success_criteria

        success = True
        details = {}

        # Check threats contained
        threats_contained = metrics.get("threats_contained_ratio", 0.0)
        if threats_contained < criteria.get("threats_contained", 0.8):
            success = False
        details["threats_contained"] = threats_contained

        # Check downtime
        downtime = metrics.get("total_downtime", 0.0)
        if downtime > criteria.get("max_downtime", 100.0):
            success = False
        details["downtime"] = downtime

        # Check reward
        reward = metrics.get("total_reward", 0.0)
        if reward < criteria.get("min_reward", 0.0):
            success = False
        details["reward"] = reward

        self.episode_history.append({
            "level": self.current_level,
            "success": success,
            "metrics": metrics,
            "details": details,
        })

        # Auto-advance logic
        result = {"level_changed": False, "new_level": self.current_level, "success": success}
        if success:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            if self.auto_advance and self.consecutive_successes >= 3 and self.current_level < 4:
                self.current_level += 1
                self.consecutive_successes = 0
                result["level_changed"] = True
                result["new_level"] = self.current_level
                result["reason"] = "Promoted — 3 consecutive successes"
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            if self.auto_advance and self.consecutive_failures >= 5 and self.current_level > 1:
                self.current_level -= 1
                self.consecutive_failures = 0
                result["level_changed"] = True
                result["new_level"] = self.current_level
                result["reason"] = "Demoted — 5 consecutive failures"

        return result

    def set_level(self, level: int) -> None:
        self.current_level = max(1, min(4, level))
        self.consecutive_successes = 0
        self.consecutive_failures = 0

    def get_progress_summary(self) -> dict[str, Any]:
        level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        level_successes = {1: 0, 2: 0, 3: 0, 4: 0}
        for ep in self.episode_history:
            lvl = ep["level"]
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
            if ep["success"]:
                level_successes[lvl] = level_successes.get(lvl, 0) + 1

        return {
            "current_level": self.current_level,
            "current_level_name": CURRICULUM_LEVELS[self.current_level].name,
            "total_episodes": len(self.episode_history),
            "consecutive_successes": self.consecutive_successes,
            "consecutive_failures": self.consecutive_failures,
            "level_stats": {
                lvl: {
                    "episodes": level_counts[lvl],
                    "successes": level_successes[lvl],
                    "success_rate": level_successes[lvl] / max(1, level_counts[lvl]),
                }
                for lvl in range(1, 5)
            },
        }
