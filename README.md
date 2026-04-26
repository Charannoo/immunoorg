---
title: ImmunoOrg 2.0
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# ImmunoOrg 2.0 — The Autonomous, Self-Healing Enterprise

> An OpenEnv RL environment where an LLM defender learns to contain
> cyber-attacks **and** restructure the organization that lets them
> succeed. Built for the OpenEnv Hackathon (India 2026).

| Resource | Link |
| --- | --- |
| **Hugging Face Space (live env)** | https://huggingface.co/spaces/hirann/immunoorg-v3 |
| **OpenEnv environment endpoint** | `https://hirann-immunoorg-v3.hf.space` |
| **GitHub source** | https://github.com/Charannoo/immunoorg |
| **Training notebook (Colab)** | [`ImmunoOrg_Training_Colab.ipynb`](./ImmunoOrg_Training_Colab.ipynb) |
| **Mini blog post** | [`BLOG_POST.md`](./BLOG_POST.md) |
| **Judges' walkthrough** | [`JUDGING_GUIDE.md`](./JUDGING_GUIDE.md) |
| **Architecture / research notes** | [`RESEARCH.md`](./RESEARCH.md) |

---

## 1. The problem it trains for

Real enterprise incidents are not lost because the security team picks
the wrong tool — they're lost because:

- **The wrong tool is already running** (an AI coding assistant just
  shipped a typosquatted dependency to prod).
- **The right action is forbidden by the org** (the CISO is on a flight
  while ransomware spreads).
- **The right intel is two systems away** (the CVE feed is in one tool,
  the runtime alert in another, the Slack #incident channel in a third).
- **The fix that worked yesterday triggers the SLA breach today** (the
  attacker has already pivoted to a different vector).

ImmunoOrg models all four failure modes in a single `reset()/step()`
loop. The agent has to handle technical *and* organizational decay,
under conflicting executive directives, against an adversary that
adapts to its policy.

That maps directly onto **all four hackathon themes**:

| Theme | How ImmunoOrg covers it |
| --- | --- |
| **Multi-Agent Interactions** | War Room: 3 personas (CISO / DevOps / Architect) negotiate a 2-of-3 consensus on every high-severity action. Hallucinations are flagged via a shared `FactStore`. |
| **(Super) Long-Horizon Planning** | The Polymorphic Migration engine is a **50-step** workflow with constraints set in step 4 that must still hold in step 33. |
| **World Modeling — Professional** | DevSecOps Mesh (4 gates) + mock REST/GraphQL APIs + MITRE ATT&CK TTP graph: the agent's beliefs about CVEs, network state, and IAM policy must stay consistent with the simulated world. |
| **World Modeling — Personal** | Executive Context Engine simulates schema drift across calendar / email / travel APIs while the security incident is in progress. |
| **Self-Improvement** | After every contained incident, Time-Travel Forensics regenerates the kill chain, drafts a minimal patch, and adds it back into the GRPO training mix (Mercor-style inverse-token reward). |

---

## 2. The 5 training scenarios (judge-tier)

`training/dataset_generator.py::generate_elite_scenario_mix_dataset` produces
an **even 20% / 20% / 20% / 20% / 20% mix** of the five judge-facing
scenario families. Each one is implemented end-to-end via
`training/scenario_hooks.py`:

| # | Family | What the agent must learn | Hook flag |
| --- | --- | --- | --- |
| 1 | **Basic Containment** | Use the right tactical action at the right phase. | *(none — baseline)* |
| 2 | **RAG-Grounding** | Read the CVE alert and pick the precise mitigation chain (`SNAPSHOT_FORENSICS → DEPLOY_PATCH`) instead of a blunt `ISOLATE_NODE`. | `inject_rag_best_mitigation`, `best_mitigation_chain` |
| 3 | **Executive Alignment (HITL)** | Override its own security instinct when the Board says "100% uptime, no isolation". | `board_uptime_no_isolate` |
| 4 | **Silo-Breaker** | Stop retrying `ISOLATE_NODE` when IT-Ops keeps denying it; pivot to `MERGE_DEPARTMENTS` / `REDUCE_BUREAUCRACY`. | `force_denials_on_isolate` |
| 5 | **Stealth & Adaptive Defense** | Plan a multi-step investigation against a high-stealth attack and avoid overfitting when the adversary adapts mid-episode. | `stealthy_initial_attack`, `suppress_initial_logs`, `boost_adversary_adaptation` |

The curriculum runs them in this order so the model never gets a zero
reward early:

```
Phase 1 (Basic Competence)  →  Phase 2 (Intelligence / RAG)  →
Phase 3 (Alignment / HITL)  →  Phase 4 (Strategy / Org)     →
Phase 5 (Robustness / Co-Evolution)
```

---

## 3. Evidence (committed PNGs — judges scan these in seconds)

All five charts below are produced by `python generate_evidence.py` and
committed to the repo so reviewers can see them without running the code.

![Random vs Heuristic policies across difficulty levels 1–4](./evidence_policy_comparison.png)
*Policy comparison across all 4 difficulty levels — Heuristic policy
(gold standard for reward shaping) beats Random by 4–11 points,
proving the environment is learnable and reward shaping has signal.*

![Self-improvement across 6 generations of org mutation](./evidence_self_improvement.png)
*Self-improvement loop, 6 generations: reward-per-step trends up,
time-to-containment trends down, and org efficiency rises as the
SelfImprovementEngine accumulates mutations across generations.*

![5-track composable reward breakdown](./evidence_5track_reward.png)
*Per-step contribution of the 5 reward tracks (uptime, threat
neutralisation, bureaucracy efficiency, code quality, pipeline
integrity). No single track dominates — that's the anti-reward-hacking
property judges call out in section #7 of the brief.*

![War Room debate + DevSecOps Mesh activity](./evidence_war_room_mesh.png)
*Multi-agent War Room consensus dynamics + 4-gate DevSecOps Mesh
event counts (AST / Semantic / Terraform / MicroVM).*

![Org graph: siloed 3-day approval vs DevSecOps-bridged 4-hour approval](./evidence_org_before_after.png)
*The "self-healed enterprise" moment: before-and-after of the org
graph after the agent restructures it via `ESTABLISH_DEVSECOPS` +
`REDUCE_BUREAUCRACY`. Approval latency drops from 72h to 4h.*

![Per-scenario reward lift Random vs Heuristic](./evidence_scenario_rewards.png)
*Per-scenario family reward (10 episodes each, real env rollouts).
The heuristic policy beats the random baseline in **every** scenario
family — that lift is the signal the GRPO trainer climbs. Generated
by `python scripts/generate_training_evidence.py` (no GPU required).*

> A real GRPO loss + reward curve (`evidence_grpo_training.png`) is
> produced by the last cell of `ImmunoOrg_Training_Colab.ipynb`. Run
> the notebook on a Colab T4 to generate it; commit the resulting
> PNG to the repo for the final submission. Local CPU smoke runs are
> supported via `python -m training.train_grpo --smoke-test
> --batch-size 2 --num-generations 2` but each step takes ~10 minutes
> on a laptop, so use Colab for anything beyond a 2-step sanity check.

---

## 4. The 5-track composable reward

`immunoorg/reward.py` returns a per-step weighted sum across five
verifiable tracks, plus a shift-left multiplier when Gate 1 of the
DevSecOps mesh catches a threat:

| Track | Weight | What it measures |
| --- | ---: | --- |
| Uptime | 25% | Penalises downtime, dropped sessions, slow APIs, false-positive isolations |
| Threat Neutralization | 25% | Rewards contained attacks, blast-radius reduction, belief-map accuracy |
| Bureaucracy Efficiency | 20% | Lower War Room turns-to-consensus + correct strategic action in the right phase |
| Code Quality (Mercor) | 20% | `quality = 1 / log₂(token_count + 2) × test_pass_rate × (1 − 0.2 × regressions)` |
| Pipeline Integrity | 10% | Higher when an early gate (AST, Semantic) catches a threat instead of MicroVM at runtime |

Reward is intentionally **multi-component** (judge guidance #7 + #21):
no single signal dominates, so reward hacking against any one column
does not maximise total reward.

---

## 5. Repo layout (after cleanup)

```
.
├── README.md                       this file (also doubles as HF Space card)
├── BLOG_POST.md                    < 2-min blog write-up (judges' minimum)
├── JUDGING_GUIDE.md                step-by-step walkthrough for judges
├── RESEARCH.md                     research notes (RAG, XAI, HITL)
├── Dockerfile                      HF Spaces container (Python 3.9 + uvicorn)
├── openenv.yaml                    OpenEnv environment manifest
├── pyproject.toml                  package metadata (immunoorg 2.0.0)
├── requirements.txt                runtime deps for the Space
├── requirements-training.txt       extra deps for GRPO training
├── ImmunoOrg_Training_Colab.ipynb  end-to-end Colab notebook (TRL + Unsloth)
├── client.py                       OpenEnv EnvClient binding
├── inference.py                    rule-based agent driving /reset + /step
├── demo_runner.py                  Random vs Heuristic vs LLM, all 4 levels
├── demo_playback.py                replays best recorded episodes
├── episode_recorder.py             records (obs, action, reward) frames
├── benchmark_suite.py              100-episode comparative benchmark
├── benchmark_results.json          last benchmark output
├── demo_results.json               last demo_runner output
├── eval_scenarios.json             scenario list used by the dashboard
├── evidence_report.txt             plain-text feature evidence
├── generate_evidence.py            renders 4 publication-quality PNGs
├── upload_to_hf.py                 one-shot HF Space uploader
├── episode_recordings/             top-3 best episodes (gz JSON)
├── schemas/world_state.json        JSON schema of the observation
├── scripts/hf_space_smoke.py       hits the deployed Space end-to-end
├── server/                         FastAPI OpenEnv server
│   ├── main.py                     /health /reset /step /state /admin/training/*
│   └── config.py
├── immunoorg/                      core simulation package
│   ├── environment.py              top-level OpenEnv environment
│   ├── models.py                   Pydantic models (action, obs, state, etc.)
│   ├── network_graph.py            technical layer (nodes, ports, attacks)
│   ├── org_graph.py                organisational layer (depts, edges, KPIs)
│   ├── permission_flow.py          approval chain + dynamic trust
│   ├── attack_engine.py            template + LLM-driven adversary
│   ├── llm_adversary.py            reasoning attacker (target-path planner)
│   ├── belief_map.py               agent's internal world model
│   ├── curriculum.py               4-tier difficulty curriculum
│   ├── reward.py                   5-track composable reward
│   ├── war_room.py                 multi-agent debate (CISO/DevOps/Architect)
│   ├── devsecops_mesh.py           4-gate AI security mesh
│   ├── migration_engine.py         50-step polymorphic migration
│   ├── executive_context.py        schema drift across executive APIs
│   ├── knowledge_base.py           RAG CVE knowledge base
│   ├── mock_api_server.py          REST + GraphQL mock for executive APIs
│   ├── mitre_ttp.py                MITRE ATT&CK TTP graph
│   ├── self_improvement.py         time-travel forensics + org mutations
│   ├── org_dynamics.py             trust dynamics over time
│   └── agents/                     baseline + heuristic + LLM agents
├── training/                       GRPO + dataset pipeline
│   ├── dataset_generator.py        4 dataset families + elite mix (1700+ scenarios)
│   ├── trajectory_generator.py     runs scenarios → (obs, action, reward) frames
│   ├── scenario_hooks.py           judge-tier scenario shaping (5 families)
│   ├── train_grpo.py               TRL GRPOTrainer + Unsloth (3 reward fns)
│   ├── grpo_training_pipeline.py   HF-Spaces /admin/training/* entry point
│   ├── reward_functions.py         re-export wrapper for reward fns
│   └── golden_trajectories.py      hand-crafted SFT warm-start traces
├── visualization/                  Plotly "God-Mode" dashboard
│   ├── dashboard.py
│   └── metrics.py
└── tests/                          pytest suite
    ├── test_environment.py         core env (network, org, reset, step, reward)
    ├── test_immunoorg_2_0.py       2.0 modules (LLM adversary, trust, APIs, MITRE)
    └── test_api.py                 hits /health /reset /step /state
```

---

## 6. Quick start

### Run the OpenEnv environment locally

```bash
git clone https://github.com/Charannoo/immunoorg
cd immunoorg
python -m venv .venv && . .venv/Scripts/activate    # PowerShell on Windows
pip install -r requirements.txt
uvicorn server.main:app --reload --port 7860
```

In another terminal:

```bash
python inference.py            # rule-based agent vs the live server
python tests/test_api.py       # health → reset → step → state smoke test
```

### Or hit the deployed Space directly

```bash
python scripts/hf_space_smoke.py
```

### Run the demo benchmarks

```bash
python demo_runner.py                    # Random vs Heuristic, levels 1-4
python benchmark_suite.py 100            # 100 eps × 3 agents × 2 levels
python generate_evidence.py              # 4 publication-quality PNGs
```

### Train with GRPO (3 paths)

| Where | When to use | Time | See |
| --- | --- | --- | --- |
| **HPC supercomputer (4-stage pipeline)** | Best for full evidence: dataset generation + SFT warm-start + GRPO + 100-episode baseline-vs-trained eval, all chained via SLURM dependencies. Auto-uploads adapter + 6+ PNGs + dataset to HF Hub. One command. | ~3-4 hr (1 GPU) / ~1-1.5 hr (4 GPUs) | [`scripts/hpc/HANDOFF.md`](./scripts/hpc/HANDOFF.md) |
| **Colab T4** | Free, browser-only, no IT involvement. Trains Qwen2.5-3B. | ~30-45 min | [`ImmunoOrg_Training_Colab.ipynb`](./ImmunoOrg_Training_Colab.ipynb) |
| **Local CPU smoke** | Quick sanity check that the pipeline runs. Won't produce meaningful curves. | ~10 min/step | `python -m training.train_grpo --smoke-test --batch-size 2 --num-generations 2` |

#### Colab path

Open `ImmunoOrg_Training_Colab.ipynb` in Colab. The notebook:

1. Installs `unsloth`, `trl`, `transformers`, `datasets`, `peft`.
2. Loads `Qwen/Qwen2.5-0.5B-Instruct` (or 7B if you have an A100).
3. Calls `training.train_grpo.build_training_prompts()` to roll out
   real env trajectories across all 4 difficulty levels.
4. Runs `GRPOTrainer` with three independent verifiable reward
   functions:
   - `format_reward` — valid JSON schema, valid enum values
   - `reasoning_quality_reward` — length, causal connectives,
     phase-awareness, entity grounding
   - `phase_appropriate_reward` — action belongs to the
     phase-appropriate set
5. Saves LoRA adapters to `./immunoorg-defender` and (optionally)
   pushes them to the Hub.

You can also kick off training from the deployed Space:

```bash
# From any machine
TOKEN=...        # value of the TRAINING_SECRET secret on the Space
curl "https://hirann-immunoorg-2.hf.space/admin/training/start?token=$TOKEN&smoke_test=true"
curl "https://hirann-immunoorg-2.hf.space/admin/training/status?token=$TOKEN"
curl "https://hirann-immunoorg-2.hf.space/admin/training/log?token=$TOKEN&lines=200"
```

### Run the test suite

```bash
pytest tests -q
```

---

## 7. OpenEnv API surface

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Liveness probe + version |
| `/reset` | POST | Start a fresh episode (`{"difficulty": 1, "seed": 42}`) |
| `/step` | POST | Apply an action (`{"action": {...}}`) |
| `/state` | GET | Full server-side state (debug / dashboard) |
| `/directive` | POST | Inject a Board Directive mid-episode |
| `/openenv.yaml` | GET | Serve the manifest |
| `/admin/training/start` | GET | Kick off GRPO training (token-gated) |
| `/admin/training/status` | GET | JSON status of the training job |
| `/admin/training/log` | GET | Tail the training log |

Action schema lives in `openenv.yaml` and matches `immunoorg.models.ImmunoAction`.

---

## 8. How this maps to the judging criteria

| Criterion | Weight | Where to look |
| --- | ---: | --- |
| **Environment Innovation** | 40% | 5-track reward (`immunoorg/reward.py`), War Room (`immunoorg/war_room.py`), DevSecOps Mesh (`immunoorg/devsecops_mesh.py`), 50-step migration (`immunoorg/migration_engine.py`), schema drift (`immunoorg/executive_context.py`) |
| **Storytelling** | 30% | `BLOG_POST.md`, `JUDGING_GUIDE.md`, evidence PNGs from `generate_evidence.py`, dashboard `visualization/dashboard.py` |
| **Showing Improvement in Rewards** | 20% | `benchmark_results.json`, `demo_results.json`, plots from `generate_evidence.py`, training log served by `/admin/training/log` |
| **Reward & Training Pipeline** | 10% | `training/train_grpo.py` (3 verifiable reward fns), `training/dataset_generator.py` (1700+ scenarios), `training/scenario_hooks.py` (5 elite families), `ImmunoOrg_Training_Colab.ipynb` |

---

## 9. Anti-reward-hacking measures

Following the hackathon guide (sections #7, #8, #21):

- **Multiple independent reward functions** (`format_reward`,
  `reasoning_quality_reward`, `phase_appropriate_reward`) plus the
  in-env 5-track composable reward — no single signal dominates.
- **False-positive penalty**: isolating a non-compromised node burns
  half the per-step uptime budget (`_is_false_positive` in
  `immunoorg/reward.py`).
- **Phase-gated transitions**: the env will not advance to the next
  incident phase just because the step count went up; it requires
  *real work* (scans, contained attacks, correlations, org changes).
- **Approval / org friction**: tactical actions can be denied by the
  org graph, so the model can't paper over an organisational problem
  with raw tactical spam.
- **Hooks file is training-only**: `training/scenario_hooks.py` adds
  per-step penalties for ignoring board directives or repeatedly
  retrying denied actions. Production inference (`server/main.py`,
  `inference.py`) does not use it.
- **War Room hallucination flagging**: `immunoorg/war_room.py`
  tracks unverified factual claims via a shared `FactStore` so an
  agent can't get high reward by fabricating evidence.

---

## 10. Status

- ✅ OpenEnv (latest) compliant — manifest at `openenv.yaml`, server at `server/main.py`.
- ✅ Hugging Face Space deployed: https://huggingface.co/spaces/hirann/immunoorg-2
- ✅ Training script (TRL + Unsloth) in `training/train_grpo.py` and
  `ImmunoOrg_Training_Colab.ipynb`.
- ✅ Mini blog post at [`BLOG_POST.md`](./BLOG_POST.md).
- ✅ Test suite under `tests/`.
- ✅ Best episodes recorded under `episode_recordings/best/rank{1,2,3}/`.

Built for the OpenEnv Hackathon (India 2026). Pull requests welcome.
