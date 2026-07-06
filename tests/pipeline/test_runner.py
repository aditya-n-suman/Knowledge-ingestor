import httpx
import respx

from knowledge_ingestor.config import Config
from knowledge_ingestor.pipeline import run_fetch_stage


@respx.mock
async def test_run_fetch_stage_fetches_all_urls(tmp_path):
    for path in ("a", "b"):
        respx.head(f"https://example.com/{path}").mock(return_value=httpx.Response(200))
        respx.get(f"https://example.com/{path}").mock(
            return_value=httpx.Response(200, text=path)
        )

    config = Config(cache_dir=tmp_path / "cache")
    results = await run_fetch_stage(
        ["https://example.com/a", "https://example.com/b"], config
    )

    assert {r.content for r in results} == {"a", "b"}


@respx.mock
async def test_run_fetch_stage_skips_failed_urls(tmp_path):
    respx.head("https://example.com/ok").mock(return_value=httpx.Response(200))
    respx.get("https://example.com/ok").mock(
        return_value=httpx.Response(200, text="ok")
    )
    respx.head("https://example.com/broken").mock(return_value=httpx.Response(200))
    respx.get("https://example.com/broken").mock(return_value=httpx.Response(500))

    config = Config(cache_dir=tmp_path / "cache", max_retries=1)
    results = await run_fetch_stage(
        ["https://example.com/ok", "https://example.com/broken"], config
    )

    assert len(results) == 1
    assert results[0].content == "ok"
