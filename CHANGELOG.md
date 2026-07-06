# v0.10.0

Two hardening features prompted by testing the pipeline against a real,
messy input file (LinkedIn shortlinks with label/timestamp text mixed in):

- Add `core.throttle`: a per-host request scheduler that spaces consecutive
  requests to the same host by a random `[min_request_delay,
  max_request_delay]` jitter, to avoid tripping a target site's bot/rate
  detection during bulk ingestion. Wired into the shared httpx client via
  an `event_hooks["request"]` hook (`core/session.py`), so it applies to
  every request — including each hop of a redirect chain — with no changes
  needed in `resolver.py`/`downloader.py`. New `Config.min_request_delay`/
  `max_request_delay` (default `0.0`, disabled) and `--min-delay`/
  `--max-delay` on `fetch`/`ingest`/`crawl`.
  - Fixes a latent bug as a side effect: `run_fetch_stage`/`crawl_links`/
    `discover_urls` now call `get_client(config)` explicitly before their
    first request, so the loaded `Config`'s `timeout`/`concurrency` (and now
    the delay settings) actually reach the shared client — previously every
    call site invoked `get_client()` bare, so the singleton was always built
    from `Config()` defaults regardless of `knowledge.yaml`.
- Add `AIProvider.extract_links` / `OllamaProvider.extract_links`: given
  arbitrary unstructured text, the model pulls out every URL (structured
  JSON-array output, same technique as flashcards). Add `knowledge ingest
  --extract-links`, which sends `--file`'s raw content through this instead
  of assuming one-clean-URL-per-line, so files with labels, prose, or
  trailing timestamps ingest correctly.
- Verified live: `extract_links` against the real messy `links.txt` (33
  URLs recovered correctly, including deduplicating one link that appeared
  under two different labels); the throttle's timing was confirmed against
  real `lnkd.in` requests (wall-clock matched the configured delay). Full
  redirect resolution for those specific links was still blocked by
  LinkedIn's per-IP rate limiting from earlier testing — the delay didn't
  clear an already-tripped block within one session, which is a target-site
  cooldown characteristic, not a defect in the throttle itself.

# v0.9.0

- Add the AI layer (`ai/`), scoped to this milestone's four capabilities —
  summary, flashcards, embeddings, search:
  - `AIProvider` contract (`summarize`, `generate_flashcards`, `embed`).
    AI stays optional per the guide: `Config.ai_provider` defaults to `""`,
    and every enrichment call is a no-op until a provider is configured.
  - `OllamaProvider`, the first (and currently only) implementation,
    talking to a local Ollama server. Flashcard generation uses Ollama's
    structured-output `format` (a JSON Schema) so parsing is exact rather
    than regex/markdown-scraped.
  - `Document` gains `summary`, `flashcards` (`list[Flashcard]`, new
    `models.Flashcard`), and `embedding` fields; all three storage backends
    round-trip them.
- Add `pipeline.run_enrich_stage`: populates summary/flashcards/embedding
  per Document via the configured provider, logging and skipping (not
  crashing) on a per-document `AIError` — partial enrichment survives if,
  say, embeddings fail but summarization succeeded.
- Add `pipeline.semantic_search`: cosine-similarity ranking of stored
  Documents against a query embedding.
- CLI: `knowledge ingest`/`crawl` gain `--enrich`; new
  `knowledge search <query> [--semantic]` (plain substring search by
  default, embedding-similarity ranking with `--semantic`).
- Verified live against a local Ollama instance (`qwen2.5:7b-instruct`):
  summarize and flashcard generation work end-to-end. This particular
  server wasn't started with `--embeddings`, so the embed path was only
  exercised via mocked tests — the pipeline degrades gracefully in this
  case, persisting summary/flashcards while leaving `embedding` empty
  rather than failing the whole ingest.

# v0.8.0

- Implement the storage layer (`storage/`), giving `StorageBackend` (defined
  in v0.3) its first concrete implementations:
  - `MarkdownStorage`: one `.md` file per document with a YAML frontmatter
    header (id, title, url, metadata, headings, images, links).
  - `JSONStorage`: one `.json` file per document (full `Document` as JSON).
  - `SQLiteStorage`: one `documents` table, list/dict fields JSON-encoded
    into TEXT columns; each op runs in a thread via `asyncio.to_thread`
    since `sqlite3` is synchronous.
  - `storage.filesystem.FilesystemPaths`: shared id→path convention reused
    by the two file-based backends.
  - All three backends' `search` does a case-insensitive substring match
    over title/content — deliberately simple; full-text/embeddings search
    is v0.9 scope.
- Add `storage.build_storage(config)`, a factory selecting the backend from
  the new `Config.storage_backend` field (`markdown` | `json` | `sqlite`,
  default `markdown`).
- `knowledge ingest` and `knowledge crawl` now persist each `Document`
  through the configured storage backend instead of writing Markdown files
  directly.

# v0.7.0

- Add the documentation crawler (`pipeline.discover_urls`): given a seed
  URL, prefers its `sitemap.xml` (following one level of sitemap indexes,
  `core.sitemap.discover_sitemap_urls`) and otherwise falls back to
  breadth-first, same-domain link traversal (`pipeline.crawl_links`).
- The crawler respects `robots.txt` (via `urllib.robotparser`), a
  configurable `max_depth` and `max_pages` (new `Config` fields, defaults
  2/50), and fetches each traversal depth concurrently (bounded by
  `config.concurrency`), reusing the same cache and retry policy as
  `run_fetch_stage`.
- Add `knowledge crawl <seed_url> [--depth N] [--max-pages N]`: discovers
  pages from the seed, then runs them through the existing
  `run_ingest_stage` (plugin dispatch + generic extraction) and writes
  Markdown files, same as `ingest`.

# v0.6.0

- Add the `GitHubPlugin` (`plugins/github.py`), covering three modes
  detected from the URL shape:
  - repo root / `tree/<branch>` → README, via the GitHub Contents API
    (`/repos/{owner}/{repo}/readme`), with repo metadata (description,
    topics, language, stars, license).
  - `wiki` / `wiki/<Page>` → fetches the rendered wiki page and reuses
    `extract_article` (trafilatura/readability) to pull out its content.
  - `blob/<branch>/<path>` → a single file via the Contents API
    (`/repos/{owner}/{repo}/contents/{path}`), base64-decoded.
  - Honors a `GITHUB_TOKEN` env var for the GitHub API's higher
    authenticated rate limit; unauthenticated requests still work.
- Register `GitHubPlugin` in the plugin registry alongside `YouTubePlugin`
  — `knowledge ingest` now dispatches GitHub URLs automatically.

# v0.5.0

- Add the `YouTubePlugin` (`plugins/youtube.py`), the first concrete
  implementation of the `Plugin` contract: fetches metadata/captions via
  `yt-dlp`, downloads the transcript track through the shared HTTP session,
  and normalizes title, description, transcript, and chapters into a
  `Document` (chapters become `headings`, thumbnail becomes `images`).
- Add `extractors.youtube`: pure transforms — `parse_vtt_transcript`
  (flattens WebVTT captions to deduplicated plain text) and
  `extract_chapters`.
- Add `plugins.find_plugin`, a minimal registry that dispatches a URL to the
  first matching plugin, fulfilling the guide's "adding a plugin never
  requires changing the pipeline" principle.
- Add `pipeline.run_ingest_stage`: routes each URL to a matching plugin when
  one exists, otherwise falls back to the generic fetch+extract path. The
  `knowledge ingest` CLI command now uses this instead of calling
  fetch/extract directly.
- Rename the article extractor's metadata key from `extractor` to `source`
  so all Document sources (`trafilatura`, `readability`, `youtube`) share
  one convention.

# v0.4.0

- Implement the extraction engine (`extractors/`):
  - `extractors.markdown`: HTML→Markdown conversion (`markdownify`) plus
    heading/link/image extraction from Markdown.
  - `extractors.article.extract_article`: primary extraction via
    `trafilatura`, falling back to `readability-lxml` (+ Markdown
    conversion) when trafilatura yields too little content. Raises
    `ExtractionError` when neither path produces usable content.
- Add `pipeline.run_extract_stage`: turns fetched raw HTML into normalized
  `Document`s (title, markdown content, headings, images, links, metadata).
- Add `knowledge ingest <url>... [--file links.txt]` CLI command: fetch +
  extract, write each document's Markdown to `output_dir/<id>.md`, print a
  results table (title, URL, word count, extractor used).

# v0.3.0

- Restructure `knowledge_ingestor` into the guide's proposed package layout:
  `cli/`, `core/`, `config/`, `models/`, `pipeline/`, `plugins/`, `storage/`,
  `extractors/`, `utils/`.
- Implement networking core (`core/`): singleton async `httpx` session with
  HTTP/2, centralized browser headers, URL resolver (shortlink redirect
  expansion), exponential-backoff retry for transient failures, Rich
  progress display, and on-disk raw HTML caching.
- Implement `pipeline.run_fetch_stage`: concurrency-bounded resolve+fetch
  stage over a list of URLs.
- Wire `knowledge fetch <url>... [--file links.txt]` CLI command to the
  pipeline, with a results table.
- Define the `Plugin` and `StorageBackend` contracts (section 6/8 of the
  guide) and the full `Document` model.
- Expand `exceptions.py` with `DownloadError`, `ExtractionError`,
  `PluginError`, `StorageError`.
- Add structured, verbosity-configurable logging via `RichHandler`.
- Add YAML-based `Config` loading (`knowledge.yaml`).
- Add `dev` extras (pytest, pytest-asyncio, respx, ruff) and wire CI to
  install them and run lint + tests.

## Migration notes

- `knowledge_ingestor.cli`, `.downloader`, `.models`, `.config`, `.storage`,
  `.utils` are now packages (`cli/`, `core/downloader.py`, `models/`, etc.)
  instead of flat modules — update any direct imports.
- `sources.BaseSource` is replaced by `plugins.Plugin`, matching the guide's
  `can_handle`/`fetch`/`extract`/`normalize` interface.

# Iteration 2
- Modern project structure
