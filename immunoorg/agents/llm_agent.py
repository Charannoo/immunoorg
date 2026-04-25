"""
LLM-Powered Defender Agent
==========================
Implements a reasoning agent that utilizes RAG intelligence and 
Board Directives to autonomously manage enterprise security.
"""

from __future__ import annotations
import random
import logging
from typing import Any
from immunoorg.models import (
    ImmunoAction, ImmunoObservation, ActionType, 
    TacticalAction, StrategicAction, DiagnosticAction
)
from immunoorg.llm_client import LLMClient


class ImmunoDefenderAgent:
    """
    An autonomous agent that uses a real LLM to solve security incidents.
    It prioritizes RAG alerts and Board Directives in its decision-making.
    """

    def __init__(self, agent_id: str = "patronus-v1", seed: int | None = None, llm_provider: str = "openai"):
        self.agent_id = agent_id
        self.rng = random.Random(seed)
        self.action_history: list[ImmunoAction] = []
        self.llm = LLMClient(provider=llm_provider, fallback_to_mock=True)


    def act(self, obs: ImmunoObservation) -> ImmunoAction:
        """
        Processes the environment observation and returns an action.
        Uses a real LLM to generate the response.
        """
        # 1. Build the prompt
        prompt = self._build_prompt(obs)
        
        # 2. Call the real LLM (or mock if no API key)
        response = self.llm.generate(prompt, max_tokens=300, temperature=0.5)
        
        # 3. Parse the response into an ImmunoAction
        action = self._parse_llm_response(response, obs)
        
        self.action_history.append(action)
        return action

    def _build_prompt(self, obs: ImmunoObservation) -> str:
        """Constructs a high-fidelity prompt for the LLM."""
        prompt_lines = [
            "You are the Patronus AI, an autonomous self-healing enterprise agent.",
            f"PHASE: {obs.current_phase.value}",
            f"THREAT_LEVEL: {obs.threat_level:.2f}",
            f"STEP: {obs.step_count} | TIME: {obs.sim_time:.0f}",
            "",
            "=== BOARD DIRECTIVES ===",
            "\n".join(obs.directives) if obs.directives else "None",
            "",
            "=== RAG CVE INTELLIGENCE ===",
            "\n".join(obs.alerts) if obs.alerts else "No alerts",
            "",
            "=== NETWORK STATE ===",
            f"Visible Nodes: {len(obs.visible_nodes)} | Threats: {obs.threat_level:.2f}",
            f"Network Health: {obs.network_health_summary}",
            "",
            "TASK: Analyze directives and intelligence. Return your reasoning and chosen action.",
            "FORMAT: REASONING: <text> | ACTION: <type> | DETAIL: <action> | TARGET: <target>"
        ]
        return "\n".join(prompt_lines)


    def _parse_llm_response(self, response: str, obs: ImmunoObservation) -> ImmunoAction:
        """Parses the simulated LLM output into a structured ImmunoAction object."""
        try:
            parts = response.split(" | ")
            reasoning = parts[0].replace("REASONING: ", "").strip()
            action_type_str = parts[1].replace("ACTION: ", "").strip()
            detail = parts[2].replace("DETAIL: ", "").strip()
            target = parts[3].replace("TARGET: ", "").strip() if len(parts) > 3 else None
            
            if target == "None" or target is None:
                target = ""


            # Map string types to Enums
            if action_type_str == "TACTICAL":
                return ImmunoAction(
                    action_type=ActionType.TACTICAL,
                    tactical_action=TacticalAction(detail),
                    target=target,
                    reasoning=reasoning
                )
            elif action_type_str == "STRATEGIC":
                # Handle secondary target for strategic actions
                secondary = None
                if len(parts) > 4:
                    secondary = parts[4].replace("SECONDARY: ", "").strip()
                return ImmunoAction(
                    action_type=ActionType.STRATEGIC,
                    strategic_action=StrategicAction(detail),
                    target=target,
                    secondary_target=secondary,
                    reasoning=reasoning
                )
            elif action_type_str == "DIAGNOSTIC":
                return ImmunoAction(
                    action_type=ActionType.DIAGNOSTIC,
                    diagnostic_action=DiagnosticAction(detail),
                    target=target,
                    reasoning=reasoning
                )
            
        except Exception as e:
            logging.error(f"Failed to parse LLM response: {response}. Error: {e}")
        
        # Safe fallback
        return ImmunoAction(
            action_type=ActionType.DIAGNOSTIC,
            diagnostic_action=DiagnosticAction.QUERY_BELIEF_MAP,
            reasoning="Fallback due to parsing error.",
            target=""
        )
