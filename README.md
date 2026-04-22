# 🛡️ ImmunoOrg: The Self-Healing Autonomous Enterprise

> A dual-layer RL training environment where AI agents learn to detect cyber-attacks and reorganize company structure to prevent future vulnerabilities — creating a self-healing enterprise immune system.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🎯 What Makes This Unique

ImmunoOrg is the **first RL environment that couples cybersecurity simulation with organizational dynamics**. Unlike traditional security environments that only model networks, ImmunoOrg recognizes that **incident response speed is gated by organizational bureaucracy** — and trains agents to fix both.

### The Two Layers

| Layer | What It Models | Key Challenge |
|-------|---------------|---------------|
| **Technical (Network Graph)** | Servers, APIs, ports, cascading failures | Detect & contain cyber-attacks |
| **Organizational (Socio-Graph)** | Departments, communication channels, bureaucracy | Navigate approval chains, eliminate silos |

### The Linkage
Every tactical action (block a port, isolate a server) requires **approval flowing through the organizational graph**. If Security and Engineering are siloed (no communication channel), the approval path is longer → response is slower → more damage.

## 🏆 Hackathon Theme Coverage

| Theme | Implementation | Status |
|-------|---------------|--------|
| **Multi-Agent** | Defender vs Adversary vs 8 Department Agents with conflicting KPIs | ✅ |
| **Long-Horizon Planning** | Detection → Containment → RCA → Org-Refactor → Validation | ✅ |
| **World Modeling** | Belief Map correlating technical failures to org flaws | ✅ |
| **Self-Improvement** | Recursive loop: contain → mutate org → harder attack → repeat | ✅ |

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the test suite
python tests/test_environment.py

# Start the OpenEnv server
uvicorn server.main:app --port 7860

# Run inference demo
python inference.py level1_single_attack 1

# Launch the interactive dashboard
python visualization/dashboard.py
```

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ImmunoOrg Environment                 │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │  Technical Layer  │  │   Organizational Layer       │ │
│  │  ┌────┐ ┌────┐   │  │  ┌─────┐  ┌────┐  ┌─────┐  │ │
│  │  │ DB │→│ API│   │  │  │ IT  │──│Sec │──│ Eng │  │ │
│  │  └────┘ └────┘   │  │  └─────┘  └────┘  └─────┘  │ │
│  │  ┌────┐ ┌────┐   │←→│  ┌─────┐  ┌────┐  ┌─────┐  │ │
│  │  │ Web│→│ FW │   │  │  │Mgmt │──│Legal│──│ HR  │  │ │
│  │  └────┘ └────┘   │  │  └─────┘  └────┘  └─────┘  │ │
│  └──────────────────┘  └──────────────────────────────┘ │
│            ↑ Permission Flow Engine (linkage) ↑         │
│  ┌──────────────────────────────────────────────────────┐│
│  │ Defender Agent ←→ Adversary Agent ←→ Dept Agents    ││
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## 🎮 Action Space

### Tactical Actions (Network Layer)
`block_port` · `isolate_node` · `scan_logs` · `deploy_patch` · `quarantine_traffic` · `escalate_alert` · `restore_backup` · `rotate_credentials` · `enable_ids` · `snapshot_forensics`

### Strategic Actions (Org Layer)  
`merge_departments` · `create_shortcut_edge` · `update_approval_protocol` · `split_department` · `reassign_authority` · `add_cross_functional_team` · `reduce_bureaucracy` · `create_incident_channel` · `rewrite_policy` · `establish_devsecops`

### Diagnostic Actions (World Model)
`query_belief_map` · `correlate_failure` · `trace_attack_path` · `audit_permissions` · `measure_org_latency` · `identify_silo` · `timeline_reconstruct` · `vulnerability_scan`

## 📊 Reward Function

```
R = α·ThreatNeutralized − β·SystemDowntime − γ·OrgChaos + δ·BeliefAccuracy + ε·ReasoningQuality
```

| Coefficient | Level 1 | Level 2 | Level 3 | Level 4 |
|-------------|---------|---------|---------|---------|
| α (Threat)  | 1.0     | 1.0     | 1.0     | 1.0     |
| β (Downtime)| 0.3     | 0.5     | 0.7     | 1.0     |
| γ (Chaos)   | 0.1     | 0.2     | 0.5     | 0.8     |
| δ (Belief)  | 0.2     | 0.4     | 0.6     | 0.8     |
| ε (Reason)  | 0.1     | 0.2     | 0.3     | 0.5     |

## 🎓 4-Tier Curriculum

| Level | Name | Attack Pattern | Org Challenge |
|-------|------|---------------|---------------|
| 1 | Novice | Single-point attack | Simple identification |
| 2 | Intermediate | Lateral movement | Timeline reconstruction |
| 3 | Advanced | Cascading breach | Silo identification + Org refactor |
| 4 | Elite | APT Campaign | Total restructure + Equilibrium |

## 🏋️ Training with GRPO

```bash
# Smoke test (CPU, 2 steps)
python training/train_grpo.py --smoke-test

# Full training (GPU required)
python training/train_grpo.py --model Qwen/Qwen2.5-7B-Instruct --epochs 3

# Extract golden trajectories for SFT warm-start
python training/golden_trajectories.py
```

## 🐳 Docker Deployment

```bash
docker build -t immunoorg .
docker run -p 7860:7860 immunoorg
```

## 📁 Project Structure

```
immunoorg/
├── models.py              # Pydantic data models (State/Action/Observation)
├── environment.py         # Core OpenEnv Environment
├── network_graph.py       # Technical layer simulation
├── org_graph.py           # Organizational layer simulation
├── permission_flow.py     # Bureaucracy/approval routing
├── attack_engine.py       # Reactive adversary
├── belief_map.py          # World model (tech↔org correlation)
├── curriculum.py          # 4-tier difficulty
├── reward.py              # Multi-objective reward
├── self_improvement.py    # Recursive improvement loop
└── agents/
    ├── defender.py        # LLM-driven defender
    ├── adversary.py       # Adversary persona
    └── department.py      # Siloed department agents
```

## 📜 License

MIT License — built for the OpenEnv Hackathon.
