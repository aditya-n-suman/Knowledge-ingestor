from .base import Plugin
from .youtube import YouTubePlugin

_PLUGINS: list[Plugin] = [YouTubePlugin()]


async def find_plugin(url: str) -> Plugin | None:
    for plugin in _PLUGINS:
        if await plugin.can_handle(url):
            return plugin
    return None
