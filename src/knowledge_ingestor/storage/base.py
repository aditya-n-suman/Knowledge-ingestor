from abc import ABC, abstractmethod

from ..models import Document


class StorageBackend(ABC):
    """Contract every storage backend (SQLite, Markdown, JSON, ...) must implement.

    Backends are interchangeable; nothing downstream depends on a specific one.
    """

    @abstractmethod
    async def save(self, document: Document) -> None: ...

    @abstractmethod
    async def load(self, document_id: str) -> Document | None: ...

    @abstractmethod
    async def delete(self, document_id: str) -> None: ...

    @abstractmethod
    async def search(self, query: str) -> list[Document]: ...
