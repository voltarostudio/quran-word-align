"""quran-word-align: word timings for a Quran recitation.

  quran-word-align reads                         mp3quran recordings that have ayah timings
  quran-word-align mp3quran READ_ID SURAH...     align mp3quran recordings
  quran-word-align file AUDIO SURAH TIMINGS      align a recording of your own

Each surah is written to OUT/<surah>.json: {ayah: [[word, start_ms, end_ms], ...]}, the words in the
order heard (a word the reciter goes back to is listed again), numbered as the Hafs mushaf numbers
them (hafs-words.json).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.request

from .align import Model, align_recording, hafs_words

API = "https://www.mp3quran.net/api/v3"
CACHE = Path.home() / ".cache" / "quran-word-align" / "audio"
USER_AGENT = "quran-word-align (github.com/voltarostudio/quran-word-align)"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def _download(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")
        part.write_bytes(_get(url))
        part.rename(path)
        time.sleep(0.25)
    return path


def _write(out: Path, surah: int, result: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{surah:03}.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    print(f"{path}: {len(result)} ayahs")


def reads() -> None:
    for read in json.loads(_get(f"{API}/ayat_timing/reads")):
        print(f"{read['id']:>5}  {read['name']}  ({read.get('rewaya', '')})")


def mp3quran(read_id: int, surahs: list[int], out: Path) -> None:
    """mp3quran's ayah timings are cut ayah to ayah with no gap and sometimes a little off, so each
    window is widened by three seconds; the fillers either side take in the rest."""
    folder = next(r["folder_url"] for r in json.loads(_get(f"{API}/ayat_timing/reads")) if r["id"] == read_id)
    words, model = hafs_words(), Model()
    for surah in surahs:
        rows = json.loads(_get(f"{API}/ayat_timing?surah={surah}&read={read_id}"))
        audio = _download(f"{folder}{surah:03}.mp3", CACHE / f"mp3quran-{read_id}" / f"{surah:03}.mp3")
        windows = [(int(r["ayah"]), r["start_time"] / 1000, r["end_time"] / 1000, int(r["end_time"]))
                   for r in rows if int(r["ayah"]) >= 1 and (surah, int(r["ayah"])) in words]
        _write(out, surah, align_recording(surah, audio, windows, words, model, margin=3.0))


def own_file(audio: Path, surah: int, timings: Path, out: Path, margin: float) -> None:
    """TIMINGS: [{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...], the recording's ayah timings."""
    rows = json.loads(timings.read_text(encoding="utf-8"))
    windows = [(int(r["ayah"]), r["start_ms"] / 1000, r["end_ms"] / 1000, int(r["end_ms"])) for r in rows]
    _write(out, surah, align_recording(surah, audio, windows, hafs_words(), Model(), margin=margin))


def main() -> None:
    parser = argparse.ArgumentParser(prog="quran-word-align", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("reads", help="list mp3quran recordings that have ayah timings")
    m = sub.add_parser("mp3quran", help="align mp3quran recordings")
    m.add_argument("read", type=int, help="the recording's id, from `reads`")
    m.add_argument("surahs", type=int, nargs="*", help="surahs to align (all 114 if none)")
    m.add_argument("--out", type=Path, default=None, help="folder to write to (default: ./aligned/<read>)")
    f = sub.add_parser("file", help="align a recording of your own")
    f.add_argument("audio", type=Path)
    f.add_argument("surah", type=int)
    f.add_argument("timings", type=Path, help='JSON: [{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...]')
    f.add_argument("--out", type=Path, default=Path("aligned"))
    f.add_argument("--margin", type=float, default=1.0, help="seconds added to each side of an ayah's window")
    args = parser.parse_args()
    if args.command == "reads":
        reads()
    elif args.command == "mp3quran":
        mp3quran(args.read, args.surahs or list(range(1, 115)), args.out or Path("aligned") / str(args.read))
    else:
        own_file(args.audio, args.surah, args.timings, args.out, args.margin)


if __name__ == "__main__":
    main()
