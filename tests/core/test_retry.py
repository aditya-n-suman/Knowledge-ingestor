import httpx
import pytest

from knowledge_ingestor.core.retry import RetryPolicy, with_retry
from knowledge_ingestor.exceptions import DownloadError


async def test_with_retry_succeeds_after_transient_failure():
    attempts = []

    async def request():
        attempts.append(1)
        if len(attempts) < 2:
            return httpx.Response(503)
        return httpx.Response(200)

    response = await with_retry(
        request, policy=RetryPolicy(max_attempts=3, base_delay=0.01)
    )

    assert response.status_code == 200
    assert len(attempts) == 2


async def test_with_retry_raises_after_exhausting_attempts():
    async def request():
        return httpx.Response(500)

    with pytest.raises(DownloadError):
        await with_retry(request, policy=RetryPolicy(max_attempts=2, base_delay=0.01))


async def test_with_retry_does_not_retry_non_transient_status():
    attempts = []

    async def request():
        attempts.append(1)
        return httpx.Response(404)

    response = await with_retry(
        request, policy=RetryPolicy(max_attempts=3, base_delay=0.01)
    )

    assert response.status_code == 404
    assert len(attempts) == 1


async def test_with_retry_raises_on_repeated_transport_error():
    async def request():
        raise httpx.ConnectError("boom")

    with pytest.raises(DownloadError):
        await with_retry(request, policy=RetryPolicy(max_attempts=2, base_delay=0.01))
