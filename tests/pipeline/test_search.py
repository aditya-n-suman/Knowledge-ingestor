import pytest

from knowledge_ingestor.config import Config
from knowledge_ingestor.exceptions import AIError
from knowledge_ingestor.models import Document
from knowledge_ingestor.pipeline import search as search_module
from knowledge_ingestor.pipeline.search import semantic_search
from knowledge_ingestor.storage import MarkdownStorage


class _FakeEmbedProvider:
    def __init__(self, query_embedding: list[float]):
        self.query_embedding = query_embedding
        self.closed = False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.query_embedding]

    async def aclose(self) -> None:
        self.closed = True


async def test_semantic_search_ranks_by_similarity(tmp_path, monkeypatch):
    storage = MarkdownStorage(tmp_path / "docs")
    await storage.save(Document(id="a", title="A", content="a", embedding=[1.0, 0.0]))
    await storage.save(Document(id="b", title="B", content="b", embedding=[0.0, 1.0]))
    await storage.save(Document(id="c", title="C", content="c", embedding=[]))

    fake = _FakeEmbedProvider(query_embedding=[1.0, 0.0])
    monkeypatch.setattr(search_module, "build_provider", lambda config: fake)

    results = await semantic_search("query", storage, Config(ai_provider="ollama"))

    assert [document.id for document, _score in results] == ["a", "b"]
    assert fake.closed is True


async def test_semantic_search_requires_provider(tmp_path, monkeypatch):
    storage = MarkdownStorage(tmp_path / "docs")
    monkeypatch.setattr(search_module, "build_provider", lambda config: None)

    with pytest.raises(AIError):
        await semantic_search("query", storage, Config())
