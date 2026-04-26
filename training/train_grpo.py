"""
GRPO Training Script for ImmunoOrg
===================================
Uses Unsloth + HF TRL to train a defender agent via GRPO.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from argparse import Namespace
from typing import Any

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_action_from_completion(text: str) -> dict[str, Any] | None:
    """Extract JSON action from model completion."""
    # Try to find JSON block
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


def format_reward(completions: list[str], prompts: list[str], **kwargs) -> list[float]:
    """Reward function: score based on valid JSON action format."""
    rewards = []
    for completion in completions:
        score = 0.0
        action = parse_action_from_completion(completion)
        if action:
            score += 0.3  # Valid JSON
            if action.get("action_type") in ("tactical", "strategic", "diagnostic"):
                score += 0.2  # Valid action type
            if action.get("reasoning") and len(action["reasoning"]) > 20:
                score += 0.2  # Has reasoning
            if action.get("target"):
                score += 0.1  # Has target
            # Check specific action fields
            if action.get("tactical_action") or action.get("strategic_action") or action.get("diagnostic_action"):
                score += 0.2  # Has specific action
        rewards.append(score)
    return rewards


def reasoning_quality_reward(completions: list[str], prompts: list[str], **kwargs) -> list[float]:
    """Reward for reasoning quality in completions."""
    rewards = []
    causal = ["because", "therefore", "since", "indicates", "correlates", "caused by", "root cause"]
    structured = ["1.", "2.", "Step", "First", "Then", "Finally"]

    for completion in completions:
        score = 0.0
        lower = completion.lower()
        words = len(completion.split())

        # Length (not too short, not padding)
        if 30 <= words <= 500:
            score += 0.2
        elif words >= 10:
            score += 0.1

        # Causal reasoning
        if any(kw in lower for kw in causal):
            score += 0.3

        # Structured thinking
        if any(m in completion for m in structured):
            score += 0.2

        # References specific entities
        if re.search(r'(node|port|department|server|attack|vulnerability|silo)', lower):
            score += 0.2

        # Phase awareness
        if re.search(r'(detection|containment|root cause|refactor|validation)', lower):
            score += 0.1

        rewards.append(min(1.0, score))
    return rewards


def phase_appropriate_reward(completions: list[str], prompts: list[str], **kwargs) -> list[float]:
    """Reward for taking actions appropriate to the current phase."""
    rewards = []
    phase_actions = {
        "detection": ["scan_logs", "vulnerability_scan", "trace_attack_path"],
        "containment": ["block_port", "isolate_node", "quarantine_traffic"],
        "rca": ["correlate_failure", "identify_silo", "timeline_reconstruct"],
        "refactor": ["merge_departments", "create_shortcut_edge", "establish_devsecops"],
        "validation": ["measure_org_latency", "vulnerability_scan"],
    }

    for completion, prompt in zip(completions, prompts):
        score = 0.0
        # Detect phase from prompt
        current_phase = None
        for phase in phase_actions:
            if phase.upper() in prompt or f"Phase: {phase}" in prompt:
                current_phase = phase
                break

        if current_phase:
            appropriate = phase_actions.get(current_phase, [])
            action = parse_action_from_completion(completion)
            if action:
                action_name = (action.get("tactical_action") or
                             action.get("strategic_action") or
                             action.get("diagnostic_action") or "")
                if action_name in appropriate:
                    score = 1.0
                else:
                    score = 0.2  # Valid but wrong phase
        rewards.append(score)
    return rewards


def build_training_prompts(num_prompts: int = 200) -> list[dict[str, str]]:
    """Generate diverse training prompts by running actual environments.
    
    Instead of 5 hardcoded scenarios, we run the environment across:
    - 4 difficulty levels
    - Multiple seeds
    - All 5 incident phases
    This produces genuine, diverse observations for GRPO training.
    """
    from immunoorg.agents.defender import get_defender_prompt, format_observation_for_llm
    from immunoorg.environment import ImmunoOrgEnvironment
    from immunoorg.models import (
        ActionType, TacticalAction, DiagnosticAction, StrategicAction, ImmunoAction
    )
    import random

    system_prompt = get_defender_prompt()
    scenarios = []
    
    # Phase-appropriate actions for generating trajectories
    phase_actions = {
        "detection": [
            lambda nodes: ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.SCAN_LOGS,
                                       target=nodes[0].id if nodes else "", reasoning="Scanning for indicators."),
            lambda nodes: ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.TRACE_ATTACK_PATH,
                                       target="", reasoning="Tracing attack path."),
        ],
        "containment": [
            lambda nodes: ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.ISOLATE_NODE,
                                       target=next((n.id for n in nodes if n.compromised), nodes[0].id if nodes else ""),
                                       reasoning="Isolating compromised node."),
            lambda nodes: ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.BLOCK_PORT,
                                       target=nodes[0].id if nodes else "", reasoning="Blocking attack port."),
        ],
        "rca": [
            lambda nodes: ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.IDENTIFY_SILO,
                                       target="", reasoning="Finding organizational silos."),
            lambda nodes: ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.CORRELATE_FAILURE,
                                       target="", parameters={"technical_indicator": "attack", "organizational_flaw": "no_devsecops", "confidence": 0.7},
                                       reasoning="Correlating technical failure to org weakness."),
        ],
        "refactor": [
            lambda nodes: ImmunoAction(action_type=ActionType.STRATEGIC, strategic_action=StrategicAction.ESTABLISH_DEVSECOPS,
                                       target="dept-security", reasoning="Establishing DevSecOps."),
            lambda nodes: ImmunoAction(action_type=ActionType.STRATEGIC, strategic_action=StrategicAction.REDUCE_BUREAUCRACY,
                                       target="dept-management", reasoning="Reducing bureaucracy."),
        ],
        "validation": [
            lambda nodes: ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.MEASURE_ORG_LATENCY,
                                       target="", reasoning="Measuring org improvements."),
            lambda nodes: ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.VULNERABILITY_SCAN,
                                       target="", reasoning="Final vulnerability check."),
        ],
    }
    
    prompts_per_combo = max(1, num_prompts // (4 * 10))  # 4 difficulties * ~10 seeds
    
    for difficulty in [1, 2, 3, 4]:
        for seed in range(50):
            if len(scenarios) >= num_prompts:
                break
                
            try:
                env = ImmunoOrgEnvironment(difficulty=difficulty, seed=seed)
                obs = env.reset()
                
                # Run a few steps to reach different phases
                rng = random.Random(seed)
                for step in range(min(15, env.state.max_steps)):
                    # Capture observation as a training prompt
                    obs_text = format_observation_for_llm(obs.model_dump())
                    prompt = f"{system_prompt}\n\n## Current Observation\n{obs_text}\n\nRespond with a JSON action:"
                    scenarios.append({"prompt": prompt})
                    
                    if len(scenarios) >= num_prompts:
                        break
                    
                    # Take an action to advance the episode
                    phase = obs.current_phase.value
                    actions = phase_actions.get(phase, phase_actions["detection"])
                    action_fn = rng.choice(actions)
                    action = action_fn(obs.visible_nodes)
                    
                    obs, reward, done = env.step(action)
                    if done:
                        break
            except Exception as e:
                continue
    
    print(f"   Generated {len(scenarios)} training prompts across 4 difficulty levels")
    return scenarios


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train ImmunoOrg defender agent with GRPO")
    parser.add_argument("--smoke-test", action="store_true", help="Quick test with 2 steps")
    parser.add_argument("--warm-start", action="store_true", help="Warm-start using golden trajectories (SFT)")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct", help="Base model")
    parser.add_argument("--output-dir", default="./immunoorg-defender", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device batch size")
    parser.add_argument("--lr", type=float, default=5e-6, help="Learning rate")
    parser.add_argument(
        "--num-generations",
        type=int,
        default=2,
        help="GRPO generations per prompt (must divide batch-size × prompts per step; default 2 with batch 2)",
    )
    parser.add_argument("--max-completion-length", type=int, default=1024, help="Max completion tokens")
    return parser


def parse_train_args(argv: list[str] | None = None) -> Namespace:
    return build_arg_parser().parse_args(argv)


def _maybe_push_to_hub(output_dir: str) -> None:
    """If HF_TRAINING_PUSH_REPO_ID is set, upload ``output_dir`` to the Hub (uses HF_TOKEN)."""
    repo_id = os.environ.get("HF_TRAINING_PUSH_REPO_ID", "").strip()
    if not repo_id:
        return
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        print("HF_TRAINING_PUSH_REPO_ID is set but HF_TOKEN is missing; skipping Hub upload.")
        return
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="model", exist_ok=True)
    api.upload_folder(folder_path=output_dir, repo_id=repo_id, repo_type="model")
    print(f"Uploaded training artifacts to https://huggingface.co/{repo_id}")


def run_grpo_training(args: Namespace) -> None:
    print("=" * 60)
    print("ImmunoOrg GRPO Training Pipeline")
    print("=" * 60)

    # Try importing training libs
    try:
        from unsloth import FastLanguageModel
        HAS_UNSLOTH = True
        print("Check: Unsloth detected - using optimized training")
    except ImportError:
        HAS_UNSLOTH = False
        print("Warning: Unsloth not found - using standard HF training")

    try:
        from trl import GRPOTrainer, GRPOConfig
        from datasets import Dataset
        print("Check: TRL and datasets loaded")
    except ImportError:
        print("Error: TRL not installed. Run: pip install trl datasets")
        sys.exit(1)

    # 1. Load model
    print(f"\nLoading model: {args.model}")
    if HAS_UNSLOTH:
        model, tokenizer = FastLanguageModel.from_pretrained(
            args.model,
            max_seq_length=2048,
            load_in_4bit=True,
        )
        model = FastLanguageModel.get_peft_model(
            model, r=16, lora_alpha=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj"],
        )
    else:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import get_peft_model, LoraConfig
        import torch as _torch
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        device_map = "auto" if _torch.cuda.is_available() else "cpu"
        model = AutoModelForCausalLM.from_pretrained(args.model, device_map=device_map)
        lora_config = LoraConfig(r=16, lora_alpha=16, target_modules="all-linear")
        model = get_peft_model(model, lora_config)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 2. Build dataset
    print("\nBuilding training dataset")
    n_prompts = 8 if args.smoke_test else 200
    scenarios = build_training_prompts(num_prompts=n_prompts)
    dataset = Dataset.from_list([{"prompt": s["prompt"]} for s in scenarios])
    print(f"   {len(dataset)} scenarios loaded")

    # 3. Configure GRPO
    max_steps = 2 if args.smoke_test else None
    try:
        import torch as _torch
        on_cpu = not _torch.cuda.is_available()
    except Exception:
        on_cpu = True

    grpo_kwargs = dict(
        output_dir=args.output_dir,
        num_generations=args.num_generations,
        max_completion_length=args.max_completion_length,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        beta=0.04,
        logging_steps=1,
        save_steps=50,
        max_steps=max_steps if max_steps else -1,
        report_to="none",
    )
    if on_cpu:
        # Recent TRL refuses to start with bf16/fp16 defaults if no GPU is
        # present; we have to opt into CPU explicitly and turn mixed
        # precision off so the smoke test works on a developer laptop.
        grpo_kwargs.update(use_cpu=True, bf16=False, fp16=False)
    config = GRPOConfig(**grpo_kwargs)

    # 4. Create trainer (TRL renamed `config` -> `args` somewhere in 1.x;
    # try both so this works against older and newer TRL releases.)
    print("\nCreating GRPO trainer")
    trainer_kwargs = dict(
        model=model,
        reward_funcs=[format_reward, reasoning_quality_reward, phase_appropriate_reward],
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    try:
        trainer = GRPOTrainer(args=config, **trainer_kwargs)
    except TypeError:
        trainer = GRPOTrainer(config=config, **trainer_kwargs)

    # 5. Train
    print("\nStarting training...")
    trainer.train()

    # 5b. Export log history for evidence plots (hackathon / README)
    try:
        from pathlib import Path as _Path

        log_hist = getattr(getattr(trainer, "state", None), "log_history", None) or []
        out_dir = _Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / "grpo_log_history.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_hist, f, indent=2)
        print(f"   Wrote training log history -> {log_path}")
    except Exception as _e:
        print(f"   (could not export log_history: {_e})")

    # 6. Save
    print(f"\nSaving model to {args.output_dir}")
    os.makedirs(args.output_dir, exist_ok=True)
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Training complete!")
    _maybe_push_to_hub(args.output_dir)


def main() -> None:
    run_grpo_training(parse_train_args())


if __name__ == "__main__":
    main()
