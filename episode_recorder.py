"""
Episode Recording & Playback System
====================================
Records and replays episodes for deterministic demos and analysis.
"""

from __future__ import annotations
import json
import gzip
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import ImmunoAction, ImmunoObservation, ActionType


@dataclass
class EpisodeFrame:
    """A single frame in an episode (observation + action + reward)."""
    step: int
    observation: dict
    action: dict
    reward: float
    terminated: bool
    
    def to_dict(self):
        return asdict(self)


@dataclass
class EpisodeMetadata:
    """Metadata about an episode."""
    episode_id: str
    agent_name: str
    difficulty: int
    seed: int
    total_reward: float
    num_steps: int
    final_phase: str
    termination_reason: str
    
    def to_dict(self):
        return asdict(self)


class EpisodeRecorder:
    """Records an episode to a file for later playback."""
    
    def __init__(self, episode_id: str, agent_name: str, difficulty: int, seed: int):
        self.episode_id = episode_id
        self.agent_name = agent_name
        self.difficulty = difficulty
        self.seed = seed
        self.frames: list[EpisodeFrame] = []
    
    def record_frame(self, step: int, obs: ImmunoObservation, action: ImmunoAction, reward: float, terminated: bool):
        """Record a single frame."""
        obs_dict = obs.model_dump(mode='json')
        action_dict = action.model_dump(mode='json')
        
        frame = EpisodeFrame(
            step=step,
            observation=obs_dict,
            action=action_dict,
            reward=reward,
            terminated=terminated
        )
        self.frames.append(frame)
    
    def save(self, directory: str = "episode_recordings", compress: bool = True):
        """Save the episode to a file."""
        Path(directory).mkdir(exist_ok=True)
        
        filename = f"{directory}/{self.episode_id}_{self.agent_name}_d{self.difficulty}.json"
        
        data = {
            "metadata": {
                "episode_id": self.episode_id,
                "agent_name": self.agent_name,
                "difficulty": self.difficulty,
                "seed": self.seed,
                "num_frames": len(self.frames),
            },
            "frames": [f.to_dict() for f in self.frames],
        }
        
        if compress:
            filename += ".gz"
            with gzip.open(filename, 'wt') as f:
                json.dump(data, f, indent=2)
        else:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        
        print(f"Episode saved: {filename}")
        return filename


class EpisodePlayer:
    """Plays back a recorded episode."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.data = self._load(filename)
        self.metadata = self.data["metadata"]
        self.frames = self.data["frames"]
    
    def _load(self, filename: str) -> dict:
        """Load episode data from file."""
        if filename.endswith('.gz'):
            with gzip.open(filename, 'rt') as f:
                return json.load(f)
        else:
            with open(filename, 'r') as f:
                return json.load(f)
    
    def play(self, callback=None):
        """Play back the episode frame by frame."""
        print(f"Playing back episode: {self.metadata['episode_id']}")
        print(f"  Agent: {self.metadata['agent_name']}")
        print(f"  Difficulty: {self.metadata['difficulty']}")
        print(f"  Frames: {len(self.frames)}\n")
        
        for frame_data in self.frames:
            frame = EpisodeFrame(**frame_data)
            if callback:
                callback(frame)
            else:
                self._default_display(frame)
    
    def _default_display(self, frame: EpisodeFrame):
        """Default display of a frame."""
        action_dict = frame.action
        action_type = action_dict.get("action_type", "unknown")
        print(f"Step {frame.step}: {action_type} (reward={frame.reward:+.3f})")
        if frame.terminated:
            print("  -> EPISODE TERMINATED")
    
    def get_total_reward(self) -> float:
        """Compute total reward for the episode."""
        return sum(f.reward for f in self.frames)


def record_best_episodes(agent_class, num_episodes: int = 10, difficulty: int = 2, 
                         output_dir: str = "episode_recordings/best"):
    """Run episodes and record the top performers."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    recorded_episodes = []
    
    print(f"Recording {num_episodes} episodes to find best performers...")
    
    for ep_idx in range(num_episodes):
        env = ImmunoOrgEnvironment(difficulty=difficulty, seed=ep_idx)
        agent = agent_class(seed=ep_idx)
        
        recorder = EpisodeRecorder(
            episode_id=f"ep-{ep_idx:04d}",
            agent_name=agent_class.__name__,
            difficulty=difficulty,
            seed=ep_idx
        )
        
        obs = env.reset()
        terminated = False
        steps = 0
        max_steps = 200
        
        while not terminated and steps < max_steps:
            action = agent.act(obs)
            obs, reward, terminated = env.step(action)
            recorder.record_frame(steps, obs, action, reward, terminated)
            steps += 1
        
        total_reward = env.state.cumulative_reward
        recorded_episodes.append((ep_idx, total_reward, recorder))
        
        print(f"  Episode {ep_idx}: reward={total_reward:+.2f}")
    
    # Sort by reward and save top 3
    recorded_episodes.sort(key=lambda x: x[1], reverse=True)
    
    print("\nSaving top 3 episodes...")
    for rank, (ep_idx, total_reward, recorder) in enumerate(recorded_episodes[:3]):
        output_subdir = f"{output_dir}/rank{rank+1}"
        Path(output_subdir).mkdir(parents=True, exist_ok=True)
        recorder.save(output_subdir)
        print(f"  Rank {rank+1}: Episode {ep_idx} (reward={total_reward:+.2f})")
    
    return recorded_episodes[:3]


if __name__ == "__main__":
    from immunoorg.agents.baseline_agents import HeuristicAgent
    
    # Example: Record best Heuristic agent episodes
    best_episodes = record_best_episodes(HeuristicAgent, num_episodes=10, difficulty=2)
    
    # Example: Playback one of the best episodes
    if best_episodes:
        top_file = "episode_recordings/best/rank1/ep-0000_HeuristicAgent_d2.json.gz"
        try:
            player = EpisodePlayer(top_file)
            print(f"\nTotal Reward: {player.get_total_reward():+.2f}")
        except FileNotFoundError:
            print(f"File not found: {top_file}")
