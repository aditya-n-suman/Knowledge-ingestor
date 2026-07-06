from __future__ import annotations

import asyncio
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from ..config import Config
from ..core.cache import HtmlCache
from ..core.downloader import fetch
from ..core.retry import RetryPolicy
from ..core.session import get_client
from ..core.sitemap import discover_sitemap_urls
from ..logger import logger


async def discover_urls(seed_url: str, config: Config | None = None) -> list[str]:
    """Discover pages reachable from seed_url, via its sitemap.xml if one
    exists, otherwise via same-domain link traversal bounded by config."""
    config = config or Config()
    get_client(config)
    sitemap_urls = await discover_sitemap_urls(seed_url, limit=config.max_pages)
    if sitemap_urls:
        return sitemap_urls[: config.max_pages]
    return await crawl_links(seed_url, config)


async def crawl_links(seed_url: str, config: Config | None = None) -> list[str]:
    """Breadth-first, same-domain link traversal from seed_url, respecting
    config.max_depth, config.max_pages, and robots.txt."""
    config = config or Config()
    get_client(config)
    cache = HtmlCache(config.cache_dir)
    policy = RetryPolicy(max_attempts=config.max_retries)
    semaphore = asyncio.Semaphore(config.concurrency)

    seed_host = urlparse(seed_url).netloc
    robots = await _load_robots(seed_url)

    visited: set[str] = set()
    discovered: list[str] = []
    frontier = [seed_url]

    for depth in range(config.max_depth + 1):
        if not frontier or len(discovered) >= config.max_pages:
            break

        frontier = [
            url
            for url in dict.fromkeys(urldefrag(u)[0] for u in frontier)
            if url not in visited and (robots is None or robots.can_fetch("*", url))
        ]
        visited.update(frontier)
        if not frontier:
            continue

        async def _fetch_one(url: str):
            async with semaphore:
                try:
                    return await fetch(url, cache=cache, policy=policy)
                except Exception:
                    logger.exception("failed to fetch %s during crawl", url)
                    return None

        results = await asyncio.gather(*(_fetch_one(url) for url in frontier))

        next_frontier: list[str] = []
        for result in results:
            if result is None or len(discovered) >= config.max_pages:
                continue
            discovered.append(result.resolved_url)
            if depth < config.max_depth:
                next_frontier.extend(
                    _same_domain_links(result.content, result.resolved_url, seed_host)
                )
        frontier = next_frontier

    if len(discovered) >= config.max_pages and frontier:
        logger.info(
            "crawl stopped at max_pages=%d; more pages were reachable but not fetched",
            config.max_pages,
        )
    return discovered[: config.max_pages]


def _same_domain_links(html: str, base_url: str, host: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        absolute, _ = urldefrag(urljoin(base_url, anchor["href"]))
        if urlparse(absolute).netloc == host:
            links.append(absolute)
    return links


async def _load_robots(seed_url: str) -> RobotFileParser | None:
    parsed = urlparse(seed_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = await get_client().get(robots_url)
    except Exception:
        return None
    if response.status_code >= 400:
        return None
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser
