import httpx
import respx

from knowledge_ingestor.core.cache import HtmlCache
from knowledge_ingestor.core.downloader import fetch


@respx.mock
async def test_fetch_downloads_and_caches(tmp_path):
    respx.head("https://example.com/page").mock(return_value=httpx.Response(200))
    route = respx.get("https://example.com/page").mock(
        return_value=httpx.Response(200, text="<html>hello</html>")
    )
    cache = HtmlCache(tmp_path / "cache")

    result = await fetch("https://example.com/page", cache=cache)

    assert result.status_code == 200
    assert result.content == "<html>hello</html>"
    assert result.from_cache is False
    assert route.call_count == 1


@respx.mock
async def test_fetch_uses_cache_on_second_call(tmp_path):
    respx.head("https://example.com/page").mock(return_value=httpx.Response(200))
    route = respx.get("https://example.com/page").mock(
        return_value=httpx.Response(200, text="<html>hello</html>")
    )
    cache = HtmlCache(tmp_path / "cache")

    await fetch("https://example.com/page", cache=cache)
    result = await fetch("https://example.com/page", cache=cache)

    assert result.from_cache is True
    assert result.content == "<html>hello</html>"
    assert route.call_count == 1
