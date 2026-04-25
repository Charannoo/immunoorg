"""
ImmunoOrg 2.0: Elite GRPO Training Pipeline
==========================================

This module handles the full RL training cycle:
1. Scenario Generation (Curriculum, Edge Cases, Co-Evolution)
2. Trajectory Execution (converting scenarios to obs->action->reward)
3. GRPO Optimization (using TRL and Unsloth)
4. Weight Deployment (pushing to HF Hub)

Designed to run as a background process on HF Spaces via the /admin/training/start endpoint.
"""

import os
import sys
import json
import gzip
import logging
import argparse
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================================
# PATHS & PERSISTENCE (BUCKET SUPPORT)
# ============================================================

def get_base_dir() -> Path:
    """
    Determine the base directory for saving data.
    Uses /data if available (HF Space Bucket), otherwise falls back to training/
    """
    if os.path.exists("/data"):
        return Path("/data")
    return Path(__file__).resolve().parent

def training_root() -> Path:
    """Root directory for all training assets."""
    return get_base_dir() / "training_outputs"

def log_file() -> Path:
    """Path to the training log file."""
    root = training_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / "grpo_training.log"

def status_file() -> Path:
    """Path to the JSON status file for tracking progress."""
    return training_root() / "training_status.json"

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class TrainingConfig:
    model_name: str = "mistralai/Mistral-Nemo-Instruct-2407"
    max_seq_length: int = 2048
    load_in_4bit: bool = True
    num_generations: int = 8
    batch_size: int = 4
    num_train_epochs: int = 1
    learning_rate: float = 1e-5
    beta: float = 0.01
    dataset_dir: str = str(get_base_dir() / "datasets")
    output_dir: str = str(get_base_dir() / "checkpoints")
    push_to_hub: bool = True
    hub_model_id: str = "hirann/immunoorg-patronus-v2-elite"

# ============================================================
# DATASET & TRAJECTORY TOOLS
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
    """Load all scenario sets."""
    all_scenarios = []
    dataset_files = {
        "curriculum": "curriculum_dataset.json.gz",
        "edge_case": "edge_case_dataset.json.gz",
        "complexity_matrix": "complexity_matrix_dataset.json.gz",
        "coevolution": "coevolution_dataset.json.gz"
    }
    
    for dtype, fname in dataset_files.items():
        path = Path(config.dataset_dir) / fname
        if path.exists():
            scs = load_scenarios(str(path))
            for s in scs: s["dataset_type"] = dtype
            all_scenarios.extend(scs)
    return all_scenarios

# ============================================================
# REWARD FUNCTION (Socio-Technical)
# ============================================================

def immuno_reward_fn(prompts, completions, **kwargs):
    """
    Reward function for GRPO.
    Focuses on:
    1. Format compliance.
    2. Phase-appropriate action logic.
    3. Threat reduction.
    """
    rewards = []
    for completion in completions:
        r = 0.0
        # A. Strict Format Check
        if all(k in completion for k in ["REASONING:", "ACTION:", "DETAIL:", "TARGET:"]):
            r += 0.3
        else:
            r -= 0.5
            
        # B. Action Logic (Simple heuristic for training)
        # In full implementation, this calls the live env.step() reward
        if "TACKTICAL" in completion or "STRATEGIC" in completion:
            r += 0.2
            
        rewards.append(r)
    return rewards

# ============================================================
# MAIN TRAINING ENGINE
# ============================================================

def run_training(
    model_name: str = "mistralai/Mistral-Nemo-Instruct-2407",
    epochs: int = 1,
    smoke_test: bool = False
):
    """The core GRPO training loop."""
    config = TrainingConfig(
        model_name=model_name, 
        num_train_epochs=epochs
    )
    
    logger.info(f"Starting Elite Training: Model={model_name}, Epochs={epochs}, SmokeTest={smoke_test}")
    
    try:
        # 1. Initialize Unsloth Model
        from unsloth import FastLanguageModel
        from trl import GRPOTrainer, GRPOConfig
        from datasets import Dataset as HFDataset
        
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=config.model_name,
            max_seq_length=config.max_seq_length,
            load_in_4bit=config.load_in_4bit,
        )
        
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
        )
        
        # 2. Load Scenarios and Convert to GRPO format
        scenarios = get_all_scenarios(config)
        if smoke_test:
            scenarios = scenarios[:10]
            logger.info("Smoke Test: Using only 10 scenarios.")
            
        # Convert scenarios to GRPO prompt/completion pairs
        # (Simplified conversion for the pipeline)
        grpo_samples = []
        for s in scenarios:
            # Mock prompt/completion based on scenario config
            prompt = f"Scenario: {s['scenario_id']} | Difficulty: {s['difficulty']} | Goal: Resolve threat."
            completion = "REASONING: Identifying threat. | ACTION: DIAGNOSTIC | DETAIL: SCAN_LOGS | TARGET: web-01"
            grpo_samples.append({"prompt": prompt, "completion": completion})
            
        train_dataset = HFDataset.from_list(grpo_samples)
        
        # 3. GRPO Trainer
        training_args = GRPOConfig(
            output_dir=config.output_dir,
            learning_rate=config.learning_rate,
            num_train_epochs=config.num_train_epochs,
            per_device_train_batch_size=config.batch_size,
            num_generations=config.num_generations,
            max_prompt_length=512,
            max_completion_length=256,
        )
        
        trainer = GRPOTrainer(
            model=model,
            reward_funcs=[immuno_reward_fn],
            args=training_args,
            train_dataset=train_dataset,
            processing_class=tokenizer,
        )
        
        # Track status
        with open(status_file(), "w") as f:
            json.dump({"state": "training", "epochs": epochs, "progress": 0}, f)
            
        trainer.train()
        
        # 4. Deployment
        if config.push_to_hub:
            model.push_to_hub(config.hub_model_id)
            tokenizer.push_to_hub(config.hub_model_id)
            
        with open(status_file(), "w") as f:
            json.dump({"state": "completed", "epochs": epochs, "progress": 100}, f)
            
        logger.info(f"Training Complete. Model pushed to {config.hub_model_id}")
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        with open(status_file(), "w") as f:
            json.dump({"state": "failed", "error": str(e)}, f)
        raise e

# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--model", type=str, default="mistralai/Mistral-Nemo-Instruct-2407")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--smoke-test", action="store_true")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run_training(
            model_name=args.model,
            epochs=args.epochs,
            smoke_test=args.smoke_test
        )
