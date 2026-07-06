from knowledge_ingestor.core.downloader import FetchResult
from knowledge_ingestor.pipeline import run_extract_stage

REALISTIC_HTML = """
<html>
<head><title>Page Title</title></head>
<body>
<nav><a href="/">Home</a></nav>
<main>
<article>
<h1>Heading One</h1>
<p>Some intro paragraph with enough content to pass the minimum length
threshold for extraction testing purposes.</p>
<p>A closing paragraph that adds a bit more length so the extractor is
confident this is the main content block of the page and not boilerplate.</p>
</article>
</main>
<footer><p>Copyright 2026</p></footer>
</body>
</html>
"""


def test_run_extract_stage_produces_documents():
    fetch_results = [
        FetchResult(
            url="https://example.com/page",
            resolved_url="https://example.com/page",
            status_code=200,
            content=REALISTIC_HTML,
            from_cache=False,
        )
    ]

    documents = run_extract_stage(fetch_results)

    assert len(documents) == 1
    document = documents[0]
    assert document.url == "https://example.com/page"
    assert "Heading One" in document.headings
    assert document.content.strip()


def test_run_extract_stage_skips_unextractable_content():
    fetch_results = [
        FetchResult(
            url="https://example.com/empty",
            resolved_url="https://example.com/empty",
            status_code=200,
            content="<html><body></body></html>",
            from_cache=False,
        )
    ]

    documents = run_extract_stage(fetch_results)

    assert documents == []
