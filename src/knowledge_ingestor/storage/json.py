from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from ..models import Document
from .base import StorageBackend
from .filesystem import FilesystemPaths


class JSONStorage(StorageBackend):
    """Stores each Document as a JSON file."""

    def __init__(self, directory: Path):
        self.paths = FilesystemPaths(directory, ".json")

    async def save(self, document: Document) -> None:
        await asyncio.to_thread(self._write, document)

    async def load(self, document_id: str) -> Document | None:
        return await asyncio.to_thread(self._read, document_id)

    async def delete(self, document_id: str) -> None:
        await asyncio.to_thread(self._delete, document_id)

    async def search(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self._search, query)

    def _write(self, document: Document) -> None:
        path = self.paths.path_for(document.id)
        path.write_text(json.dumps(asdict(document), indent=2), encoding="utf-8")

    def _read(self, document_id: str) -> Document | None:
        path = self.paths.path_for(document_id)
        if not path.exists():
            return None
        return Document(**json.loads(path.read_text(encoding="utf-8")))

    def _delete(self, document_id: str) -> None:
        self.paths.path_for(document_id).unlink(missing_ok=True)

    def _search(self, query: str) -> list[Document]:
        needle = query.lower()
        matches = []
        for path in self.paths.all_paths():
            document = Document(**json.loads(path.read_text(encoding="utf-8")))
            if needle in document.title.lower() or needle in document.content.lower():
                matches.append(document)
        return matches
