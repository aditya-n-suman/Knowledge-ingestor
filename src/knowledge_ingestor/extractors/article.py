from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import trafilatura
from readability import Document as ReadabilityDocument

from ..exceptions import ExtractionError
from .markdown import extract_headings, extract_images, extract_links, html_to_markdown

MIN_MARKDOWN_LENGTH = 200

_METADATA_FIELDS = (
    "title",
    "author",
    "url",
    "hostname",
    "description",
    "sitename",
    "date",
    "categories",
    "tags",
    "license",
    "language",
    "image",
    "pagetype",
)


@dataclass
class ExtractedArticle:
    title: str = ""
    markdown: str = ""
    headings: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def extract_article(html: str, url: str = "") -> ExtractedArticle:
    """Extract the main article content as Markdown, using trafilatura first
    and falling back to readability when trafilatura yields too little content."""
    article = _via_trafilatura(html, url)
    if article is None or len(article.markdown) < MIN_MARKDOWN_LENGTH:
        fallback = _via_readability(html)
        if fallback is not None and (
            article is None or len(fallback.markdown) > len(article.markdown)
        ):
            article = fallback

    if article is None or not article.markdown.strip():
        raise ExtractionError(
            f"could not extract article content from {url or '<unknown>'}"
        )
    return article


def _via_trafilatura(html: str, url: str) -> ExtractedArticle | None:
    markdown = trafilatura.extract(
        html,
        url=url or None,
        output_format="markdown",
        include_links=True,
        include_images=True,
        include_comments=False,
    )
    if not markdown:
        return None

    metadata = trafilatura.extract_metadata(html, default_url=url or None)
    metadata_dict = (
        {k: v for k, v in metadata.as_dict().items() if k in _METADATA_FIELDS}
        if metadata
        else {}
    )
    return ExtractedArticle(
        title=(metadata_dict.get("title") or ""),
        markdown=markdown,
        headings=extract_headings(markdown),
        images=extract_images(markdown),
        links=extract_links(markdown),
        metadata={"extractor": "trafilatura", **metadata_dict},
    )


def _via_readability(html: str) -> ExtractedArticle | None:
    try:
        document = ReadabilityDocument(html)
        title = document.short_title()
        summary_html = document.summary()
    except Exception:
        return None

    markdown = html_to_markdown(summary_html)
    if not markdown.strip():
        return None
    return ExtractedArticle(
        title=title or "",
        markdown=markdown,
        headings=extract_headings(markdown),
        images=extract_images(markdown),
        links=extract_links(markdown),
        metadata={"extractor": "readability"},
    )
