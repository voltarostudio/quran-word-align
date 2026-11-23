"""quran-word-align: word timings for a Quran recitation.

  quran-word-align file AUDIO [SURAH]            a recording of your own: a surah, part of one, or
                                                 several in a row (where it begins is found if not given)
  quran-word-align ayahs FOLDER                  one file per ayah, named SSSAAA.mp3 (as everyayah.com)
  quran-word-align reads                         mp3quran.net recordings, with their ids
  quran-word-align mp3quran READ_ID [SURAH...]   align mp3quran.net recordings

Each surah is written to OUT/<surah>.json: {ayah: [[word, start_ms, end_ms, confidence], ...]}, the
words in the order heard (a word the reciter goes back to is listed again), numbered as the King Fahd
Complex's mushaf of the riwayah numbers them. --format adds csv, srt, vtt or Quran.com-style segments.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import time
import urllib.error
import urllib.request

from .align import RIWAYAT, Model, Recording, align_ayahs, align_recording, follow, mushaf_words, next_words
from .detect import locate
from .formats import EXTENSIONS, FORMATS

API = "https://www.mp3quran.net/api/v3"
CACHE = Path.home() / ".cache" / "quran-word-align" / "audio"
USER_AGENT = "quran-word-align (github.com/voltarostudio/quran-word-align)"
# mp3quran's names of the riwayat this tool has the mushaf of.
# "المصحف المجود" is Hafs, recited mujawwad (slow, with repeats, which the aligner follows).
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac"}
MP3QURAN_RIWAYAT = {"حفص": "hafs", "ورش": "warsh", "قالون": "qalun", "المصحف المجود": "hafs"}


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


def _median_confidence(result: dict) -> float:
    confs = sorted(w[3] for ws in result.values() for w in ws)
    return confs[len(confs) // 2] if confs else 0.0


UNSURE = 0.4      # an ayah (or a surah run on into) whose words' median confidence is below this was not heard


def own_file(audio: Path, surah: int | None, first: int | None, riwayah: str, timings: Path | None, out: Path,
             margin: float, formats: list[str]) -> None:
    """A recording of a surah, of part of one, or of several in a row (a juz). TIMINGS, if given:
    [{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...], the recording's ayah timings (one surah).
    Without SURAH, where the recording begins is found from what is heard."""
    rec = Recording.hear(audio, Model())
    words = mushaf_words(riwayah)
    located = surah is None
    if located:
        (score, surah, ayah), *rest = locate(rec.lp)
        print(f"{audio.name}: begins at {surah}:{ayah} (letters shared {score:.2f})")
        first = max(1, ayah - 1)          # neighbouring ayahs score alike: begin one early, drop it if not heard
        if score < 0.5:
            print("  not sure: if that is wrong, give the surah: quran-word-align file AUDIO SURAH [--from-ayah N]")
    first = first or 1
    if timings:
        rows = json.loads(timings.read_text(encoding="utf-8"))
        windows = {surah: [(int(r["ayah"]), r["start_ms"] / 1000, r["end_ms"] / 1000) for r in rows]}
    else:
        windows = follow(rec, words, surah, first)
    for i, (s, found) in enumerate(windows.items()):
        result = align_ayahs(s, rec, found, words, margin, then=None if timings else next_words(s, words))
        if i == 0 and located:            # ayahs before the recording's real start
            for n in sorted(result):
                ws = result[n]
                if sorted(w[3] for w in ws)[len(ws) // 2] >= UNSURE:
                    break
                del result[n]
        if i > 0 and _median_confidence(result) < UNSURE:
            break                         # what follows the last surah is not the next surah
        write(out, s, result, words, formats)


AYAH_FILE = re.compile(r"^(\d{3})(\d{3})$")


def ayah_files(folder: Path, riwayah: str, out: Path, formats: list[str]) -> None:
    """One recording per ayah, SSSAAA.<ext> (ayah 000, a basmala on its own, left out). Each ayah's
    times are from the start of its own file."""
    words = mushaf_words(riwayah)
    model = Model()
    by_surah: dict[int, dict] = {}
    files = sorted(p for p in folder.iterdir() if AYAH_FILE.match(p.stem) and p.suffix.lower() in AUDIO_EXTENSIONS)
    for path in files:
        surah, ayah = (int(x) for x in AYAH_FILE.match(path.stem).groups())
        if ayah == 0 or (surah, ayah) not in words:
            continue
        rec = Recording.hear(path, model)
        result = align_ayahs(surah, rec, [(ayah, 0.0, rec.seconds)], words, margin=0.0)
        by_surah.setdefault(surah, {}).update(result)
    for surah, result in sorted(by_surah.items()):
        write(out, surah, dict(sorted(result.items(), key=lambda kv: int(kv[0]))), words, formats)


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
    f.add_argument("surah", type=int, nargs="?", help="the surah it begins with (found from the recording if left out)")
    f.add_argument("--from-ayah", type=int, default=None, help="the ayah it begins at (default 1)")
    f.add_argument("--riwayah", choices=RIWAYAT, default="hafs")
    f.add_argument("--timings", type=Path, default=None,
                   help='the recording\'s ayah timings, if it has them: [{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...]')
    f.add_argument("--margin", type=float, default=1.0, help="seconds added to each side of an ayah's window")
    common(f, Path("aligned"))
    y = sub.add_parser("ayahs", help="align a folder of one file per ayah, named SSSAAA.mp3 (as everyayah.com)")
    y.add_argument("folder", type=Path)
    y.add_argument("--riwayah", choices=RIWAYAT, default="hafs")
    common(y, Path("aligned"))
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
    elif args.command == "ayahs":
        ayah_files(args.folder, args.riwayah, args.out, formats)
    else:
        own_file(args.audio, args.surah, args.from_ayah, args.riwayah, args.timings, args.out, args.margin, formats)


if __name__ == "__main__":
    main()
