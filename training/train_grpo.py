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


def build_training_prompts() -> list[dict[str, str]]:
    """Build training prompts from scenario templates."""
    from immunoorg.agents.defender import get_defender_prompt

    system_prompt = get_defender_prompt()

    scenarios = [
        {
            "prompt": f"{system_prompt}\n\n## Current Situation\nPhase: DETECTION\nWeb server web-server-01 shows anomalous traffic on port 3306. Threat level: 0.4.\nNetwork health: web=95%, app=100%, data=90%.\n\nWhat action should you take?",
        },
        {
            "prompt": f"{system_prompt}\n\n## Current Situation\nPhase: CONTAINMENT\nConfirmed SQL injection on data-database-05 via port 3306. Lateral movement to app-api-03.\nThreat level: 0.7. Pending approval: isolate_node for data-database-05.\n\nWhat action should you take?",
        },
        {
            "prompt": f"{system_prompt}\n\n## Current Situation\nPhase: ROOT CAUSE ANALYSIS\nAttack contained. SQL injection originated from unpatched database.\nSecurity and Engineering departments have NO direct communication channel.\nApproval latency was 4.5 time steps (above average).\n\nWhat action should you take?",
        },
        {
            "prompt": f"{system_prompt}\n\n## Current Situation\nPhase: ORG REFACTOR\nBelief map: SQL injection correlates with missing DevSecOps (confidence: 0.8).\nSilo identified: dept-security ↔ dept-engineering.\nOrg efficiency: 52%.\n\nWhat action should you take?",
        },
        {
            "prompt": f"{system_prompt}\n\n## Current Situation\nPhase: VALIDATION\nDevSecOps bridge established. Org efficiency improved to 71%.\nNo active threats. Need to verify security posture.\n\nWhat action should you take?",
        },
    ]
    return scenarios


def main():
    parser = argparse.ArgumentParser(description="Train ImmunoOrg defender agent with GRPO")
    parser.add_argument("--smoke-test", action="store_true", help="Quick test with 2 steps")
    parser.add_argument("--warm-start", action="store_true", help="Warm-start using golden trajectories (SFT)")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct", help="Base model")
    parser.add_argument("--output-dir", default="./immunoorg-defender", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device batch size")
    parser.add_argument("--lr", type=float, default=5e-6, help="Learning rate")
    parser.add_argument("--num-generations", type=int, default=4, help="GRPO generations per prompt")
    parser.add_argument("--max-completion-length", type=int, default=1024, help="Max completion tokens")
    args = parser.parse_args()


    print("=" * 60)
    print("ImmunoOrg GRPO Training Pipeline")
    print("=" * 60)

    # Try importing training libs
    try:
        from unsloth import FastLanguageModel
        HAS_UNSLOTH = True
        print("✅ Unsloth detected — using optimized training")
    except ImportError:
        HAS_UNSLOTH = False
        print("⚠️ Unsloth not found — using standard HF training")

    try:
        from trl import GRPOTrainer, GRPOConfig
        from datasets import Dataset
        print("✅ TRL and datasets loaded")
    except ImportError:
        print("❌ TRL not installed. Run: pip install trl datasets")
        sys.exit(1)

    # 1. Load model
    print(f"\n📦 Loading model: {args.model}")
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
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto")
        lora_config = LoraConfig(r=16, lora_alpha=16, target_modules="all-linear")
        model = get_peft_model(model, lora_config)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 2. Build dataset
    print("\n📊 Building training dataset")
    scenarios = build_training_prompts()
    dataset = Dataset.from_list([{"prompt": s["prompt"]} for s in scenarios])
    print(f"   {len(dataset)} scenarios loaded")

    # 3. Configure GRPO
    max_steps = 2 if args.smoke_test else None
    config = GRPOConfig(
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

    # 4. Create trainer
    print("\n🏋️ Creating GRPO trainer")
    trainer = GRPOTrainer(
        model=model,
        config=config,
        reward_funcs=[format_reward, reasoning_quality_reward, phase_appropriate_reward],
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # 5. Train
    print("\n🚀 Starting training...")
    trainer.train()

    # 6. Save
    print(f"\n💾 Saving model to {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("✅ Training complete!")


if __name__ == "__main__":
    main()
