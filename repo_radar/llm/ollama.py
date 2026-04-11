"""Ollama provider — local models, no API cost."""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")

    def _call(self, prompt: str) -> Optional[str]:
        try:
            import httpx, json
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            print(f"  ⚠ Ollama error: {e}")
            return None
