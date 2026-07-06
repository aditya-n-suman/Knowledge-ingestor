import httpx
import pytest
import respx
import yt_dlp

from knowledge_ingestor.plugins.youtube import YouTubePlugin

FAKE_INFO = {
    "title": "Test Video",
    "description": "A short description.",
    "webpage_url": "https://www.youtube.com/watch?v=abc123",
    "uploader": "Some Channel",
    "duration": 42,
    "upload_date": "20260101",
    "thumbnail": "https://img.example.com/thumb.jpg",
    "chapters": [{"title": "Intro", "start_time": 0, "end_time": 10}],
    "subtitles": {
        "en": [{"ext": "vtt", "url": "https://captions.example.com/en.vtt"}],
    },
    "automatic_captions": {},
}

FAKE_VTT = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello from the transcript\n"


class _FakeYoutubeDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def extract_info(self, url, download=False):
        return FAKE_INFO


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc123", True),
        ("https://youtu.be/abc123", True),
        ("https://example.com/watch?v=abc123", False),
    ],
)
async def test_can_handle(url, expected):
    assert await YouTubePlugin().can_handle(url) == expected


@respx.mock
async def test_fetch_extract_normalize(monkeypatch):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", _FakeYoutubeDL)
    respx.get("https://captions.example.com/en.vtt").mock(
        return_value=httpx.Response(200, text=FAKE_VTT)
    )

    plugin = YouTubePlugin()
    raw = await plugin.fetch("https://www.youtube.com/watch?v=abc123")
    extracted = await plugin.extract(raw)
    document = await plugin.normalize(extracted)

    assert document.title == "Test Video"
    assert document.url == "https://www.youtube.com/watch?v=abc123"
    assert "A short description." in document.content
    assert "Hello from the transcript" in document.content
    assert document.headings == ["Intro"]
    assert document.images == ["https://img.example.com/thumb.jpg"]
    assert document.metadata["source"] == "youtube"
    assert document.metadata["uploader"] == "Some Channel"
