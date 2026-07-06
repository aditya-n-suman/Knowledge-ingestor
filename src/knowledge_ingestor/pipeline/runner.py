from __future__ import annotations

import asyncio

from ..config import Config
from ..core import FetchResult, RetryPolicy
from ..core.cache import HtmlCache
from ..core.downloader import fetch
from ..core.progress import build_progress
from ..core.session import get_client
from ..exceptions import ExtractionError, PluginError
from ..extractors import extract_article
from ..logger import logger
from ..models import Document
from ..plugins import Plugin, find_plugin
from ..utils import url_digest

# Pipeline stages beyond resolve+fetch+extract+plugin-dispatch (enrich, store,
# export) land in later milestones as storage matures.


async def run_fetch_stage(
    urls: list[str], config: Config | None = None
) -> list[FetchResult]:
    """Run the resolve+fetch stage over one or more URLs, bounded by config.concurrency."""
    config = config or Config()
    get_client(config)
    cache = HtmlCache(config.cache_dir)
    policy = RetryPolicy(max_attempts=config.max_retries)
    semaphore = asyncio.Semaphore(config.concurrency)

    results: list[FetchResult] = []
    with build_progress() as progress:
        task_id = progress.add_task("Fetching", total=len(urls))

        async def _run(url: str) -> FetchResult | None:
            async with semaphore:
                try:
                    result = await fetch(url, cache=cache, policy=policy)
                except Exception:
                    logger.exception("failed to fetch %s", url)
                    return None
                finally:
                    progress.advance(task_id)
                return result

        fetched = await asyncio.gather(*(_run(url) for url in urls))
    results.extend(result for result in fetched if result is not None)
    return results


def run_extract_stage(fetch_results: list[FetchResult]) -> list[Document]:
    """Run the extract+normalize stage over fetched raw HTML, producing Documents."""
    documents: list[Document] = []
    for result in fetch_results:
        try:
            article = extract_article(result.content, result.resolved_url)
        except ExtractionError:
            logger.exception("failed to extract %s", result.resolved_url)
            continue
        documents.append(
            Document(
                id=url_digest(result.resolved_url),
                title=article.title,
                url=result.resolved_url,
                content=article.markdown,
                metadata=article.metadata,
                headings=article.headings,
                images=article.images,
                links=article.links,
            )
        )
    return documents


async def run_ingest_stage(
    urls: list[str], config: Config | None = None
) -> list[Document]:
    """Detect a matching plugin for each URL, dispatching to it when found,
    and falling back to the generic fetch+extract path otherwise."""
    config = config or Config()
    plugin_matches: list[tuple[str, Plugin]] = []
    generic_urls: list[str] = []
    for url in urls:
        plugin = await find_plugin(url)
        if plugin is not None:
            plugin_matches.append((url, plugin))
        else:
            generic_urls.append(url)

    documents: list[Document] = []

    async def _run_plugin(url: str, plugin: Plugin) -> Document | None:
        try:
            raw = await plugin.fetch(url)
            extracted = await plugin.extract(raw)
            return await plugin.normalize(extracted)
        except PluginError:
            logger.exception("plugin failed to ingest %s", url)
            return None

    if plugin_matches:
        plugin_documents = await asyncio.gather(
            *(_run_plugin(url, plugin) for url, plugin in plugin_matches)
        )
        documents.extend(
            document for document in plugin_documents if document is not None
        )

    if generic_urls:
        fetch_results = await run_fetch_stage(generic_urls, config)
        documents.extend(run_extract_stage(fetch_results))

    return documents
