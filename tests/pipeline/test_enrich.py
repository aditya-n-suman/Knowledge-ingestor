from knowledge_ingestor.config import Config
from knowledge_ingestor.exceptions import AIError
from knowledge_ingestor.models import Document, Flashcard
from knowledge_ingestor.pipeline import enrich as enrich_module
from knowledge_ingestor.pipeline.enrich import run_enrich_stage


class _FakeProvider:
    def __init__(self):
        self.closed = False

    async def summarize(self, text: str) -> str:
        return "a summary"

    async def generate_flashcards(self, text: str, count: int = 5) -> list[Flashcard]:
        return [Flashcard(question="Q", answer="A")]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    async def aclose(self) -> None:
        self.closed = True


class _FailingProvider(_FakeProvider):
    async def summarize(self, text: str) -> str:
        raise AIError("boom")


async def test_run_enrich_stage_populates_documents(monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(enrich_module, "build_provider", lambda config: fake)
    documents = [Document(id="1", content="hello world")]

    result = await run_enrich_stage(documents, Config(ai_provider="ollama"))

    assert result[0].summary == "a summary"
    assert result[0].flashcards == [Flashcard(question="Q", answer="A")]
    assert result[0].embedding == [1.0, 0.0]
    assert fake.closed is True


async def test_run_enrich_stage_is_noop_without_provider(monkeypatch):
    monkeypatch.setattr(enrich_module, "build_provider", lambda config: None)
    documents = [Document(id="1", content="hello world")]

    result = await run_enrich_stage(documents, Config())

    assert result[0].summary == ""


async def test_run_enrich_stage_survives_provider_error(monkeypatch):
    fake = _FailingProvider()
    monkeypatch.setattr(enrich_module, "build_provider", lambda config: fake)
    documents = [Document(id="1", content="hello world")]

    result = await run_enrich_stage(documents, Config(ai_provider="ollama"))

    assert result[0].summary == ""
    assert fake.closed is True
