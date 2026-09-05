"""
Thin wrapper around the Anthropic Claude API.

Design goal: the whole pipeline must keep working end-to-end even with
NO API key configured (offline demo / grading environment) by falling
back to the deterministic rule-based engines in each agent. This module
only decides WHETHER an LLM call is possible; each agent decides what
to do if it isn't.
"""
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "claude-sonnet-4-6"


class ClaudeClient:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:  # noqa: BLE001
                logger.warning("Anthropic SDK unavailable, using fallback mode: %s", e)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> Optional[dict]:
        """Calls Claude and expects a pure-JSON response. Returns None on any failure
        so the caller can fall back to rule-based logic."""
        if not self.available:
            return None
        try:
            response = self._client.messages.create(
                model=MODEL_NAME,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            )
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                text = text.split("\n", 1)[-1] if text.lower().startswith("json") else text
            return json.loads(text)
        except Exception as e:  # noqa: BLE001
            logger.warning("Claude call failed, falling back to rule-based logic: %s", e)
            return None


claude_client = ClaudeClient()
