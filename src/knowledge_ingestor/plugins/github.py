from __future__ import annotations

import base64
import os
from typing import Any
from urllib.parse import urlparse

from ..core.session import get_client
from ..exceptions import ExtractionError, PluginError
from ..extractors.article import extract_article
from ..models import Document
from ..utils import url_digest
from .base import Plugin

API_BASE = "https://api.github.com"
GITHUB_HOSTS = {"github.com", "www.github.com"}


class GitHubPlugin(Plugin):
    """Ingests a GitHub repository's README, a wiki page, or a single doc file."""

    async def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc.lower() not in GITHUB_HOSTS:
            return False
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) < 2:
            return False
        rest = segments[2:]
        if not rest:
            return True
        if rest[0] == "tree" and len(rest) <= 2:
            return True
        if rest[0] == "wiki":
            return True
        if rest[0] == "blob" and len(rest) > 2:
            return True
        return False

    async def fetch(self, url: str) -> dict[str, Any]:
        owner, repo, rest = _parse_repo_path(url)
        client = get_client()
        headers = _api_headers()

        if not rest or rest[0] == "tree":
            repo_resp = await client.get(
                f"{API_BASE}/repos/{owner}/{repo}", headers=headers
            )
            readme_resp = await client.get(
                f"{API_BASE}/repos/{owner}/{repo}/readme", headers=headers
            )
            if repo_resp.status_code >= 400 or readme_resp.status_code >= 400:
                raise PluginError(f"failed to fetch GitHub repo {owner}/{repo}")
            return {
                "mode": "readme",
                "repo": repo_resp.json(),
                "file": readme_resp.json(),
            }

        if rest[0] == "wiki":
            wiki_url = f"https://github.com/{owner}/{repo}/wiki"
            if len(rest) > 1:
                wiki_url = f"{wiki_url}/{rest[1]}"
            response = await client.get(wiki_url)
            if response.status_code >= 400:
                raise PluginError(f"failed to fetch GitHub wiki page {wiki_url}")
            return {"mode": "wiki", "html": response.text, "url": str(response.url)}

        path = "/".join(rest[2:])
        file_resp = await client.get(
            f"{API_BASE}/repos/{owner}/{repo}/contents/{path}", headers=headers
        )
        if file_resp.status_code >= 400:
            raise PluginError(f"failed to fetch GitHub file {owner}/{repo}/{path}")
        return {"mode": "file", "file": file_resp.json()}

    async def extract(self, raw: dict[str, Any]) -> dict[str, Any]:
        mode = raw["mode"]
        if mode == "readme":
            return _extract_readme(raw)
        if mode == "wiki":
            return _extract_wiki(raw)
        return _extract_file(raw)

    async def normalize(self, extracted: dict[str, Any]) -> Document:
        return Document(
            id=url_digest(extracted["url"]),
            title=extracted["title"],
            url=extracted["url"],
            content=extracted["content"],
            metadata=extracted["metadata"],
            headings=extracted.get("headings", []),
            images=extracted.get("images", []),
            links=extracted.get("links", []),
        )


def _extract_readme(raw: dict[str, Any]) -> dict[str, Any]:
    repo = raw["repo"]
    license_info = repo.get("license") or {}
    return {
        "title": repo.get("full_name", ""),
        "url": repo.get("html_url", ""),
        "content": _decode_content(raw["file"]),
        "metadata": {
            "source": "github",
            "mode": "readme",
            "description": repo.get("description") or "",
            "topics": repo.get("topics") or [],
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count"),
            "license": license_info.get("name"),
        },
    }


def _extract_wiki(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        article = extract_article(raw["html"], raw["url"])
    except ExtractionError as exc:
        raise PluginError(
            f"failed to extract GitHub wiki page {raw['url']}: {exc}"
        ) from exc
    return {
        "title": article.title,
        "url": raw["url"],
        "content": article.markdown,
        "headings": article.headings,
        "links": article.links,
        "images": article.images,
        "metadata": {"source": "github", "mode": "wiki"},
    }


def _extract_file(raw: dict[str, Any]) -> dict[str, Any]:
    file_json = raw["file"]
    return {
        "title": file_json.get("path", file_json.get("name", "")),
        "url": file_json.get("html_url", ""),
        "content": _decode_content(file_json),
        "metadata": {"source": "github", "mode": "file"},
    }


def _parse_repo_path(url: str) -> tuple[str, str, list[str]]:
    segments = [s for s in urlparse(url).path.split("/") if s]
    if len(segments) < 2:
        raise PluginError(f"not a GitHub repository URL: {url}")
    return segments[0], segments[1], segments[2:]


def _decode_content(file_json: dict[str, Any]) -> str:
    encoded = file_json.get("content", "")
    if not encoded:
        return ""
    return base64.b64decode(encoded).decode("utf-8", errors="replace")


def _api_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
