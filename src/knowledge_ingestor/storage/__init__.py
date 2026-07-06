from __future__ import annotations

from typing import TYPE_CHECKING

from .base import StorageBackend
from .json import JSONStorage
from .markdown import MarkdownStorage
from .sqlite import SQLiteStorage

if TYPE_CHECKING:
    from ..config import Config

_BACKENDS = {
    "markdown": MarkdownStorage,
    "json": JSONStorage,
}


def build_storage(config: Config) -> StorageBackend:
    if config.storage_backend == "sqlite":
        return SQLiteStorage(config.output_dir / "knowledge.db")
    try:
        backend_cls = _BACKENDS[config.storage_backend]
    except KeyError:
        raise ValueError(f"unknown storage backend: {config.storage_backend}") from None
    return backend_cls(config.output_dir)


__all__ = [
    "StorageBackend",
    "MarkdownStorage",
    "JSONStorage",
    "SQLiteStorage",
    "build_storage",
]
