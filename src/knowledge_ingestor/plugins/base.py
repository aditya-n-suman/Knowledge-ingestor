from abc import ABC, abstractmethod
from typing import Any

from ..models import Document


class Plugin(ABC):
    """Contract every source plugin (GitHub, YouTube, docs, ...) must implement.

    The core pipeline depends only on this interface, never on a specific plugin.
    """

    @abstractmethod
    async def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    async def fetch(self, url: str) -> Any: ...

    @abstractmethod
    async def extract(self, raw: Any) -> Any: ...

    @abstractmethod
    async def normalize(self, extracted: Any) -> Document: ...
