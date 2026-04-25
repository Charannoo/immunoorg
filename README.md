---
title: ImmunoOrg 2.0 - Autonomous Self-Healing Enterprise
emoji: 🛡️
colorFrom: blue
colorTo: purple
sdk: docker
pinned: true
license: mit
short_description: AI DevSecOps + War Room + GRPO-Trained Reasoning Agent
---

# ImmunoOrg 2.0 — The Autonomous, Self-Healing Enterprise
### AI DevSecOps Mesh | Multi-Agent War Room | GRPO-Trained Reasoning Engine | Executive Context Engine

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-brightgreen)](https://openenv.ai)
[![Version](https://img.shields.io/badge/version-2.0.0-blue)](./openenv.yaml)
[![Model](https://img.shields.io/badge/Model-Mistral--Nemo--12B-purple)](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407)
[![Training](https://img.shields.io/badge/Training-GRPO_Optimized-gold)](https://github.com/unslothai/unsloth)

> **OpenEnv Hackathon** April 26, 2026
> **Core Innovation**: Transitioning from heuristic-based defense to a **Reasoning Agent** trained via Group Relative Policy Optimization (GRPO) to navigate corporate bureaucracy and technical threats.

---

## 🚀 The Core Innovation: GRPO Reasoning Agent
Unlike traditional RL agents, ImmunoOrg 2.0 employs a **Reasoning Agent** based on `Mistral-Nemo-12B`, trained using **GRPO (Group Relative Policy Optimization)**. 

The agent is trained not just to "win," but to **reason**. It is rewarded for:
1. **Logical Chain-of-Thought**: Providing a detailed "why" before every action.
2. **Phase-Awareness**: Selecting actions that match the current incident phase (Detection $\rightarrow$ Containment $\rightarrow$ RCA $\rightarrow$ Refactor).
3. **Bureaucracy Navigation**: Optimizing for the fastest consensus in the Multi-Agent War Room.

---

## 🏛️ System Architecture

### 1. The Defender (Trained Agent)
The brain of the system. It observes network telemetry and organizational graphs, producing structured JSON actions. It manages the entire lifecycle of an incident.

### 2. Multi-Agent War Room
A simulation of executive conflict. Three personas (**CISO, DevOps Lead, Lead Architect**) debate critical actions.
- **Halluminate Layer**: Cross-validates claims against a ground-truth `FactStore` to prevent AI hallucinations during crises.
- **Snorkel AI Integration**: Allows external "Board Directives" to inject priority overrides (e.g., HIPAA compliance) mid-debate.

### 3. AI DevSecOps Mesh
A world-modeling engine that maps technical vulnerabilities to organizational silos. It tracks how "siloed" departments slow down response times, creating a tangible link between **company structure** and **cyber security**.

---

## 📊 Results & Evidence

### Policy Comparison (Base vs. GRPO-Trained)
| Agent | Level 1 | Level 2 | Level 3 | Reasoning Quality |
|:---:|:---:|:---:|:---:|:---:|
| Random Baseline | -0.89 | -9.9 | -16.6 | N/A |
| Base Mistral-Nemo | +1.12 | -4.5 | -11.2 | Low |
| **GRPO-Trained Agent** | **+5.45** | **+1.2** | **-2.1** | **High** |

### Evidence Charts
![Policy Comparison](https://raw.githubusercontent.com/Charannoo/immunoorg/master/evidence_policy_comparison.png)
![Self Improvement](https://raw.githubusercontent.com/Charannoo/immunoorg/master/evidence_self_improvement.png)
![War Room Mesh](https://raw.githubusercontent.com/Charannoo/immunoorg/master/evidence_war_room_mesh.png)

---

## 🛠️ Quickstart

```bash
git clone https://github.com/Charannoo/immunoorg
cd immunoorg
pip install -r requirements.txt

python visualization/dashboard.py  # Launch the God Mode Dashboard
```

## 🏆 Bonus Prize Coverage
| Prize | Implementation |
|---|---|
| **Halluminate** | War Room `FactStore` cross-validates claims in real-time |
| **Snorkel AI** | `PreferenceInjection` API for mid-debate board directives |
| **Scale AI** | 50-step Polymorphic Migration with long-horizon planning |
| **Fleet AI** | FleetAIOversightAgent for atomic cross-platform lockouts |
| **Patronus AI** | ExecutiveContextEngine for mid-episode schema drift adaptation |
| **Mercor** | Patch quality scoring based on token efficiency and test pass rates |

---
## License
MIT
