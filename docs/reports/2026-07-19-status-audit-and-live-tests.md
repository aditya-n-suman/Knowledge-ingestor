# Knowledge Ingestor v0.10.0 — Status Audit & Live Test Report

**Date:** 2026-07-19
**Scope:** Conformance audit against `AGENT_GUIDE.md` v1.0, full test-suite run, live redirect-resolution tests against real URL shorteners, and live end-to-end ingestion of real content websites and public LinkedIn posts.
**Method:** Four parallel review/test tracks against commit `65c810e` (master, clean tree) in a fresh venv (Python 3.12.4).

---

## TL;DR

The implementation honestly delivers everything the guide claims for v0.3–v0.10, the test suite is fully green (97/97, zero warnings), and **HTTP-level redirect resolution is correct** — including multi-hop chains, bit.ly, tinyurl, is.gd, youtu.be, and lnkd.in links whose destinations are fetchable. But live testing surfaced real defects: HTML-interstitial pages defeat the resolver silently, a **link-rewriting bug corrupts nearly every internal link in stored documents**, and plugin detection runs before URL resolution so shortened links bypass their plugins.

---

## 1. Conformance to AGENT_GUIDE.md (audit)

Strong overall — clean plugin/storage/AI abstractions (`plugins/base.py`, `storage/base.py`, `ai/provider.py`), no synchronous HTTP anywhere (sync libs wrapped in `asyncio.to_thread`), textbook retry (transient-only, exponential backoff, cap, jitter), 24 respx-mocked test files mirroring the src tree, and an unusually candid CHANGELOG.

### Gaps / violations, ranked by severity

1. **`Config.plugins` enable/disable toggle is a no-op.** Defined at `config/settings.py:18` and documented in README (lines 91–93), but nothing in `src` ever reads it — `find_plugin` (`plugins/registry.py:8-12`) consults only the hardcoded `_PLUGINS` list. Documented-but-unimplemented behavior.
2. **Store and Export are not pipeline stages.** Storage is done inline in the CLI (`cli/main.py:101-104`, `_persist_documents`); no `exporters/` directory or Export stage exists; the comment at `pipeline/runner.py:18-19` is stale (claims storage "lands in later milestones" though it shipped in v0.8). "Every stage should be replaceable" (guide §2) fails for the pipeline's tail.
3. **Pipeline order: Detect runs before Resolve.** `run_ingest_stage` matches plugins on the raw input URL (`pipeline/runner.py:84-89`); resolution happens later inside the generic fetch path (`core/downloader.py:28`). A shortened link (e.g. `lnkd.in/...`) pointing at a YouTube/GitHub target silently bypasses its plugin and gets generic article extraction. Guide §10 orders Resolve before Detect.
4. **Silent exception swallowing without logging** (guide §13): `extractors/article.py:92-93` (readability fallback failure hidden), `pipeline/discovery.py:102-103` (robots.txt fetch failure silently means "crawl without robots"), `core/sitemap.py:27-35` (transport / HTTP / XML-parse errors all silently return `[]`). Deliberate fallbacks, but none emit even a debug log.
5. **Plugin HTTP calls bypass the retry policy.** `with_retry` protects only the generic fetch path (`downloader.py:42`). GitHub API calls (`github.py:46-74`) and the YouTube transcript download (`youtube.py:92`) use bare `client.get`, so `Config.max_retries` never applies to plugins; their transient 5xx/429s fail immediately.
6. **Hidden global mutable state** (guide §2/§12): session singleton (`core/session.py:9`), throttle table (`core/throttle.py:8-9`), plugin list (`plugins/registry.py:5`). The session's apply-config-only-on-first-creation semantics already caused one shipped bug (CHANGELOG v0.10); the current fix (each stage must remember to call `get_client(config)` first) is convention, not design. `downloader.fetch` offers no client injection.
7. **Hardcoded values that belong in Config** (guide §15): Ollama timeout 120 s (`ai/ollama.py:44`); retry `base_delay`/`max_delay` (`core/retry.py:19-20`); transcript language `("en",)` (`plugins/youtube.py:17`).
8. **Missing `docs/` directory** (guide §4/§19) — this report creates it.
9. **No CLI tests** — `cli/main.py` (the largest module: URL-collection, override, persist logic) has zero coverage.
10. **Dead code**: `is_shortened`/`SHORTENER_DOMAINS` (`core/resolver.py:9-20`) are never called anywhere; the list also omits is.gd/youtu.be/rb.gy while including the long-dead goo.gl.
11. Minor: `links.txt` scratch input committed at repo root; `run_enrich_stage` is strictly sequential (`enrich.py:21-27`); "structured logging" is plain stdlib logging, not key-value/JSON; config is YAML-only (no TOML).

### Notable strengths

- Every feature claimed in guide §3 / CHANGELOG v0.3–v0.10 verifiably exists, including the fiddly ones: throttle attached as an httpx request event hook so it covers redirect hops (`session.py:27-38`), sitemap-index recursion with depth guard, robots.txt + max_pages/max_depth in the crawler, structured-output JSON Schemas for Ollama flashcards/links, SQLite upserts.
- Core has zero knowledge of any concrete plugin; everything normalizes to `Document`; downstream code depends on `Document` only.
- Async discipline throughout; concurrency bounded by semaphore.
- All five charter exceptions (`IngestorError`, `DownloadError`, `ExtractionError`, `PluginError`, `StorageError`) + `AIError` exist and are raised at the right sites.

---

## 2. Test suite

**97 passed, 0 failed, 0 skipped, 0 warnings** in 12.7 s (pytest 9.1.1, pytest-asyncio 1.4.0, respx 0.23.1).

Coverage gaps (no corresponding test file): `cli/main.py` (the only significant one), `core/cache.py` / `core/headers.py` / `core/progress.py` (cache exercised indirectly), `models/*`, `storage/filesystem.py` / `storage/base.py` (backends built on them are covered), `plugins/base.py`, `exceptions.py`, `logger.py`, `utils/hashing.py`.

---

## 3. Redirect resolution — live test results

Resolver under test: `resolve()` at `core/resolver.py:23` — HEAD-first with GET fallback, redirects followed by httpx (`follow_redirects=True` in `core/session.py:37`). Ground-truth shortlinks were freshly created via the TinyURL and is.gd APIs so expected destinations were known exactly. All cases ran through the project's real client (browser-like headers, HTTP/2), plus one end-to-end pass through `knowledge fetch`.

| # | Input | Expected | Actual | Verdict | Hops / Latency |
|---|-------|----------|--------|---------|----------------|
| 1 | tinyurl.com/mtnje98 | https://www.python.org/ | exact match | PASS | 1 hop, 547 ms |
| 2 | is.gd/RXuRZx | https://www.python.org/ | exact match | PASS | 1 hop, 377 ms |
| 3 | tinyurl.com/k9ubhhq | docs.python.org/3/library/asyncio.html | exact match | PASS | 1 hop, 674 ms |
| 4 | is.gd/eYt7Hj | docs.python.org/3/library/asyncio.html | exact match | PASS | 1 hop, 283 ms |
| 5 | tinyurl.com/ysfdmaox | https://example.com/?a=1&b=2 | **tinyurl.com/preview/deprecated/ysfdmaox** | **FAIL** (interstitial) | 666 ms |
| 6 | is.gd/jtcSnD | https://example.com/?a=1&b=2 | exact match (params preserved) | PASS | 1 hop, 1164 ms |
| 7 | CHAIN is.gd/fWHiqG → http://github.com | https://github.com/ | exact match | PASS | **2 hops**, 850 ms |
| 8 | CHAIN tinyurl.com/7872 → http://www.python.org | https://www.python.org/ | exact match | PASS | **2 hops**, 602 ms |
| 9 | youtu.be/dQw4w9WgXcQ | youtube.com/watch?v=dQw4w9WgXcQ | match (+`&feature=youtu.be`) | PASS | 1 hop, 5818 ms |
| 10 | http://github.com | https://github.com/ | exact match | PASS | 1 hop, 216 ms |
| 11 | bit.ly/1sNZMwL | en.wikipedia.org/wiki/Bitly | exact match | PASS | 1 hop, 851 ms |
| 12 | lnkd.in/gW5y9mq | (document behavior) | input returned unchanged; HEAD 404 → GET 404 | DOCUMENTED | 1103 ms |
| 13 | EDGE tinyurl.com/nonexistent-xyz123986 | error per charter | input returned, **no exception** | DOCUMENTED | 602 ms |
| 14 | EDGE dead host (.invalid) | DownloadError per charter | **raw `httpx.ConnectError`** propagated | DOCUMENTED | — |

Notes: is.gd and TinyURL blacklist other shorteners as destinations, so shortener→shortener chains cannot be built; the 2-hop chains (shortener → http:// → https://) prove multi-hop resolution instead. lnkd.in also intermittently serves a reCAPTCHA "Checking your browser" page with HTTP 200 — either way the resolver returns the lnkd.in URL itself. A separate live case (see §4) confirmed the resolver *does* transparently follow a valid lnkd.in redirect to its LinkedIn destination.

CLI end-to-end: `knowledge fetch` on is.gd/youtu.be/dead-shortlink showed correct resolution in the results table and a properly logged `DownloadError` (from `core/downloader.py:44`) for the dead link.

### Resolver defects found

1. **HTML interstitials defeat resolution** (`resolver.py:23-32`): resolution is HTTP-Location-only — no meta-refresh/JS/HTML handling. TinyURL's `preview/deprecated` interstitial (HTTP 200, no Location) is returned as the "resolved" URL. Verified trigger: the project's own `Accept: text/html` header (`core/headers.py:6-8`) — with a bare UA the same link resolves fine. Same failure class as LinkedIn's lnkd.in interstitial/captcha.
2. **Charter violation — raw httpx exceptions escape** (`resolver.py:26-31`): only the HEAD's `TransportError` is caught; the fallback GET's exceptions propagate as raw `httpx.ConnectError`, not `DownloadError`. Masked in the pipeline only by the blanket `except Exception` at `runner.py:40`.
3. **Silent 4xx pass-through**: a 404 shortlink returns the input URL with no error signal (plus a wasted duplicate GET after the HEAD 404).
4. **No retry during resolution**: `resolve()` never uses `with_retry`; a transient 429/503 from a shortener yields the shortener's own URL as the "resolved" result.

**Verdict: HTTP-level redirect resolution is correct** (single-hop, multi-hop, query-param preservation, http→https, youtu.be/bit.ly/lnkd.in). It is **not robust against non-HTTP redirects** (interstitials/captchas returned silently as final URLs), and its error behavior violates the exception charter.

---

## 4. Real-site + LinkedIn ingestion — live E2E results

Run via `knowledge.exe` with a scratch `knowledge.yaml` (sqlite backend, throttle 1.0–2.5 s, concurrency 2). All reachable URLs ingested, stored, and retrievable via `knowledge search`, with zero crashes.

| URL | Outcome | Title | Quality (1–5) | Stored? |
|---|---|---|---|---|
| en.wikipedia.org/wiki/Knowledge_management | Success, 6,639 words | "Knowledge management - Wikipedia" | 3.5 — clean body, but sidebar-table artifact, edit-links, citation noise | Yes |
| martinfowler.com/articles/is-quality-worth-cost.html | Success, 2,817 words | "Is High Quality Software Worth the Cost?" | 4.5 — near-perfect | Yes |
| bbc.com/news/articles/c0jygjezvlwo | Success, 2,245 words | correct H1 | 5 — zero boilerplate, correct author/date | Yes |
| docs.python.org/3/library/asyncio.html | Success, 332 words | "asyncio — Asynchronous I/O" | 3 — **all headings lost** (`headings: []`), links broken, lists mangled | Yes |
| linkedin.com/posts/alindnbrg_…activity-7446939578675957760 | Success — **no authwall**; SSR guest "public_post" page (387 KB) | og:title junk ("…\| André Lindenberg \| 18 comments") | 2.5 — real post text verbatim, but comments blended in, signup-redirect links | Yes |
| linkedin.com/posts/generationkm_…activity-6954791707246800896 | Success — same guest page (103 KB) | og:title junk | 2.5 — post text OK; empty-bullet "More from this author" boilerplate | Yes |
| lnkd.in/fKpknQz | **Clean failure** — redirect followed to linkedin.com profile-activity page, LinkedIn answered **HTTP 999**; `DownloadError` logged, nothing stored, clean exit | — | — | Correctly not stored |

Storage round-trip verified two ways: direct SQLite reads (all rows, JSON fields deserialize, valid UTF-8 — the "�" seen in CLI tables is Windows-console rendering only) and `knowledge search` returning exactly the right document per query.

### Extraction-quality problems (quoted from stored content)

1. **Systematic broken link rewriting — the worst cross-site bug.** Relative/fragment hrefs are resolved against the *domain root*, dropping the page path:
   - asyncio doc: stored `[run Python coroutines](https://docs.python.org/asyncio-task.html#coroutine)` — real URL is `/3/library/asyncio-task.html`; every cross-reference on the page 404s.
   - Wikipedia: `[[1]](https://en.wikipedia.org#cite_note-1)`; Fowler TOC: `[…](https://martinfowler.com#WeAreUsedToATrade-offBetweenQualityAndCost)` — fragment anchors lose the article path.
   - Consequence: stored link graphs cannot be trusted for re-crawling or citation.
2. **HTML-entity mangling in URLs**: `action=edit§ion=1` — `&section=` was entity-decoded into `§ion=`.
3. **Boilerplate leakage** (Wikipedia): LIS sidebar rendered as a broken table, 90+ `[[edit](…)]` links, reference-list noise.
4. **Whitespace loss around inline links**: `[Peter Drucker](…)first identified…` — link text fused to the following word.
5. **Headings destroyed on docs pages**: asyncio stored with zero headings; toctree bodies dropped.
6. **List markup mangling** (asyncio): stray mid-item hyphens, e.g. `- perform - [network IO and IPC](…);`.
7. **LinkedIn-specific**: title from og:title includes author + comment count; comment thread concatenated into `content` with no delimiter after the post body; hashtag/profile links rewritten to `linkedin.com/signup/cold-join?session_redirect=…` redirects; trailing "More from this author" empty-bullet block.

### LinkedIn / authwall behavior

With the pipeline's Chrome-like desktop UA (`core/headers.py`), LinkedIn did **not** authwall the two public `/posts/` URLs — it served full SSR guest pages and the extractor recovered the genuine post text. This is current observed behavior, not a guarantee; LinkedIn's anti-bot responses vary. The profile-activity URL behind the lnkd.in short link got LinkedIn's anti-bot HTTP 999, which the pipeline handled exactly right (logged `DownloadError`, URL skipped, no junk stored). No authentication bypass was attempted.

---

## 5. Recommended fix priority

1. **Fix relative-link/fragment rewriting in the extractor** — resolve hrefs against the page URL, not the domain root (also fixes the `&section=` entity mangling if the same code path).
2. **Reorder pipeline: Resolve before Detect** (`pipeline/runner.py:84-89`) so shortened links reach the correct plugin.
3. **Harden `resolve()`**: wrap all transport errors in `DownloadError`; surface 4xx instead of silently returning the input; consider detecting known interstitial patterns (no-Location 200 from a shortener domain) and flagging non-resolution; use `with_retry`.
4. **Implement or remove the documented `plugins:` config toggle.**
5. **Preserve headings on docs-site pages** (trafilatura settings or fallback path).
6. Route plugin HTTP calls through the retry policy; add debug logging to the silent fallback `except` blocks; add CLI tests; make Store a pipeline stage and stub the Export stage; move hardcoded values (Ollama timeout, retry delays, transcript language) into `Config`.

---

*Generated from a four-track parallel review: guide-conformance audit, pytest run, live resolver tests (ground-truth shortlinks created via TinyURL/is.gd APIs), and live E2E ingestion. Test scripts and raw results were kept out of the repo (session scratchpad).*
