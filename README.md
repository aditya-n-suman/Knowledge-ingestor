# Knowledge Ingestor

A general-purpose knowledge ingestion framework: fetch, normalize, store, and
export knowledge from heterogeneous sources (articles, docs, GitHub, YouTube,
PDFs, ...) through a plugin-based pipeline. See [AGENT_GUIDE.md](AGENT_GUIDE.md)
for the full architecture and roadmap.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
knowledge version
knowledge fetch https://example.com
knowledge fetch --file links.txt
knowledge ingest https://example.com
knowledge ingest https://www.youtube.com/watch?v=...
knowledge ingest https://github.com/owner/repo
knowledge ingest https://github.com/owner/repo/wiki
knowledge ingest https://github.com/owner/repo/blob/main/docs/guide.md
knowledge crawl https://docs.example.com/ --depth 2 --max-pages 50
```

`fetch` resolves each URL (following shortlink redirects), downloads it with
retry/backoff, and caches the raw HTML on disk so repeat runs are free.

`ingest` dispatches each URL to a matching plugin — YouTube (transcript,
chapters, metadata) or GitHub (README, a wiki page, or a single file) — or,
for everything else, falls back to fetch + article extraction (via
`trafilatura`, falling back to `readability` when needed). Each result is
written as Markdown to `output_dir`. Set `GITHUB_TOKEN` in the environment
to use the GitHub API's higher authenticated rate limit.

`crawl` discovers pages from a seed URL — preferring its `sitemap.xml`, and
otherwise following same-domain links up to `--depth` — then runs each
discovered URL through the same dispatch as `ingest`. It respects
`robots.txt` and stops at `--max-pages`.

## Configuration

Settings are loaded from `knowledge.yaml` in the current directory if present:

```yaml
concurrency: 8
timeout: 30
max_retries: 3
cache_dir: cache
output_dir: output
max_depth: 2
max_pages: 50
plugins:
  github: true
```

## Development

```bash
pytest
ruff check .
ruff format .
```
