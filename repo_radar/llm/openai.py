"""OpenAI / Codex provider via OpenAI SDK."""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.api_key = os.getenv("OPENAI_API_KEY")

    def _call(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            print("  ⚠ OPENAI_API_KEY not set")
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            resp = client.chat.completions.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"  ⚠ OpenAI error: {e}")
            return None
