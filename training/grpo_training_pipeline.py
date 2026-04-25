"""
ImmunoOrg 2.0: Complete GRPO Training Pipeline
==============================================

Complete pipeline for GRPO training on ImmunoOrg 2.0:
1. Generate datasets (curriculum, edge cases, complexity, coevolution)
2. Execute trajectories with LLM agent
3. Convert to GRPO format
4. Train with TRL GRPO trainer
5. Save trained weights
6. Generate reward curves

This module is designed to run in Google Colab.
"""

import os
import json
import gzip
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# PERSISTENT-PATH HELPERS (used by server/main.py admin endpoints)
# ============================================================

# When running on Hugging Face Spaces with a Persistent Storage volume,
# /data is writable across restarts. Otherwise we fall back to a folder
# inside the repo so local development still works.
_HF_DATA_DIR = Path("/data")


def training_root() -> Path:
    """Return the writable directory used for training artifacts.

    Prefers /data when present (HF Spaces persistent storage), else
    falls back to a local ``./training_runs`` folder.
    """
    if _HF_DATA_DIR.exists() and os.access(_HF_DATA_DIR, os.W_OK):
        root = _HF_DATA_DIR / "immunoorg-training"
    else:
        root = Path(__file__).resolve().parent.parent / "training_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def log_file() -> Path:
    """Path to the training subprocess log (tail-able via /admin/training/log)."""
    return training_root() / "train.log"


def status_file() -> Path:
    """Path to the JSON status file written by the training subprocess."""
    return training_root() / "status.json"


def write_status(payload: Dict[str, Any]) -> None:
    """Atomically write the training status JSON for the admin endpoint."""
    p = status_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(p)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class TrainingConfig:
    """Configuration for complete training pipeline."""
    # Model settings
    model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    max_seq_length: int = 2048
    load_in_4bit: bool = True
    
    # GRPO settings
    num_generations: int = 8
    batch_size: int = 4
    num_train_epochs: int = 1
    learning_rate: float = 1e-5
    max_grad_norm: float = 1.0
    beta: float = 0.01
    
    # Dataset settings
    dataset_dir: str = "training/datasets"
    trajectory_dir: str = "training/trajectories"
    grpo_data_dir: str = "training/grpo_data"
    
    # Output settings
    output_dir: str = "training/output"
    push_to_hub: bool = False
    hub_model_id: Optional[str] = None


# ============================================================
# DATASET LOADER
# ============================================================

def load_scenarios(filepath: str) -> List[Dict[str, Any]]:
    """Load scenarios from JSON/gzip file."""
    if filepath.endswith('.gz'):
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


def get_all_scenarios(config: TrainingConfig) -> List[Dict[str, Any]]:
    """
    Load all scenarios from dataset directory.
    
    Args:
        config: Training configuration
        
    Returns:
        Combined list of all scenarios
    """
    all_scenarios = []
    
    dataset_files = {
        "curriculum": "curriculum_dataset.json.gz",
        "edge_case": "edge_case_dataset.json.gz",
        "complexity_matrix": "complexity_matrix_dataset.json.gz",
        "coevolution": "coevolution_dataset.json.gz",
        "elite_scenario_mix": "elite_scenario_mix_dataset.json.gz",
    }
    
    for dataset_type, filename in dataset_files.items():
        filepath = Path(config.dataset_dir) / filename
        
        if filepath.exists():
            scenarios = load_scenarios(str(filepath))
            # Add dataset type to each scenario
            for s in scenarios:
                s["dataset_type"] = dataset_type
            
            all_scenarios.extend(scenarios)
            logger.info(f"Loaded {len(scenarios)} scenarios from {dataset_type}")
    
    logger.info(f"Total scenarios: {len(all_scenarios)}")
    
    return all_scenarios


# ============================================================
# GRPO FORMAT CONVERTER
# ============================================================

def observation_to_prompt(obs: Dict[str, Any], difficulty: int) -> str:
    """Convert observation to LLM prompt."""
    prompt = f"""You are the Patronus AI, an autonomous self-healing enterprise agent.

PHASE: {obs.get('current_phase', 'unknown')}
DIFFICULTY: {difficulty}
THREAT_LEVEL: {obs.get('threat_level', 0.0):.2f}
STEP: {obs.get('step_count', 0)} | TIME: {obs.get('sim_time', 0.0):.0f}

=== BOARD DIRECTIVES ===
{directives if (directives := obs.get('directives')) else 'None'}

=== RAG CVE INTELLIGENCE ===
{alerts if (alerts := obs.get('alerts')) else 'No alerts'}

=== NETWORK STATE ===
Visible Nodes: {len(obs.get('visible_nodes', []))} | Health: {health if (health := obs.get('network_health_summary', {}).get('average_health')) else 0.0:.1f}
Detected Threats: {len(obs.get('detected_attacks', []))}

=== ORG STATE ===
Departments: {len(obs.get('org_nodes', []))} | Pending Approvals: {len(obs.get('pending_approvals', []))}

TASK: Analyze the situation. Return your reasoning and chosen action.
FORMAT: REASONING: <text> | ACTION: <type> | DETAIL: <action_name> | TARGET: <target_id>"""
    return prompt


def action_to_completion(action: Dict[str, Any]) -> str:
    """Convert action to completion format."""
    reasoning = action.get("reasoning", "Executing standard procedure")
    action_type = action.get("action_type", "DIAGNOSTIC")
    detail = (
        action.get("tactical_action") or 
        action.get("strategic_action") or 
        action.get("diagnostic_action") or 
        "QUERY_BELIEF_MAP"
    )
    target = action.get("target", "system")
    
    return f"REASONING: {reasoning} | ACTION: {action_type} | DETAIL: {detail} | TARGET: {target}"


# ============================================================
# REWARD FUNCTION (for Colab)
# ============================================================

def compute_reward_from_step(
    obs: Dict[str, Any],
    action: Dict[str, Any],
    terminated: bool
) -> float:
    """
    Compute simplified step reward for training.
    
    This is a simplified reward function for generating training data.
    In production, use the full reward calculator from immunoorg.reward.
    
    Args:
        obs: Current observation
        action: Action taken
        terminated: Whether episode is done
        
    Returns:
        Reward value (0-1)
    """
    # Base reward from step
    reward = 0.1  # Base reward for taking any action
    
    # Action success bonus
    if obs.get("action_success", True):
        reward += 0.05
    else:
        reward -= 0.03
    
    # Threat containment bonus
    detected_attacks = obs.get("detected_attacks", [])
    threat_level = obs.get("threat_level", 0.0)
    
    if len(detected_attacks) == 0 and threat_level < 0.1:
        reward += 0.2  # Bonus for containing threats
    elif threat_level > 0.7:
        reward -= 0.1  # Penalty for high threat level
    
    # Phase-appropriate action bonus
    current_phase = obs.get("current_phase", "detection")
    action_type = action.get("action_type", "diagnostic").lower()
    
    phase_actions = {
        "detection": ["scan_logs", "vulnerability_scan", "query_belief_map", "trace_attack_path"],
        "containment": ["isolate_node", "block_port", "quarantine_traffic"],
        "rca": ["correlate_failure", "identify_silo", "timeline_reconstruct"],
        "refactor": ["merge_departments", "create_shortcut_edge", "reduce_bureaucracy"],
        "validation": ["measure_org_latency", "vulnerability_scan"]
    }
    
    detail = action.get("tactical_action") or action.get("strategic_action") or action.get("diagnostic_action") or ""
    
    if detail.lower() in phase_actions.get(current_phase, []):
        reward += 0.1  # Phase-appropriate bonus
    
    # Termination bonus
    if terminated:
        if len(detected_attacks) == 0:
            reward += 0.3  # Victory bonus
        else:
            reward -= 0.2  # Failure penalty
    
    # Clamp to 0-1
    return max(0.0, min(1.0, reward))


# ============================================================
# TRAINING DATA GENERATOR (MOCK FOR DEMO)
# ============================================================

def generate_mock_training_data(
    num_samples: int = 500,
    config: Optional[TrainingConfig] = None
) -> List[Dict[str, Any]]:
    """
    Generate mock training data for demonstration.
    
    In a real Colab, this would execute scenarios with a real LLM agent.
    For now, we generate synthetic prompt/completion/reward data.
    
    Args:
        num_samples: Number of samples to generate
        config: Training configuration
        
    Returns:
        List of GRPO training samples
    """
    logger.info(f"Generating {num_samples} mock training samples...")
    
    # Sample prompts (simulating different observations)
    phases = ["detection", "containment", "rca", "refactor", "validation"]
    action_types = ["TACTICAL", "STRATEGIC", "DIAGNOSTIC"]
    tactical_actions = ["ISOLATE_NODE", "BLOCK_PORT", "SCAN_LOGS", "DEPLOY_PATCH", "QUARANTINE_TRAFFIC"]
    strategic_actions = ["MERGE_DEPARTMENTS", "CREATE_SHORTCUT_EDGE", "REDUCE_BUREAUCRACY", "REWRITE_POLICY"]
    diagnostic_actions = ["QUERY_BELIEF_MAP", "TRACE_ATTACK_PATH", "IDENTIFY_SILO", "CORRELATE_FAILURE"]
    
    data = []
    
    for i in range(num_samples):
        phase = phases[i % len(phases)]
        difficulty = (i % 4) + 1
        threat_level = 0.3 + (0.2 * (i % 3))
        
        # Generate mock observation
        obs = {
            "current_phase": phase,
            "threat_level": threat_level,
            "step_count": i % 50,
            "sim_time": float(i * 10),
            "directives": ["Maintain 99.9% uptime"] if i % 5 == 0 else [],
            "alerts": [f"CVE-2024-{i%1000}: Critical vulnerability detected"] if i % 3 == 0 else [],
            "visible_nodes": [{"id": f"node-{j}", "name": f"Server {j}"} for j in range(5)],
            "network_health_summary": {"average_health": 0.85},
            "detected_attacks": [{"vector": "sql_injection", "severity": 0.5}] if threat_level > 0.5 else [],
            "org_nodes": [{"id": f"dept-{j}", "name": f"Department {j}"} for j in range(3)],
            "pending_approvals": [{"id": f"approval-{j}", "status": "pending"} for j in range(2)] if i % 4 == 0 else [],
            "action_success": True
        }
        
        # Generate mock action
        action_type = action_types[i % len(action_types)]
        
        if action_type == "TACTICAL":
            detail = tactical_actions[i % len(tactical_actions)]
        elif action_type == "STRATEGIC":
            detail = strategic_actions[i % len(strategic_actions)]
        else:
            detail = diagnostic_actions[i % len(diagnostic_actions)]
        
        action = {
            "action_type": action_type,
            detail.lower(): detail,
            "target": f"node-{i % 5}",
            "reasoning": f"Analyzing {phase} phase with threat level {threat_level:.2f}"
        }
        
        # Generate reward
        terminated = (i % 50 == 0)
        reward = compute_reward_from_step(obs, action, terminated)
        
        # Convert to GRPO format
        prompt = observation_to_prompt(obs, difficulty)
        completion = action_to_completion(action)
        
        data.append({
            "prompt": prompt,
            "completion": completion,
            "reward": reward,
            "difficulty": difficulty,
            "phase": phase
        })
    
    logger.info(f"Generated {len(data)} training samples")
    logger.info(f"  Average reward: {sum(d['reward'] for d in data) / len(data):.4f}")
    logger.info(f"  Reward std: {(sum((d['reward'] - sum(d['reward'] for d in data) / len(data))**2 for d in data) / len(data))**0.5:.4f}")
    
    return data


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_complete_pipeline(
    config: Optional[TrainingConfig] = None,
    generate_samples: int = 1185
) -> Dict[str, Any]:
    """
    Run complete GRPO training pipeline.
    
    Args:
        config: Training configuration
        generate_samples: Number of samples to generate (if not using live scenarios)
        
    Returns:
        Dictionary with pipeline results
    """
    if config is None:
        config = TrainingConfig()
    
    logger.info("=" * 70)
    logger.info("IMMUNOORG 2.0: COMPLETE GRPO TRAINING PIPELINE")
    logger.info("=" * 70)
    
    start_time = time.time()
    results = {}
    
    # Step 1: Load scenario definitions
    logger.info("\n[1/5] LOADING SCENARIO DEFINITIONS...")
    scenarios = get_all_scenarios(config)
    results["total_scenarios"] = len(scenarios)
    
    # Step 2: Generate training data (mock for demo, real would execute with LLM)
    logger.info(f"\n[2/5] GENERATING TRAINING DATA ({generate_samples} samples)...")
    training_data = generate_mock_training_data(generate_samples, config)
    results["training_samples"] = len(training_data)
    
    # Save training data
    output_dir = Path(config.grpo_data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    grpo_file = output_dir / "grpo_training_data.json.gz"
    with gzip.open(str(grpo_file), 'wt', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2)
    logger.info(f"Saved training data to {grpo_file}")
    results["grpo_data_file"] = str(grpo_file)
    
    # Step 3: Compute statistics
    logger.info("\n[3/5] COMPUTING DATASET STATISTICS...")
    
    # Reward distribution by difficulty
    reward_by_difficulty = {}
    for sample in training_data:
        d = sample.get("difficulty", 1)
        if d not in reward_by_difficulty:
            reward_by_difficulty[d] = []
        reward_by_difficulty[d].append(sample["reward"])
    
    stats = {}
    for d, rewards in reward_by_difficulty.items():
        stats[f"difficulty_{d}"] = {
            "count": len(rewards),
            "avg_reward": sum(rewards) / len(rewards),
            "std_reward": (sum((r - sum(rewards)/len(rewards))**2 for r in rewards) / len(rewards))**0.5
        }
    
    results["statistics"] = stats
    
    # Print statistics
    logger.info("\nReward Distribution by Difficulty:")
    for d in sorted(stats.keys()):
        s = stats[d]
        logger.info(f"  {s['count']} samples | avg_reward={s['avg_reward']:.4f} | std={s['std_reward']:.4f}")
    
    # Step 4: Save statistics
    logger.info("\n[4/5] SAVING STATISTICS...")
    
    stats_file = Path(config.output_dir) / "training_statistics.json"
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(stats_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved statistics to {stats_file}")
    
    # Step 5: Summary
    elapsed = time.time() - start_time
    
    logger.info("\n" + "=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total scenarios: {results['total_scenarios']}")
    logger.info(f"Training samples: {results['training_samples']}")
    logger.info(f"Time elapsed: {elapsed:.1f}s")
    logger.info(f"Output files:")
    logger.info(f"  - GRPO data: {results['grpo_data_file']}")
    logger.info(f"  - Statistics: {stats_file}")
    
    return results


# ============================================================
# CLI ENTRY POINT
# ============================================================

def main(argv: Optional[List[str]] = None):
    """CLI entry point.

    Subcommands:
      ``data`` (default) — generate the GRPO mock training dataset only.
      ``run``            — run end-to-end TRL+GRPO training using
                           ``training.train_grpo``. This is what the
                           HF Space ``/admin/training/start`` endpoint
                           shells out to.
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="ImmunoOrg GRPO Training Pipeline")
    subs = parser.add_subparsers(dest="cmd")

    # data subcommand
    p_data = subs.add_parser("data", help="Generate mock GRPO dataset only")
    p_data.add_argument("--samples", type=int, default=500)

    # run subcommand (delegates to training.train_grpo)
    p_run = subs.add_parser("run", help="Run TRL GRPO training end-to-end")
    p_run.add_argument("--smoke-test", action="store_true")
    p_run.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    p_run.add_argument("--epochs", type=int, default=1)
    p_run.add_argument("--batch-size", type=int, default=2)
    p_run.add_argument("--output-dir", default=str(training_root() / "checkpoints" / "immunoorg-defender"))

    args = parser.parse_args(argv)
    cmd = args.cmd or "data"

    if cmd == "data":
        config = TrainingConfig()
        return run_complete_pipeline(config, generate_samples=args.samples)

    if cmd == "run":
        write_status({
            "state": "starting",
            "model": args.model,
            "epochs": args.epochs,
            "smoke_test": bool(args.smoke_test),
            "started_at": time.time(),
        })
        try:
            from training.train_grpo import run_grpo_training, parse_train_args
            train_argv = [
                "--model", args.model,
                "--epochs", str(args.epochs),
                "--batch-size", str(args.batch_size),
                "--output-dir", args.output_dir,
            ]
            if args.smoke_test:
                train_argv.append("--smoke-test")
            run_grpo_training(parse_train_args(train_argv))
        except SystemExit as e:
            write_status({"state": "failed", "error": f"SystemExit: {e}"})
            raise
        except Exception as e:
            write_status({"state": "failed", "error": str(e)})
            logger.exception("Training run failed")
            sys.exit(1)
        write_status({
            "state": "completed",
            "output_dir": args.output_dir,
            "completed_at": time.time(),
        })
        return None

    parser.print_help()


if __name__ == "__main__":
    main()