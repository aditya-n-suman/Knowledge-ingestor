from knowledge_ingestor.extractors.youtube import extract_chapters, parse_vtt_transcript

MANUAL_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.200 --> 00:00:03.360
All right, so here we are, in front of the
elephants

00:00:05.318 --> 00:00:07.974
the cool thing about these guys is that they
have really long trunks
"""

AUTO_VTT_WITH_ROLLING_DUPLICATES = """WEBVTT

1
00:00:00.000 --> 00:00:02.000
<00:00:00.160><c> hello</c><00:00:00.320><c> world</c>
hello world

2
00:00:02.000 --> 00:00:04.000
hello world
this is new
"""


def test_parse_vtt_transcript_strips_headers_and_timestamps():
    transcript = parse_vtt_transcript(MANUAL_VTT)

    assert "WEBVTT" not in transcript
    assert "-->" not in transcript
    assert "elephants" in transcript
    assert "long trunks" in transcript


def test_parse_vtt_transcript_dedupes_rolling_captions():
    transcript = parse_vtt_transcript(AUTO_VTT_WITH_ROLLING_DUPLICATES)

    assert transcript.count("hello world") == 1
    assert "this is new" in transcript
    assert "<c>" not in transcript


def test_extract_chapters():
    info = {
        "chapters": [
            {"title": "Intro", "start_time": 0, "end_time": 5},
            {"title": "Body", "start_time": 5, "end_time": 20},
        ]
    }

    chapters = extract_chapters(info)

    assert chapters == [
        {"title": "Intro", "start": 0, "end": 5},
        {"title": "Body", "start": 5, "end": 20},
    ]


def test_extract_chapters_defaults_to_empty_list():
    assert extract_chapters({}) == []
