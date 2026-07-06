from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from ..exceptions import DownloadError
from ..logger import logger

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0


async def with_retry(
    request: Callable[[], Awaitable[httpx.Response]],
    policy: RetryPolicy | None = None,
) -> httpx.Response:
    """Run an async HTTP request, retrying transient failures with exponential backoff."""
    policy = policy or RetryPolicy()
    attempt = 0
    while True:
        attempt += 1
        try:
            response = await request()
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            if attempt >= policy.max_attempts:
                raise DownloadError(
                    f"request failed after {attempt} attempts: {exc}"
                ) from exc
            logger.debug("transient network error (attempt %d): %s", attempt, exc)
            await _sleep(attempt, policy)
            continue

        if response.status_code not in TRANSIENT_STATUS_CODES:
            return response
        if attempt >= policy.max_attempts:
            raise DownloadError(
                f"request failed after {attempt} attempts: HTTP {response.status_code}"
            )
        logger.debug("transient HTTP %d (attempt %d)", response.status_code, attempt)
        await _sleep(attempt, policy)


async def _sleep(attempt: int, policy: RetryPolicy) -> None:
    delay = min(policy.max_delay, policy.base_delay * (2 ** (attempt - 1)))
    delay += random.uniform(0, delay * 0.1)
    await asyncio.sleep(delay)
