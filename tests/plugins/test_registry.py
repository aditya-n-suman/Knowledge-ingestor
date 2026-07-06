from knowledge_ingestor.plugins import find_plugin
from knowledge_ingestor.plugins.github import GitHubPlugin
from knowledge_ingestor.plugins.youtube import YouTubePlugin


async def test_find_plugin_matches_youtube():
    plugin = await find_plugin("https://www.youtube.com/watch?v=abc123")

    assert isinstance(plugin, YouTubePlugin)


async def test_find_plugin_matches_github():
    plugin = await find_plugin("https://github.com/octocat/Hello-World")

    assert isinstance(plugin, GitHubPlugin)


async def test_find_plugin_returns_none_for_unmatched_url():
    plugin = await find_plugin("https://example.com/article")

    assert plugin is None
