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
