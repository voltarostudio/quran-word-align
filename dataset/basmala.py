"""How each reciter's surah files open, and where their own basmala and isti'adha are: for apps that
play the reciter's basmala before a surah whose file lacks one, and the isti'adha once when listening
begins. Nothing is cut: places are given (surah file, start and end, in ms from the start of
mp3quran's file), and the audio stays mp3quran's.

    python dataset/basmala.py ALIGNED AUDIO OUT.json

ALIGNED: the aligned reads (one folder per mp3quran read id); AUDIO: the mp3 cache, with a folder
mp3quran-<id> per read. OUT.json: {read id: {"basmala": place, "istiadha": place, "openings":
{surah: {"has_istiadha", "has_basmala", "first_word_ms"}}}}.

Each surah's opening, up to where its first word begins, is heard alone. In it:
- has_basmala is 1 when a basmala is heard (mean confidence >= HEARD, its words of sound length), 0 when there is almost
  no voice there (under NO_ROOM seconds) or no basmala is heard at all while the voice is short, and
  the first word was heard clearly (SURE_FIRST); empty when it cannot be told. At-Tawba: 0. Al-Fatiha in Hafs: 1 when its first ayah (the basmala)
  was timed, else 0.
- has_istiadha is 1 when an isti'adha is heard clearly before the basmala, 0 when there is no room
  for one (the basmala, or the first word, begins within NO_ROOM seconds of voice), else empty.
- basmala_words: the basmala's four words in that file, when has_basmala is 1 (lit_basmala says when
  they are clear enough to give); istiadha_end_ms, where a clearly heard isti'adha ends.
- The basmala given for a reciter (heard at CLEAR or better) is in the shortest file (bytes) whose basmala is heard within MARGIN
  of the reciter's clearest, as an app must download the whole file to play it; likewise the
  isti'adha.
"""

import json
import statistics
import sys
from pathlib import Path

from quran_word_align.align import Model, decode, heard_text, opening

CLEAR = 0.85            # mean confidence of a basmala clear enough to be played
HEARD = 0.6             # mean confidence of a basmala taken as said
MARGIN = 0.05           # how much less clear than the clearest a shorter file's basmala may be
NO_ROOM = 1.5           # seconds of voice too short for a basmala or an isti'adha (the fastest basmala heard: 1.8 s)
NOT_HEARD = 0.3         # a basmala's confidence where none is said
SHORT_VOICE = 3.0       # seconds of voice in which an unheard basmala is taken as not said


# A first word's place can be wrong (a surah opening with letters like the basmala's, الر or حم, placed
# inside the basmala), and the model, hearing a short clip, often leaves out a basmala that more words
# follow; so a 0 is given only when the first word itself was heard clearly, and nothing like a basmala
# or an isti'adha is heard up to a little past it.
SURE_FIRST = 0.85
PAST = 4.0
SAID_BEFORE = ("بسم", "لله", "رحمن", "رحيم", "عوذ", "شيط", "رجيم")


# The basmala's words are given, to light them as they are heard, only when each is heard clearly
# where it is placed and the four fit before the first ayah: a light must never run ahead of the voice.
WORD_CLEAR = 0.5        # each word's confidence
MEAN_CLEAR = 0.75       # the four words' mean confidence


def lit_basmala(row: dict) -> list[list] | None:
    """The basmala's words [[word, start_ms, end_ms, confidence], ...] of an opening, when clear enough to light."""
    words, first = row.get("basmala_words"), row.get("first_word_ms")
    if not words or len(words) != 4 or row.get("has_basmala") != 1:
        return None
    if min(w[3] for w in words) < WORD_CLEAR or mean(words) < MEAN_CLEAR:
        return None
    if any(w[2] <= w[1] for w in words) or any(b[1] < a[1] for a, b in zip(words, words[1:])):
        return None
    if first is not None and words[-1][2] > first:
        return None
    return words


def says_something_before(model, mp3: Path, first_s: float) -> bool:
    text = heard_text(model, decode(mp3, first_s + PAST)).replace(" ", "")
    return any(p in text for p in SAID_BEFORE)


def mean(words: list[list]) -> float:
    return statistics.mean(w[3] for w in words)


def place(surah: int, words: list[list]) -> dict:
    return {"surah": surah, "start_ms": words[0][1], "end_ms": words[-1][2],
            "confidence": round(mean(words), 3), "words": words}


def shortest(found: list[tuple[float, int, int, list[list]]]) -> dict | None:
    """Of (confidence, file size, surah, words), the shortest file within MARGIN of the clearest."""
    if not found:
        return None
    best = max(f[0] for f in found)
    _, _, surah, words = min((f for f in found if f[0] >= best - MARGIN), key=lambda f: f[1])
    return place(surah, words)


def read_openings(folder: Path, audio: Path, model) -> dict:
    openings, basmalas, istiadhas = {}, [], []
    for timed in sorted(folder.glob("*.json")):
        surah, mp3 = int(timed.stem), audio / f"{timed.stem}.mp3"
        t = json.loads(timed.read_text())
        first = t.get("1")
        row = {"has_istiadha": None, "has_basmala": None, "first_word_ms": first[0][1] if first else None}
        openings[surah] = row
        # In Hafs al-Fatiha's basmala is its first ayah (4, 4, 2, ... words): what precedes it ends
        # where the second ayah begins. Without a timed first ayah, the recording has no basmala.
        hafs_fatiha = surah == 1 and [len(t.get(str(a), [])) for a in range(2, 4)] == [4, 2]
        after = t.get("2") if hafs_fatiha else first
        if not mp3.exists() or not after:
            continue
        o = opening(mp3, model, after[0][1] / 1000)
        size = mp3.stat().st_size
        if hafs_fatiha:
            row["has_basmala"] = int("1" in t and len(t["1"]) == 4)
        elif surah == 9:
            row["has_basmala"] = 0
        elif o.basmala and mean(o.basmala) >= HEARD:
            row["has_basmala"] = 1
            if mean(o.basmala) >= CLEAR:
                basmalas.append((mean(o.basmala), size, surah, o.basmala))
        elif (first and first[0][3] >= SURE_FIRST and (o.voiced < NO_ROOM or (o.basmala_score < NOT_HEARD and o.voiced < SHORT_VOICE))
              and not says_something_before(model, mp3, first[0][1] / 1000)):
            row["has_basmala"] = 0
        if row["has_basmala"] == 1 and o.basmala and not hafs_fatiha:
            row["basmala_words"] = o.basmala
        if o.istiadha:
            row["has_istiadha"] = 1
            row["istiadha_end_ms"] = o.istiadha[-1][2]
            istiadhas.append((mean(o.istiadha), size, surah, o.istiadha))
        else:
            begins = o.basmala[0][1] / 1000 if row["has_basmala"] == 1 and o.basmala else None
            if (begins is not None and begins < NO_ROOM) or row["has_basmala"] == 0:
                row["has_istiadha"] = 0
    out = {"openings": openings}
    for kind, found in (("basmala", basmalas), ("istiadha", istiadhas)):
        chosen = shortest(found)
        if chosen:
            out[kind] = chosen
    return out


def main() -> None:
    aligned, audio, out = (Path(a) for a in sys.argv[1:4])
    model, found = Model(), {}
    for folder in sorted(aligned.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not folder.name.isdigit():
            continue
        found[folder.name] = read_openings(folder, audio / f"mp3quran-{folder.name}", model)
        rows = found[folder.name]["openings"].values()
        print(folder.name, {k: found[folder.name].get(k, {}).get("surah") for k in ("basmala", "istiadha")},
              "basmala 1/0/?:", [sum(r["has_basmala"] == v for r in rows) for v in (1, 0, None)],
              "isti'adha 1/0/?:", [sum(r["has_istiadha"] == v for r in rows) for v in (1, 0, None)], flush=True)
    out.write_text(json.dumps(found, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
