import httpx
import respx

from knowledge_ingestor.config import Config
from knowledge_ingestor.pipeline.discovery import crawl_links, discover_urls

SEED_HTML = """
<html><body>
<a href="/page1">Page 1</a>
<a href="/page2">Page 2</a>
<a href="https://other.com/external">External</a>
</body></html>
"""

LEAF_HTML = "<html><body><p>Leaf page, no further links.</p></body></html>"

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://docs.example.com/from-sitemap/</loc></url>
</urlset>
"""


def _mock_page(url: str, html: str) -> None:
    respx.head(url).mock(return_value=httpx.Response(200))
    respx.get(url).mock(return_value=httpx.Response(200, text=html))


@respx.mock
async def test_crawl_links_discovers_same_domain_pages(tmp_path):
    respx.get("https://docs.example.com/robots.txt").mock(
        return_value=httpx.Response(404)
    )
    _mock_page("https://docs.example.com/", SEED_HTML)
    _mock_page("https://docs.example.com/page1", LEAF_HTML)
    _mock_page("https://docs.example.com/page2", LEAF_HTML)

    config = Config(cache_dir=tmp_path / "cache", max_depth=1, max_pages=10)
    urls = await crawl_links("https://docs.example.com/", config)

    assert set(urls) == {
        "https://docs.example.com/",
        "https://docs.example.com/page1",
        "https://docs.example.com/page2",
    }


@respx.mock
async def test_crawl_links_respects_max_depth(tmp_path):
    respx.get("https://docs.example.com/robots.txt").mock(
        return_value=httpx.Response(404)
    )
    _mock_page("https://docs.example.com/", SEED_HTML)

    config = Config(cache_dir=tmp_path / "cache", max_depth=0, max_pages=10)
    urls = await crawl_links("https://docs.example.com/", config)

    assert urls == ["https://docs.example.com/"]


@respx.mock
async def test_crawl_links_respects_robots_disallow(tmp_path):
    respx.get("https://docs.example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /page2\n")
    )
    _mock_page("https://docs.example.com/", SEED_HTML)
    _mock_page("https://docs.example.com/page1", LEAF_HTML)

    config = Config(cache_dir=tmp_path / "cache", max_depth=1, max_pages=10)
    urls = await crawl_links("https://docs.example.com/", config)

    assert "https://docs.example.com/page2" not in urls
    assert "https://docs.example.com/page1" in urls


@respx.mock
async def test_discover_urls_prefers_sitemap(tmp_path):
    respx.get("https://docs.example.com/sitemap.xml").mock(
        return_value=httpx.Response(200, text=SITEMAP)
    )

    config = Config(cache_dir=tmp_path / "cache")
    urls = await discover_urls("https://docs.example.com/", config)

    assert urls == ["https://docs.example.com/from-sitemap/"]


@respx.mock
async def test_discover_urls_falls_back_to_crawl(tmp_path):
    respx.get("https://docs.example.com/sitemap.xml").mock(
        return_value=httpx.Response(404)
    )
    respx.get("https://docs.example.com/robots.txt").mock(
        return_value=httpx.Response(404)
    )
    _mock_page("https://docs.example.com/", LEAF_HTML)

    config = Config(cache_dir=tmp_path / "cache", max_depth=0, max_pages=10)
    urls = await discover_urls("https://docs.example.com/", config)

    assert urls == ["https://docs.example.com/"]
