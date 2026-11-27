"""Make the two lists the lab page works from.

1. The gold set: ayahs from the dataset whose word starts and ends Basel checks by ear. Each ayah is
   cut from the recording the dataset was timed on, with the dataset's timings as the starting point.
2. The deliberate mistakes: words Basel recites wrongly on purpose, once correctly and once with the
   named mistake, so that al-Mu'allim can be checked on real errors in a non-professional voice.

The Quran text is taken from the dataset's own words files, never typed.

    python tools/lab/make_sample.py DATASET AUDIO_CACHE OUT
"""

import csv
import json
import random
import subprocess
import sys
from pathlib import Path

SEED = 1447
RECITATIONS = 20          # spread across the dataset's confidence range
AYAHS_EACH = 2
WORDS = (6, 10)           # ayahs of this many words: long enough to matter, short enough to check
PAD_MS = 500
RATE = 22050

SUKUN, SHADDA, MADDAH = "ۡ", "ّ", "ٓ"
QALQALA = "قطبجد"
SWAPS = {"ح": "ه", "ع": "ء", "ق": "ك", "ط": "ت", "ض": "د", "ص": "س", "ظ": "ز", "ذ": "ز", "ث": "س"}
FAMILIAR = [1] + list(range(78, 115))   # al-Fatiha and juz' 30, which Basel recites from memory


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick_recitations(dataset, rnd):
    """Recitations spread evenly from the least to the most confident, Warsh and Qalun included."""
    rows = sorted(read_csv(dataset / "quality.csv"), key=lambda r: float(r["median_confidence"]))
    step = (len(rows) - 1) / (RECITATIONS - 1)
    chosen = [rows[round(i * step)] for i in range(RECITATIONS)]
    for riwayah in ("warsh", "qalun"):
        if not any(r["riwayah"] == riwayah for r in chosen):
            chosen[rnd.randrange(1, RECITATIONS - 1)] = rnd.choice([r for r in rows if r["riwayah"] == riwayah])
    return chosen


def gold(dataset, cache, out, rnd):
    reciters = {r["reciter"]: r for r in read_csv(dataset / "reciters.csv")}
    texts = {rw: json.load(open(dataset / f"{rw}-words.json", encoding="utf-8")) for rw in ("hafs", "warsh", "qalun")}
    ayahs = {}
    for r in read_csv(dataset / "ayah-timings.csv"):
        ayahs.setdefault(r["reciter"], []).append(r)

    wanted = {}
    for rec in pick_recitations(dataset, rnd):
        name, riwayah = rec["reciter"], rec["riwayah"]
        fits = [a for a in ayahs[name]
                if WORDS[0] <= len(texts[riwayah].get(f'{a["surah"]}:{a["ayah"]}', [])) <= WORDS[1]
                and a["ayah"] != "1"]
        for a in rnd.sample(fits, AYAHS_EACH):
            wanted[(name, a["surah"], a["ayah"])] = {"reciter": name, "riwayah": riwayah, "surah": int(a["surah"]),
                                                       "ayah": int(a["ayah"]), "start_ms": int(a["start_ms"]),
                                                       "end_ms": int(a["end_ms"]), "words": []}

    with open(dataset / "words.csv", newline="", encoding="utf-8") as f:
        for w in csv.DictReader(f):
            item = wanted.get((w["reciter"], w["surah"], w["ayah"]))
            if item is not None:
                item["words"].append([int(w["word"]), int(w["start_ms"]) if w["start_ms"] else None,
                                      int(w["end_ms"]) if w["end_ms"] else None, float(w["confidence"] or 0)])

    clips = out / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    items = []
    for item in wanted.values():
        text = dict((n, t) for n, t in texts[item["riwayah"]][f'{item["surah"]}:{item["ayah"]}'])
        rec = reciters[item["reciter"]]
        src = cache / f'mp3quran-{rec["read_id"]}' / f'{item["surah"]:03d}.mp3'
        begin = max(0, item["start_ms"] - PAD_MS)
        clip = f'{item["reciter"]}-{item["surah"]:03d}{item["ayah"]:03d}.wav'
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-ss", f"{begin / 1000:.3f}",
                        "-t", f"{(item['end_ms'] + PAD_MS - begin) / 1000:.3f}", "-ac", "1", "-ar", str(RATE),
                        str(clips / clip)], check=True)
        item.update(clip=f"clips/{clip}", clip_starts_ms=begin, name_ar=rec["name_ar"],
                    words=[{"word": n, "text": text[n], "start_ms": s, "end_ms": e, "confidence": c}
                           for n, s, e, c in sorted(item["words"])])
        items.append(item)
    items.sort(key=lambda i: (i["reciter"], i["surah"], i["ayah"]))
    return items


def mistakes_in(word):
    """The deliberate mistakes this word can carry, from its letters and marks alone."""
    found = []
    letters = [(i, ch) for i, ch in enumerate(word) if "ء" <= ch <= "ي" or ch == "ٱ"]
    for k, (i, ch) in enumerate(letters):
        marks = word[i + 1: letters[k + 1][0] if k + 1 < len(letters) else len(word)]
        if ch in "نم" and SHADDA in marks:
            found.append(("ghunna", f"اقرأ «{ch}ّ» بلا غنّة"))
        # A madd inside the word (muttasil before a hamza, lazim before a shadda or sukun) must be
        # long. A maddah on the word's last letter is munfasil, which Hafs may shorten: not a mistake.
        # An alif after a hamza (أٓ, as in ٱلۡأٓخِرَة) is madd badal, two counts: not a long madd either.
        badal = ch in "أآ" or (ch == "ا" and k and letters[k - 1][1] in "ءأإؤئ")
        if MADDAH in marks and k + 1 < len(letters) and not badal:
            found.append(("madd", "اقصر المدّ فيها إلى حركتين"))
        if ch in QALQALA and SUKUN in marks:
            found.append(("qalqala", f"اقرأ «{ch}» الساكنة بلا قلقلة"))
        if ch in SWAPS:
            found.append(("letter", f"انطق «{ch}» كأنها «{SWAPS[ch]}»"))
    return found


def mistakes(dataset, rnd):
    text = json.load(open(dataset / "hafs-words.json", encoding="utf-8"))
    pool = {}
    for key, words in text.items():
        surah, ayah = map(int, key.split(":"))
        if surah not in FAMILIAR or (surah == 1 and ayah == 1):
            continue
        for n, w in words:
            for kind, how in mistakes_in(w):
                pool.setdefault(kind, []).append({"surah": surah, "ayah": ayah, "word": n, "kind": kind, "how": how})
    # Each kind as often as the others; each ayah used once, so the list covers many surahs.
    chosen, used, said = [], set(), set()
    for kind, n in (("ghunna", 8), ("madd", 8), ("qalqala", 8), ("letter", 10)):
        for m in rnd.sample(pool[kind], len(pool[kind])):
            if len([c for c in chosen if c["kind"] == kind]) == n:
                break
            word = dict(text[f'{m["surah"]}:{m["ayah"]}'])[m["word"]]
            if (m["surah"], m["ayah"]) not in used and word not in said:
                used.add((m["surah"], m["ayah"]))
                said.add(word)
                chosen.append(m)
    for kind, how in (("skip", "تخطَّ هذه الكلمة"), ("repeat", "كرّر هذه الكلمة مرتين")):
        for _ in range(3):
            key = rnd.choice([k for k in text if int(k.split(":")[0]) in FAMILIAR and len(text[k]) >= 4
                              and tuple(map(int, k.split(":"))) not in used])
            s, a = map(int, key.split(":"))
            used.add((s, a))
            chosen.append({"surah": s, "ayah": a, "word": rnd.randrange(2, len(text[key])), "kind": kind, "how": how})
    for i, m in enumerate(sorted(chosen, key=lambda m: (m["surah"], m["ayah"]))):
        m["id"] = i + 1
        m["words"] = [t for _, t in text[f'{m["surah"]}:{m["ayah"]}']]
    return sorted(chosen, key=lambda m: m["id"])


def main():
    dataset, cache, out = map(Path, sys.argv[1:4])
    rnd = random.Random(SEED)
    out.mkdir(parents=True, exist_ok=True)
    data = {"gold": gold(dataset, cache, out, rnd), "mistakes": mistakes(dataset, rnd)}
    (out / "sample.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    words = sum(len(i["words"]) for i in data["gold"])
    print(f'gold: {len(data["gold"])} ayahs, {words} words; mistakes: {len(data["mistakes"])}')


if __name__ == "__main__":
    main()
