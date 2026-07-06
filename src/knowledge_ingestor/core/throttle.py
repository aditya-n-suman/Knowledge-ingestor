from __future__ import annotations

import asyncio
import random
import time
from urllib.parse import urlparse

_next_allowed_at: dict[str, float] = {}
_lock = asyncio.Lock()


async def wait_for_host(url: str, min_delay: float, max_delay: float) -> None:
    """Space out requests to url's host by a random delay in [min_delay,
    max_delay] seconds, to avoid tripping a target site's bot/rate-limit
    detection during bulk ingestion. A no-op when max_delay <= 0.
    """
    if max_delay <= 0:
        return
    host = urlparse(url).netloc
    async with _lock:
        now = time.monotonic()
        scheduled_at = max(now, _next_allowed_at.get(host, now))
        _next_allowed_at[host] = scheduled_at + random.uniform(min_delay, max_delay)
    wait_time = scheduled_at - now
    if wait_time > 0:
        await asyncio.sleep(wait_time)


def reset() -> None:
    """Clear throttle state; primarily for test isolation."""
    _next_allowed_at.clear()
