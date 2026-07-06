import pytest

from knowledge_ingestor.exceptions import ExtractionError
from knowledge_ingestor.extractors import article as article_module
from knowledge_ingestor.extractors.article import extract_article

REALISTIC_HTML = """
<html>
<head><title>Page Title</title></head>
<body>
<nav><a href="/">Home</a><a href="/about">About</a></nav>
<header><h1>Site Name</h1></header>
<main>
<article>
<h1>Heading One</h1>
<p>Some intro paragraph with enough content to pass the minimum length
threshold for extraction testing purposes.</p>
<h2>Sub heading</h2>
<p>More content here with a <a href="https://example.com/link">link</a> and
an image <img src="https://example.com/img.png">.</p>
<p>A closing paragraph that adds a bit more length so the extractor is
confident this is the main content block of the page and not boilerplate
navigation or footer text.</p>
</article>
</main>
<footer><p>Copyright 2026</p></footer>
</body>
</html>
"""


def test_extract_article_via_trafilatura():
    article = extract_article(REALISTIC_HTML, url="https://example.com/page")

    assert "Heading One" in article.headings
    assert "https://example.com/link" in article.links
    assert "https://example.com/img.png" in article.images
    assert article.metadata["extractor"] == "trafilatura"


def test_extract_article_falls_back_to_readability(monkeypatch):
    monkeypatch.setattr(article_module, "_via_trafilatura", lambda html, url: None)

    html = (
        "<html><head><title>Fallback Title</title></head>"
        "<body><div id='content'><h1>Fallback Heading</h1>"
        "<p>Readability should pick this content up instead of trafilatura "
        "since trafilatura has been forced to fail for this test case.</p>"
        "</div></body></html>"
    )

    article = extract_article(html, url="https://example.com/fallback")

    assert article.metadata["extractor"] == "readability"
    assert "Fallback Heading" in article.headings


def test_extract_article_raises_when_no_content_found(monkeypatch):
    monkeypatch.setattr(article_module, "_via_trafilatura", lambda html, url: None)
    monkeypatch.setattr(article_module, "_via_readability", lambda html: None)

    with pytest.raises(ExtractionError):
        extract_article("<html><body></body></html>", url="https://example.com/empty")
