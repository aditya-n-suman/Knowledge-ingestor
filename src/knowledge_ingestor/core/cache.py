from __future__ import annotations

from pathlib import Path

from ..utils import url_digest


class HtmlCache:
    """Caches raw fetched HTML on disk, keyed by a hash of the resolved URL."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, url: str) -> Path:
        return self.directory / f"{url_digest(url)}.html"

    def get(self, url: str) -> str | None:
        path = self._path_for(url)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def set(self, url: str, content: str) -> None:
        self._path_for(url).write_text(content, encoding="utf-8")
