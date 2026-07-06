from __future__ import annotations

import httpx

from ..config import Config
from . import throttle
from .headers import DEFAULT_HEADERS

_client: httpx.AsyncClient | None = None


def get_client(config: Config | None = None) -> httpx.AsyncClient:
    """Return the singleton AsyncClient, creating it on first use.

    config is only applied when the client is (re)created — call this with
    the run's real Config early (e.g. at the top of a pipeline stage) to
    make sure it takes effect.
    """
    global _client
    if _client is None or _client.is_closed:
        config = config or Config()
        limits = httpx.Limits(
            max_connections=config.concurrency,
            max_keepalive_connections=config.concurrency,
        )

        async def _throttle_hook(request: httpx.Request) -> None:
            await throttle.wait_for_host(
                str(request.url), config.min_request_delay, config.max_request_delay
            )

        _client = httpx.AsyncClient(
            http2=True,
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(config.timeout),
            limits=limits,
            follow_redirects=True,
            event_hooks={"request": [_throttle_hook]},
        )
    return _client


async def close_client() -> None:
    """Close the singleton AsyncClient, if open."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
