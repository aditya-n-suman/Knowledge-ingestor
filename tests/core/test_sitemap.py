import httpx
import respx

from knowledge_ingestor.core.sitemap import discover_sitemap_urls

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about/</loc></url>
</urlset>
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-a.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-b.xml</loc></sitemap>
</sitemapindex>
"""

SITEMAP_A = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a-1/</loc></url>
</urlset>
"""

SITEMAP_B = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/b-1/</loc></url>
</urlset>
"""


@respx.mock
async def test_discover_sitemap_urls_parses_urlset():
    respx.get("https://example.com/sitemap.xml").mock(
        return_value=httpx.Response(200, text=SITEMAP)
    )

    urls = await discover_sitemap_urls("https://example.com/")

    assert urls == ["https://example.com/", "https://example.com/about/"]


@respx.mock
async def test_discover_sitemap_urls_follows_sitemap_index():
    respx.get("https://example.com/sitemap.xml").mock(
        return_value=httpx.Response(200, text=SITEMAP_INDEX)
    )
    respx.get("https://example.com/sitemap-a.xml").mock(
        return_value=httpx.Response(200, text=SITEMAP_A)
    )
    respx.get("https://example.com/sitemap-b.xml").mock(
        return_value=httpx.Response(200, text=SITEMAP_B)
    )

    urls = await discover_sitemap_urls("https://example.com/")

    assert urls == ["https://example.com/a-1/", "https://example.com/b-1/"]


@respx.mock
async def test_discover_sitemap_urls_returns_empty_when_missing():
    respx.get("https://example.com/sitemap.xml").mock(return_value=httpx.Response(404))

    urls = await discover_sitemap_urls("https://example.com/")

    assert urls == []


@respx.mock
async def test_discover_sitemap_urls_respects_limit():
    respx.get("https://example.com/sitemap.xml").mock(
        return_value=httpx.Response(200, text=SITEMAP)
    )

    urls = await discover_sitemap_urls("https://example.com/", limit=1)

    assert urls == ["https://example.com/"]
