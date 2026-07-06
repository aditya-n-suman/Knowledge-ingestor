from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from ..core.session import get_client
from ..exceptions import PluginError
from ..extractors.youtube import extract_chapters, parse_vtt_transcript
from ..models import Document
from ..utils import url_digest
from .base import Plugin

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
TRANSCRIPT_LANGUAGES = ("en",)

_YDL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "writesubtitles": True,
    "writeautomaticsub": True,
    "subtitleslangs": list(TRANSCRIPT_LANGUAGES),
}


class YouTubePlugin(Plugin):
    async def can_handle(self, url: str) -> bool:
        return urlparse(url).netloc.lower() in YOUTUBE_HOSTS

    async def fetch(self, url: str) -> dict[str, Any]:
        def _extract_info() -> dict[str, Any]:
            with yt_dlp.YoutubeDL(_YDL_OPTIONS) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_extract_info)
        except yt_dlp.utils.DownloadError as exc:
            raise PluginError(
                f"failed to fetch YouTube metadata for {url}: {exc}"
            ) from exc

        vtt = await _fetch_transcript_vtt(info)
        return {"info": info, "vtt": vtt}

    async def extract(self, raw: dict[str, Any]) -> dict[str, Any]:
        info = raw["info"]
        return {
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "url": info.get("webpage_url", ""),
            "uploader": info.get("uploader", ""),
            "duration": info.get("duration"),
            "upload_date": info.get("upload_date"),
            "thumbnail": info.get("thumbnail"),
            "chapters": extract_chapters(info),
            "transcript": parse_vtt_transcript(raw["vtt"]) if raw["vtt"] else "",
        }

    async def normalize(self, extracted: dict[str, Any]) -> Document:
        sections = [
            part for part in (extracted["description"], extracted["transcript"]) if part
        ]
        return Document(
            id=url_digest(extracted["url"] or extracted["title"]),
            title=extracted["title"],
            url=extracted["url"],
            content="\n\n".join(sections),
            metadata={
                "source": "youtube",
                "uploader": extracted["uploader"],
                "duration": extracted["duration"],
                "upload_date": extracted["upload_date"],
                "thumbnail": extracted["thumbnail"],
            },
            headings=[
                chapter["title"]
                for chapter in extracted["chapters"]
                if chapter.get("title")
            ],
            images=[extracted["thumbnail"]] if extracted["thumbnail"] else [],
        )


async def _fetch_transcript_vtt(info: dict[str, Any]) -> str:
    track = _select_transcript_track(info)
    if track is None:
        return ""
    client = get_client()
    response = await client.get(track["url"])
    if response.status_code >= 400:
        return ""
    return response.text


def _select_transcript_track(info: dict[str, Any]) -> dict[str, Any] | None:
    subtitles = info.get("subtitles") or {}
    automatic_captions = info.get("automatic_captions") or {}
    for language in TRANSCRIPT_LANGUAGES:
        for source in (subtitles, automatic_captions):
            tracks = source.get(language) or []
            vtt_track = next(
                (track for track in tracks if track.get("ext") == "vtt"), None
            )
            if vtt_track is not None:
                return vtt_track
    return None
