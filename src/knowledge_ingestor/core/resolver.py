from __future__ import annotations

from urllib.parse import urlparse

import httpx

from .session import get_client

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "lnkd.in",
    "goo.gl",
    "ow.ly",
}


def is_shortened(url: str) -> bool:
    return urlparse(url).netloc.lower() in SHORTENER_DOMAINS


async def resolve(url: str, client: httpx.AsyncClient | None = None) -> str:
    """Follow redirects to return the canonical URL. Falls back to GET if HEAD is rejected."""
    client = client or get_client()
    try:
        response = await client.head(url)
        if response.status_code >= 400:
            response = await client.get(url)
    except httpx.TransportError:
        response = await client.get(url)
    return str(response.url)
