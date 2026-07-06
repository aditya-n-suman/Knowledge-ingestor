# Knowledge Ingestor

## Engineering Charter & Agent Handoff Document

Version: 1.0

---

# 1. Project Vision

Knowledge Ingestor is **not** intended to become another web crawler.

Its objective is to become a **general-purpose knowledge ingestion framework** capable of collecting, normalizing, enriching, storing, indexing and exporting knowledge from heterogeneous sources.

Examples include:

* Articles
* Documentation websites
* GitHub repositories
* YouTube videos
* PDFs
* Markdown repositories
* Blogs
* Wikis
* Future plugins

Eventually the project should support AI-assisted summarization, embeddings, flashcards, quizzes and semantic search.

---

# 2. Guiding Principles

The project should follow these principles.

## Single Responsibility

Every module should do exactly one thing.

Avoid "god modules".

---

## Plugin First

The core should never know implementation details of a specific source.

Everything should be implemented as plugins.

For example

* GitHub plugin
* YouTube plugin
* Documentation plugin
* Medium plugin
* Reddit plugin

Adding a plugin should never require changing the ingestion pipeline.

---

## Pipeline Architecture

The system is a sequence of stages.

```
Input URL

↓

Resolve

↓

Fetch

↓

Detect

↓

Extract

↓

Normalize

↓

Enrich

↓

Store

↓

Export
```

Every stage should be replaceable.

---

## Everything becomes a Document

Every source should eventually produce a common model.

Example

```python
Document(
    id=...
    title=...
    url=...
    content=...
    metadata=...
    headings=...
    images=...
    links=...
)
```

Downstream components must depend only on Document.

Never depend on YouTube, GitHub, etc.

---

## Composition over Inheritance

Prefer dependency injection and composition.

Avoid deep inheritance hierarchies.

---

## Async First

Networking should always use asynchronous APIs.

Avoid synchronous requests.

Use:

* asyncio
* httpx.AsyncClient

---

## Testability

Networking, storage, parsing and extraction should all be independently testable.

No hidden globals.

---

# 3. Current Repository Status

Current branch

```
master
```

Current philosophy

Modern Python package.

Current package

```
src/knowledge_ingestor
```

Current implementation

v0.3 networking core implemented: async session, resolver, retry, progress,
raw HTML caching, and the resolve+fetch pipeline stage wired to the CLI.

---

# 4. Proposed Architecture

```
src/

    knowledge_ingestor/

        cli/

        core/

        plugins/

        pipeline/

        models/

        storage/

        exporters/

        extractors/

        config/

        utils/

tests/

docs/
```

---

# 5. Core Modules

## core/

Contains networking primitives.

Suggested modules

```
headers.py

http.py

resolver.py

retry.py

session.py

progress.py
```

Responsibilities

### session.py

Singleton AsyncClient

Connection pooling

Timeouts

HTTP2

Headers

Cookies

---

### resolver.py

Resolve shortened URLs

Examples

* lnkd.in
* bit.ly
* t.co
* tinyurl

Returns canonical URL.

---

### retry.py

Exponential backoff

Retry policy

Maximum attempts

Retry only transient failures.

---

### headers.py

Centralized browser headers.

No hardcoded headers elsewhere.

---

### progress.py

Rich progress display.

---

# 6. Plugin System

Every source becomes a plugin.

Structure

```
plugins/

    article/

    github/

    youtube/

    docs/

    pdf/
```

Each plugin should implement

```python
class Plugin:

    async def can_handle(url)

    async def fetch(...)

    async def extract(...)

    async def normalize(...)
```

Core never imports plugin internals.

---

# 7. Extraction Layer

Separate from plugins.

Plugins fetch.

Extractors transform.

Examples

```
extractors/

    article.py

    github.py

    markdown.py

    pdf.py

    youtube.py
```

---

# 8. Storage Layer

Storage should be backend independent.

```
storage/

    markdown.py

    sqlite.py

    json.py

    filesystem.py
```

Every backend exposes

```
save(document)

load(...)

delete(...)

search(...)
```

---

# 9. Export Layer

Future exporters

```
PDF

HTML

EPUB

Obsidian

Notion

JSON

SQLite
```

---

# 10. Pipeline

Recommended orchestration

```
Resolve URL

↓

Download

↓

Detect source

↓

Plugin fetch

↓

Extractor

↓

Normalize

↓

Store

↓

Export
```

Pipeline stages should remain independent.

---

# 11. AI Integration (Future)

AI should never replace deterministic extraction.

AI only operates after normalization.

Pipeline

```
Document

↓

Summary

↓

Flashcards

↓

Interview Questions

↓

Quiz

↓

Embeddings

↓

Knowledge Graph
```

Suggested providers

Local

* Ollama

Cloud

* OpenAI
* Anthropic
* Gemini

Must remain optional.

---

# 12. Coding Standards

Python

* Python >=3.11
* Type hints everywhere
* dataclasses
* pathlib
* asyncio
* Rich
* Typer

Avoid

* global mutable state
* circular imports
* synchronous HTTP

---

# 13. Error Handling

Never silently ignore exceptions.

Create custom exceptions.

Example

```
IngestorError

DownloadError

ExtractionError

PluginError

StorageError
```

---

# 14. Logging

Use structured logging.

Never print.

Allow configurable verbosity.

---

# 15. Configuration

Prefer YAML/TOML.

Avoid hardcoded values.

Support

* concurrency
* timeout
* retries
* cache location
* output location
* plugin enable/disable

---

# 16. Testing Strategy

Use pytest.

Target

* resolver tests
* downloader tests
* plugin tests
* storage tests
* extractor tests

Mock network whenever practical.

---

# 17. Development Workflow

Every iteration should produce

* CHANGELOG
* Migration notes
* Updated documentation
* Tests
* Commit script

One logical feature per commit.

Use Conventional Commits.

Examples

```
feat(core): implement async downloader

feat(resolver): support LinkedIn redirects

feat(extractor): add article extraction

refactor(storage): introduce storage abstraction

test(core): downloader retry tests
```

---

# 18. Milestones

## v0.1

Bootstrap

Completed

---

## v0.2

Modern package structure

Completed

---

## v0.3

Networking core

* Async HTTP
* Redirect expansion
* Retry
* Progress
* Raw HTML caching

Completed

---

## v0.4

Extraction engine

* Trafilatura
* Readability fallback
* Markdown conversion

---

## v0.5

YouTube support

* Transcript
* Chapters
* Metadata

---

## v0.6

GitHub ingestion

* README
* Wiki
* Docs

---

## v0.7

Documentation crawler

* Internal link traversal
* Depth control
* Sitemap support

---

## v0.8

Storage

* SQLite
* Markdown
* JSON

---

## v0.9

AI

* Summary
* Flashcards
* Embeddings
* Search

---

## v1.0

Stable release

---

# 19. Repository Standards

Maintain

```
README.md

CHANGELOG.md

docs/

tests/
```

Keep documentation synchronized with implementation.

---

# 20. Long-Term Goal

The end product should not merely download webpages.

It should become a reusable framework capable of ingesting knowledge from multiple sources, transforming it into a normalized representation, enriching it through optional AI components, and exporting it into formats suitable for learning, search, and long-term knowledge management.

The architecture should prioritize extensibility, maintainability, deterministic behavior, and clean separation of concerns over short-term implementation convenience.
