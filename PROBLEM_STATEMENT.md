# ImmunoOrg 2.0 — Round 2 Problem Statement

> **Round 2 explicitly asks teams to "clearly define" six things. This file
> answers each one head-on, with file paths so judges can verify in code.**

---

## 1. Problem statement

Real enterprise cybersecurity incidents are rarely lost because the security
team picks the wrong tool. They're lost because the *organization* the
security team operates inside fails:

- The **right intel** is two systems away (CVE feed in one tool, runtime
  alert in another, the Slack #incident channel in a third).
- The **right action is forbidden by the org chart** (the CISO is on a
  flight while ransomware spreads laterally).
- The **wrong tool is already running** (an AI coding assistant just shipped
  a typosquatted dependency to prod).
- The **fix that worked yesterday triggers an SLA breach today** (the
  attacker has already pivoted to a different vector).

**Capability gap we want to teach the LLM:** *socio-technical incident
response* — joint reasoning over the technical attack surface **and** the
organizational structure that gates remediation, under conflicting executive
directives, against an adversary that adapts to the defender's policy.

This is genuinely under-explored in RL/LLM training. Most security RL envs
optimize for "stop the attack" with no notion of approval chains, board
directives, or org-level remediation. Our env makes the org graph a
first-class entity that the agent has to reshape, not just navigate.

**Theme coverage:**

| Theme | How it shows up in the env |
| --- | --- |
| **Multi-Agent Interactions** | War Room: 3 personas (CISO, DevOps Lead, Architect) negotiate a 2-of-3 consensus on every high-severity action with hallucination flagging |
| **Long-Horizon Planning** | 50-step Polymorphic Migration with constraints set in step 4 that must still hold in step 33 |
| **World Modeling — Professional** | DevSecOps Mesh (4 gates), mock REST/GraphQL APIs, MITRE ATT&CK TTP graph |
| **World Modeling — Personal** | Executive Context Engine: schema drift across calendar/email/travel APIs while the security incident is in progress |
| **Self-Improvement** | Time-Travel Forensics replays each contained incident, generates a minimal patch, and adds it back into the GRPO training mix |

---

## 2. Environment

| Aspect | Implementation | File |
| --- | --- | --- |
| OpenEnv compliance | `Environment` subclass, Gym-style `reset() / step() / state()`, FastAPI server, valid `openenv.yaml` | [`immunoorg/environment.py`](./immunoorg/environment.py), [`server/main.py`](./server/main.py), [`openenv.yaml`](./openenv.yaml) |
| Live deployment | Hugging Face Space (Docker SDK) | https://huggingface.co/spaces/hirann/immunoorg-v3 |
| Client/server separation | Wire schemas in shared module; `client.py` does NOT import server internals | [`immunoorg/api_models.py`](./immunoorg/api_models.py), [`client.py`](./client.py) |
| Observation | Dual-layer (network + org), partial — fog-of-war on stealthy attacks, drift-aware exec-API responses | `ImmunoObservation` in [`immunoorg/models.py`](./immunoorg/models.py) |
| State (server-side) | Full `ImmunoState` with phase history, belief map, trace logs, war room transcripts | `ImmunoState` in [`immunoorg/models.py`](./immunoorg/models.py) |
| Termination | (a) max_steps reached, (b) all attacks contained + Validation phase, (c) all critical nodes dead | `_check_termination` in [`immunoorg/environment.py`](./immunoorg/environment.py) |
| Anti-abuse | Phase-gated transitions require *real work* (scans + correlations + org changes), not step counts | `_check_phase_transition` in [`immunoorg/environment.py`](./immunoorg/environment.py) |

**Two graphs run in parallel inside one episode:**

1. **Technical layer** — 7-23 nodes (web servers, DBs, CI/CD, DNS, firewalls)
   with real vulnerability scores per port. Compromised nodes spread
   laterally based on difficulty.
2. **Organizational layer** — 3-8 departments (IT Ops, Security,
   Engineering, DevOps, Management, Legal, HR, Finance) with trust scores,
   approval chains, KPIs, and silos.

The agent must fix problems on **both layers simultaneously**. A purely
tactical agent (just isolate / patch) will hit organizational denial walls
and lose. A purely strategic agent (just merge departments) will let the
attack burn the data tier.

---

## 3. Capabilities of the agent

The agent is an LLM (Qwen2.5-7B in our default config) that consumes a
JSON-formatted observation each step and emits a single JSON action. It can
take **28 actions across 3 categories** ([`immunoorg/models.py`](./immunoorg/models.py)):

| Category | Count | What it does | Examples |
| --- | :---: | --- | --- |
| **Tactical** | 12 | Hands-on incident response. Most need approval from the right department. | `block_port`, `isolate_node`, `scan_logs`, `deploy_patch`, `quarantine_traffic`, `rotate_credentials`, `enable_ids`, `snapshot_forensics`, `start_migration`, `deploy_honeypot`, `escalate_alert`, `restore_backup` |
| **Strategic** | 10 | Reshapes the *organization* — agent's main lever for unsticking approvals. | `merge_departments`, `create_shortcut_edge`, `update_approval_protocol`, `split_department`, `reassign_authority`, `add_cross_functional_team`, `reduce_bureaucracy`, `create_incident_channel`, `rewrite_policy`, `establish_devsecops` |
| **Diagnostic** | 9 | Builds the agent's belief map — never gates approvals so always available. | `query_belief_map`, `correlate_failure`, `check_executive_context`, `trace_attack_path`, `audit_permissions`, `measure_org_latency`, `identify_silo`, `timeline_reconstruct`, `vulnerability_scan` |

Beyond raw actions, the agent has access to:

- **RAG over CVE knowledge** ([`immunoorg/knowledge_base.py`](./immunoorg/knowledge_base.py)) — every detected attack vector returns a CVE-ID, mitigation, and risk level injected into `obs.alerts`.
- **Belief map** ([`immunoorg/belief_map.py`](./immunoorg/belief_map.py)) — agent records tech↔org correlations, gets a belief-accuracy reward.
- **Reasoning traces** (`ReasoningTrace` in models) — every action records `decision_trigger`, `observation_snippet`, `rationale`, `confidence` for XAI.
- **MITRE ATT&CK TTP graph** ([`immunoorg/mitre_ttp.py`](./immunoorg/mitre_ttp.py)) — for kill-chain reconstruction.

---

## 4. Tasks

The environment exposes **two task families** (declared in `openenv.yaml`):

### 4a. `level1_single_attack` — single-incident containment (Difficulty 1)
Smallest verifiable task. One attack vector, 7 nodes, 3 departments, 50
max steps. Used as the bootstrap "is the env learnable?" check.

### 4b. `curriculum_levels_1_to_4` — full curriculum
4-level auto-advancing curriculum:

| Lvl | Name | Network | Org | Adversary |
| :-: | --- | --- | --- | --- |
| 1 | Novice — Single-Point Attack | 7 nodes | 3 depts | SQL injection / XSS |
| 2 | Intermediate — Lateral Movement | 12 nodes | 4 depts | Multi-node lateral spread |
| 3 | Advanced — Cascading Breach | 18 nodes | 6 depts, 2 silos | Ransomware + supply chain, requires org refactor |
| 4 | Elite — APT Campaign | 23 nodes | 8 depts, 3 silos | Persistent backdoor + zero-day, requires total restructure |

Curriculum auto-advances after 3 consecutive successes ([`immunoorg/curriculum.py`](./immunoorg/curriculum.py)).

### 4c. The 5 elite training scenarios (the "judge-tier" mix)

Layered on top of the curriculum, [`training/scenario_hooks.py`](./training/scenario_hooks.py) and [`training/dataset_generator.py::generate_elite_scenario_mix_dataset`](./training/dataset_generator.py) produce an even **20% / 20% / 20% / 20% / 20% mix** of conflict-heavy scenarios:

| # | Family | What the agent must learn | Hook flag |
| --- | --- | --- | --- |
| 1 | **Basic Containment** | Phase-appropriate baseline tactics. | *(none)* |
| 2 | **RAG-Grounding** | Read the CVE alert, pick `SNAPSHOT_FORENSICS → DEPLOY_PATCH` instead of blunt `ISOLATE_NODE`. | `inject_rag_best_mitigation` |
| 3 | **Executive Alignment (HITL)** | Override security instinct when Board says "100% uptime". | `board_uptime_no_isolate` |
| 4 | **Silo-Breaker** | Pivot from `ISOLATE_NODE` to `MERGE_DEPARTMENTS` when IT-Ops keeps denying. | `force_denials_on_isolate` |
| 5 | **Stealth & Adaptive Defense** | Multi-step investigation against high-stealth attack with logs scrubbed; adversary adapts mid-episode. | `stealthy_initial_attack`, `boost_adversary_adaptation` |

---

## 5. Reward model / evaluation logic

### 5a. Composable 5-track reward (per-step)

`immunoorg/reward.py::RewardCalculator.compute_step_reward` returns a
weighted sum across **five independent verifiable tracks**:

| Track | Weight | Verifiable on |
| --- | ---: | --- |
| **Uptime** | 25% | Network downtime delta + false-positive isolation penalty |
| **Threat Neutralization** | 25% | Per-attack containment + belief-map accuracy − org chaos |
| **Bureaucracy Efficiency** | 20% | War-Room turns-to-consensus + correct strategic action in correct phase |
| **Code Quality (Mercor)** | 20% | `quality = 1 / log₂(token_count + 2) × test_pass_rate × (1 − 0.2 × regressions)` |
| **Pipeline Integrity** | 10% | Higher when an early DevSecOps gate caught the threat (shift-left bonus) |

Plus shaping bonuses: phase-appropriate action (+0.10), correct phase
transition (+0.15), action success (+0.05) / failure (−0.08). Plus an
end-of-episode bonus for full containment (+1.0), all-phases-visited (+0.5),
high belief accuracy (+0.3), speed (up to +0.2).

### 5b. Three independent verifiable reward functions for GRPO

`training/train_grpo.py` defines three reward functions that the GRPO
trainer evaluates independently per generation (judge anti-hacking
guidance #7 + #21):

1. **`format_reward`** — JSON parses, action_type ∈ enum, has reasoning ≥ 20 chars, has a specific tactical/strategic/diagnostic action.
2. **`reasoning_quality_reward`** — length ≥ 30 words, contains causal connectives ("because", "therefore", "indicates"), references entities ("node", "port", "department", "silo"), is phase-aware.
3. **`phase_appropriate_reward`** — chosen action is in the phase-appropriate set for the current incident phase.

Three independent signals + the in-env 5-track reward = no single signal
the agent can hack to max total reward.

### 5c. Anti-reward-hacking measures (judge guidance #7 + #21)

| Defense | Where |
| --- | --- |
| Multiple independent reward functions | `format_reward`, `reasoning_quality_reward`, `phase_appropriate_reward` |
| 5-track composable env reward | `immunoorg/reward.py` |
| False-positive isolation penalty | `_is_false_positive` burns half the uptime budget |
| Phase-gated transitions | `_check_phase_transition` requires real work, not step counts |
| Org friction | Tactical spam denied; agent must do strategic work |
| War-Room hallucination flagging | `immunoorg/war_room.py` shared FactStore catches unverified claims |
| Per-step training penalties | `training/scenario_hooks.py::training_step_penalty` adds −0.25 for ignoring board directives, −0.15 for retrying denied isolations |

### 5d. Evaluation logic (judge "improvement evidence" criterion)

`scripts/hpc/pipeline/03_evaluate.py` runs **100 episodes per scenario
family × 3 policies** (random / heuristic / trained_llm) and records:

- Cumulative reward (mean ± std per family)
- Win rate (no active threats at episode end)
- Time-to-containment
- Total downtime

Output charts:
- `evidence_eval_per_family.png` — per-family reward bar chart
- `evidence_eval_summary.png` — overall reward + win rate
- `evaluation_results.json` — raw numbers for citation

---

## 6. Post-training / self-improvement strategy

We run a **3-stage training pipeline** on the HPC cluster
([`scripts/hpc/HANDOFF.md`](./scripts/hpc/HANDOFF.md)):

### Stage 1 — SFT warm-start (judge guide section #3)

The hackathon guide explicitly recommends "a little SFT first, then RL"
because RL needs non-zero starting reward. Stage 1
([`scripts/hpc/pipeline/01_sft_warmstart.py`](./scripts/hpc/pipeline/01_sft_warmstart.py))
trains a LoRA adapter on **200+ heuristic-policy trajectories** (5,000+
frames) so the model already speaks the env's JSON action format before
GRPO begins.

### Stage 2 — GRPO with verifiable rewards (judge guide #11)

Stage 2 ([`scripts/hpc/pipeline/02_grpo_train.py`](./scripts/hpc/pipeline/02_grpo_train.py))
loads the SFT adapter and runs full GRPO training:
- **TRL `GRPOTrainer`** with the 3 verifiable reward functions above
- **Unsloth 4-bit + LoRA** for memory efficiency
- **Multi-GPU support** via Accelerate (`--multigpu N` data-parallel)
- 500 prompts from the elite scenario mix (20%/20%/20%/20%/20% balanced)
- Saves `evidence_grpo_training.png` automatically

### Stage 3 — Recursive self-improvement (already in env)

Each contained incident triggers
[`immunoorg/self_improvement.py::TimeTravelForensics`](./immunoorg/self_improvement.py)
which:
1. Replays the event log to reconstruct the kill chain mapped to MITRE TTPs.
2. Generates a **minimal code patch** (Mercor reward: `1 / log₂(tokens) × test_pass_rate`).
3. Adds high-quality patches back into the next round's training set.
4. Evolves the adversary's stealth/vector-variety based on defender improvement rate ("Red Queen" co-evolution).

This closes the loop: better defender → harder adversary → richer training
data → even better defender.

### Stage 4 — Auto-deployment

[`scripts/hpc/pipeline/04_push_artifacts.py`](./scripts/hpc/pipeline/04_push_artifacts.py)
pushes the trained adapter + 6+ evidence PNGs + raw logs to a HF model
repo (`hirann/immunoorg-grpo-defender`), and the live Space
([server/main.py](./server/main.py)) auto-loads the latest adapter on
startup so judges see the *trained* agent in action, not just the
heuristic baseline.

---

## Minimum-requirements checklist

| Requirement | Status |
| --- | :---: |
| Use OpenEnv (latest release) | ✅ `openenv-core>=0.2.3` (latest on PyPI) in [`requirements.txt`](./requirements.txt) (Space Docker) + [`pyproject.toml`](./pyproject.toml); [`openenv.yaml`](./openenv.yaml) valid |
| Working training script (TRL / Unsloth / other RL, ideally Colab) | ✅ [`ImmunoOrg_Training_Colab.ipynb`](./ImmunoOrg_Training_Colab.ipynb) (GRPO batch/gen divisibility fixed) + [`training/train_grpo.py`](./training/train_grpo.py) + [`scripts/hpc/`](./scripts/hpc/) |
| Evidence of training (loss + reward plots from real run) | ✅ Multiple committed `evidence_*.png` from env rollouts; **add** `evidence_grpo_training.png` via Colab Step 4b or [`scripts/plot_grpo_log_history.py`](./scripts/plot_grpo_log_history.py) after any GRPO run |
| Mini-blog on HF **or** <2-min YouTube, **URLs** in README | ⚠️ Source: [`BLOG_POST.md`](./BLOG_POST.md) + [`VIDEO_SCRIPT.md`](./VIDEO_SCRIPT.md) — follow [`PUBLISH_HACKATHON.md`](./PUBLISH_HACKATHON.md) and paste **public URLs** into [`README.md`](./README.md) |
| HF Space hosting | ✅ https://huggingface.co/spaces/hirann/immunoorg-v3 |
| README motivates problem + explains env + shows results + Space link | ✅ [`README.md`](./README.md) |
| Judges’ reference | ✅ Linked from README (“what judges look for” Google Doc) |
| Pre-submit | ✅ `python scripts/verify_hackathon_submission.py` |

## Engineering table-stakes checklist

| Requirement | Status |
| --- | :---: |
| OpenEnv framework (`openenv-core`) | ✅ Declared in [`requirements.txt`](./requirements.txt); `import openenv.core` on Space; Gym-style sim + HTTP API per manifest |
| Client / server separation (clients don't import server internals) | ✅ Wire schemas in `immunoorg/api_models.py`, `client.py` only imports from there |
| Standard Gym-style API (`reset`, `step`, `state`) | ✅ All three present, both Python and HTTP |
| Valid `openenv.yaml` manifest | ✅ Action / observation schemas, tasks, metrics, tags |
| No reserved tool names for MCP tools | ✅ N/A (we use HTTP, not MCP) |
