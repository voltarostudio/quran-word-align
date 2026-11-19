"""quran-word-align: word timings for a Quran recitation.

  quran-word-align file AUDIO SURAH              a recording of a whole surah, of your own
  quran-word-align reads                         mp3quran.net recordings, with their ids
  quran-word-align mp3quran READ_ID [SURAH...]   align mp3quran.net recordings

Each surah is written to OUT/<surah>.json: {ayah: [[word, start_ms, end_ms, confidence], ...]}, the
words in the order heard (a word the reciter goes back to is listed again), numbered as the King Fahd
Complex's mushaf of the riwayah numbers them. --format adds csv, srt, vtt or Quran.com-style segments.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from .align import RIWAYAT, Model, align_recording, mushaf_words
from .formats import EXTENSIONS, FORMATS

API = "https://www.mp3quran.net/api/v3"
CACHE = Path.home() / ".cache" / "quran-word-align" / "audio"
USER_AGENT = "quran-word-align (github.com/voltarostudio/quran-word-align)"
# mp3quran's names of the riwayat this tool has the mushaf of.
MP3QURAN_RIWAYAT = {"حفص": "hafs", "ورش": "warsh", "قالون": "qalun"}


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


def write(out: Path, surah: int, result: dict, words, formats: list[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in formats:
        path = out / f"{surah:03}.{EXTENSIONS[name]}"
        path.write_text(FORMATS[name](surah, result, words), encoding="utf-8")
    timed = sum(len(v) for v in result.values())
    print(f"{out}/{surah:03}: {len(result)} ayahs, {timed} words")


def _riwayah_of(rewaya: str) -> str | None:
    return next((r for name, r in MP3QURAN_RIWAYAT.items() if rewaya.startswith(name)), None)


def reads() -> None:
    for read in json.loads(_get(f"{API}/ayat_timing/reads")):
        known = _riwayah_of(read.get("rewaya", "")) or "not supported"
        print(f"{read['id']:>5}  {read['name']}  ({read.get('rewaya', '')}: {known})")


def mp3quran(read_id: int, surahs: list[int], out: Path, ayah_timings: bool, formats: list[str],
             resume: bool = False) -> None:
    """Without `ayah_timings`, the ayahs are found in the recording itself, which is right also where
    mp3quran's ayah timings are not (they are off by an ayah in some surahs). With it, each ayah is
    aligned in the window of mp3quran's timing, widened by three seconds: they are cut ayah to ayah
    with no gap, and sometimes a little off."""
    read = next(r for r in json.loads(_get(f"{API}/ayat_timing/reads")) if r["id"] == read_id)
    riwayah = _riwayah_of(read.get("rewaya", ""))
    if not riwayah:
        raise SystemExit(f"{read['name']}: {read.get('rewaya')} is not one of the riwayat this tool has ({', '.join(RIWAYAT)})")
    words, model = mushaf_words(riwayah), Model()
    for surah in surahs:
        if resume and (out / f"{surah:03}.{EXTENSIONS[formats[0]]}").exists():
            continue
        try:
            audio = _download(f"{read['folder_url']}{surah:03}.mp3", CACHE / f"mp3quran-{read_id}" / f"{surah:03}.mp3")
        except urllib.error.HTTPError as e:
            print(f"{surah:03}: no recording on mp3quran.net ({e.code})")
            continue
        windows = None
        if ayah_timings:
            rows = json.loads(_get(f"{API}/ayat_timing?surah={surah}&read={read_id}"))
            windows = [(int(r["ayah"]), r["start_time"] / 1000, r["end_time"] / 1000)
                       for r in rows if int(r["ayah"]) >= 1 and (surah, int(r["ayah"])) in words]
        result = align_recording(surah, audio, words, model, windows, margin=3.0 if windows else 1.0)
        write(out, surah, result, words, formats)


def own_file(audio: Path, surah: int, riwayah: str, timings: Path | None, out: Path, margin: float,
             formats: list[str]) -> None:
    """TIMINGS, if given: [{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...], the recording's ayah timings."""
    windows = None
    if timings:
        rows = json.loads(timings.read_text(encoding="utf-8"))
        windows = [(int(r["ayah"]), r["start_ms"] / 1000, r["end_ms"] / 1000) for r in rows]
    words = mushaf_words(riwayah)
    write(out, surah, align_recording(surah, audio, words, Model(), windows, margin=margin), words, formats)


def main() -> None:
    parser = argparse.ArgumentParser(prog="quran-word-align", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, out_default):
        p.add_argument("--out", type=Path, default=out_default, help="folder to write to")
        p.add_argument("--format", default="json",
                       help=f"comma-separated: {', '.join(FORMATS)} (default: json)")

    f = sub.add_parser("file", help="align a recording of a whole surah")
    f.add_argument("audio", type=Path)
    f.add_argument("surah", type=int)
    f.add_argument("--riwayah", choices=RIWAYAT, default="hafs")
    f.add_argument("--timings", type=Path, default=None,
                   help='the recording\'s ayah timings, if it has them: [{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...]')
    f.add_argument("--margin", type=float, default=1.0, help="seconds added to each side of an ayah's window")
    common(f, Path("aligned"))
    sub.add_parser("reads", help="list mp3quran.net recordings that have ayah timings")
    m = sub.add_parser("mp3quran", help="align mp3quran.net recordings")
    m.add_argument("read", type=int, help="the recording's id, from `reads`")
    m.add_argument("surahs", type=int, nargs="*", help="surahs to align (all 114 if none)")
    m.add_argument("--ayah-timings", action="store_true",
                   help="align each ayah in the window of mp3quran's ayah timing instead of finding the ayahs")
    m.add_argument("--resume", action="store_true", help="leave out surahs already written")
    common(m, None)
    args = parser.parse_args()
    formats = [x.strip() for x in getattr(args, "format", "json").split(",") if x.strip()]
    unknown = [x for x in formats if x not in FORMATS]
    if unknown:
        parser.error(f"unknown format: {', '.join(unknown)}")
    if args.command == "reads":
        reads()
    elif args.command == "mp3quran":
        mp3quran(args.read, args.surahs or list(range(1, 115)), args.out or Path("aligned") / str(args.read),
                 args.ayah_timings, formats, args.resume)
    else:
        own_file(args.audio, args.surah, args.riwayah, args.timings, args.out, args.margin, formats)


if __name__ == "__main__":
    main()
