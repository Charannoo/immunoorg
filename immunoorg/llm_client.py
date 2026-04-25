"""
LLM Client
==========
Flexible wrapper for OpenAI and Anthropic APIs.
Falls back to mock if no API key is configured.
"""

from __future__ import annotations
import os
import logging
from typing import Optional

class LLMClient:
    """
    Wraps OpenAI (GPT-4o) or Anthropic (Claude 3.5) APIs.
    Falls back to mock if no API key is provided.
    """
    
    def __init__(self, provider: str = "openai", model_path: str | None = None, fallback_to_mock: bool = True):
        """
        Initialize the LLM client.
        
        Args:
            provider: "openai" or "anthropic"
            model_path: Path to trained HF weights (e.g., "username/immunoorg-patronus-rl")
            fallback_to_mock: If True and no API key found, use mock LLM
        """
        self.provider = provider.lower()
        self.model_path = model_path # Store the path to trained weights
        self.fallback_to_mock = fallback_to_mock
        self.api_key = None
        self.model = None
        self.use_mock = False

        
        if self.provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
            self.model = "gpt-4o"
            if not self.api_key:
                if fallback_to_mock:
                    logging.warning("OPENAI_API_KEY not found. Using mock LLM.")
                    self.use_mock = True
                else:
                    raise ValueError("OPENAI_API_KEY not configured")
        elif self.provider == "anthropic":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            self.model = "claude-3-5-sonnet-20241022"
            if not self.api_key:
                if fallback_to_mock:
                    logging.warning("ANTHROPIC_API_KEY not found. Using mock LLM.")
                    self.use_mock = True
                else:
                    raise ValueError("ANTHROPIC_API_KEY not configured")
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate a response from the LLM."""
        if self.use_mock:
            return self._mock_generate(prompt)
        
        if self.provider == "openai":
            return self._openai_generate(prompt, max_tokens, temperature)
        elif self.provider == "anthropic":
            return self._anthropic_generate(prompt, max_tokens, temperature)
    
    def _openai_generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using OpenAI GPT-4o."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a cybersecurity expert analyzing enterprise incidents. Respond concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            logging.warning("openai package not installed. Falling back to mock.")
            return self._mock_generate(prompt)
        except Exception as e:
            logging.error(f"OpenAI API error: {e}. Falling back to mock.")
            return self._mock_generate(prompt)
    
    def _anthropic_generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using Anthropic Claude."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system="You are a cybersecurity expert analyzing enterprise incidents. Respond concisely.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
            )
            return response.content[0].text.strip()
        except ImportError:
            logging.warning("anthropic package not installed. Falling back to mock.")
            return self._mock_generate(prompt)
        except Exception as e:
            logging.error(f"Anthropic API error: {e}. Falling back to mock.")
            return self._mock_generate(prompt)
    
    def _mock_generate(self, prompt: str) -> str:
        """Fallback mock generation."""
        # Minimal heuristic parsing to return valid format
        if "SQL Injection" in prompt or "sql_injection" in prompt.lower():
            return "REASONING: Detected SQL injection attack. Isolation is the priority response. | ACTION: TACTICAL | DETAIL: isolate_node | TARGET: node-1"
        if "Board Directive" in prompt and "availability" in prompt.lower():
            return "REASONING: Board prioritizes uptime. Using patching instead of isolation. | ACTION: TACTICAL | DETAIL: deploy_patch | TARGET: node-1"
        return "REASONING: Performing diagnostic scan for situational awareness. | ACTION: DIAGNOSTIC | DETAIL: query_belief_map | TARGET: "
