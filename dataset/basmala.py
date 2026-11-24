"""Where each reciter's own basmala is, clearest first: for apps that play it before a surah whose
recording lacks one. Nothing is cut: the place is given (surah file, start and end), and the audio
stays mp3quran's.

    python dataset/basmala.py ALIGNED AUDIO OUT.json

ALIGNED: the aligned reads (one folder per mp3quran read id); AUDIO: the mp3 cache, with a folder
mp3quran-<id> per read. A surah's own opening is heard alone, up to where its first word begins.
"""

import json
import statistics
import sys
from pathlib import Path

from quran_word_align.align import Model, basmala_at_start

# Surahs tried, in order: short openings, which most reads have. Al-Fatiha is not among them: its
# basmala is its first ayah (in Hafs), timed with the rest. At-Tawba has none.
TRIED = (112, 113, 114, 67, 36, 55, 18, 2)
CLEAR = 0.85            # mean confidence taken without trying further


def main() -> None:
    aligned, audio, out = (Path(a) for a in sys.argv[1:4])
    model, found = Model(), {}
    for folder in sorted(aligned.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not folder.name.isdigit():
            continue
        best = None
        for surah in TRIED:
            mp3, timed = audio / f"mp3quran-{folder.name}" / f"{surah:03}.mp3", folder / f"{surah:03}.json"
            if not (mp3.exists() and timed.exists()):
                continue
            first = json.loads(timed.read_text()).get("1")
            if not first:
                continue
            words = basmala_at_start(mp3, model, first[0][1] / 1000)
            if not words:
                continue
            score = statistics.mean(w[3] for w in words)
            if best is None or score > best[0]:
                best = (score, surah, words)
            if score >= CLEAR:
                break
        if best and best[0] >= CLEAR:
            score, surah, words = best
            found[folder.name] = {"surah": surah, "start_ms": words[0][1], "end_ms": words[-1][2],
                                  "confidence": round(score, 3), "words": words}
        print(folder.name, found.get(folder.name, {}).get("surah", "none"), round(best[0], 2) if best else "-", flush=True)
    out.write_text(json.dumps(found, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
