import httpx
import respx

from knowledge_ingestor.config import Config
from knowledge_ingestor.pipeline import run_ingest_stage

ARTICLE_HTML = """
<html>
<head><title>Page Title</title></head>
<body>
<main>
<article>
<h1>Heading One</h1>
<p>Some intro paragraph with enough content to pass the minimum length
threshold for extraction testing purposes.</p>
<p>A closing paragraph that adds a bit more length so the extractor is
confident this is the main content block of the page and not boilerplate.</p>
</article>
</main>
</body>
</html>
"""


@respx.mock
async def test_run_ingest_stage_routes_generic_url_through_fetch_and_extract(tmp_path):
    respx.head("https://example.com/article").mock(return_value=httpx.Response(200))
    respx.get("https://example.com/article").mock(
        return_value=httpx.Response(200, text=ARTICLE_HTML)
    )

    config = Config(cache_dir=tmp_path / "cache")
    documents = await run_ingest_stage(["https://example.com/article"], config)

    assert len(documents) == 1
    assert documents[0].url == "https://example.com/article"
    assert documents[0].metadata["source"] in {"trafilatura", "readability"}
