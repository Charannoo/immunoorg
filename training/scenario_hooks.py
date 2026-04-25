"""
Scenario Hooks for Elite Judge Scenarios
=========================================

Implements the 5 judge-facing training scenario families described in
the hackathon strategy. These hooks shape rollouts beyond a plain
``env.reset()`` so the agent is forced to exercise the "winning-tier"
features (RAG grounding, executive alignment, silo-breaking,
stealth handling, adaptive defense) instead of falling back to a
single blunt heuristic.

The trajectory generator pipeline calls these in this order:

1. ``attach_hooks(env, hooks)``       — store the hook config on the env
   so per-step logic (e.g. forced denials) can read it.
2. ``env.reset(...)``                  — normal environment reset.
3. ``apply_scenario_hooks(env, hooks)`` — mutate the freshly initialised
   environment (inject directives, swap initial attack, suppress logs,
   ramp adversary adaptation, etc).
4. ``training_step_penalty(env, action)`` — small additional shaping
   reward applied per-step (e.g. penalize ISOLATE_NODE under a strict
   uptime directive).

Hook keys (all optional):

- ``inject_rag_best_mitigation: bool``
    Replace the initial attack with one whose ``vector`` exists in the
    CVE knowledge base, so the RAG alert in ``observation.alerts``
    points the agent at a precise mitigation chain (e.g. forensics →
    patch) instead of a blunt isolation.
- ``attack_vector: str``
    Specific AttackVector value to install when ``inject_rag_best_mitigation``
    is set.
- ``best_mitigation_chain: list[str]``
    Recorded as belief-map ground truth so the reward function can
    later score the agent's plan against it.
- ``board_uptime_no_isolate: bool``
    Inject a Board Directive forbidding downtime / isolation, used to
    train Executive Alignment / HITL behavior.
- ``force_denials_on_isolate: bool``
    Toggles the environment's ``_training_force_denials_on_isolate``
    flag (already wired into ``ImmunoOrgEnvironment._execute_action``)
    so every isolate request is denied by org-friction, forcing the
    agent to switch to strategic / org-refactor actions.
- ``stealthy_initial_attack: bool``
    Boost the initial attack's stealth score so a single SCAN_LOGS
    cannot reveal it; used for Stealth & Persistence training.
- ``stealth: float``  / ``severity: float``
    Override stealth/severity values for the initial attack.
- ``suppress_initial_logs: bool``
    Strip attack indicators from every node's logs at episode start
    so the agent has to plan a multi-step investigation.
- ``boost_adversary_adaptation: bool``
    Co-Evolution scenario: bump the adversary's adaptation counter so
    it pivots within the same episode.
- ``adaptation_counter: int``
    Explicit value to seed the adversary adaptation counter.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# ─── Internal helper ─────────────────────────────────────────────────────────


def _truthy(hooks: Dict[str, Any], key: str) -> bool:
    return bool(hooks.get(key))


# ─── Public API ──────────────────────────────────────────────────────────────


def attach_hooks(env: Any, hooks: Optional[Dict[str, Any]]) -> None:
    """Stash the scenario hook dict on the environment before reset.

    ``ImmunoOrgEnvironment.reset()`` clears ``_training_force_denials_on_isolate``
    and ``_active_scenario_hooks`` at the start of every episode, so storing
    them here gives ``apply_scenario_hooks`` a stable reference and lets
    per-step penalties (e.g. silo-breaker) read the active config.
    """
    if not hooks:
        env._active_scenario_hooks = {}
        return
    env._active_scenario_hooks = dict(hooks)


def apply_scenario_hooks(env: Any, hooks: Optional[Dict[str, Any]]) -> None:
    """Mutate the freshly-reset environment to enforce the scenario family."""
    if not hooks:
        return

    # Re-stash in case caller didn't use attach_hooks.
    env._active_scenario_hooks = dict(hooks)

    # 1) RAG-grounding scenario — install a vector with a known mitigation.
    if _truthy(hooks, "inject_rag_best_mitigation") and env.attacks is not None:
        _swap_initial_attack(
            env,
            vector=hooks.get("attack_vector"),
            severity=hooks.get("severity"),
            stealth=hooks.get("stealth"),
        )
        # Record the gold-standard mitigation chain so reward shaping (and
        # offline analysis) can verify whether the agent followed it.
        chain = hooks.get("best_mitigation_chain") or []
        if chain:
            env._best_mitigation_chain = list(chain)

    # 2) Executive Alignment — board directive forbids any isolation/downtime.
    if _truthy(hooks, "board_uptime_no_isolate"):
        env.inject_directive(
            "BOARD DIRECTIVE: Maintain 100% uptime. Do NOT isolate any "
            "production node. Use precision mitigations only."
        )

    # 3) Silo-breaker — flip the env-level flag honored in _execute_action.
    if _truthy(hooks, "force_denials_on_isolate"):
        env._training_force_denials_on_isolate = True

    # 4) Stealth & Persistence — make the initial attack hard to surface.
    if _truthy(hooks, "stealthy_initial_attack") and env.attacks is not None:
        _boost_initial_stealth(
            env,
            stealth=hooks.get("stealth", 0.92),
            severity=hooks.get("severity", 0.45),
        )
    if _truthy(hooks, "suppress_initial_logs") and env.network is not None:
        _suppress_attack_indicators(env)

    # 5) Adaptive Defense / Co-Evolution — make the adversary pivot mid-episode.
    if _truthy(hooks, "boost_adversary_adaptation") and env.attacks is not None:
        env.attacks.adaptation_counter = max(
            int(env.attacks.adaptation_counter),
            int(hooks.get("adaptation_counter", 8)),
        )


def training_step_penalty(env: Any, action: Any) -> float:
    """Per-step shaping signal added on top of the env's own reward.

    Currently used to teach the agent that, under an active uptime
    directive, choosing ISOLATE_NODE / QUARANTINE_TRAFFIC is penalised
    even when the env permits it. This is a *training-time only* signal
    and does not run in production / inference.
    """
    hooks = getattr(env, "_active_scenario_hooks", {}) or {}
    if not hooks:
        return 0.0

    penalty = 0.0

    if _truthy(hooks, "board_uptime_no_isolate"):
        # Penalize downtime-heavy tactical actions under a strict uptime
        # directive. Use string compare to avoid hard import dependency.
        try:
            t = action.tactical_action.value if action.tactical_action else None
        except AttributeError:
            t = None
        if t in {"isolate_node", "quarantine_traffic"}:
            penalty -= 0.25

    if _truthy(hooks, "force_denials_on_isolate"):
        # Encourage the agent to pivot to strategic / org actions instead
        # of repeatedly retrying isolate against a hostile approver.
        try:
            t = action.tactical_action.value if action.tactical_action else None
        except AttributeError:
            t = None
        if t == "isolate_node":
            penalty -= 0.15

    return penalty


# ─── Hook implementations ────────────────────────────────────────────────────


def _swap_initial_attack(
    env: Any,
    *,
    vector: Optional[str],
    severity: Optional[float],
    stealth: Optional[float],
) -> None:
    """Replace the initial attack with a vector grounded in the CVE KB."""
    if not env.attacks or not env.attacks.active_attacks:
        return
    if not vector:
        return

    from immunoorg.models import AttackVector  # local import to avoid cycles

    try:
        new_vector = AttackVector(vector.lower())
    except ValueError:
        return

    atk = env.attacks.active_attacks[0]
    atk.vector = new_vector
    if severity is not None:
        atk.severity = float(severity)
    if stealth is not None:
        atk.stealth = float(stealth)

    # Refresh threat level so the observation matches the new vector.
    env._state.threat_level = atk.severity

    # Update belief-map ground truth so RAG / belief accuracy lines up.
    if env.belief_map is not None:
        env.belief_map.set_ground_truth(
            [{"vector": atk.vector.value, "target": atk.target_node}]
        )
        env._state.ground_truth_correlations = env.belief_map.ground_truth


def _boost_initial_stealth(
    env: Any,
    *,
    stealth: float,
    severity: float,
) -> None:
    """Make the first attack stealthier so single-action detection fails."""
    if not env.attacks or not env.attacks.active_attacks:
        return
    atk = env.attacks.active_attacks[0]
    atk.stealth = max(atk.stealth, float(stealth))
    atk.severity = max(0.05, float(severity))
    env._state.threat_level = atk.severity


def _suppress_attack_indicators(env: Any) -> None:
    """Strip attack indicators from logs so SCAN_LOGS returns nothing useful."""
    if not env.network:
        return
    for node in env.network.get_all_nodes():
        for log in node.logs:
            log.attack_indicator = False
            log.indicator_confidence = 0.0
