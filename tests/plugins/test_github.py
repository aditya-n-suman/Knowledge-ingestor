import base64

import httpx
import pytest
import respx

from knowledge_ingestor.plugins.github import GitHubPlugin

REPO_JSON = {
    "full_name": "octocat/Hello-World",
    "html_url": "https://github.com/octocat/Hello-World",
    "description": "My first repository on GitHub!",
    "topics": ["demo"],
    "language": "Python",
    "stargazers_count": 42,
    "license": {"name": "MIT License"},
}


def _content_response(name: str, path: str, html_url: str, text: str) -> dict:
    return {
        "name": name,
        "path": path,
        "html_url": html_url,
        "encoding": "base64",
        "content": base64.b64encode(text.encode()).decode(),
    }


WIKI_HTML = """
<html><head><title>Home</title></head><body>
<main><article>
<h1>Home</h1>
<p>Welcome to the wiki. This page has enough content to satisfy the
extractor's minimum length threshold for a confident extraction result.</p>
<p>Another paragraph with a bit more detail so trafilatura is confident
this is the main content block rather than boilerplate chrome.</p>
</article></main>
</body></html>
"""


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/octocat/Hello-World", True),
        ("https://github.com/octocat/Hello-World/tree/main", True),
        ("https://github.com/octocat/Hello-World/wiki", True),
        ("https://github.com/octocat/Hello-World/wiki/Home", True),
        ("https://github.com/octocat/Hello-World/blob/main/docs/guide.md", True),
        ("https://github.com/octocat/Hello-World/issues/1", False),
        ("https://github.com/octocat/Hello-World/tree/main/docs", False),
        ("https://gitlab.com/octocat/Hello-World", False),
        ("https://github.com/octocat", False),
    ],
)
async def test_can_handle(url, expected):
    assert await GitHubPlugin().can_handle(url) == expected


@respx.mock
async def test_readme_mode():
    respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
        return_value=httpx.Response(200, json=REPO_JSON)
    )
    respx.get("https://api.github.com/repos/octocat/Hello-World/readme").mock(
        return_value=httpx.Response(
            200,
            json=_content_response(
                "README.md",
                "README.md",
                "https://github.com/octocat/Hello-World/blob/master/README.md",
                "# Hello World\n\nThis is the readme.",
            ),
        )
    )

    plugin = GitHubPlugin()
    raw = await plugin.fetch("https://github.com/octocat/Hello-World")
    extracted = await plugin.extract(raw)
    document = await plugin.normalize(extracted)

    assert document.title == "octocat/Hello-World"
    assert "This is the readme." in document.content
    assert document.metadata["source"] == "github"
    assert document.metadata["mode"] == "readme"
    assert document.metadata["stars"] == 42


@respx.mock
async def test_wiki_mode():
    respx.get("https://github.com/octocat/Hello-World/wiki/Home").mock(
        return_value=httpx.Response(200, text=WIKI_HTML)
    )

    plugin = GitHubPlugin()
    raw = await plugin.fetch("https://github.com/octocat/Hello-World/wiki/Home")
    extracted = await plugin.extract(raw)
    document = await plugin.normalize(extracted)

    assert "Welcome to the wiki" in document.content
    assert document.metadata == {"source": "github", "mode": "wiki"}


@respx.mock
async def test_file_mode():
    respx.get(
        "https://api.github.com/repos/octocat/Hello-World/contents/docs/guide.md"
    ).mock(
        return_value=httpx.Response(
            200,
            json=_content_response(
                "guide.md",
                "docs/guide.md",
                "https://github.com/octocat/Hello-World/blob/main/docs/guide.md",
                "# Guide\n\nDocs content here.",
            ),
        )
    )

    plugin = GitHubPlugin()
    raw = await plugin.fetch(
        "https://github.com/octocat/Hello-World/blob/main/docs/guide.md"
    )
    extracted = await plugin.extract(raw)
    document = await plugin.normalize(extracted)

    assert document.title == "docs/guide.md"
    assert "Docs content here." in document.content
    assert document.metadata == {"source": "github", "mode": "file"}
