"""
ImmunoOrg 2.0: Dataset Validation & Statistics
=========================================

Validates dataset quality and computes statistics for GRPO training readiness.
"""

import json
import gzip
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class DatasetStats:
    """Statistics for a dataset."""
    total_scenarios: int
    difficulty_distribution: Dict[int, int]
    avg_expected_reward: float
    std_expected_reward: float
    edge_case_coverage: Optional[Dict[str, int]] = None
    complexity_coverage: Optional[Dict[str, int]] = None
    generation_coverage: Optional[Dict[int, int]] = None


@dataclass
class ValidationResult:
    """Result of dataset validation."""
    is_valid: bool
    error_count: int
    warnings: List[str]
    stats: DatasetStats


# ============================================================
# VALIDATOR
# ============================================================

class DatasetValidator:
    """
    Validates dataset quality and computes statistics.
    
    Checks:
    - Scenario completeness
    - Difficulty distribution balance
    - Expected reward distribution
    - Edge case coverage
    - Complexity matrix coverage
    """
    
    def __init__(self):
        self.validation_results = {}
    
    def validate_dataset(
        self,
        scenarios: List[Dict[str, Any]],
        dataset_type: str
    ) -> ValidationResult:
        """
        Validate a dataset.
        
        Args:
            scenarios: List of scenario dictionaries
            dataset_type: Type of dataset ("curriculum", "edge_case", etc.)
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # 1. Check completeness
        if len(scenarios) < 50:
            warnings.append(f"Small dataset: only {len(scenarios)} scenarios")
        
        # 2. Required fields check
        required_fields = ["scenario_id", "difficulty", "config", "seed"]
        for i, scenario in enumerate(scenarios[:10]):  # Check first 10
            missing = [f for f in required_fields if f not in scenario]
            if missing:
                errors.append(f"Scenario {i} missing fields: {missing}")
        
        # 3. Difficulty distribution
        difficulty_counts = {}
        expected_rewards = []
        for scenario in scenarios:
            d = scenario.get("difficulty", 1)
            difficulty_counts[d] = difficulty_counts.get(d, 0) + 1
            
            # Get expected reward range
            config = scenario.get("config", {})
            if "expected_reward_range" in config:
                expected_rewards.extend(config["expected_reward_range"])
        
        if expected_rewards:
            avg_expected = statistics.mean(expected_rewards)
            std_expected = statistics.stdev(expected_rewards) if len(expected_rewards) > 1 else 0.0
        else:
            avg_expected = 0.0
            std_expected = 0.0
        
        # 4. Edge case coverage (if edge_case dataset)
        edge_case_coverage = None
        if dataset_type == "edge_case":
            edge_cases = {}
            for scenario in scenarios:
                ecs = scenario.get("edge_case_type", "unknown")
                edge_cases[ecs] = edge_cases.get(ecs, 0) + 1
            edge_case_coverage = edge_cases
            
            expected_edge_cases = [
                "war_room_deadlock", "silo_bottleneck", "false_positive",
                "stealth_attack", "cascading_failure", "belief_divergence"
            ]
            missing_cases = [e for e in expected_edge_cases if e not in edge_cases]
            if missing_cases:
                warnings.append(f"Missing edge cases: {missing_cases}")
        
        # 5. Complexity coverage (if complexity_matrix dataset)
        complexity_coverage = None
        if dataset_type == "complexity_matrix":
            combos = {}
            for scenario in scenarios:
                mp = scenario.get("matrix_position", {})
                key = f"D{mp.get('difficulty')}-{mp.get('primary_attack')}"
                combos[key] = combos.get(key, 0) + 1
            complexity_coverage = combos
        
        # 6. Generation coverage (if coevolution dataset)
        generation_coverage = None
        if dataset_type == "coevolution":
            generations = {}
            for scenario in scenarios:
                g = scenario.get("generation", 0)
                generations[g] = generations.get(g, 0) + 1
            generation_coverage = generations
        
        # Build stats
        stats = DatasetStats(
            total_scenarios=len(scenarios),
            difficulty_distribution=difficulty_counts,
            avg_expected_reward=avg_expected,
            std_expected_reward=std_expected,
            edge_case_coverage=edge_case_coverage,
            complexity_coverage=complexity_coverage,
            generation_coverage=generation_coverage
        )
        
        # Build result
        is_valid = len(errors) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            error_count=len(errors),
            warnings=warnings,
            stats=stats
        )
        
        self.validation_results[dataset_type] = result
        
        return result
    
    def print_validation_report(self, result: ValidationResult, dataset_type: str):
        """Print validation report."""
        logger.info(f"\n{'='*60}")
        logger.info(f"VALIDATION REPORT: {dataset_type.upper()}")
        logger.info(f"{'='*60}")
        
        logger.info(f"Status: {'✓ VALID' if result.is_valid else '✗ INVALID'}")
        
        logger.info(f"\nScenarios: {result.stats.total_scenarios}")
        
        logger.info(f"\nDifficulty Distribution:")
        for d in sorted(result.stats.difficulty_distribution.keys()):
            count = result.stats.difficulty_distribution[d]
            pct = 100 * count / result.stats.total_scenarios
            logger.info(f"  Difficulty {d}: {count} ({pct:.1f}%)")
        
        logger.info(f"\nExpected Reward Distribution:")
        logger.info(f"  Average: {result.stats.avg_expected_reward:.4f}")
        logger.info(f"  Std Dev: {result.stats.std_expected_reward:.4f}")
        
        if result.stats.edge_case_coverage:
            logger.info(f"\nEdge Case Coverage ({len(result.stats.edge_case_coverage)} types):")
            for ec, count in sorted(result.stats.edge_case_coverage.items()):
                logger.info(f"  {ec}: {count}")
        
        if result.stats.complexity_coverage:
            logger.info(f"\nComplexity Coverage: {len(result.stats.complexity_coverage)} unique combos")
        
        if result.stats.generation_coverage:
            logger.info(f"\nGeneration Coverage:")
            for g, count in sorted(result.stats.generation_coverage.items()):
                logger.info(f"  Generation {g}: {count}")
        
        if result.warnings:
            logger.info(f"\nWarnings ({len(result.warnings)}):")
            for w in result.warnings:
                logger.info(f"  ⚠ {w}")
        
        if result.error_count > 0:
            logger.info(f"\nErrors ({result.error_count}):")
            for e in result.errors[:5]:  # Show first 5
                logger.info(f"  ✗ {e}")


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def load_scenarios(filepath: str) -> List[Dict[str, Any]]:
    """Load scenarios from JSON/gzip file."""
    if filepath.endswith('.gz'):
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


def validate_all_datasets(
    dataset_dir: str = "training/datasets"
) -> Dict[str, ValidationResult]:
    """
    Validate all generated datasets.
    
    Args:
        dataset_dir: Directory containing dataset files
        
    Returns:
        Dictionary of validation results by dataset type
    """
    validator = DatasetValidator()
    results = {}
    
    # Define dataset files
    dataset_files = {
        "curriculum": "curriculum_dataset.json.gz",
        "edge_case": "edge_case_dataset.json.gz",
        "complexity_matrix": "complexity_matrix_dataset.json.gz",
        "coevolution": "coevolution_dataset.json.gz"
    }
    
    for dataset_type, filename in dataset_files.items():
        filepath = Path(dataset_dir) / filename
        
        if filepath.exists():
            logger.info(f"\nLoading {filepath}...")
            scenarios = load_scenarios(str(filepath))
            
            result = validator.validate_dataset(scenarios, dataset_type)
            validator.print_validation_report(result, dataset_type)
            
            results[dataset_type] = result
        else:
            logger.warning(f"File not found: {filepath}")
    
    return results


def main():
    """Validate all datasets."""
    results = validate_all_datasets()
    
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    
    all_valid = all(r.is_valid for r in results.values())
    
    if all_valid:
        logger.info("✓ All datasets are valid for GRPO training!")
    else:
        logger.warning("✗ Some datasets have validation issues")
    
    return results


if __name__ == "__main__":
    main()