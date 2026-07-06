import httpx
import respx

from knowledge_ingestor.core.resolver import resolve


@respx.mock
async def test_resolve_follows_redirect():
    respx.head("https://bit.ly/example").mock(
        return_value=httpx.Response(
            301, headers={"Location": "https://example.com/final"}
        )
    )
    respx.head("https://example.com/final").mock(return_value=httpx.Response(200))

    resolved = await resolve("https://bit.ly/example")

    assert resolved == "https://example.com/final"


@respx.mock
async def test_resolve_falls_back_to_get_when_head_rejected():
    respx.head("https://example.com/no-head").mock(return_value=httpx.Response(405))
    respx.get("https://example.com/no-head").mock(return_value=httpx.Response(200))

    resolved = await resolve("https://example.com/no-head")

    assert resolved == "https://example.com/no-head"
