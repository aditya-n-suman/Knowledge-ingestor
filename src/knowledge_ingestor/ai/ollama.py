from __future__ import annotations

import json

import httpx

from ..exceptions import AIError
from ..models import Flashcard
from .provider import AIProvider

DEFAULT_BASE_URL = "http://localhost:11434"

_FLASHCARDS_SCHEMA = {
    "type": "object",
    "properties": {
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
            },
        }
    },
    "required": ["flashcards"],
}

_LINKS_SCHEMA = {
    "type": "object",
    "properties": {
        "links": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["links"],
}


class OllamaProvider(AIProvider):
    """AIProvider backed by a local Ollama server."""

    def __init__(
        self, model: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 120.0
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def summarize(self, text: str) -> str:
        prompt = (
            "Summarize the following text in 2-4 concise sentences. "
            "Respond with only the summary, no preamble.\n\n" + text
        )
        response = await self._generate(prompt)
        return response.strip()

    async def generate_flashcards(self, text: str, count: int = 5) -> list[Flashcard]:
        prompt = (
            f"Generate exactly {count} flashcards (question and answer pairs) "
            f"that test understanding of the following text.\n\n{text}"
        )
        response = await self._generate(prompt, response_format=_FLASHCARDS_SCHEMA)
        try:
            cards = json.loads(response).get("flashcards", [])
        except json.JSONDecodeError as exc:
            raise AIError(f"Ollama returned malformed flashcards JSON: {exc}") from exc
        return [
            Flashcard(question=card.get("question", ""), answer=card.get("answer", ""))
            for card in cards
        ]

    async def extract_links(self, text: str) -> list[str]:
        prompt = (
            "Extract every http:// or https:// URL mentioned in the following "
            "text, exactly as written (do not invent, complete, or modify any "
            "URL). Return only the URLs.\n\n" + text
        )
        response = await self._generate(prompt, response_format=_LINKS_SCHEMA)
        try:
            links = json.loads(response).get("links", [])
        except json.JSONDecodeError as exc:
            raise AIError(f"Ollama returned malformed links JSON: {exc}") from exc
        return [str(link) for link in links if link]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.post(
                "/api/embed", json={"model": self.model, "input": texts}
            )
        except httpx.TransportError as exc:
            raise AIError(f"failed to reach Ollama at {self.base_url}: {exc}") from exc
        if response.status_code >= 400:
            raise AIError(
                f"Ollama embeddings request failed: HTTP {response.status_code}: {response.text}"
            )
        return response.json().get("embeddings", [])

    async def _generate(self, prompt: str, response_format: dict | None = None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if response_format is not None:
            payload["format"] = response_format
        try:
            response = await self._client.post("/api/generate", json=payload)
        except httpx.TransportError as exc:
            raise AIError(f"failed to reach Ollama at {self.base_url}: {exc}") from exc
        if response.status_code >= 400:
            raise AIError(
                f"Ollama generate request failed: HTTP {response.status_code}: {response.text}"
            )
        return response.json().get("response", "")

    async def aclose(self) -> None:
        await self._client.aclose()
