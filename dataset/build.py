"""Package word timings on mp3quran.net's recordings as an open dataset (CC-BY 4.0).

  sh dataset/align.sh ALIGNED                       # align every recording below (hours)
  python dataset/build.py ALIGNED MP3QURAN AUDIO OUT [--version V]

ALIGNED   folder of <read id>/<surah>.json, as `quran-word-align mp3quran` writes them
MP3QURAN  folder with timing/<read id>/<surah>.json (api/v3/ayat_timing?surah=&read=), mp3quran's
          ayah timings, to compare with; fetched into it when missing
AUDIO     folder of mp3quran-<read id>/<surah>.mp3, the recordings aligned (to fingerprint them)
OUT       folder to write the dataset to; a zip of it is written beside it

Version 1.0 was built from Midad's alignments in mp3quran's ayah windows (git history has that
script). Nothing from Quran.com goes in.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys
import urllib.request
import zipfile

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from quran_word_align.align import mushaf_words  # noqa: E402

API = "https://www.mp3quran.net/api/v3"

# mp3quran read id → (riwayah, slug, English name). Order: as listed in the dataset.
RECITERS = {
    123: ("hafs", "alafasy", "Mishary Alafasy"),
    118: ("hafs", "husary", "Mahmoud Khalil Al-Husary"),
    112: ("hafs", "minshawi", "Muhammad Siddiq Al-Minshawi"),
    53: ("hafs", "abdulbasit", "Abdul Basit Abdul Samad"),
    54: ("hafs", "sudais", "Abdul Rahman Al-Sudais"),
    31: ("hafs", "shuraim", "Saud Al-Shuraim"),
    30: ("hafs", "ghamdi", "Saad Al-Ghamdi"),
    92: ("hafs", "yasser-dosari", "Yasser Al-Dosari"),
    86: ("hafs", "qatami", "Nasser Al-Qatami"),
    5: ("hafs", "ajmi", "Ahmad Al-Ajmi"),
    109: ("hafs", "ayyub", "Muhammad Ayyub"),
    4: ("hafs", "shatri", "Abu Bakr Al-Shatri"),
    62: ("hafs", "juhani", "Abdullah Awad Al-Juhani"),
    76: ("hafs", "ali-jaber", "Ali Jaber"),
    20: ("hafs", "jaleel", "Khalid Al-Jaleel"),
    217: ("hafs", "baleela", "Bandar Baleela"),
    12: ("hafs", "abkar", "Idris Abkar"),
    81: ("hafs", "fares-abbad", "Fares Abbad"),
    46: ("hafs", "bukhatir", "Salah Bukhatir"),
    60: ("hafs", "basfar", "Abdullah Basfar"),
    106: ("hafs", "tablawi", "Muhammad Al-Tablawi"),
    14: ("warsh", "yassin-jazairi", "Yassin Al-Jazairi"),
    16: ("warsh", "kouchi", "Laayoun El Kouchi"),
    80: ("warsh", "kazabri", "Omar Al-Kazabri"),
    120: ("warsh", "husary-warsh", "Mahmoud Khalil Al-Husary (Warsh)"),
    75: ("qalun", "hudhaifi-qalun", "Ali Al-Hudhaifi (Qalun)"),
    270: ("qalun", "husary-qalun", "Mahmoud Khalil Al-Husary (Qalun)"),
    208: ("qalun", "dokali-alim", "Al-Dokali Muhammad Al-Alim (Qalun)"),
}
RIWAYAH_NAMES = {"hafs": "Hafs", "warsh": "Warsh", "qalun": "Qalun"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def mp3quran_rows(mp3quran: Path, read_id: int, surah: int) -> list[dict]:
    path = mp3quran / "timing" / str(read_id) / f"{surah:03}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(f"{API}/ayat_timing?surah={surah}&read={read_id}",
                                         headers={"User-Agent": "quran-word-align dataset build"})
        path.write_bytes(urllib.request.urlopen(request, timeout=120).read())
    return json.loads(path.read_text(encoding="utf-8"))


def build(aligned: Path, mp3quran: Path, audio: Path, out: Path, version: str) -> None:
    request = urllib.request.Request(f"{API}/ayat_timing/reads", headers={"User-Agent": "quran-word-align dataset build"})
    reads = {r["id"]: r for r in json.loads(urllib.request.urlopen(request, timeout=120).read())}
    if out.exists():
        shutil.rmtree(out)
    (out / "timings").mkdir(parents=True)
    reciters, quality, differ, fingerprints, words_rows = [], [], [], [], []
    for read_id, (riwayah, slug, name_en) in RECITERS.items():
        words = mushaf_words(riwayah)
        read = reads[read_id]
        files = sorted((aligned / str(read_id)).glob("*.json"))
        target = out / "timings" / slug
        target.mkdir()
        expected_words = timed_words = n_words = compared = agree = 0
        confidence = []
        for path in files:
            surah = int(path.stem)
            result = json.loads(path.read_text(encoding="utf-8"))
            (target / path.name).write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
            ayahs = sorted(n for (s, n) in words if s == surah)
            expected_words += sum(len(words[(surah, n)]) for n in ayahs)
            timed_words += sum(len({w[0] for w in result.get(str(n), [])}) for n in ayahs)
            # Is each ayah where mp3quran's ayah timing puts it? Our start inside their span.
            rows = {int(r["ayah"]): r for r in mp3quran_rows(mp3quran, read_id, surah) if int(r["ayah"]) >= 1}
            for n in ayahs:
                ws, r = result.get(str(n)), rows.get(n)
                if not ws or not r:
                    continue
                compared += 1
                start = min(w[1] for w in ws)
                if r["start_time"] - 500 <= start < r["end_time"]:
                    agree += 1
                else:
                    differ.append({"reciter": slug, "read_id": read_id, "surah": surah, "ayah": n, "our_start_ms": start,
                                   "mp3quran_start_ms": r["start_time"], "mp3quran_end_ms": r["end_time"]})
            for ayah, ws in result.items():
                n_words += len(ws)
                for word, start, end, conf in ws:
                    confidence.append(conf)
                    words_rows.append((slug, riwayah, surah, int(ayah), word, start, end, conf))
            mp3 = audio / f"mp3quran-{read_id}" / f"{path.stem}.mp3"
            fingerprints.append({"reciter": slug, "read_id": read_id, "surah": surah,
                                 "url": f"{read['folder_url']}{path.stem}.mp3",
                                 "bytes": mp3.stat().st_size, "sha256": sha256(mp3)})
        reciters.append({"reciter": slug, "read_id": read_id, "riwayah": riwayah, "name_en": name_en, "name_ar": read["name"],
                         "rewaya": read["rewaya"], "surahs": len(files), "audio_folder": read["folder_url"]})
        quality.append({"reciter": slug, "name_en": name_en, "riwayah": riwayah, "surahs": len(files),
                        "words_timed_pct": round(100 * timed_words / expected_words, 2), "words": n_words,
                        "median_confidence": round(statistics.median(confidence), 2),
                        "confident_pct": round(100 * sum(c >= 0.7 for c in confidence) / len(confidence), 1),
                        "ayahs_compared": compared, "agree_with_mp3quran_pct": round(100 * agree / max(compared, 1), 2)})
        print(f"{slug}: {len(files)} surahs, {n_words} words, {agree}/{compared} ayahs where mp3quran puts them")

    def write_csv(name: str, rows: list[dict]) -> None:
        with (out / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    write_csv("reciters.csv", reciters)
    write_csv("quality.csv", quality)
    write_csv("differs-from-mp3quran.csv", differ)
    write_csv("audio-sha256.csv", fingerprints)
    with (out / "words.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["reciter", "riwayah", "surah", "ayah", "word", "start_ms", "end_ms", "confidence"])
        w.writerows(words_rows)

    table = ["| Reciter | Riwayah | Surahs | Words timed | Median confidence | Confidence ≥ 0.7 | Ayahs where mp3quran puts them |",
             "|---|---|---|---|---|---|---|"]
    for q in quality:
        table.append(f"| {q['name_en']} | {RIWAYAH_NAMES[q['riwayah']]} | {q['surahs']} | {q['words_timed_pct']}% | "
                     f"{q['median_confidence']:.2f} | {q['confident_pct']}% | {q['agree_with_mp3quran_pct']}% |")
    names = {slug: name for _, slug, name in RECITERS.values()}
    worst = Counter((d["reciter"], d["surah"]) for d in differ).most_common(6)
    worst_text = ", ".join(f"{names[r]}, surah {s}: {n} ayahs" for (r, s), n in worst)
    totals = {"words": f"{len(words_rows) / 1e6:.2f} million", "reciters": str(len(RECITERS)),
              "differ": f"{len(differ):,}", "compared": f"{sum(q['ayahs_compared'] for q in quality):,}"}
    readme = (HERE / "card.md").read_text(encoding="utf-8").replace("{version}", version)
    readme = readme.replace("{quality_table}", "\n".join(table)).replace("{worst_surahs}", worst_text)
    for k, v in totals.items():
        readme = readme.replace("{" + k + "}", v)
    (out / "README.md").write_text(readme, encoding="utf-8")
    (HERE / "README.md").write_text(readme, encoding="utf-8")  # the card as published, to read on GitHub
    shutil.copy(HERE / "LICENSE-DATA.md", out / "LICENSE.md")
    for riwayah in ("hafs", "warsh", "qalun"):
        shutil.copy(HERE.parent / "quran_word_align" / "data" / f"{riwayah}-words.json", out / f"{riwayah}-words.json")
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
    p.add_argument("--version", default="2.0")
    a = p.parse_args()
    build(a.aligned, a.mp3quran, a.audio, a.out, a.version)


if __name__ == "__main__":
    main()
