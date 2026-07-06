import time

import httpx
import respx

from knowledge_ingestor.config import Config
from knowledge_ingestor.core.session import get_client


@respx.mock
async def test_get_client_throttles_requests_per_host():
    respx.get("https://example.com/a").mock(return_value=httpx.Response(200))
    respx.get("https://example.com/b").mock(return_value=httpx.Response(200))
    client = get_client(Config(min_request_delay=0.05, max_request_delay=0.05))

    start = time.monotonic()
    await client.get("https://example.com/a")
    await client.get("https://example.com/b")
    elapsed = time.monotonic() - start

    assert elapsed >= 0.04


@respx.mock
async def test_get_client_does_not_throttle_by_default():
    respx.get("https://example.com/a").mock(return_value=httpx.Response(200))
    respx.get("https://example.com/b").mock(return_value=httpx.Response(200))
    client = get_client(Config())

    start = time.monotonic()
    await client.get("https://example.com/a")
    await client.get("https://example.com/b")
    elapsed = time.monotonic() - start

    assert elapsed < 0.04
