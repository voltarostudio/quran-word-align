"""Each of Basel's takes aligned word by word with quran-word-align, for al-Mu'allim to judge one word at a time.

    python align_takes.py RECORDINGS_DIR

Writes RECORDINGS_DIR/word_spans.csv: take file, surah, ayah, word, start_ms, end_ms, confidence.
The text is the dataset's Hafs words file (the tool's own copy), never typed.
"""
import csv
import sys
from pathlib import Path

import quran_word_align.align as qa


def main():
    folder = Path(sys.argv[1])
    model, words = qa.Model(), qa.mushaf_words("hafs")
    rows = list(csv.DictReader(open(folder / "mistakes.csv", encoding="utf-8")))
    out = []
    for r in rows:
        surah, ayah = int(r["surah"]), int(r["ayah"])
        for take in ("correct_file", "mistake_file"):
            audio = folder / r[take]
            seconds = len(qa.decode(audio)) / qa.SAMPLE_RATE
            got = qa.align_recording(surah, audio, words, model, [(ayah, 0.0, seconds)], margin=0.0)
            spans = got.get(ayah, [])
            for w, start, end, conf in spans:
                out.append([r[take], surah, ayah, w, start, end, conf])
            low = [w for w, _, _, c in spans if c < 0.3]
            print(r[take], f"{len(spans)}/{len(words[(surah, ayah)])} words", f"low: {low}" if low else "", flush=True)
    with open(folder / "word_spans.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["take", "surah", "ayah", "word", "start_ms", "end_ms", "confidence"], *out])


if __name__ == "__main__":
    main()
