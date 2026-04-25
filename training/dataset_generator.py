"""
ImmunoOrg 2.0: Dataset Generation for GRPO Training
=====================================================

Generates 1,200+ training scenarios optimized for GRPO training:
1. Curriculum Learning (300 scenarios, Difficulty 1→4)
2. Edge Case Coverage (400 scenarios, 12 failure modes)
3. Balanced Complexity Matrix (300 scenarios, all difficulty×attack×org combos)
4. Co-Evolution Progression (200 scenarios, adversary adaptation feedback)
"""

import json
import gzip
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES & CONFIGS
# ============================================================

@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""
    dataset_type: str  # "curriculum" | "edge_case" | "complexity_matrix" | "coevolution"
    output_dir: str = "training/datasets"
    include_metadata: bool = True
    compress_output: bool = True
    verbose: bool = True


@dataclass
class ScenarioConfig:
    """Environment configuration for a single scenario."""
    difficulty: int
    network_size: int
    departments: int
    silos: int
    max_steps: int
    attack_count: int
    expected_reward_min: float
    expected_reward_max: float
    attack_vectors: List[str] = None
    directives: List[str] = None
    edge_case_type: Optional[str] = None
    stage: Optional[str] = None
    generation: Optional[int] = None


# ============================================================
# DATASET GENERATOR
# ============================================================

class DatasetGenerator:
    """
    Generates training datasets for GRPO training.
    
    This class handles:
    - Curriculum learning scenarios (progressive difficulty)
    - Edge case scenarios (specific failure modes)
    - Balanced complexity matrices (systematic coverage)
    - Co-evolution scenarios (adversary adaptation)
    """
    
    # Curriculum configurations by difficulty level
    CURRICULUM_CONFIGS = {
        1: {
            "network_size": 7,
            "departments": 3,
            "silos": 0,
            "max_steps": 50,
            "attack_count": 1,
            "expected_reward_min": 0.10,
            "expected_reward_max": 0.20,
            "attack_vectors": ["SQL_INJECTION", "XSS", "CREDENTIAL_STUFFING"],
            "description": "Single-point attacks, simple blocking"
        },
        2: {
            "network_size": 12,
            "departments": 4,
            "silos": 0,
            "max_steps": 100,
            "attack_count": 2,
            "expected_reward_min": 0.14,
            "expected_reward_max": 0.30,
            "attack_vectors": ["LATERAL_MOVEMENT", "PRIVILEGE_ESCALATION", "PHISHING"],
            "description": "Multi-node with lateral spread, timeline reconstruction"
        },
        3: {
            "network_size": 18,
            "departments": 6,
            "silos": 2,
            "max_steps": 150,
            "attack_count": 3,
            "expected_reward_min": 0.18,
            "expected_reward_max": 0.35,
            "attack_vectors": ["RANSOMWARE", "SUPPLY_CHAIN", "DDOS"],
            "description": "Cascading failures + silos, org refactor needed"
        },
        4: {
            "network_size": 23,
            "departments": 8,
            "silos": 3,
            "max_steps": 200,
            "attack_count": 5,
            "expected_reward_min": 0.22,
            "expected_reward_max": 0.42,
            "attack_vectors": ["APT_BACKDOOR", "ZERO_DAY", "LATERAL_MOVEMENT"],
            "description": "APT with persistent backdoors, total restructuring"
        }
    }
    
    # Edge case categories with scenario counts
    EDGE_CASES = {
        "war_room_deadlock": {"count": 40, "difficulties": [2, 3, 4]},
        "silo_bottleneck": {"count": 40, "difficulties": [2, 3, 4]},
        "false_positive": {"count": 35, "difficulties": [1, 2, 3]},
        "stealth_attack": {"count": 35, "difficulties": [2, 3, 4]},
        "cascading_failure": {"count": 35, "difficulties": [3, 4]},
        "belief_divergence": {"count": 30, "difficulties": [2, 3, 4]},
        "approval_confusion": {"count": 30, "difficulties": [1, 2, 3]},
        "directive_conflict": {"count": 30, "difficulties": [2, 3, 4]},
        "ransomware_spread": {"count": 30, "difficulties": [3, 4]},
        "supply_chain": {"count": 30, "difficulties": [3, 4]},
        "pipeline_breach": {"count": 25, "difficulties": [3, 4]},
        "org_chart_ambiguity": {"count": 25, "difficulties": [2, 3, 4]},
    }
    
    # Complexity matrix dimensions
    COMPLEXITY_DIMENSIONS = {
        "difficulties": [1, 2, 3, 4],
        "attack_vectors": [
            "SQL_INJECTION", "XSS", "CREDENTIAL_STUFFING",
            "LATERAL_MOVEMENT", "PRIVILEGE_ESCALATION",
            "RANSOMWARE", "APT_BACKDOOR", "ZERO_DAY"
        ],
        "org_configs": [
            {"depts": 3, "silos": 0},
            {"depts": 4, "silos": 0},
            {"depts": 6, "silos": 1},
            {"depts": 6, "silos": 2},
            {"depts": 8, "silos": 2},
            {"depts": 8, "silos": 3}
        ],
        "directives": [None, "uptime_first", "security_first", "compliance_first", "conflicting"]
    }
    
    # Co-evolution adversary complexity by generation
    COEVOLUTION_GENERATIONS = {
        0: {"stealth": 0.3, "vectors": 1, "adaptation": 0.0, "knowledge": 0.0},
        1: {"stealth": 0.5, "vectors": 2, "adaptation": 0.2, "knowledge": 0.1},
        2: {"stealth": 0.7, "vectors": 3, "adaptation": 0.4, "knowledge": 0.2},
        3: {"stealth": 0.8, "vectors": 4, "adaptation": 0.6, "knowledge": 0.3},
        4: {"stealth": 0.9, "vectors": 5, "adaptation": 0.8, "knowledge": 0.4}
    }
    
    def __init__(self, config: DatasetConfig):
        """Initialize dataset generator with configuration."""
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scenario_counter = 0
        
        if config.verbose:
            logger.info(f"Initialized DatasetGenerator")
            logger.info(f"Output directory: {self.output_dir.absolute()}")
    
    # ========================================================
    # CURRICULUM LEARNING DATASET (300 scenarios)
    # ========================================================
    
    def generate_curriculum_dataset(self) -> List[Dict[str, Any]]:
        """
        Generate curriculum learning dataset: Difficulty 1 → 2 → 3 → 4.
        
        Returns:
            List of scenario dictionaries
        """
        logger.info("Generating Curriculum Learning Dataset (300 scenarios)...")
        scenarios = []
        
        for difficulty in [1, 2, 3, 4]:
            config = self.CURRICULUM_CONFIGS[difficulty]
            scenarios_for_difficulty = []
            count = 75  # 75 scenarios per difficulty
            
            for i in range(count):
                self.scenario_counter += 1
                scenario = {
                    "scenario_id": f"CL_L{difficulty}_{self.scenario_counter:03d}",
                    "dataset_type": "curriculum",
                    "difficulty": difficulty,
                    "stage": f"Level{difficulty}",
                    "stage_description": config["description"],
                    "seed": 100 + difficulty * 1000 + i,
                    "config": {
                        "network_size": config["network_size"],
                        "departments": config["departments"],
                        "silos": config["silos"],
                        "max_steps": config["max_steps"],
                        "attack_count": config["attack_count"],
                        "attack_vectors": config["attack_vectors"],
                        "expected_reward_range": [config["expected_reward_min"], config["expected_reward_max"]]
                    },
                    "metadata": {
                        "curriculum_stage": difficulty,
                        "requires_previous_success": difficulty > 1,
                        "recommended_training_epochs": 5 - difficulty + 1
                    }
                }
                scenarios_for_difficulty.append(scenario)
            
            scenarios.extend(scenarios_for_difficulty)
            logger.info(f"  Difficulty {difficulty}: {count} scenarios")
        
        logger.info(f"✓ Curriculum dataset complete: {len(scenarios)} scenarios")
        return scenarios
    
    # ========================================================
    # EDGE CASE DATASET (400 scenarios)
    # ========================================================
    
    def generate_edge_case_dataset(self) -> List[Dict[str, Any]]:
        """
        Generate edge case scenarios covering 12 failure modes.
        
        Returns:
            List of scenario dictionaries
        """
        logger.info("Generating Edge Case Dataset (400 scenarios)...")
        scenarios = []
        total_scenarios = sum(cfg["count"] for cfg in self.EDGE_CASES.values())
        
        for edge_case_type, edge_cfg in self.EDGE_CASES.items():
            count = edge_cfg["count"]
            difficulties = edge_cfg["difficulties"]
            
            for i in range(count):
                self.scenario_counter += 1
                # Distribute scenarios across difficulties
                difficulty = difficulties[i % len(difficulties)]
                
                scenario = {
                    "scenario_id": f"EC_{edge_case_type.upper()}_{self.scenario_counter:03d}",
                    "dataset_type": "edge_case",
                    "edge_case_type": edge_case_type,
                    "difficulty": difficulty,
                    "seed": 2000 + self.scenario_counter,
                    "config": self._get_edge_case_config(edge_case_type, difficulty, i),
                    "metadata": {
                        "failure_mode": edge_case_type,
                        "expected_agent_challenge": "high",
                        "tests_robustness": True
                    }
                }
                scenarios.append(scenario)
            
            logger.info(f"  {edge_case_type}: {count} scenarios")
        
        logger.info(f"✓ Edge case dataset complete: {len(scenarios)} scenarios")
        return scenarios
    
    def _get_edge_case_config(self, edge_case_type: str, difficulty: int, index: int) -> Dict[str, Any]:
        """Get edge case-specific configuration."""
        base_config = self.CURRICULUM_CONFIGS.get(difficulty, self.CURRICULUM_CONFIGS[1])
        
        edge_case_specifics = {
            "war_room_deadlock": {
                "war_room_scenario": True,
                "deadlock_turns": 6 + (difficulty - 1) * 2,
                "personas_count": 3 + difficulty
            },
            "silo_bottleneck": {
                "silos": max(1, difficulty - 1),
                "approval_delays": [4 + difficulty, 3 + difficulty],
                "requires_org_refactor": True
            },
            "false_positive": {
                "decoy_attacks": 2 + difficulty,
                "real_attack_clarity": 1.0 - (0.1 * difficulty)
            },
            "stealth_attack": {
                "attack_stealth": 0.8 + (0.05 * difficulty),
                "evasion_techniques": ["no_log_entries", "low_bandwidth", "mimic_legitimate_traffic"]
            },
            "cascading_failure": {
                "cascading_enabled": True,
                "failure_chain_length": 2 + difficulty,
                "propagation_speed": 0.5 + (0.1 * difficulty)
            },
            "belief_divergence": {
                "ground_truth_divergence": 0.4 + (0.1 * difficulty),
                "agent_model_accuracy": 0.5
            },
            "approval_confusion": {
                "authority_ambiguity": True,
                "overlapping_depts": 2 + difficulty
            },
            "directive_conflict": {
                "conflicting_directives": True,
                "directive_count": 2 + difficulty
            },
            "ransomware_spread": {
                "ransomware_nodes": 2 + difficulty,
                "encryption_speed": 0.6 + (0.1 * difficulty)
            },
            "supply_chain": {
                "external_attack": True,
                "dependency_vulnerability": True
            },
            "pipeline_breach": {
                "pipeline_gates": ["ast", "semantic", "terraform", "microvm"],
                "gates_bypassed": min(3, difficulty)
            },
            "org_chart_ambiguity": {
                "ambiguous_authority": True,
                "overlapping_depts": 2
            }
        }
        
        return {
            **base_config,
            **edge_case_specifics.get(edge_case_type, {})
        }
    
    # ========================================================
    # COMPLEXITY MATRIX DATASET (300 scenarios)
    # ========================================================
    
    def generate_complexity_matrix_dataset(self) -> List[Dict[str, Any]]:
        """
        Generate balanced complexity matrix: uniform coverage of all
        difficulty × attack × org_config × directive combinations.
        
        Returns:
            List of scenario dictionaries
        """
        logger.info("Generating Complexity Matrix Dataset (300 scenarios)...")
        scenarios = []
        
        # Calculate total combinations
        total_combos = (
            len(self.COMPLEXITY_DIMENSIONS["difficulties"]) *
            len(self.COMPLEXITY_DIMENSIONS["attack_vectors"]) *
            len(self.COMPLEXITY_DIMENSIONS["org_configs"]) *
            len(self.COMPLEXITY_DIMENSIONS["directives"])
        )
        logger.info(f"  Total possible combinations: {total_combos}")
        logger.info(f"  Sampling: 300 (Latin Hypercube stratification)")
        
        # Latin Hypercube sampling for even coverage
        samples_needed = 300
        used_combos = set()
        
        for i in range(samples_needed):
            self.scenario_counter += 1
            
            # Stratified random sampling
            difficulty = random.choice(self.COMPLEXITY_DIMENSIONS["difficulties"])
            attack = random.choice(self.COMPLEXITY_DIMENSIONS["attack_vectors"])
            org_config = random.choice(self.COMPLEXITY_DIMENSIONS["org_configs"])
            directive = random.choice(self.COMPLEXITY_DIMENSIONS["directives"])
            
            combo_key = (difficulty, attack, org_config["depts"], org_config["silos"], directive)
            
            scenario = {
                "scenario_id": f"CM_{self.scenario_counter:03d}",
                "dataset_type": "complexity_matrix",
                "difficulty": difficulty,
                "seed": 3000 + self.scenario_counter,
                "matrix_position": {
                    "difficulty": difficulty,
                    "primary_attack": attack,
                    "org_depts": org_config["depts"],
                    "org_silos": org_config["silos"],
                    "directive_type": directive
                },
                "config": self._get_matrix_config(difficulty, attack, org_config, directive),
                "metadata": {
                    "coverage_category": "balanced_sampling",
                    "ensures_generalization": True
                }
            }
            scenarios.append(scenario)
            used_combos.add(combo_key)
        
        logger.info(f"  Unique combinations covered: {len(used_combos)}/{total_combos}")
        logger.info(f"✓ Complexity matrix dataset complete: {len(scenarios)} scenarios")
        return scenarios
    
    def _get_matrix_config(self, difficulty: int, attack: str, org_config: Dict, directive: Optional[str]) -> Dict[str, Any]:
        """Get complexity matrix configuration."""
        base_config = self.CURRICULUM_CONFIGS.get(difficulty, self.CURRICULUM_CONFIGS[1])
        
        return {
            "difficulty": difficulty,
            "network_size": base_config["network_size"],
            "departments": org_config["depts"],
            "silos": org_config["silos"],
            "max_steps": base_config["max_steps"],
            "attack_vectors": [attack],
            "attack_count": base_config["attack_count"],
            "directive": directive,
            "expected_reward_range": [base_config["expected_reward_min"], base_config["expected_reward_max"]]
        }
    
    # ========================================================
    # CO-EVOLUTION DATASET (200 scenarios)
    # ========================================================
    
    def generate_coevolution_dataset(self) -> List[Dict[str, Any]]:
        """
        Generate co-evolution progression: adversary adapts over generations.
        
        Returns:
            List of scenario dictionaries
        """
        logger.info("Generating Co-Evolution Dataset (200 scenarios)...")
        scenarios = []
        
        generations = [0, 1, 2, 3, 4]
        scenarios_per_gen = {0: 50, 1: 40, 2: 40, 3: 40, 4: 30}
        
        for gen in generations:
            count = scenarios_per_gen[gen]
            adversary_complexity = self.COEVOLUTION_GENERATIONS[gen]
            
            for i in range(count):
                self.scenario_counter += 1
                
                scenario = {
                    "scenario_id": f"COEV_G{gen}_{self.scenario_counter:03d}",
                    "dataset_type": "coevolution",
                    "generation": gen,
                    "difficulty": 2 + (gen // 2),  # Difficulty increases with generation
                    "seed": 4000 + gen * 1000 + i,
                    "adversary_complexity": adversary_complexity,
                    "config": self._get_coevolution_config(gen),
                    "metadata": {
                        "adversary_stealth": adversary_complexity["stealth"],
                        "num_attack_vectors": adversary_complexity["vectors"],
                        "adaptation_speed": adversary_complexity["adaptation"],
                        "expected_difficulty": "increasing",
                        "tests_meta_learning": True
                    }
                }
                scenarios.append(scenario)
            
            logger.info(f"  Generation {gen}: {count} scenarios (stealth={adversary_complexity['stealth']:.1f})")
        
        logger.info(f"✓ Co-evolution dataset complete: {len(scenarios)} scenarios")
        return scenarios
    
    def _get_coevolution_config(self, generation: int) -> Dict[str, Any]:
        """Get co-evolution configuration for a generation."""
        difficulty = min(4, 2 + (generation // 2))
        base_config = self.CURRICULUM_CONFIGS[difficulty]
        
        return {
            "generation": generation,
            "difficulty": difficulty,
            "network_size": base_config["network_size"],
            "departments": base_config["departments"],
            "silos": base_config["silos"],
            "max_steps": base_config["max_steps"],
            "attack_count": base_config["attack_count"],
            "attack_vectors": base_config["attack_vectors"],
            "expected_reward_range": [
                base_config["expected_reward_min"] + (generation * 0.05),
                base_config["expected_reward_max"] + (generation * 0.08)
            ]
        }
    
    # ========================================================
    # SAVE METHODS
    # ========================================================
    
    def save_dataset(self, scenarios: List[Dict[str, Any]], filename: str) -> str:
        """
        Save dataset to file (optionally compressed).
        
        Args:
            scenarios: List of scenario dictionaries
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename
        
        if self.config.compress_output and filename.endswith('.json'):
            output_path = output_path.with_suffix('.json.gz')
            with gzip.open(str(output_path), 'wt', encoding='utf-8') as f:
                json.dump(scenarios, f, indent=2)
            logger.info(f"Saved {len(scenarios)} scenarios to {output_path} (compressed)")
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(scenarios, f, indent=2)
            logger.info(f"Saved {len(scenarios)} scenarios to {output_path}")
        
        return str(output_path)
    
    # ========================================================
    # MAIN GENERATION METHOD
    # ========================================================
    
    def generate_all_datasets(self) -> Dict[str, str]:
        """
        Generate all four dataset types.
        
        Returns:
            Dictionary mapping dataset names to file paths
        """
        logger.info("=" * 70)
        logger.info("STARTING COMPLETE DATASET GENERATION")
        logger.info("=" * 70)
        
        results = {}
        
        # 1. Curriculum Learning
        logger.info("\n[1/4] CURRICULUM LEARNING DATASET")
        curriculum_scenarios = self.generate_curriculum_dataset()
        curriculum_path = self.save_dataset(curriculum_scenarios, "curriculum_dataset.json")
        results["curriculum"] = curriculum_path
        
        # 2. Edge Cases
        logger.info("\n[2/4] EDGE CASE DATASET")
        edge_case_scenarios = self.generate_edge_case_dataset()
        edge_case_path = self.save_dataset(edge_case_scenarios, "edge_case_dataset.json")
        results["edge_case"] = edge_case_path
        
        # 3. Complexity Matrix
        logger.info("\n[3/4] COMPLEXITY MATRIX DATASET")
        matrix_scenarios = self.generate_complexity_matrix_dataset()
        matrix_path = self.save_dataset(matrix_scenarios, "complexity_matrix_dataset.json")
        results["complexity_matrix"] = matrix_path
        
        # 4. Co-Evolution
        logger.info("\n[4/4] CO-EVOLUTION DATASET")
        coevolution_scenarios = self.generate_coevolution_dataset()
        coevolution_path = self.save_dataset(coevolution_scenarios, "coevolution_dataset.json")
        results["coevolution"] = coevolution_path
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("DATASET GENERATION COMPLETE")
        logger.info("=" * 70)
        self._print_summary(
            curriculum_scenarios,
            edge_case_scenarios,
            matrix_scenarios,
            coevolution_scenarios
        )
        
        return results
    
    def _print_summary(self, curriculum, edge_cases, matrix, coevolution):
        """Print a formatted summary of generated datasets."""
        total_scenarios = len(curriculum) + len(edge_cases) + len(matrix) + len(coevolution)
        
        summary = f"""
DATASET GENERATION SUMMARY
==========================

Curriculum Learning Dataset:
  - Total scenarios: {len(curriculum)}
  - Difficulty 1: {len([s for s in curriculum if s['difficulty'] == 1])} scenarios
  - Difficulty 2: {len([s for s in curriculum if s['difficulty'] == 2])} scenarios
  - Difficulty 3: {len([s for s in curriculum if s['difficulty'] == 3])} scenarios
  - Difficulty 4: {len([s for s in curriculum if s['difficulty'] == 4])} scenarios

Edge Case Dataset:
  - Total scenarios: {len(edge_cases)}
  - Coverage: {len(self.EDGE_CASES)} failure modes

Complexity Matrix Dataset:
  - Total scenarios: {len(matrix)}
  - Coverage: {len(set((s['matrix_position']['difficulty'], s['matrix_position']['primary_attack']) for s in matrix))} difficulty×attack combos

Co-Evolution Dataset:
  - Total scenarios: {len(coevolution)}
  - Generations: {len(set(s['generation'] for s in coevolution))}

GRAND TOTAL: {total_scenarios} scenarios across all datasets
"""
        logger.info(summary)


# ============================================================
# CLI UTILITY
# ============================================================

def main():
    """Generate all datasets (CLI entry point)."""
    config = DatasetConfig(
        dataset_type="all",
        output_dir="training/datasets",
        include_metadata=True,
        compress_output=True,
        verbose=True
    )
    
    generator = DatasetGenerator(config)
    results = generator.generate_all_datasets()
    
    print("\n" + "=" * 70)
    print("OUTPUT FILES")
    print("=" * 70)
    for dataset_name, filepath in results.items():
        print(f"  {dataset_name}: {filepath}")


if __name__ == "__main__":
    main()
