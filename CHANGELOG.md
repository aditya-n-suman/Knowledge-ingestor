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
