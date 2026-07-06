import pytest

from knowledge_ingestor.ai import build_provider
from knowledge_ingestor.ai.ollama import OllamaProvider
from knowledge_ingestor.config import Config


def test_build_provider_returns_none_when_disabled():
    assert build_provider(Config()) is None


def test_build_provider_returns_ollama():
    config = Config(ai_provider="ollama", ai_model="llama3")

    provider = build_provider(config)

    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama3"


def test_build_provider_raises_for_unknown_provider():
    config = Config(ai_provider="carrier-pigeon")

    with pytest.raises(ValueError, match="carrier-pigeon"):
        build_provider(config)
