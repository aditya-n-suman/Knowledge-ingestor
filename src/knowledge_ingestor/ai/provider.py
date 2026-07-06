from abc import ABC, abstractmethod

from ..models import Flashcard


class AIProvider(ABC):
    """Contract every AI provider (Ollama, OpenAI, Anthropic, ...) must implement.

    AI only operates after normalization — it never replaces deterministic
    extraction, and the rest of the pipeline never depends on a specific provider.
    """

    @abstractmethod
    async def summarize(self, text: str) -> str: ...

    @abstractmethod
    async def generate_flashcards(
        self, text: str, count: int = 5
    ) -> list[Flashcard]: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
