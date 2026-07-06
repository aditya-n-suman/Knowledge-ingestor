from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .flashcard import Flashcard


@dataclass
class Document:
    id: str = ""
    title: str = ""
    url: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    headings: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    summary: str = ""
    flashcards: list[Flashcard] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)
