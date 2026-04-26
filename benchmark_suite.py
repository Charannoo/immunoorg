"""
Comparative Benchmarking Suite
===============================
Runs Random, Heuristic, and LLM agents across 100 episodes each
and compares performance across difficulty levels.
"""

from __future__ import annotations
import json
import time
from collections import defaultdict
from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.agents.llm_agent import ImmunoDefenderAgent
from immunoorg.agents.baseline_agents import RandomAgent, HeuristicAgent


class BenchmarkSuite:
    def __init__(self, num_episodes: int = 100, max_episode_steps: int = 200):
        self.num_episodes = num_episodes
        self.max_episode_steps = max_episode_steps
        self.results = defaultdict(list)

    
    def run_benchmark(self, model_path: str | None = None) -> dict:
        """Run benchmark across all agents and difficulty levels."""
        agents = {
            "random": RandomAgent,
            "heuristic": HeuristicAgent,
            "llm": (lambda seed: ImmunoDefenderAgent(seed=seed, model_path=model_path)),
        }
        
        difficulties = [1, 2]  # Keep it fast: levels 1-2 only
        
        print("Starting Comparative Benchmark...")
        print(f"Episodes per config: {self.num_episodes}")
        print(f"Agents: {list(agents.keys())}")
        print(f"Difficulties: {difficulties}\n")
        
        for difficulty in difficulties:
            print(f"\n=== Difficulty Level {difficulty} ===")
            for agent_name, agent_init in agents.items():
                print(f"  {agent_name.upper()}...", end="", flush=True)
                self.run_agent_episodes(agent_name, agent_init, difficulty)
                print(" DONE")
        
        return self._aggregate_results()
    
    def run_agent_episodes(self, agent_name: str, agent_init, difficulty: int):
        """Run n episodes for a given agent at a given difficulty."""
        for ep in range(self.num_episodes):
            env = ImmunoOrgEnvironment(difficulty=difficulty, seed=ep)
            agent = agent_init(seed=ep)
            
            obs = env.reset()
            terminated = False
            steps = 0

            while not terminated and steps < self.max_episode_steps:
                action = agent.act(obs)
                obs, reward, terminated = env.step(action)
                steps += 1
            
            # Collect metrics
            metrics = {
                "reward": env.state.cumulative_reward,
                "steps_to_termination": steps,
                "final_threat_level": env.state.threat_level,
                "total_downtime": env.state.total_downtime,
                "belief_accuracy": env.belief_map.calculate_belief_accuracy() if env.belief_map else 0.0,
                "org_chaos_score": env.state.org_chaos_score,
                "attacks_contained": len(env.state.contained_attacks),
                "attacks_active": len(env.state.active_attacks),
            }
            self.results[f"d{difficulty}_{agent_name}"].append(metrics)
    
    def _aggregate_results(self) -> dict:
        """Aggregate and compute statistics."""
        aggregated = {}
        for key, metrics_list in self.results.items():
            if not metrics_list:
                continue
            
            # Compute stats
            stats = {
                "count": len(metrics_list),
                "avg_reward": sum(m["reward"] for m in metrics_list) / len(metrics_list),
                "max_reward": max(m["reward"] for m in metrics_list),
                "min_reward": min(m["reward"] for m in metrics_list),
                "avg_steps": sum(m["steps_to_termination"] for m in metrics_list) / len(metrics_list),
                "avg_downtime": sum(m["total_downtime"] for m in metrics_list) / len(metrics_list),
                "avg_belief_accuracy": sum(m["belief_accuracy"] for m in metrics_list) / len(metrics_list),
                "avg_contained": sum(m["attacks_contained"] for m in metrics_list) / len(metrics_list),
                "win_rate": sum(1 for m in metrics_list if m["attacks_active"] == 0) / len(metrics_list),
            }
            aggregated[key] = stats
        
        return aggregated
    
    def save_results(self, filename: str = "benchmark_results.json"):
        """Save results to JSON."""
        aggregated = self._aggregate_results()
        with open(filename, "w") as f:
            json.dump(aggregated, f, indent=2)
        print(f"\nResults saved to {filename}")
    
    def print_summary(self):
        """Print a human-readable summary."""
        aggregated = self._aggregate_results()
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 80)
        
        for difficulty in [1, 2]:
            print(f"\nDifficulty Level {difficulty}:")
            print("-" * 80)
            for agent_name in ["random", "heuristic", "llm"]:
                key = f"d{difficulty}_{agent_name}"
                if key not in aggregated:
                    continue
                
                stats = aggregated[key]
                print(f"\n  {agent_name.upper()}")
                print(f"    Episodes: {stats['count']}")
                print(f"    Avg Reward: {stats['avg_reward']:+.2f} (range: {stats['min_reward']:+.2f} to {stats['max_reward']:+.2f})")
                print(f"    Avg Steps: {stats['avg_steps']:.1f}")
                print(f"    Win Rate: {stats['win_rate']:.0%}")
                print(f"    Avg Belief Accuracy: {stats['avg_belief_accuracy']:.1%}")
                print(f"    Avg Attacks Contained: {stats['avg_contained']:.1f}")
                print(f"    Avg Downtime: {stats['avg_downtime']:.1f}")


if __name__ == "__main__":
    import argparse
    import sys

    argv = sys.argv[1:]
    # Legacy: python benchmark_suite.py 12 [model_path]
    if argv and argv[0].isdigit():
        argv = ["-n", argv[0]] + argv[1:]

    parser = argparse.ArgumentParser(description="Benchmark random / heuristic / LLM agents")
    parser.add_argument("-n", "--episodes", type=int, default=100, help="Episodes per agent per difficulty")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=200,
        help="Max env steps per episode (lower = faster smoke)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fast smoke: 5 episodes, 55-step cap (~15–25s on a laptop)",
    )
    parser.add_argument("model_path", nargs="?", default=None)
    args = parser.parse_args(argv)
    if args.quick:
        args.episodes = 5
        args.max_steps = 55

    suite = BenchmarkSuite(num_episodes=args.episodes, max_episode_steps=args.max_steps)
    start = time.time()
    suite.run_benchmark(model_path=args.model_path)
    elapsed = time.time() - start
    
    suite.print_summary()
    suite.save_results()
    
    print(f"\nBenchmark completed in {elapsed:.1f}s")
