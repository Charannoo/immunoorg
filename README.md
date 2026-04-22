# 🛡️ ImmunoOrg: The Self-Healing Autonomous Enterprise

> **"The biggest security hole isn't a missing patch; it's a manager who takes 3 days to approve a firewall change."**

ImmunoOrg is a cutting-edge dual-layer Reinforcement Learning (RL) training environment designed to simulate the intersection of cybersecurity technical failures and organizational bureaucracy. It trains AI agents to not only neutralize threats but to **restructure the organization itself** to remove the silos that enable attacks.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 The Core Innovation: Socio-Technical Coupling

Traditional security simulators model networks. **ImmunoOrg models the *Enterprise*.**

We recognize that in real-world organizations, technical actions (like blocking a port) are gated by approval flows. If the Security and Engineering departments are siloed, the response is slow, and the attacker wins. 

### 📐 The Dual-Layer Architecture
- **Technical Layer (Network Graph):** Simulates servers, APIs, and cascading failures.
- **Organizational Layer (Socio-Graph):** Simulates departments, communication channels, and bureaucracy.
- **The Linkage (Permission Flow):** A dynamic engine that maps technical actions to organizational approval paths.

---

## 🏆 Hackathon Theme Alignment

ImmunoOrg is designed to push the boundaries of LLM agency across four critical themes:

| Theme | Implementation | Capability Tested |
| :--- | :--- | :--- |
| **Multi-Agent** | Defender vs Adversary vs Dept Agents | Theory-of-Mind & Strategic Negotiation |
| **Long-Horizon** | 5-Phase Cycle: Detection $\rightarrow$ Containment $\rightarrow$ RCA $\rightarrow$ Refactor $\rightarrow$ Validation | Deep Reasoning & State Tracking |
| **World Modeling** | Belief Map correlating tech failures to org flaws | Causal Reasoning & Internal Belief Updates |
| **Self-Improvement** | Recursive loop: contain $\rightarrow$ mutate org $\rightarrow$ harder attack $\rightarrow$ repeat | Recursive Skill Amplification |

---

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Running the Environment
```bash
# Start the OpenEnv server (FastAPI)
uvicorn server.main:app --port 7860

# Run the Comparative Demo (Random vs Base vs Trained)
python demo_runner.py --model-path ./immunoorg-defender
```

### Training the Agent (GPU Required)
```bash
# SFT Warm-start + GRPO Training
python training/train_grpo.py --warm-start --model Qwen/Qwen2.5-7B-Instruct
```

---

## 🎮 Action Space & Reward Logic

### 🛠️ Action Categories
- **Tactical:** `block_port`, `isolate_node`, `deploy_patch`, etc.
- **Strategic:** `merge_departments`, `establish_devsecops`, `reduce_bureaucracy`, etc.
- **Diagnostic:** `correlate_failure`, `identify_silo`, `measure_org_latency`, etc.

### 📊 Multi-Objective Reward Function
$$R = \alpha \cdot \text{ThreatNeutralized} - \beta \cdot \text{SystemDowntime} - \gamma \cdot \text{OrgChaos} + \delta \cdot \text{BeliefAccuracy} + \epsilon \cdot \text{ReasoningQuality}$$

We penalize **Organizational Chaos** and **Downtime** to ensure the agent doesn't simply "destroy the company" to stop the attack.

---

## 🎓 4-Tier Curriculum

| Level | Name | Attack Pattern | Org Challenge |
| :--- | :--- | :--- | :--- |
| 1 | **Novice** | Single-point attack | Simple identification |
| 2 | **Intermediate** | Lateral movement | Timeline reconstruction |
| 3 | **Advanced** | Cascading breach | Silo identification + Org refactor |
| 4 | **Elite** | APT Campaign | Total restructure + Equilibrium |

---

## 📁 Project Structure
- `immunoorg/`: Core simulation logic (Network, Org, Rewards, Agents).
- `server/`: FastAPI wrapper for OpenEnv compatibility.
- `training/`: GRPO and SFT training pipelines.
- `visualization/`: Real-time monitoring dashboard.
- `schemas/`: Environment world-state definitions.

## 📜 License
MIT License — Built for the OpenEnv Hackathon.
