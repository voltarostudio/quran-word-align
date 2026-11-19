"""How good the timings are, measured on mp3quran.net's recordings with nothing but public data.

  python eval/evaluate.py [--jobs 4] [--audio DIR] [--out eval/RESULTS.md]

For each recording in SAMPLE (21 Hafs reciters, 4 Warsh, 3 Qalun; a spread of surahs, long and
short), the surah is aligned without ayah timings, and three things are measured:

1. **Ayahs found**: how many of the surah's ayahs were placed.
2. **Ayah starts against mp3quran's ayah timings.** mp3quran's ayah start, moved forward to where
   the voice begins (their cut often falls in the silence before), against the start we found.
   Surahs where mp3quran's timings are known not to fit the recording (listed in KNOWN_OFF, from
   the dataset's suspect-ayahs.csv) are counted apart: there we expect to differ, and we checked
   (by the model's reading at both places) that ours is the ayah.
3. **Words after a pause against the voice onset.** A word that follows half a second of quiet
   should begin where the voice comes back. This needs no reference at all.

Every word also carries a confidence; its spread is reported.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quran_word_align import align as A  # noqa: E402
from quran_word_align import cli as C  # noqa: E402

HAFS = [123, 118, 112, 53, 54, 31, 30, 92, 86, 5, 109, 4, 62, 76, 20, 217, 12, 81, 46, 60, 106]
SURAHS = [1, 12, 18, 36, 55, 67, 78, 112]
SAMPLE = ([(r, "hafs", s) for r in HAFS for s in SURAHS]
          + [(r, "warsh", s) for r in (14, 16, 80, 120) for s in (1, 36, 67, 78, 112)]
          + [(r, "qalun", s) for r in (75, 270, 208) for s in (1, 36, 67, 78, 112)])
# (read, surah) where mp3quran's ayah timings do not fit the recording: al-Shuraim's Yusuf and Idris
# Abkar's Ya-Sin (off by an ayah or two), al-Husary's al-Fatiha (the basmala counted as ayah 0),
# al-Minshawi's ar-Rahman (each ayah starts 1-2 s early, in the one before). In each, the model's
# reading at our ayah starts is the ayah's first words, and at mp3quran's it is not.
KNOWN_OFF = {(31, 12), (12, 36), (118, 1), (112, 55)}

QUIET = 30.0   # dB below the recording's loud frames: quiet
VOICE = 20.0   # dB below them: voice


def onset(db, t: int, loud: float) -> int:
    while t < len(db) and db[t] < loud - VOICE:
        t += 1
    return t


def measure(job) -> dict:
    import numpy as np
    read, riwayah, surah, audio_dir = job
    words = A.mushaf_words(riwayah)
    reads = {r["id"]: r for r in json.loads(C._get(f"{C.API}/ayat_timing/reads"))}
    audio = C._download(f"{reads[read]['folder_url']}{surah:03}.mp3", Path(audio_dir) / f"mp3quran-{read}" / f"{surah:03}.mp3")
    rows = [x for x in json.loads(C._get(f"{C.API}/ayat_timing?surah={surah}&read={read}")) if int(x["ayah"]) >= 1]
    rec = A.Recording.hear(audio, A.Model())
    found = A.find_ayahs(surah, rec, words)
    result = A.align_ayahs(surah, rec, found, words, 1.0)
    loud = float(np.percentile(rec.db, 90))
    theirs = {int(x["ayah"]): onset(rec.db, int(x["start_time"] / 1000 / A.FRAME), loud) * A.FRAME for x in rows}
    ayah_gaps = [start - theirs[a] for a, start, _ in found if a in theirs]
    pause_gaps = []
    for ws in result.values():
        for w in ws:
            t = round(w[1] / 1000 / A.FRAME)
            if 12 <= t < len(rec.db) - 15 and rec.db[t - 12:t - 3].max() < loud - QUIET:
                pause_gaps.append((t - onset(rec.db, t - 8, loud)) * A.FRAME)
    return {"read": read, "riwayah": riwayah, "surah": surah, "ayahs": sum(1 for s, _ in words if s == surah),
            "found": len(found), "known_off": (read, surah) in KNOWN_OFF, "ayah_gaps": ayah_gaps,
            "pause_gaps": pause_gaps, "confidence": [w[3] for ws in result.values() for w in ws],
            "hours": rec.seconds / 3600}


def report(rows: list[dict]) -> str:
    import numpy as np

    def share(xs, limit):
        xs = np.abs(np.array(xs))
        return f"{100 * np.mean(xs <= limit):.1f}%" if len(xs) else "—"

    lines = ["# How good the timings are", "",
             "Made by `python eval/evaluate.py`, on mp3quran.net's recordings, with no ayah timings given "
             "to the aligner. See the script for what each column means.", ""]
    lines += ["| Riwayah | Recordings | Surahs | Hours | Ayahs found | Ayah start within 0.5 s of mp3quran's | within 1 s | Words after a pause within 80 ms of the voice | Words with confidence ≥ 0.7 |",
              "|---|---|---|---|---|---|---|---|---|"]
    for riwayah in ("hafs", "warsh", "qalun"):
        g = [r for r in rows if r["riwayah"] == riwayah]
        fit = [r for r in g if not r["known_off"]]
        gaps = [x for r in fit for x in r["ayah_gaps"]]
        pauses = [x for r in g for x in r["pause_gaps"]]
        conf = np.array([x for r in g for x in r["confidence"]])
        lines.append(f"| {riwayah.capitalize()} | {len({r['read'] for r in g})} | {len(g)} | {sum(r['hours'] for r in g):.1f} | "
                     f"{sum(r['found'] for r in g):,} of {sum(r['ayahs'] for r in g):,} | {share(gaps, 0.5)} | {share(gaps, 1.0)} | "
                     f"{share(pauses, 0.08)} | {100 * np.mean(conf >= 0.7):.1f}% |")
    off = [r for r in rows if r["known_off"]]
    if off:
        gaps = [x for r in off for x in r["ayah_gaps"]]
        lines += ["", f"In the {len(off)} surahs where mp3quran's ayah timings are known to be off, our ayah starts "
                      f"are within 1 s of theirs for {share(gaps, 1.0)} of ayahs: there they are wrong, not us."]
    lines += ["", "## Each recording", "", "| Read | Riwayah | Surah | Ayahs found | Start within 1 s | Note |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['read']} | {r['riwayah']} | {r['surah']} | {r['found']}/{r['ayahs']} | {share(r['ayah_gaps'], 1.0)} | "
                     f"{'mp3quran timings off' if r['known_off'] else ''} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--audio", type=Path, default=C.CACHE, help="folder of mp3quran-<read>/<surah>.mp3 (downloaded if missing)")
    p.add_argument("--out", type=Path, default=Path(__file__).parent / "RESULTS.md")
    a = p.parse_args()
    jobs = [(r, w, s, str(a.audio)) for r, w, s in SAMPLE]
    with ProcessPoolExecutor(a.jobs) as pool:
        rows = []
        for row in pool.map(measure, jobs):
            rows.append(row)
            print(row["read"], row["riwayah"], row["surah"], f"{row['found']}/{row['ayahs']}", flush=True)
    (a.out.with_suffix(".json")).write_text(json.dumps(rows), encoding="utf-8")
    a.out.write_text(report(rows), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
