from __future__ import annotations

from typing import TYPE_CHECKING

from .ollama import OllamaProvider
from .provider import AIProvider

if TYPE_CHECKING:
    from ..config import Config


def build_provider(config: Config) -> AIProvider | None:
    """Build the configured AI provider, or None if AI is disabled (the default)."""
    if not config.ai_provider:
        return None
    if config.ai_provider == "ollama":
        return OllamaProvider(model=config.ai_model, base_url=config.ollama_base_url)
    raise ValueError(f"unknown AI provider: {config.ai_provider}")


__all__ = ["AIProvider", "OllamaProvider", "build_provider"]
