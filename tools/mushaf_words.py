"""Make quran_word_align/data/<riwayah>-words.json from the King Fahd Complex's developer package.

  python tools/mushaf_words.py hafs  kfgqpc_hafs_v30.zip
  python tools/mushaf_words.py warsh kfgqpc_warsh_v30.zip
  python tools/mushaf_words.py qalun kfgqpc_qalun_v30.zip

The packages are the Complex's own (https://qurancomplex.gov.sa/quran-dev/, version 3.0), checked
against their SHA-256 below. Each ayah's text is split into words at its spaces, unchanged: the ayah
number is left out, and a ۞ that stands before a word is kept with it, as the mushaf prints them.
Words are numbered from 1 in each ayah, and ayahs are numbered as that riwayah's mushaf numbers them.
No word is typed by hand: every one is the package's.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

PACKAGES = {
    "hafs": ("kfgqpc_hafs_v30-data/kfgqpc_hafs_v30.json",
             "227e6b1564d980f2bd09c2c35ebfb0330ac268c79a7c247cd1ab665bc635f245",
             "https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_hafs_v30.zip"),
    "warsh": ("kfgqpc_warsh_v30-data/kfgqpc_warsh_v30.json",
              "d79b0e9d71696e6967a8f9051e62da87e3ad797e76c6b9d931d66fcf7739bbda",
              "https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_warsh_v30.zip"),
    "qalun": ("kfgqpc_qalun_v30-data/kfgqpc_qalun_v30.json",
              "32552185fda5520eb4cae741cc01162dc866fe3a224d921f4c182de4a7b965d9",
              "https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_qalun_v30.zip"),
}
OUT = Path(__file__).parent.parent / "quran_word_align" / "data"


def split(text: str) -> list[str]:
    words: list[str] = []
    for w in text.replace("\xa0", " ").split(" "):
        if not w or w.startswith("۝"):      # the ayah number
            continue
        if words and words[-1] == "۞":
            words[-1] += " " + w
        else:
            words.append(w)
    return words


def make(riwayah: str, package: Path) -> Path:
    member, digest, url = PACKAGES[riwayah]
    if hashlib.sha256(package.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"{package} is not the Complex's package ({url})")
    with zipfile.ZipFile(package) as z:
        ayahs = json.loads(z.read(member))
    words = {f"{a['sura_no']}:{a['aya_no']}": [[i + 1, w] for i, w in enumerate(split(a["aya_text_unicode"]))]
             for a in ayahs}
    out = OUT / f"{riwayah}-words.json"
    out.write_text(json.dumps(words, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(make(sys.argv[1], Path(sys.argv[2])))
