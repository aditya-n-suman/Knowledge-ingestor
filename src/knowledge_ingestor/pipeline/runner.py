from __future__ import annotations

import asyncio

from ..config import Config
from ..core import FetchResult, RetryPolicy
from ..core.cache import HtmlCache
from ..core.downloader import fetch
from ..core.progress import build_progress
from ..logger import logger

# Pipeline stages beyond resolve+fetch (detect, extract, normalize, enrich,
# store, export) land in later milestones as plugins/extractors/storage mature.


async def run_fetch_stage(
    urls: list[str], config: Config | None = None
) -> list[FetchResult]:
    """Run the resolve+fetch stage over one or more URLs, bounded by config.concurrency."""
    config = config or Config()
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
