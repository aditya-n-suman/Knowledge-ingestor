from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

import yaml

from ..models import Document, Flashcard
from .base import StorageBackend
from .filesystem import FilesystemPaths


class MarkdownStorage(StorageBackend):
    """Stores each Document as a Markdown file with a YAML frontmatter header."""

    def __init__(self, directory: Path):
        self.paths = FilesystemPaths(directory, ".md")

    async def save(self, document: Document) -> None:
        await asyncio.to_thread(self._write, document)

    async def load(self, document_id: str) -> Document | None:
        return await asyncio.to_thread(self._read, document_id)

    async def delete(self, document_id: str) -> None:
        await asyncio.to_thread(self._delete, document_id)

    async def search(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self._search, query)

    def _write(self, document: Document) -> None:
        frontmatter = {
            "id": document.id,
            "title": document.title,
            "url": document.url,
            "metadata": document.metadata,
            "headings": document.headings,
            "images": document.images,
            "links": document.links,
            "summary": document.summary,
            "flashcards": [asdict(card) for card in document.flashcards],
            "embedding": document.embedding,
        }
        text = f"---\n{yaml.safe_dump(frontmatter, sort_keys=False)}---\n\n{document.content}"
        self.paths.path_for(document.id).write_text(text, encoding="utf-8")

    def _read(self, document_id: str) -> Document | None:
        path = self.paths.path_for(document_id)
        if not path.exists():
            return None
        return _parse(path.read_text(encoding="utf-8"))

    def _delete(self, document_id: str) -> None:
        self.paths.path_for(document_id).unlink(missing_ok=True)

    def _search(self, query: str) -> list[Document]:
        needle = query.lower()
        matches = []
        for path in self.paths.all_paths():
            document = _parse(path.read_text(encoding="utf-8"))
            if needle in document.title.lower() or needle in document.content.lower():
                matches.append(document)
        return matches


def _parse(text: str) -> Document:
    if text.startswith("---\n"):
        _, frontmatter_text, content = text.split("---\n", 2)
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    else:
        frontmatter, content = {}, text
    return Document(
        id=frontmatter.get("id", ""),
        title=frontmatter.get("title", ""),
        url=frontmatter.get("url", ""),
        content=content.lstrip("\n"),
        metadata=frontmatter.get("metadata") or {},
        headings=frontmatter.get("headings") or [],
        images=frontmatter.get("images") or [],
        links=frontmatter.get("links") or [],
        summary=frontmatter.get("summary", ""),
        flashcards=[Flashcard(**card) for card in frontmatter.get("flashcards") or []],
        embedding=frontmatter.get("embedding") or [],
    )
