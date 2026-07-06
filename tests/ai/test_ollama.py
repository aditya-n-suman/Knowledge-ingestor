import httpx
import pytest
import respx

from knowledge_ingestor.ai.ollama import OllamaProvider
from knowledge_ingestor.exceptions import AIError


@respx.mock
async def test_summarize():
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "  A concise summary.  "})
    )
    provider = OllamaProvider(model="test-model")

    summary = await provider.summarize("Some long text.")

    assert summary == "A concise summary."
    await provider.aclose()


@respx.mock
async def test_generate_flashcards():
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(
            200,
            json={
                "response": (
                    '{"flashcards": [{"question": "Q1", "answer": "A1"}, '
                    '{"question": "Q2", "answer": "A2"}]}'
                )
            },
        )
    )
    provider = OllamaProvider(model="test-model")

    cards = await provider.generate_flashcards("Some text.", count=2)

    assert [(c.question, c.answer) for c in cards] == [("Q1", "A1"), ("Q2", "A2")]
    await provider.aclose()


@respx.mock
async def test_generate_flashcards_raises_on_malformed_json():
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "not json"})
    )
    provider = OllamaProvider(model="test-model")

    with pytest.raises(AIError):
        await provider.generate_flashcards("Some text.")
    await provider.aclose()


@respx.mock
async def test_embed():
    respx.post("http://localhost:11434/api/embed").mock(
        return_value=httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})
    )
    provider = OllamaProvider(model="test-model")

    embeddings = await provider.embed(["some text"])

    assert embeddings == [[0.1, 0.2, 0.3]]
    await provider.aclose()


@respx.mock
async def test_embed_raises_on_http_error():
    respx.post("http://localhost:11434/api/embed").mock(
        return_value=httpx.Response(500)
    )
    provider = OllamaProvider(model="test-model")

    with pytest.raises(AIError):
        await provider.embed(["some text"])
    await provider.aclose()


@respx.mock
async def test_generate_raises_on_transport_error():
    respx.post("http://localhost:11434/api/generate").mock(
        side_effect=httpx.ConnectError("boom")
    )
    provider = OllamaProvider(model="test-model")

    with pytest.raises(AIError):
        await provider.summarize("text")
    await provider.aclose()
