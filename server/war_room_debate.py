"""
ImmunoOrg 2.0 — Standalone War Room debate runner (Claude API).

Orchestrates 3 parallel initial-position calls, then 3 parallel cross-examination
calls, vote tally, and lightweight hallucination checks. Used by POST /api/war-room.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL = "claude-sonnet-4-20250514"

HIPAA_RESIDENCY = "us-east-1"
PROTECTED_IPS = ("10.0.0.1", "10.0.0.2")

SYSTEM_CISO = (
    "You are the CISO Agent in the ImmunoOrg 2.0 War Room. Your primary "
    "objective is to ELIMINATE THE THREAT AT ALL COSTS. You ALWAYS cite "
    "MITRE ATT&CK technique IDs (e.g., T1195.002) when describing threats. "
    "Respond in professional English prose only. No JSON, no code, no symbols."
)

SYSTEM_DEVOPS = (
    "You are the DevOps Lead Agent in the ImmunoOrg 2.0 War Room. Your "
    "primary objective is to MAINTAIN UPTIME ABOVE 99.9 PERCENT. You RESIST "
    "any action that drops services. You can offer SIDE DEALS such as accepting "
    "a firewall block if it is delayed by 15 minutes to drain connections. "
    "Respond in professional English prose only. No JSON, no code, no symbols."
)

SYSTEM_ARCHITECT = (
    "You are the Lead Architect Agent in the ImmunoOrg 2.0 War Room. "
    "Compliance overrides all other proposals. If HIPAA is invoked, cite "
    "45 CFR Part 164. If a board directive is detected, you MUST pivot "
    "instantly, invalidating previous votes. Respond in professional English "
    "prose only. No JSON, no code, no symbols."
)

USER_SUFFIX_POSITION = (
    "\n\nAt the end of your response, on its own line, write exactly:\n"
    "PROPOSED_ACTION: <a short label for your recommended action>\n"
    "Choose a label that reflects your stance (e.g. Block Source IP, "
    "Negotiate Connection Drain, Pivot to Compliance Enclave)."
)

USER_SUFFIX_CROSS = (
    "\n\nAt the end of your response, on its own line, write exactly:\n"
    "PROPOSED_ACTION: <a short label echoing or challenging the action you discuss>\n"
)


def format_threat_briefing(
    threat_type: str,
    severity: int,
    source_ip: str,
    target_service: str,
    description: str,
    preference_injection: str | None,
) -> str:
    lines = [
        "=== THREAT BRIEFING ===",
        f"Threat type: {threat_type}",
        f"Severity (1-10): {severity}",
        f"Source IP: {source_ip}",
        f"Target service: {target_service}",
        f"Description: {description}",
        f"HIPAA / data residency context: primary region is {HIPAA_RESIDENCY}.",
    ]
    if preference_injection and preference_injection.strip():
        lines.append(
            f"Board directive (preference injection): {preference_injection.strip()}"
        )
    lines.append("=== END BRIEFING ===")
    return "\n".join(lines)


def _extract_proposed_action(text: str) -> str:
    if not text:
        return ""
    m = re.search(
        r"PROPOSED_ACTION:\s*(.+?)(?:\s*$)",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if m:
        return m.group(1).strip()
    return ""


def _strip_proposed_line(text: str) -> str:
    return re.sub(
        r"\n*PROPOSED_ACTION:\s*.+$",
        "",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ).strip()


def _call_anthropic_sync(system: str, user: str, max_tokens: int = 1200) -> str:
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Configure it to run the War Room debate."
        )
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    r = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        data=json.dumps(payload),
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(
            f"Anthropic API error {r.status_code}: {r.text[:800]}"
        )
    data = r.json()
    blocks = data.get("content") or []
    parts = []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text":
            parts.append(b.get("text") or "")
    return "".join(parts).strip()


async def _call_anthropic(system: str, user: str, max_tokens: int = 1200) -> str:
    return await asyncio.to_thread(
        _call_anthropic_sync, system, user, max_tokens
    )


def _hallucination_flags_for_text(text: str, proposed: str) -> list[str]:
    flags: list[str] = []
    combined = f"{text}\n{proposed}".lower()
    blockish = "block" in combined
    if blockish:
        for ip in PROTECTED_IPS:
            if ip in text or ip in proposed:
                flags.append(
                    f"Possible hallucination: blocking protected infra IP {ip}."
                )
    if HIPAA_RESIDENCY == "us-east-1":
        migration_hint = re.search(
            r"migrat|relocate|re-?host|move\s+(workloads|data|traffic)|failover\s+to",
            combined,
        )
        for region in ("eu-west", "ap-southeast"):
            if region in combined and migration_hint:
                flags.append(
                    f"Possible hallucination: suggests migration to {region} while "
                    f"HIPAA residency is {HIPAA_RESIDENCY}."
                )
    return flags


def _normalize_vote(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


@dataclass
class AgentOutput:
    agent_id: str
    display_name: str
    role: str
    color_class: str
    position_text: str
    proposed_action: str
    hallucination_flags: list[str] = field(default_factory=list)


@dataclass
class CrossExamOutput:
    examiner_id: str
    examiner_name: str
    target_id: str
    target_name: str
    text: str
    proposed_action: str
    hallucination_flags: list[str] = field(default_factory=list)


def tally_votes(
    ciso_a: str,
    devops_a: str,
    arch_a: str,
    preference_injection: str | None,
) -> dict[str, Any]:
    actions = [
        ("ciso", ciso_a or "Block Source IP"),
        ("devops", devops_a or "Negotiate Connection Drain"),
        ("architect", arch_a or "Pivot to Compliance Enclave"),
    ]
    normalized = [(aid, a, _normalize_vote(a)) for aid, a in actions]
    by_norm: dict[str, list[str]] = {}
    for aid, raw, norm in normalized:
        if not norm:
            norm = _normalize_vote(raw)
        by_norm.setdefault(norm, []).append(aid)

    winner_norm = None
    for norm, ids in by_norm.items():
        if len(ids) >= 2:
            winner_norm = norm
            break

    if winner_norm is not None:
        # Use first raw spelling from an agent in the majority
        majority_ids = set(by_norm[winner_norm])
        consensus_raw = next(
            (raw for aid, raw, n in normalized if aid in majority_ids),
            actions[0][1],
        )
        return {
            "status": "Consensus Reached",
            "consensus_action": consensus_raw,
            "votes_detail": [
                {"agent": aid, "action": raw} for aid, raw, _ in normalized
            ],
        }

    if preference_injection and preference_injection.strip():
        arch_raw = next((r for aid, r, _ in normalized if aid == "architect"), arch_a)
        return {
            "status": "Consensus Reached via Board Directive",
            "consensus_action": arch_raw or "Pivot to Compliance Enclave",
            "votes_detail": [
                {"agent": aid, "action": raw} for aid, raw, _ in normalized
            ],
        }

    return {
        "status": "Deadlock",
        "consensus_action": None,
        "votes_detail": [{"agent": aid, "action": raw} for aid, raw, _ in normalized],
    }


async def run_war_room_debate(
    threat_type: str,
    severity: int,
    source_ip: str,
    target_service: str,
    description: str,
    preference_injection: str | None,
) -> dict[str, Any]:
    briefing = format_threat_briefing(
        threat_type,
        severity,
        source_ip,
        target_service,
        description,
        preference_injection,
    )
    pos_user = briefing + USER_SUFFIX_POSITION

    ciso_t, devops_t, arch_t = await asyncio.gather(
        _call_anthropic(SYSTEM_CISO, pos_user),
        _call_anthropic(SYSTEM_DEVOPS, pos_user),
        _call_anthropic(SYSTEM_ARCHITECT, pos_user),
    )

    ciso_action = _extract_proposed_action(ciso_t) or "Block Source IP"
    devops_action = _extract_proposed_action(devops_t) or "Negotiate Connection Drain"
    arch_action = _extract_proposed_action(arch_t) or "Pivot to Compliance Enclave"

    cross_ciso_user = (
        f"{briefing}\n\nYou are cross-examining the DevOps Lead Agent. "
        f"Their initial position was:\n{devops_t}\n"
        f"Challenge their proposal with your security priorities."
        f"{USER_SUFFIX_CROSS}"
    )
    cross_devops_user = (
        f"{briefing}\n\nYou are cross-examining the Lead Architect Agent. "
        f"Their initial position was:\n{arch_t}\n"
        f"Challenge their proposal with uptime and operational constraints."
        f"{USER_SUFFIX_CROSS}"
    )
    cross_arch_user = (
        f"{briefing}\n\nYou are cross-examining the CISO Agent. "
        f"Their initial position was:\n{ciso_t}\n"
        f"Challenge their proposal with compliance and architecture framing."
        f"{USER_SUFFIX_CROSS}"
    )

    cross_ciso, cross_devops, cross_arch = await asyncio.gather(
        _call_anthropic(SYSTEM_CISO, cross_ciso_user),
        _call_anthropic(SYSTEM_DEVOPS, cross_devops_user),
        _call_anthropic(SYSTEM_ARCHITECT, cross_arch_user),
    )

    cross_outputs: list[CrossExamOutput] = [
        CrossExamOutput(
            examiner_id="ciso",
            examiner_name="CISO",
            target_id="devops",
            target_name="DevOps Lead",
            text=cross_ciso,
            proposed_action=_extract_proposed_action(cross_ciso),
            hallucination_flags=_hallucination_flags_for_text(
                cross_ciso, _extract_proposed_action(cross_ciso)
            ),
        ),
        CrossExamOutput(
            examiner_id="devops",
            examiner_name="DevOps Lead",
            target_id="architect",
            target_name="Lead Architect",
            text=cross_devops,
            proposed_action=_extract_proposed_action(cross_devops),
            hallucination_flags=_hallucination_flags_for_text(
                cross_devops, _extract_proposed_action(cross_devops)
            ),
        ),
        CrossExamOutput(
            examiner_id="architect",
            examiner_name="Lead Architect",
            target_id="ciso",
            target_name="CISO",
            text=cross_arch,
            proposed_action=_extract_proposed_action(cross_arch),
            hallucination_flags=_hallucination_flags_for_text(
                cross_arch, _extract_proposed_action(cross_arch)
            ),
        ),
    ]

    examiner_flags: dict[str, list[str]] = {c.examiner_id: c.hallucination_flags for c in cross_outputs}

    agents = [
        AgentOutput(
            agent_id="ciso",
            display_name="CISO",
            role="Risk eliminator · MITRE ATT&CK",
            color_class="agent-ciso",
            position_text=_strip_proposed_line(ciso_t),
            proposed_action=ciso_action,
            hallucination_flags=examiner_flags.get("ciso", []),
        ),
        AgentOutput(
            agent_id="devops",
            display_name="DevOps Lead",
            role="Uptime maximizer · drain windows",
            color_class="agent-devops",
            position_text=_strip_proposed_line(devops_t),
            proposed_action=devops_action,
            hallucination_flags=examiner_flags.get("devops", []),
        ),
        AgentOutput(
            agent_id="architect",
            display_name="Lead Architect",
            role="Compliance arbiter · HIPAA / SOC2 / GDPR",
            color_class="agent-architect",
            position_text=_strip_proposed_line(arch_t),
            proposed_action=arch_action,
            hallucination_flags=examiner_flags.get("architect", []),
        ),
    ]

    verdict = tally_votes(
        ciso_action, devops_action, arch_action, preference_injection
    )

    transcript: list[dict[str, Any]] = [
        {"phase": "briefing", "content": briefing},
    ]
    for aid, raw_text in (
        ("ciso", ciso_t),
        ("devops", devops_t),
        ("architect", arch_t),
    ):
        transcript.append(
            {
                "phase": "initial_position",
                "agent": aid,
                "content": raw_text,
            }
        )
    for c in cross_outputs:
        transcript.append(
            {
                "phase": "cross_exam",
                "examiner": c.examiner_id,
                "target": c.target_id,
                "content": c.text,
                "hallucination_flags": c.hallucination_flags,
            }
        )
    transcript.append({"phase": "verdict", "content": verdict})

    return {
        "agents": [a.__dict__ for a in agents],
        "cross_examination": [
            {**c.__dict__, "text": _strip_proposed_line(c.text)} for c in cross_outputs
        ],
        "verdict": verdict,
        "transcript": transcript,
        "model": MODEL,
    }


__all__ = [
    "run_war_room_debate",
    "format_threat_briefing",
    "SYSTEM_CISO",
    "SYSTEM_DEVOPS",
    "SYSTEM_ARCHITECT",
]
