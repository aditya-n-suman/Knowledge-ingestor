from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
