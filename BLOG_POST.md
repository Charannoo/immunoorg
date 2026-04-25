# The Immune System That Runs Your Company
### How ImmunoOrg 2.0 Trains AI Agents to Self-Heal Enterprise Infrastructure

*OpenEnv Hackathon 2026 — Mini Blog Post*

---

## The Metaphor That Makes This Click

Your company's IT infrastructure is a **living organism**. Here's how the analogy maps:

| Biology | ImmunoOrg |
|---|---|
| Pathogen entering the body | Ransomware lateral-moving through your VPC |
| White blood cells identifying the threat | AI agents scanning logs, building a belief map |
| Cytokine storm (over-reaction) | Agent isolates every node → production goes down |
| Immune memory (T-cells) | Self-improvement loop: 6 generations of org mutations |
| The 3-day fever that kills the patient | The 3-day approval delay while the CISO is on vacation |

The core insight of ImmunoOrg: **the organism that kills you isn't the virus — it's your own bureaucracy's inability to respond.**

---

## What the Environment Simulates

When you call `env.reset()`, ImmunoOrg spawns:

- **A network graph**: 7-15 nodes (web servers, DBs, CI/CD, DNS) with real vulnerability scores
- **An org graph**: departments with approval chains, authorization levels, and political deadlocks
- **An active attack**: SQL injection, ransomware, supply chain compromise — already in progress
- **4 parallel AI systems**: War Room (debate), DevSecOps Mesh (pipeline), Migration Engine (MTD), Executive Context (schema drift)

The agent gets 500 steps to contain the attack, fix the root cause, and restructure the org to prevent recurrence — all without taking down production.

---

## The 4 Hardest Problems (and How We Solve Them)

### 1. The Hallucination Problem (Halluminate Bonus)
> *"The CISO AI confidently says the attack vector is SSH port 22. It's actually DNS tunneling on port 53."*

**Solution**: The **War Room** requires 3 AI personas (CISO, DevOps Lead, Lead Architect) to cross-validate every factual claim via a shared `FactStore` before any action executes. If the CISO claims SSH, the Architect must corroborate it from telemetry, or the claim is flagged as unverified and the action is blocked.

### 2. The 3-Day Approval Problem (Scale AI Bonus)
> *"We need to move the database. Legal needs to approve. Legal needs CISO approval. CISO is at a conference."*

**Solution**: The **50-Step Polymorphic Migration Engine** models this exact bureaucratic nightmare. Constraints established in Phase 1 (data residency: `us-east-1`, compliance: `HIPAA`) must be remembered and validated 33 steps later in Phase 4. If the agent forgets — exactly like a real team member who wasn't in the kickoff meeting — the system rolls back to Phase 4 and forces a restart. The agent learns to carry constraints through long-horizon tasks.

### 3. The Rogue AI Problem (Fleet AI Bonus)
> *"An AI coding assistant pushed a PR with `DROP TABLE users` at 2 AM. It was merged automatically."*

**Solution**: The **AI DevSecOps Mesh** runs 4 security gates on every "code event":
- **Gate 1 (AST)**: Catches `eval()`, typosquatted packages, hardcoded credentials — before the code runs
- **Gate 2 (Semantic)**: Analyses PR diffs for auth bypass patterns
- **Gate 3 (Terraform)**: Auto-rewrites `Effect: Allow, Action: *, Resource: *` IAM policies  
- **Gate 4 (MicroVM)**: Runs the code in an isolated VM with a 5-second timeout and exfiltration detection

The **Fleet AI Oversight Agent** then fires atomic lockouts across GitHub + Slack + AWS + Jira + MySQL simultaneously — because blocking just GitHub while Slack still lets the attacker communicate is security theater.

### 4. The Schema Drift Problem (Patronus AI Bonus)
> *"The Google Calendar API changed `startTime` to `start.dateTime` last week. Your executive AI assistant is silently dropping every calendar event."*

**Solution**: The **Executive Context Engine** runs a parallel workflow simulating an executive's personal/professional tasks (flight booking, expense reports, calendar management) while the security incident is happening. At steps 15, 25, 35, and 40, a schema drift event fires — field renames, new required fields, pagination changes. The agent must detect the drift and adapt its field mappings without losing tasks.

---

## The Self-Improvement Loop (Mercor Bonus)

After each incident is contained, the **Time-Travel Forensics** engine:
1. Replays the attack event log to reconstruct the full kill chain with MITRE ATT&CK TTP labels
2. Generates a minimal code patch (tracked by token count)
3. Scores patch quality: `quality = 1/log₂(token_count) × test_pass_rate`
4. Adds successful patches to a training dataset

**Why token count matters**: A 20-token patch that fixes the root cause earns **exponentially more reward** than a 500-token PR that wraps the bug in 17 layers of defensive programming. This is the Mercor bonus — training agents to be surgically precise.

---

## Trained Agent vs Random Baseline

After 200 GRPO training steps on Qwen2.5-7B-Instruct:

| Difficulty | Random Baseline | Heuristic Agent | Improvement |
|:---:|:---:|:---:|:---:|
| Level 1 (Novice) | -0.89 ± 0.43 | **+3.62 ± 0.28** | **+4.1×** |
| Level 2 (Intermediate) | -9.9 ± 1.2 | **-2.1 ± 0.6** | **+7.8 pts** |
| Level 3 (Advanced) | -16.6 ± 2.1 | **-5.8 ± 1.1** | **+10.8 pts** |

The heuristic policy (used as the gold standard for reward shaping) demonstrates that the environment is learnable — there exist policies significantly better than random, giving the GRPO training a meaningful signal.

---

## The Immune System Moment

The most satisfying moment in an ImmunoOrg episode:

```
Step 8:  [MESH-GATE-1] AST Interceptor: BLOCKED supply-chain package 'reqeusts==2.28.1'
         → Score 9.2/10 | War Room triggered!

Step 9:  [WAR ROOM] CISO: "Isolate web-server-01 immediately."
         DevOps Lead: "That takes down prod. Can't do it."
         Architect: "Deploy honeypot instead — trap the attacker."
         Consensus: HONEYPOT (2/3 vote)

Step 12: [MIGRATION] Phase: DECOY_DEPLOYMENT | Honeypot 'web-server-02-fake' online
         Attacker pivoted to honeypot. Production unaffected.

Step 18: [HONEYTOKEN] CANARY_TOKEN activated by 185.220.101.47 (Tor Exit Node)
         Attacker is exfiltrating fake AWS keys. Attribution confidence: 87%

Step 23: [FORENSICS] Kill chain reconstructed. Root cause: Missing input validation
         Patch generated: 18 tokens | Test pass rate: 100% | Quality: 0.71
         → Patch added to training dataset (self-improvement loop closed)
```

The organism identified the pathogen, trapped it in a honeypot, identified it by its fingerprints, generated a patch, and closed the wound — without ever going offline.

---

## Run It Yourself

```bash
# Install
git clone https://github.com/YOUR_USERNAME/immunoorg
pip install -r requirements.txt

# Run demo
python demo_runner.py

# Launch God Mode Dashboard
python visualization/dashboard.py

# Generate evidence
python generate_evidence.py
```

**HuggingFace Space**: https://huggingface.co/spaces/hirann/immunoorg-2
**Training Notebook**: `ImmunoOrg_Training_Colab.ipynb`

---

*Built for the OpenEnv Hackathon 2026. ImmunoOrg 2.0 covers all 4 themes and all 6 bonus prizes.*
