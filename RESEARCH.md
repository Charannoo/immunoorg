# 🧬 ImmunoOrg: Intelligence & Architecture Research

## Overview
ImmunoOrg is a high-fidelity simulation of an autonomous, self-healing enterprise. It demonstrates "Winning-Tier" AI research patterns by integrating multi-agent coordination, retrieval-augmented generation (RAG), and explainable AI (XAI) within a competitive co-evolutionary framework.

## 1. Adversarial Co-Evolution (Self-Play)
The core of ImmunoOrg's intelligence is its **Co-Evolutionary Cycle**. Unlike static security simulations, ImmunoOrg employs a dynamic feedback loop between the Defender and the Adversary.

### The Cycle:
1. **Defender Adaptation**: The agent learns to identify and contain threats, improving its "Belief Map" and organizational efficiency.
2. **Improvement Metric**: The `SelfImprovementEngine` tracks the rate of reward increase and time-to-containment across generations.
3. **Adversary Evolution**: The `AttackEngine` dynamically increases adversary complexity (stealth, lateral movement capability, and vector variety) based on the defender's improvement rate.
4. **New Equilibrium**: This creates a "Red Queen" effect, where the agent must continuously innovate its defense strategies to keep pace with an evolving threat.

## 2. RAG-Powered CVE Intelligence
To bridge the gap between simulated environments and real-world security, ImmunoOrg implements a **Retrieval-Augmented Generation (RAG)** system.

- **Knowledge Base**: The `CVEKnowledgeBase` simulates a vector database of real-world CVEs (e.g., SQL Injection, Rootkits, Supply Chain attacks).
- **Semantic Retrieval**: When a threat is detected, the agent retrieves technical details and recommended mitigations from the knowledge base.
- **Observation Injection**: This intelligence is injected directly into the agent's observation stream, allowing the model to reason about *why* a specific mitigation (e.g., "parameterized queries") is the correct choice for a specific CVE.

## 3. XAI: The Reasoning Heatmap
To solve the "black box" problem of LLM agents, ImmunoOrg implements a **Reasoning Trace** architecture for full interpretability.

### Trace Components:
- **Decision Trigger**: The exact observation or alert that sparked the action (e.g., "RAG alert for CVE-2023-1234").
- **Observation Snippet**: The raw data evidence used for the decision.
- **Rationale**: The agent's internal chain-of-thought justification.

### The Heatmap:
These traces are aggregated into a **Reasoning Heatmap**, allowing human judges to audit the agent's logic in real-time. This transforms a simple action log into a transparent map of the agent's cognitive process.

## 4. HITL: The Judge's Console
The **Judge's Console** introduces Human-in-the-Loop (HITL) dynamics, simulating a corporate board of directors.

- **Directive Injection**: Judges can inject high-level board directives (e.g., *"Prioritize Uptime over Isolation"*) mid-simulation.
- **Constraint Adaptation**: The agent must dynamically shift its reward function and action priorities to align with these new constraints, demonstrating high-level cognitive flexibility and alignment.

## Summary of Intelligence Tiers
| Feature | Research Pattern | Value Proposition |
| :--- | :--- | :--- |
| **Co-Evolution** | Competitive Self-Play | Continuous improvement of agent robustness |
| **RAG-CVE** | External Knowledge Retrieval | Grounding simulation in real-world security |
| **Reasoning Heatmap** | Explainable AI (XAI) | Full transparency of decision-making |
| **Judge's Console** | Human-in-the-Loop (HITL) | Dynamic alignment with executive goals |
