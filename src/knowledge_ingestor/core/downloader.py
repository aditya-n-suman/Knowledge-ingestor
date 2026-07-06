from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DownloadError
from .cache import HtmlCache
from .resolver import resolve
from .retry import RetryPolicy, with_retry
from .session import get_client


@dataclass
class FetchResult:
    url: str
    resolved_url: str
    status_code: int
    content: str
    from_cache: bool


async def fetch(
    url: str,
    *,
    cache: HtmlCache | None = None,
    policy: RetryPolicy | None = None,
) -> FetchResult:
    """Resolve, fetch (with retry), and optionally cache the raw HTML for a URL."""
    resolved_url = await resolve(url)

    if cache is not None:
        cached = cache.get(resolved_url)
        if cached is not None:
            return FetchResult(
                url=url,
                resolved_url=resolved_url,
                status_code=200,
                content=cached,
                from_cache=True,
            )

    client = get_client()
    response = await with_retry(lambda: client.get(resolved_url), policy=policy)
    if response.status_code >= 400:
        raise DownloadError(
            f"failed to download {resolved_url}: HTTP {response.status_code}"
        )

    if cache is not None:
        cache.set(resolved_url, response.text)

    return FetchResult(
        url=url,
        resolved_url=resolved_url,
        status_code=response.status_code,
        content=response.text,
        from_cache=False,
    )
