import re

import markdownify

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)")


def html_to_markdown(html: str) -> str:
    return markdownify.markdownify(html, heading_style="ATX").strip()


def extract_headings(markdown: str) -> list[str]:
    return [heading.strip() for heading in _HEADING_RE.findall(markdown)]


def extract_images(markdown: str) -> list[str]:
    return _IMAGE_RE.findall(markdown)


def extract_links(markdown: str) -> list[str]:
    return _LINK_RE.findall(markdown)
