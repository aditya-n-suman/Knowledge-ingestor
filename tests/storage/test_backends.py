import pytest

from knowledge_ingestor.models import Document
from knowledge_ingestor.storage.json import JSONStorage
from knowledge_ingestor.storage.markdown import MarkdownStorage
from knowledge_ingestor.storage.sqlite import SQLiteStorage


def _make_backend(name, tmp_path):
    if name == "markdown":
        return MarkdownStorage(tmp_path / "docs")
    if name == "json":
        return JSONStorage(tmp_path / "docs")
    if name == "sqlite":
        return SQLiteStorage(tmp_path / "docs.db")
    raise ValueError(name)


@pytest.fixture(params=["markdown", "json", "sqlite"])
def backend(request, tmp_path):
    return _make_backend(request.param, tmp_path)


def _sample_document() -> Document:
    return Document(
        id="doc-1",
        title="Sample Title",
        url="https://example.com/sample",
        content="This is the body of the sample document.",
        metadata={"source": "test"},
        headings=["Intro"],
        images=["https://example.com/img.png"],
        links=["https://example.com/other"],
    )


async def test_save_and_load_roundtrip(backend):
    document = _sample_document()

    await backend.save(document)
    loaded = await backend.load(document.id)

    assert loaded == document


async def test_load_missing_returns_none(backend):
    assert await backend.load("missing") is None


async def test_save_overwrites_existing(backend):
    document = _sample_document()
    await backend.save(document)

    document.title = "Updated Title"
    await backend.save(document)
    loaded = await backend.load(document.id)

    assert loaded.title == "Updated Title"


async def test_delete_removes_document(backend):
    document = _sample_document()
    await backend.save(document)

    await backend.delete(document.id)

    assert await backend.load(document.id) is None


async def test_delete_missing_is_a_noop(backend):
    await backend.delete("missing")


async def test_search_matches_title_and_content(backend):
    document = _sample_document()
    await backend.save(document)
    other = Document(id="doc-2", title="Unrelated", content="Nothing to see here.")
    await backend.save(other)

    results = await backend.search("sample")

    assert [d.id for d in results] == ["doc-1"]
