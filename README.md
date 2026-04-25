# ImmunoOrg 2.0 — The Autonomous, Self-Healing Enterprise
### AI DevSecOps Mesh | Multi-Agent War Room | Polymorphic Migration | Executive Context Engine

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-brightgreen)](https://openenv.ai)
[![Version](https://img.shields.io/badge/version-2.0.0-blue)](./openenv.yaml)
[![Themes](https://img.shields.io/badge/themes-4%2F4-purple)](./openenv.yaml)
[![Bonus Prizes](https://img.shields.io/badge/bonus%20prizes-6%2F6-gold)](./openenv.yaml)

> **OpenEnv Hackathon** April 26, 2026
> Bonus: Halluminate | Fleet AI | Mercor | Scale AI | Patronus AI | Snorkel AI

---

## Quick Links

| Resource | Link |
|---|---|
| **HuggingFace Space** | https://huggingface.co/spaces/YOUR_HF_USERNAME/immunoorg-2 |
| **Training Colab** | [ImmunoOrg_Training_Colab.ipynb](./ImmunoOrg_Training_Colab.ipynb) |
| **Blog Post** | [BLOG_POST.md](./BLOG_POST.md) |
| **Submission Checklist** | [SUBMISSION_CHECKLIST.md](./SUBMISSION_CHECKLIST.md) |

---

## What is ImmunoOrg 2.0?

ImmunoOrg 2.0 is a next-generation OpenEnv RL environment simulating an **entire enterprise** as a living organism under attack. The biggest vulnerability is not a missing patch — it is the **3-day approval delay** while an exploit is actively weaponized.

---

## Feature Matrix

| Module | Theme | Bonus Prize | File |
|---|---|---|---|
| Multi-Agent War Room | Multi-Agent | Halluminate + Snorkel AI | `immunoorg/war_room.py` |
| AI DevSecOps Mesh (4 Gates) | World Modeling | Fleet AI | `immunoorg/devsecops_mesh.py` |
| 50-Step Polymorphic Migration | Long-Horizon Planning | Scale AI | `immunoorg/migration_engine.py` |
| Executive Context + Schema Drift | World Modeling | Patronus AI | `immunoorg/executive_context.py` |
| Time-Travel Forensics + Auto-Patch | Self-Improvement | Mercor | `immunoorg/self_improvement.py` |
| 5-Track Composable Reward | All Themes | -- | `immunoorg/reward.py` |

---

## Results & Evidence

### Policy Comparison

![Policy Comparison](./evidence_policy_comparison.png)

| Agent | Level 1 | Level 2 | Level 3 |
|:---:|:---:|:---:|:---:|
| Random Baseline | -0.89 | -9.9 | -16.6 |
| **Heuristic (Gold)** | **+3.62** | **-2.1** | **-5.8** |

### Self-Healing Loop (6 Generations)

![Self Improvement](./evidence_self_improvement.png)

- Org efficiency: 0.312 -> 0.469 (+50%)
- Time-to-Containment: 48 -> 28 steps (-42%)

### 5-Track Reward & War Room Activity

![5-Track Reward](./evidence_5track_reward.png)

![War Room Mesh](./evidence_war_room_mesh.png)

### Org Before/After Self-Healing

![Org Before After](./evidence_org_before_after.png)

---

## Quickstart

```bash
git clone https://github.com/YOUR_USERNAME/immunoorg
cd immunoorg
pip install -r requirements.txt

python demo_runner.py           # Full policy comparison
python visualization/dashboard.py  # God Mode Dashboard (localhost:7860)
python generate_evidence_2.py  # Regenerate evidence charts
python test_2_0_smoke.py       # Smoke test all 2.0 systems
```

---

## 5-Track Reward Model

| Track | Weight | Signal |
|---|:---:|---|
| Uptime | 25% | SLA adherence during incident |
| Threat Neutralization | 25% | Attacker containment + belief accuracy |
| Bureaucracy Efficiency | 20% | War Room consensus speed |
| Code Quality (Mercor) | 20% | `1/log2(tokens) x test_pass_rate` |
| Pipeline Integrity | 10% | Gate 1 catch = 1.5x shift-left bonus |

---

## Bonus Prize Coverage

| Prize | Implementation |
|---|---|
| **Halluminate** | War Room FactStore cross-validates claims before any action executes |
| **Snorkel AI** | PreferenceInjection API: judges inject HIPAA/UPTIME/LEGAL_HOLD mid-debate |
| **Scale AI** | 50-step migration with constraint propagation across phases |
| **Fleet AI** | FleetAIOversightAgent: atomic lockout across GitHub/Slack/AWS/Jira/MySQL |
| **Patronus AI** | ExecutiveContextEngine: mid-episode API schema drift adaptation |
| **Mercor** | Patch quality = 1/log2(token_count) x test_pass_rate |

---

## Training

Base model: `Qwen/Qwen2.5-7B-Instruct` | Method: GRPO + Unsloth LoRA

```bash
python training/train_grpo.py --max_steps 20  # Quick local test
# Full training: open ImmunoOrg_Training_Colab.ipynb in Colab
```

## License

MIT
