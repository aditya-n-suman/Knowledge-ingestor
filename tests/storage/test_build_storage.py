import pytest

from knowledge_ingestor.config import Config
from knowledge_ingestor.storage import (
    JSONStorage,
    MarkdownStorage,
    SQLiteStorage,
    build_storage,
)


@pytest.mark.parametrize(
    ("backend_name", "expected_type"),
    [
        ("markdown", MarkdownStorage),
        ("json", JSONStorage),
        ("sqlite", SQLiteStorage),
    ],
)
def test_build_storage_returns_matching_backend(tmp_path, backend_name, expected_type):
    config = Config(output_dir=tmp_path / "output", storage_backend=backend_name)

    storage = build_storage(config)

    assert isinstance(storage, expected_type)


def test_build_storage_raises_for_unknown_backend(tmp_path):
    config = Config(output_dir=tmp_path / "output", storage_backend="carrier-pigeon")

    with pytest.raises(ValueError, match="carrier-pigeon"):
        build_storage(config)
