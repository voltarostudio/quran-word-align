"""The ways a surah's timings can be written.

Each takes the surah's result, {ayah: [[word, start_ms, end_ms, confidence], ...]} in the order heard,
and the mushaf's words, and returns the file's text.

  json      the result as it is
  csv       one row a word: surah, ayah, word, start_ms, end_ms, confidence, text
  srt       one subtitle an ayah, its text shown while it is read
  vtt       WebVTT, one cue an ayah, with a timestamp before each word for word-by-word highlighting
  segments  Quran.com's form: {"verse_timings": [{"verse_key", "timestamp_from", "timestamp_to",
            "segments": [[word, start_ms, end_ms], ...]}]}
"""

from __future__ import annotations

import csv
import io
import json

from .align import Words


def _ayahs(result: dict):
    for ayah in sorted(result, key=int):
        if result[ayah]:
            yield int(ayah), result[ayah]


def _text(words: Words, surah: int, ayah: int, word: int) -> str:
    for i, t in words.get((surah, ayah), []):
        if i == word:
            return t
    return ""


def to_json(surah: int, result: dict, words: Words) -> str:
    return json.dumps({str(k): v for k, v in result.items()}, ensure_ascii=False, separators=(",", ":"))


def to_csv(surah: int, result: dict, words: Words) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["surah", "ayah", "word", "start_ms", "end_ms", "confidence", "text"])
    for ayah, ws in _ayahs(result):
        for word, start, end, *rest in ws:
            w.writerow([surah, ayah, word, start, end, rest[0] if rest else "", _text(words, surah, ayah, word)])
    return out.getvalue()


def _clock(ms: int, sep: str) -> str:
    h, ms = divmod(int(ms), 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def _span(ws) -> tuple[int, int]:
    return min(w[1] for w in ws), max(w[2] for w in ws)


def _ayah_text(words: Words, surah: int, ayah: int) -> str:
    return " ".join(t for _, t in words.get((surah, ayah), []))


def to_srt(surah: int, result: dict, words: Words) -> str:
    cues = []
    for i, (ayah, ws) in enumerate(_ayahs(result), 1):
        start, end = _span(ws)
        cues.append(f"{i}\n{_clock(start, ',')} --> {_clock(end, ',')}\n{_ayah_text(words, surah, ayah)} ({ayah})\n")
    return "\n".join(cues)


def to_vtt(surah: int, result: dict, words: Words) -> str:
    cues = ["WEBVTT\n"]
    for ayah, ws in _ayahs(result):
        start, end = _span(ws)
        body = []
        for i, (word, s, *_rest) in enumerate(ws):
            text = _text(words, surah, ayah, word)
            body.append(text if i == 0 else f"<{_clock(s, '.')}>{text}")
        cues.append(f"{surah}:{ayah}\n{_clock(start, '.')} --> {_clock(end, '.')}\n{' '.join(body)}\n")
    return "\n".join(cues)


def to_segments(surah: int, result: dict, words: Words) -> str:
    timings = []
    for ayah, ws in _ayahs(result):
        start, end = _span(ws)
        timings.append({"verse_key": f"{surah}:{ayah}", "timestamp_from": start, "timestamp_to": end,
                        "segments": [[w[0], w[1], w[2]] for w in ws]})
    return json.dumps({"chapter_id": surah, "verse_timings": timings}, ensure_ascii=False, separators=(",", ":"))


FORMATS = {"json": to_json, "csv": to_csv, "srt": to_srt, "vtt": to_vtt, "segments": to_segments}
EXTENSIONS = {"json": "json", "csv": "csv", "srt": "srt", "vtt": "vtt", "segments": "segments.json"}
