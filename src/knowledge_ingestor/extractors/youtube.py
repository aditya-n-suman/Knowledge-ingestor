import re
from typing import Any

_TAG_RE = re.compile(r"<[^>]+>")
_TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->")
_CUE_INDEX_RE = re.compile(r"^\d+$")
_SKIP_PREFIXES = ("Kind:", "Language:", "NOTE", "STYLE")


def parse_vtt_transcript(vtt: str) -> str:
    """Flatten a WebVTT (or SRT) caption track into plain, deduplicated text."""
    lines: list[str] = []
    previous: str | None = None
    for raw_line in vtt.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.upper().startswith("WEBVTT")
            or line.startswith(_SKIP_PREFIXES)
            or _TIMESTAMP_RE.match(line)
            or _CUE_INDEX_RE.match(line)
        ):
            continue
        text = _TAG_RE.sub("", line).strip()
        if not text or text == previous:
            continue
        lines.append(text)
        previous = text
    return "\n".join(lines)


def extract_chapters(info: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "title": chapter.get("title", ""),
            "start": chapter.get("start_time"),
            "end": chapter.get("end_time"),
        }
        for chapter in info.get("chapters") or []
    ]
