from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from ..models import Document
from .base import StorageBackend

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT,
    url TEXT,
    content TEXT,
    metadata TEXT,
    headings TEXT,
    images TEXT,
    links TEXT
)
"""


class SQLiteStorage(StorageBackend):
    """Stores Documents as rows in a SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(_SCHEMA)

    async def save(self, document: Document) -> None:
        await asyncio.to_thread(self._save, document)

    async def load(self, document_id: str) -> Document | None:
        return await asyncio.to_thread(self._load, document_id)

    async def delete(self, document_id: str) -> None:
        await asyncio.to_thread(self._delete, document_id)

    async def search(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self._search, query)

    def _save(self, document: Document) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO documents (id, title, url, content, metadata, headings, images, links)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, url=excluded.url, content=excluded.content,
                    metadata=excluded.metadata, headings=excluded.headings,
                    images=excluded.images, links=excluded.links
                """,
                _to_row(document),
            )

    def _load(self, document_id: str) -> Document | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT id, title, url, content, metadata, headings, images, links "
                "FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return _from_row(row) if row else None

    def _delete(self, document_id: str) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def _search(self, query: str) -> list[Document]:
        needle = f"%{query.lower()}%"
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT id, title, url, content, metadata, headings, images, links "
                "FROM documents WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?",
                (needle, needle),
            ).fetchall()
        return [_from_row(row) for row in rows]


def _to_row(document: Document) -> tuple:
    return (
        document.id,
        document.title,
        document.url,
        document.content,
        json.dumps(document.metadata),
        json.dumps(document.headings),
        json.dumps(document.images),
        json.dumps(document.links),
    )


def _from_row(row: tuple) -> Document:
    document_id, title, url, content, metadata, headings, images, links = row
    return Document(
        id=document_id,
        title=title,
        url=url,
        content=content,
        metadata=json.loads(metadata),
        headings=json.loads(headings),
        images=json.loads(images),
        links=json.loads(links),
    )
