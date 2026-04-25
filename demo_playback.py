"""
Demo Playback Script
====================
Loads and plays back the best recorded episodes.
"""

from episode_recorder import EpisodePlayer, record_best_episodes
from immunoorg.agents.baseline_agents import HeuristicAgent
from immunoorg.agents.llm_agent import ImmunoDefenderAgent
import glob


def list_recorded_episodes():
    """List all recorded episodes."""
    episodes = glob.glob("episode_recordings/**/*.json.gz", recursive=True)
    return sorted(episodes, reverse=True)


def play_best_episode():
    """Play the best recorded episode."""
    episodes = list_recorded_episodes()
    if not episodes:
        print("No recorded episodes found. Recording best Heuristic episodes...")
        record_best_episodes(HeuristicAgent, num_episodes=10, difficulty=2)
        episodes = list_recorded_episodes()
    
    if episodes:
        best_file = episodes[0]
        print(f"Playing best episode: {best_file}\n")
        player = EpisodePlayer(best_file)
        print(f"Metadata: {player.metadata}\n")
        print("Episode Playback:")
        
        def display_frame(frame):
            action_dict = frame.action
            action_type = action_dict.get("action_type", "unknown")
            reasoning = action_dict.get("reasoning", "")
            print(f"Step {frame.step:3d}: {action_type:10s} | Reward: {frame.reward:+.3f} | {reasoning[:50]}")
            if frame.terminated:
                print("           --> EPISODE TERMINATED")
        
        player.play(callback=display_frame)
        print(f"\nTotal Episode Reward: {player.get_total_reward():+.2f}")


if __name__ == "__main__":
    play_best_episode()
