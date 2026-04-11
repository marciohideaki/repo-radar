"""Multi-LLM factory — supports Claude, Gemini, OpenAI and Ollama."""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider


def get_provider(provider_name: Optional[str] = None) -> Optional[LLMProvider]:
    name = (provider_name or os.getenv("LLM_PROVIDER", "claude")).lower().strip()

    if name == "claude":
        from .anthropic import AnthropicProvider
        return AnthropicProvider()
    elif name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider()
    elif name in ("openai", "codex"):
        from .openai import OpenAIProvider
        return OpenAIProvider()
    elif name == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider()
    else:
        return None


__all__ = ["get_provider", "LLMProvider"]
