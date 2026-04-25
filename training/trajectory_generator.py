"""
ImmunoOrg 2.0: Trajectory Generator for GRPO Training
=======================================================

Executes scenarios and records observation → action → reward trajectories
suitable for GRPO training with TRL (Transformers Reinforcement Learning).
"""

import json
import gzip
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class TrajectoryFrame:
    """Single step in a trajectory."""
    step: int
    observation: Dict[str, Any]
    action: Dict[str, Any]
    reward: float
    terminated: bool


@dataclass
class Trajectory:
    """Complete episode trajectory."""
    scenario_id: str
    dataset_type: str
    difficulty: int
    seed: int
    frames: List[TrajectoryFrame] = field(default_factory=list)
    cumulative_reward: float = 0.0
    num_frames: int = 0
    avg_reward: float = 0.0
    max_steps: int = 0
    time_to_containment: Optional[int] = None
    status: str = "pending"  # pending | completed | failed
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "dataset_type": self.dataset_type,
            "difficulty": self.difficulty,
            "seed": self.seed,
            "frames": [
                {
                    "step": f.step,
                    "observation": f.observation,
                    "action": f.action,
                    "reward": f.reward,
                    "terminated": f.terminated
                }
                for f in self.frames
            ],
            "cumulative_reward": self.cumulative_reward,
            "num_frames": self.num_frames,
            "avg_reward": self.avg_reward,
            "max_steps": self.max_steps,
            "time_to_containment": self.time_to_containment,
            "status": self.status,
            "error_message": self.error_message
        }


# ============================================================
# TRAJECTORY GENERATOR
# ============================================================

class TrajectoryGenerator:
    """
    Generates training trajectories by executing scenarios in the environment.
    
    This class:
    - Loads scenario definitions
    - Initializes the environment with scenario configs
    - Runs agent to completion
    - Records observation → action → reward frames
    - Computes trajectory statistics
    """
    
    def __init__(self, env=None, agent=None, output_dir: str = "training/trajectories"):
        """
        Initialize trajectory generator.
        
        Args:
            env: ImmunoOrgEnvironment instance
            agent: Agent with act(obs) -> action method
            output_dir: Directory for saving trajectories
        """
        self.env = env
        self.agent = agent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trajectories = []
        self.stats = {
            "total_trajectories": 0,
            "successful": 0,
            "failed": 0,
            "total_frames": 0,
            "avg_reward_overall": 0.0
        }
    
    def generate_trajectory(
        self,
        scenario: Dict[str, Any],
        max_steps: Optional[int] = None,
        verbose: bool = False
    ) -> Trajectory:
        """
        Execute one scenario and record trajectory.
        
        Args:
            scenario: Scenario configuration dictionary
            max_steps: Override max steps (if None, use scenario config)
            verbose: Print progress
            
        Returns:
            Trajectory object with all frames and stats
        """
        if not self.env or not self.agent:
            raise ValueError("Environment and agent must be initialized before generating trajectories")
        
        scenario_id = scenario.get("scenario_id", "unknown")
        difficulty = scenario.get("difficulty", 1)
        seed = scenario.get("seed", 42)
        dataset_type = scenario.get("dataset_type", "unknown")
        config = scenario.get("config", {})
        
        # Get max steps from config
        max_steps = max_steps or config.get("max_steps", 100)
        
        # Create trajectory object
        trajectory = Trajectory(
            scenario_id=scenario_id,
            dataset_type=dataset_type,
            difficulty=difficulty,
            seed=seed,
            max_steps=max_steps
        )
        
        try:
            # Reset environment with scenario seed
            obs = self.env.reset(seed=seed)
            
            if verbose:
                logger.info(f"Executing {scenario_id} (difficulty={difficulty}, seed={seed})")
            
            step = 0
            containment_time = None
            
            # Run episode to completion or max steps
            while step < max_steps:
                # Agent observes and acts
                action = self.agent.act(obs)
                
                # Environment steps
                next_obs, reward, terminated = self.env.step(action)
                
                # Serialize observation and action
                obs_dict = self._serialize_observation(obs)
                action_dict = self._serialize_action(action)
                
                # Record frame
                frame = TrajectoryFrame(
                    step=step,
                    observation=obs_dict,
                    action=action_dict,
                    reward=float(reward),
                    terminated=terminated
                )
                trajectory.frames.append(frame)
                trajectory.cumulative_reward += reward
                
                # Track containment time (first step where threats are contained)
                if containment_time is None and self._is_contained(next_obs):
                    containment_time = step
                
                if terminated:
                    trajectory.status = "completed"
                    break
                
                obs = next_obs
                step += 1
            
            # Compute trajectory stats
            trajectory.num_frames = len(trajectory.frames)
            trajectory.avg_reward = (
                trajectory.cumulative_reward / max(1, len(trajectory.frames))
            )
            trajectory.time_to_containment = containment_time
            
            if trajectory.status == "pending":
                trajectory.status = "truncated"  # Max steps reached
            
            self.stats["total_trajectories"] += 1
            self.stats["successful"] += 1
            self.stats["total_frames"] += trajectory.num_frames
            self.trajectories.append(trajectory)
            
            if verbose:
                logger.info(
                    f"  → {scenario_id}: {trajectory.num_frames} frames, "
                    f"reward={trajectory.cumulative_reward:.3f}, "
                    f"avg={trajectory.avg_reward:.3f}"
                )
            
            return trajectory
        
        except Exception as e:
            logger.error(f"Error executing {scenario_id}: {str(e)}")
            trajectory.status = "failed"
            trajectory.error_message = str(e)
            self.stats["failed"] += 1
            return trajectory
    
    def generate_trajectories_batch(
        self,
        scenarios: List[Dict[str, Any]],
        max_parallel: int = 1,
        verbose: bool = True
    ) -> List[Trajectory]:
        """
        Generate trajectories for multiple scenarios.
        
        Args:
            scenarios: List of scenario configurations
            max_parallel: Number of parallel workers (currently 1, TODO: implement parallelism)
            verbose: Print progress
            
        Returns:
            List of Trajectory objects
        """
        trajectories = []
        total = len(scenarios)
        
        logger.info(f"Generating {total} trajectories...")
        
        start_time = time.time()
        
        for i, scenario in enumerate(scenarios):
            trajectory = self.generate_trajectory(scenario, verbose=verbose)
            trajectories.append(trajectory)
            
            if (i + 1) % max(1, total // 10) == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate if rate > 0 else 0
                logger.info(
                    f"Progress: {i+1}/{total} ({100*(i+1)/total:.1f}%) | "
                    f"Elapsed: {elapsed:.1f}s | ETA: {remaining:.1f}s"
                )
        
        elapsed = time.time() - start_time
        logger.info(f"Batch complete: {len(trajectories)} trajectories in {elapsed:.1f}s")
        
        return trajectories
    
    def save_trajectories(
        self,
        trajectories: List[Trajectory],
        filename: str,
        compress: bool = True
    ) -> str:
        """
        Save trajectories to file.
        
        Args:
            trajectories: List of Trajectory objects
            filename: Output filename
            compress: Compress with gzip
            
        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename
        
        # Convert to dictionaries
        trajectory_dicts = [t.to_dict() for t in trajectories]
        
        if compress and filename.endswith('.json'):
            output_path = output_path.with_suffix('.json.gz')
            with gzip.open(str(output_path), 'wt', encoding='utf-8') as f:
                json.dump(trajectory_dicts, f, indent=2)
            logger.info(f"Saved {len(trajectories)} trajectories to {output_path} (compressed)")
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(trajectory_dicts, f, indent=2)
            logger.info(f"Saved {len(trajectories)} trajectories to {output_path}")
        
        return str(output_path)
    
    def _serialize_observation(self, obs) -> Dict[str, Any]:
        """Serialize observation for storage."""
        if hasattr(obs, 'dict'):
            return obs.dict()
        elif isinstance(obs, dict):
            return obs
        else:
            return {"raw": str(obs)}
    
    def _serialize_action(self, action) -> Dict[str, Any]:
        """Serialize action for storage."""
        if hasattr(action, 'dict'):
            return action.dict()
        elif isinstance(action, dict):
            return action
        else:
            return {"raw": str(action)}
    
    def _is_contained(self, obs) -> bool:
        """Check if all threats are contained based on observation."""
        if isinstance(obs, dict):
            # Check for threat indicators
            detected_attacks = obs.get("detected_attacks", [])
            threat_level = obs.get("threat_level", 0.0)
            return len(detected_attacks) == 0 and threat_level < 0.1
        elif hasattr(obs, 'detected_attacks') and hasattr(obs, 'threat_level'):
            return len(obs.detected_attacks) == 0 and obs.threat_level < 0.1
        return False
    
    def print_stats(self):
        """Print trajectory generation statistics."""
        total = self.stats["total_trajectories"]
        successful = self.stats["successful"]
        failed = self.stats["failed"]
        
        if total > 0:
            self.stats["avg_reward_overall"] = sum(
                t.cumulative_reward for t in self.trajectories
            ) / total
        
        stats_str = f"""
TRAJECTORY GENERATION STATISTICS
=================================
Total Trajectories: {total}
  - Successful: {successful} ({100*successful/max(1,total):.1f}%)
  - Failed: {failed} ({100*failed/max(1,total):.1f}%)

Total Frames: {self.stats['total_frames']}
Average Frames per Trajectory: {self.stats['total_frames']/max(1,total):.1f}
Average Reward (Overall): {self.stats['avg_reward_overall']:.4f}

Difficulty Distribution:
"""
        for d in range(1, 5):
            count = sum(1 for t in self.trajectories if t.difficulty == d)
            if count > 0:
                avg_reward = sum(
                    t.cumulative_reward for t in self.trajectories if t.difficulty == d
                ) / count
                stats_str += f"  - Difficulty {d}: {count} trajectories (avg_reward={avg_reward:.4f})\n"
        
        logger.info(stats_str)


# ============================================================
# GRPO DATASET CONVERTER
# ============================================================

class GRPODatasetConverter:
    """
    Converts trajectories to GRPO training format for TRL.
    
    GRPO Training Inputs:
    - prompt: LLM input (formatted observation)
    - completion: LLM output (formatted action)
    - reward: scalar feedback (0-1)
    """
    
    def __init__(self, tokenizer=None):
        """
        Initialize converter.
        
        Args:
            tokenizer: HuggingFace tokenizer for prompt/completion
        """
        self.tokenizer = tokenizer
    
    def convert_trajectory_to_grpo(self, trajectory: Trajectory) -> List[Dict[str, Any]]:
        """
        Convert single trajectory to GRPO training samples.
        
        Args:
            trajectory: Trajectory object
            
        Returns:
            List of {prompt, completion, reward} dictionaries
        """
        grpo_samples = []
        
        for frame in trajectory.frames:
            obs = frame.observation
            action = frame.action
            reward = frame.reward
            
            # Build prompt from observation
            prompt = self._build_llm_prompt(obs, trajectory.difficulty)
            
            # Format action as completion
            completion = self._format_action_as_completion(action)
            
            grpo_samples.append({
                "prompt": prompt,
                "completion": completion,
                "reward": reward,
                "scenario_id": trajectory.scenario_id,
                "step": frame.step,
                "difficulty": trajectory.difficulty
            })
        
        return grpo_samples
    
    def convert_trajectories_to_grpo(self, trajectories: List[Trajectory]) -> List[Dict[str, Any]]:
        """
        Convert multiple trajectories to GRPO training data.
        
        Args:
            trajectories: List of Trajectory objects
            
        Returns:
            List of GRPO training samples
        """
        grpo_data = []
        
        for trajectory in trajectories:
            samples = self.convert_trajectory_to_grpo(trajectory)
            grpo_data.extend(samples)
        
        logger.info(f"Converted {len(trajectories)} trajectories to {len(grpo_data)} GRPO samples")
        
        return grpo_data
    
    def _build_llm_prompt(self, obs: Dict[str, Any], difficulty: int) -> str:
        """
        Build LLM prompt from observation.
        
        Args:
            obs: Observation dictionary
            difficulty: Current difficulty level
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are the Patronus AI, an autonomous self-healing enterprise agent.

PHASE: {obs.get('current_phase', 'unknown')}
DIFFICULTY: {difficulty}
THREAT_LEVEL: {obs.get('threat_level', 0.0):.2f}
STEP: {obs.get('step_count', 0)} | TIME: {obs.get('sim_time', 0.0):.0f}

=== BOARD DIRECTIVES ===
{chr(10).join(obs.get('directives', [])) if obs.get('directives') else 'None'}

=== RAG CVE INTELLIGENCE ===
{chr(10).join(obs.get('alerts', [])) if obs.get('alerts') else 'No alerts'}

=== NETWORK STATE ===
Visible Nodes: {len(obs.get('visible_nodes', []))} | Health: {obs.get('network_health_summary', {}).get('average_health', 0.0):.1f}
Detected Threats: {len(obs.get('detected_attacks', []))}

=== ORG STATE ===
Departments: {len(obs.get('org_nodes', []))} | Pending Approvals: {len(obs.get('pending_approvals', []))}

TASK: Analyze the situation. Return your reasoning and chosen action.
FORMAT: REASONING: <text> | ACTION: <type> | DETAIL: <action_name> | TARGET: <target_id>"""
        
        return prompt
    
    def _format_action_as_completion(self, action: Dict[str, Any]) -> str:
        """
        Format action as LLM completion.
        
        Args:
            action: Action dictionary
            
        Returns:
            Formatted action string
        """
        reasoning = action.get("reasoning", "Executing standard procedure")
        action_type = action.get("action_type", "DIAGNOSTIC")
        detail = action.get("tactical_action") or action.get("strategic_action") or action.get("diagnostic_action") or "QUERY_BELIEF_MAP"
        target = action.get("target", "system")
        
        completion = f"REASONING: {reasoning} | ACTION: {action_type} | DETAIL: {detail} | TARGET: {target}"
        
        return completion
    
    def save_grpo_data(
        self,
        grpo_data: List[Dict[str, Any]],
        filename: str,
        output_dir: str = "training/grpo_data",
        compress: bool = True
    ) -> str:
        """
        Save GRPO training data to file.
        
        Args:
            grpo_data: List of GRPO training samples
            filename: Output filename
            output_dir: Output directory
            compress: Compress with gzip
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        output_file = output_path / filename
        
        if compress and filename.endswith('.json'):
            output_file = output_file.with_suffix('.json.gz')
            with gzip.open(str(output_file), 'wt', encoding='utf-8') as f:
                json.dump(grpo_data, f, indent=2)
            logger.info(f"Saved {len(grpo_data)} GRPO samples to {output_file} (compressed)")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(grpo_data, f, indent=2)
            logger.info(f"Saved {len(grpo_data)} GRPO samples to {output_file}")
        
        return str(output_file)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def load_scenarios(filepath: str) -> List[Dict[str, Any]]:
    """
    Load scenarios from JSON file (handles gzip).
    
    Args:
        filepath: Path to scenarios file
        
    Returns:
        List of scenario dictionaries
    """
    if filepath.endswith('.gz'):
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


def load_trajectories(filepath: str) -> List[Trajectory]:
    """
    Load trajectories from JSON file (handles gzip).
    
    Args:
        filepath: Path to trajectories file
        
    Returns:
        List of Trajectory objects
    """
    if filepath.endswith('.gz'):
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    trajectories = []
    for traj_dict in data:
        traj = Trajectory(
            scenario_id=traj_dict["scenario_id"],
            dataset_type=traj_dict["dataset_type"],
            difficulty=traj_dict["difficulty"],
            seed=traj_dict["seed"],
            cumulative_reward=traj_dict["cumulative_reward"],
            num_frames=traj_dict["num_frames"],
            avg_reward=traj_dict["avg_reward"],
            max_steps=traj_dict["max_steps"],
            time_to_containment=traj_dict.get("time_to_containment"),
            status=traj_dict.get("status", "unknown")
        )
        # Note: frames not loaded for memory efficiency
        trajectories.append(traj)
    
    return trajectories
