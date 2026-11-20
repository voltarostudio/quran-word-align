"""How often `quran_word_align.detect` names the right surah and riwayah, on the dataset's reads.

  python eval/detect_eval.py [JOBS]      # writes eval/DETECT.md

The truth is mp3quran's: the read's riwayah and the surah of the file. The surah is told
from the opening, the riwayah from the whole recording.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "dataset"))

AUDIO = Path.home() / ".cache" / "quran-word-align" / "audio"
SURAHS = [1, 12, 18, 36, 55, 67, 78, 112]

_model = None


def one(job):
    global _model
    read, riwayah, surah = job
    from quran_word_align.align import Model, SAMPLE_RATE, decode
    from quran_word_align.detect import detect
    if _model is None:
        _model = Model()
    path = AUDIO / f"mp3quran-{read}" / f"{surah:03}.mp3"
    if not path.exists():
        return None
    g = detect(_model.log_probs(decode(path)))
    return {"read": read, "riwayah": riwayah, "surah": surah, "guess_surah": g.surah, "guess_riwayah": g.riwayah,
            "score": round(g.score, 3), "votes": g.votes}


def main():
    from build import RECITERS
    jobs = [(read, r, s) for read, (r, _, _) in RECITERS.items() for s in SURAHS]
    out = []
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as pool:
        for res in pool.map(one, jobs):
            if res:
                out.append(res)
                print(json.dumps(res, ensure_ascii=False), flush=True)
    (HERE / "DETECT.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    lines = ["# Telling the surah and riwayah from the audio", "",
             f"`python eval/detect_eval.py`: {len(out)} recordings of the dataset's 28 reads, surahs {', '.join(map(str, SURAHS))}, "
             "the surah told from the opening, the riwayah from the whole recording.", "",
             "The surah is what the tool uses. The riwayah is an experiment only: the riwayat share the mushaf's letters "
             "and differ in about 690 of its 325,000 letters as the model hears them (none in 41 surahs, al-Fatiha and "
             "the short surahs among them), and the model leans to Hafs, so Warsh and Qalun recordings are often taken "
             "for Hafs. \"Cannot tell\": the riwayat read the same letters in that surah. The tool asks for the riwayah.", "", "| Riwayah | Recordings | Surah right | Riwayah right | Riwayah wrong | Cannot tell |", "|---|---|---|---|---|---|"]
    for r in ("hafs", "warsh", "qalun"):
        rows = [x for x in out if x["riwayah"] == r]
        if rows:
            s = sum(x["guess_surah"] == x["surah"] for x in rows)
            w = sum(x["guess_riwayah"] == x["riwayah"] for x in rows)
            none = sum(x["guess_riwayah"] is None for x in rows)
            lines.append(f"| {r.title()} | {len(rows)} | {s} ({100 * s / len(rows):.1f}%) | {w} | {len(rows) - w - none} | {none} |")
    wrong = [x for x in out if x["guess_surah"] != x["surah"] or (x["guess_riwayah"] and x["guess_riwayah"] != x["riwayah"])]
    lines += ["", "Wrong guesses:", ""] + [f"- read {x['read']} ({x['riwayah']}), surah {x['surah']}: guessed surah {x['guess_surah']}, "
                                           f"{x['guess_riwayah']} (votes {x['votes']})" for x in wrong]
    (HERE / "DETECT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
