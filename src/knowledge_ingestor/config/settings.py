from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path("knowledge.yaml")


@dataclass
class Config:
    concurrency: int = 8
    timeout: float = 30.0
    max_retries: int = 3
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    plugins: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> Config:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        known_fields = {f for f in cls.__dataclass_fields__}
        kwargs = {k: v for k, v in data.items() if k in known_fields}
        if "cache_dir" in kwargs:
            kwargs["cache_dir"] = Path(kwargs["cache_dir"])
        if "output_dir" in kwargs:
            kwargs["output_dir"] = Path(kwargs["output_dir"])
        return cls(**kwargs)

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        path = path or DEFAULT_CONFIG_PATH
        if path.exists():
            return cls.from_file(path)
        return cls()
