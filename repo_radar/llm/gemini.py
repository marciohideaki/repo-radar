"""Gemini provider via Google Generative AI SDK."""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self):
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.api_key = os.getenv("GEMINI_API_KEY")

    def _call(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            print("  ⚠ GEMINI_API_KEY not set")
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"  ⚠ Gemini error: {e}")
            return None
