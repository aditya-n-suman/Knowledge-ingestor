from __future__ import annotations

import httpx

from ..config import Config
from .headers import DEFAULT_HEADERS

_client: httpx.AsyncClient | None = None


def get_client(config: Config | None = None) -> httpx.AsyncClient:
    """Return the singleton AsyncClient, creating it on first use."""
    global _client
    if _client is None or _client.is_closed:
        config = config or Config()
        limits = httpx.Limits(
            max_connections=config.concurrency,
            max_keepalive_connections=config.concurrency,
        )
        _client = httpx.AsyncClient(
            http2=True,
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(config.timeout),
            limits=limits,
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    """Close the singleton AsyncClient, if open."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
