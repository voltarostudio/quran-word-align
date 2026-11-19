"""Package word timings on mp3quran.net's recordings as an open dataset (CC-BY 4.0).

  python dataset/build.py ALIGNED MP3QURAN AUDIO OUT [--version V]

ALIGNED   folder of <read id>/<surah>.json, as `quran-word-align` writes them
MP3QURAN  folder with reads.json (api/v3/ayat_timing/reads) and timing/<read id>/<surah>.json
          (api/v3/ayat_timing?surah=&read=), the ayah timings the alignment was windowed on
AUDIO     folder of mp3quran-<read id>/<surah>.mp3, the recordings aligned (to fingerprint them)
OUT       folder to write the dataset to; a zip of it is written beside it

Only Hafs recordings are packaged: the words are the Hafs mushaf's. Nothing from Quran.com goes in.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import zipfile

HERE = Path(__file__).parent

# mp3quran read id → (slug, English name). The 21 Hafs recordings Midad aligned.
RECITERS = {
    123: ("alafasy", "Mishary Alafasy"),
    118: ("husary", "Mahmoud Khalil Al-Husary"),
    112: ("minshawi", "Muhammad Siddiq Al-Minshawi"),
    53: ("abdulbasit", "Abdul Basit Abdul Samad"),
    54: ("sudais", "Abdul Rahman Al-Sudais"),
    31: ("shuraim", "Saud Al-Shuraim"),
    30: ("ghamdi", "Saad Al-Ghamdi"),
    92: ("yasser-dosari", "Yasser Al-Dosari"),
    86: ("qatami", "Nasser Al-Qatami"),
    5: ("ajmi", "Ahmad Al-Ajmi"),
    109: ("ayyub", "Muhammad Ayyub"),
    4: ("shatri", "Abu Bakr Al-Shatri"),
    62: ("juhani", "Abdullah Awad Al-Juhani"),
    76: ("ali-jaber", "Ali Jaber"),
    20: ("jaleel", "Khalid Al-Jaleel"),
    217: ("baleela", "Bandar Baleela"),
    12: ("abkar", "Idris Abkar"),
    81: ("fares-abbad", "Fares Abbad"),
    46: ("bukhatir", "Salah Bukhatir"),
    60: ("basfar", "Abdullah Basfar"),
    106: ("tablawi", "Muhammad Al-Tablawi"),
}

# Agreement with Quran.com's word timings where Quran.com's recording is the same performance:
# the share of words whose start (from their ayah's start) is within 0.25 s / 0.5 s of Quran.com's.
# Measured in Midad's pipeline (build/word-timings-mp3quran-eval.md); only these numbers are kept.
AGREEMENT = {
    "husary": (79.9, 85.4), "shuraim": (94.1, 96.6), "abdulbasit": (51.0, 82.0), "minshawi": (61.8, 82.2),
    "shatri": (3.9, 71.2), "yasser-dosari": (68.1, 83.8), "jaleel": (72.7, 83.3),
}

# An ayah's words more than this far from mp3quran's ayah timing mean the ayah timing (and so the
# window the ayah was aligned in) does not fit the recording there.
OFF_MS = 2500


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def suspect_ayahs(result: dict, rows: list[dict]) -> list[tuple[int, str]]:
    """Ayahs whose timings are likely wrong, with why: their words run back into the previous ayah's,
    or their first word is far from where mp3quran says the ayah starts."""
    starts = {int(r["ayah"]): int(r["start_time"]) for r in rows}
    out, previous = [], None
    for ayah in sorted(result, key=int):
        words = result[ayah]
        if not words:
            continue
        first = words[0][1]
        if previous is not None and first < previous - 200:
            out.append((int(ayah), "overlaps the previous ayah"))
        elif int(ayah) in starts and abs(first - starts[int(ayah)]) > OFF_MS:
            out.append((int(ayah), "far from mp3quran's ayah start"))
        previous = max(w[1] for w in words)
    return out


def build(aligned: Path, mp3quran: Path, audio: Path, out: Path, version: str) -> None:
    reads = {r["id"]: r for r in json.loads((mp3quran / "reads.json").read_text(encoding="utf-8"))}
    if out.exists():
        shutil.rmtree(out)
    (out / "timings").mkdir(parents=True)
    reciters, quality, issues, fingerprints, words_rows = [], [], [], [], []
    for read_id, (slug, name_en) in RECITERS.items():
        read = reads[read_id]
        assert read["rewaya"].startswith("حفص"), (read_id, read["rewaya"])
        files = sorted((aligned / str(read_id)).glob("*.json"))
        target = out / "timings" / slug
        target.mkdir()
        n_ayahs = n_words = 0
        durations, suspect = [], 0
        for path in files:
            surah = int(path.stem)
            result = json.loads(path.read_text(encoding="utf-8"))
            (target / path.name).write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
            rows = json.loads((mp3quran / "timing" / str(read_id) / path.name).read_text(encoding="utf-8"))
            for ayah, why in suspect_ayahs(result, rows):
                issues.append({"reciter": slug, "read_id": read_id, "surah": surah, "ayah": ayah, "why": why})
                suspect += 1
            for ayah, words in result.items():
                n_ayahs += 1
                n_words += len(words)
                for word, start, end in words:
                    durations.append(end - start)
                    words_rows.append((slug, surah, int(ayah), word, start, end))
            mp3 = audio / f"mp3quran-{read_id}" / path.name.replace(".json", ".mp3")
            fingerprints.append({"reciter": slug, "read_id": read_id, "surah": surah,
                                 "url": f"{read['folder_url']}{path.stem}.mp3",
                                 "bytes": mp3.stat().st_size, "sha256": sha256(mp3)})
        reciters.append({"reciter": slug, "read_id": read_id, "name_en": name_en, "name_ar": read["name"],
                         "rewaya": read["rewaya"], "surahs": len(files), "audio_folder": read["folder_url"]})
        agree = AGREEMENT.get(slug, ("", ""))
        quality.append({"reciter": slug, "name_en": name_en, "surahs": len(files), "ayahs": n_ayahs,
                        "words": n_words, "median_word_ms": int(statistics.median(durations)),
                        "suspect_ayahs": suspect, "suspect_pct": round(100 * suspect / n_ayahs, 2),
                        "qurancom_within_0.25s_pct": agree[0], "qurancom_within_0.5s_pct": agree[1]})
        print(f"{slug}: {len(files)} surahs, {n_words} words, {suspect} suspect ayahs")

    def write_csv(name: str, rows: list[dict]) -> None:
        with (out / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    write_csv("reciters.csv", reciters)
    write_csv("quality.csv", quality)
    write_csv("suspect-ayahs.csv", issues)
    write_csv("audio-sha256.csv", fingerprints)
    with (out / "words.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["reciter", "surah", "ayah", "word", "start_ms", "end_ms"])
        w.writerows(words_rows)
    table = ["| Reciter | Words | Median word | Suspect ayahs | vs Quran.com ≤0.25 s | ≤0.5 s |",
             "|---|---|---|---|---|---|"]
    for q in quality:
        agree = (f"{q['qurancom_within_0.25s_pct']}% | {q['qurancom_within_0.5s_pct']}%"
                 if q["qurancom_within_0.25s_pct"] != "" else "— | —")
        table.append(f"| {q['name_en']} | {q['words']:,} | {q['median_word_ms'] / 1000:.2f} s | "
                     f"{q['suspect_ayahs']} ({q['suspect_pct']}%) | {agree} |")
    from collections import Counter
    surah_names = {1: "al-Fatiha", 2: "al-Baqarah", 3: "Al Imran", 4: "an-Nisa'", 9: "at-Tawbah", 12: "Yusuf", 36: "Ya-Sin", 39: "az-Zumar"}
    worst = Counter((i["reciter"], i["surah"]) for i in issues).most_common(6)
    names = {slug: name for slug, name in RECITERS.values()}
    worst_text = ", ".join(f"{names[r].split()[-1]}'s {surah_names.get(s, f'surah {s}')}: {n}" for (r, s), n in worst)
    readme = ((HERE / "card.md").read_text(encoding="utf-8").replace("{version}", version)
              .replace("{quality_table}", "\n".join(table)).replace("{worst_surahs}", worst_text))
    (out / "README.md").write_text(readme, encoding="utf-8")
    (HERE / "README.md").write_text(readme, encoding="utf-8")  # the card as published, to read on GitHub
    shutil.copy(HERE / "LICENSE-DATA.md", out / "LICENSE.md")
    shutil.copy(HERE.parent / "quran_word_align" / "data" / "hafs-words.json", out / "hafs-words.json")
    archive = out.parent / f"{out.name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                z.write(path, Path(out.name) / path.relative_to(out))
    print(f"{archive}: {archive.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("aligned", "mp3quran", "audio", "out"):
        p.add_argument(name, type=Path)
    p.add_argument("--version", default="1.0")
    a = p.parse_args()
    build(a.aligned, a.mp3quran, a.audio, a.out, a.version)


if __name__ == "__main__":
    main()
