"""Claude provider via Anthropic SDK."""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def _call(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            print("  ⚠ ANTHROPIC_API_KEY not set")
            return None
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            msg = client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            print(f"  ⚠ Claude error: {e}")
            return None
