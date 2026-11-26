"""Whether mp3quran.net still serves the recordings the dataset was timed on.

    python tools/check_audio.py [audio-sha256.csv] [--out changed.csv]

Each recording's size, as its server gives it (an HTTP HEAD request, no download), is compared with the
size of the file that was aligned (`bytes` in the dataset's audio-sha256.csv, by default the published one
on Hugging Face). A recording replaced by another of a different size, or gone, is listed: its timings no
longer fit it. A replacement of exactly the same size would pass; the sha256 is there to check that by
hand. Exits 1 when anything changed.
"""

import argparse
import csv
import io
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PUBLISHED = "https://huggingface.co/datasets/voltarostudio/quran-word-timings-mp3quran/resolve/main/audio-sha256.csv"
AGENT = {"User-Agent": "quran-word-align audio check (monthly)"}
WORKERS = 4                 # a light load on mp3quran's server


def served_size(url: str) -> int | None:
    request = urllib.request.Request(url, method="HEAD", headers=AGENT)
    for _ in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as r:
                return int(r.headers.get("Content-Length", -1))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except (urllib.error.URLError, TimeoutError):
            pass
    return -1                                           # could not be reached: not taken as changed


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fingerprints", nargs="?", default=PUBLISHED)
    p.add_argument("--out", help="write the changed recordings here (csv)")
    a = p.parse_args()
    if a.fingerprints.startswith("http"):
        text = urllib.request.urlopen(urllib.request.Request(a.fingerprints, headers=AGENT), timeout=120).read().decode()
    else:
        text = open(a.fingerprints, encoding="utf-8").read()
    rows = list(csv.DictReader(io.StringIO(text)))
    with ThreadPoolExecutor(WORKERS) as pool:
        sizes = list(pool.map(served_size, (r["url"] for r in rows)))
    changed = [{**r, "served_bytes": "gone" if s is None else s} for r, s in zip(rows, sizes)
               if s is None or (s >= 0 and s != int(r["bytes"]))]
    unreached = sum(s == -1 for s in sizes)
    print(f"{len(rows)} recordings: {len(changed)} changed or gone, {unreached} not reached")
    for c in changed[:50]:
        print(f"  {c['reciter']} surah {c['surah']}: {c['bytes']} bytes timed, {c['served_bytes']} served")
    if a.out and changed:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(changed[0]))
            w.writeheader()
            w.writerows(changed)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
