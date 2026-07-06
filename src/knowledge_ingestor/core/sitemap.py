from __future__ import annotations

from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx

from .session import get_client

_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_MAX_SITEMAP_INDEX_DEPTH = 1


async def discover_sitemap_urls(base_url: str, limit: int = 500) -> list[str]:
    """Fetch base_url's sitemap.xml (following one level of sitemap indexes)
    and return the page URLs it lists, or [] if no usable sitemap is found."""
    client = get_client()
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    return (await _fetch_sitemap_urls(client, sitemap_url, limit))[:limit]


async def _fetch_sitemap_urls(
    client: httpx.AsyncClient, sitemap_url: str, limit: int, depth: int = 0
) -> list[str]:
    try:
        response = await client.get(sitemap_url)
    except httpx.TransportError:
        return []
    if response.status_code >= 400:
        return []

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        return []

    nested_sitemaps = _texts(root, "sm:sitemap/sm:loc")
    if nested_sitemaps and depth < _MAX_SITEMAP_INDEX_DEPTH:
        urls: list[str] = []
        for nested_url in nested_sitemaps:
            if len(urls) >= limit:
                break
            urls.extend(
                await _fetch_sitemap_urls(
                    client, nested_url, limit - len(urls), depth + 1
                )
            )
        return urls

    return _texts(root, "sm:url/sm:loc")[:limit]


def _texts(root: ElementTree.Element, path: str) -> list[str]:
    return [el.text.strip() for el in root.findall(path, _NAMESPACE) if el.text]
