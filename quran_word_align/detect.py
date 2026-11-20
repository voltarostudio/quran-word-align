"""Which surah a recording is, and (an experiment) in which riwayah: told from what the model hears.

Surah: the opening minutes are read off the model's letters (best path, CTC collapsed), and the surah
is the one whose opening shares the most letter triples with them. Right for all 224 recordings of
eval/DETECT.md.

Riwayah: not used by the tool. The riwayat share the mushaf's letters (the Uthmani rasm) and differ in
about 690 of its 325,000 letters as the model hears them, none at all in 41 surahs. At each place
where two riwayat differ, `detect_riwayah` asks which one the recording is closer to. The model leans
to Hafs, so Warsh and Qalun recordings are often taken for Hafs (eval/DETECT.md): kept to measure, not
to decide.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import math

from .align import BLANK, RIWAYAT, SPACE, letters, mushaf_words

HEAR_SECONDS = 180.0      # the opening heard to decide
SURAH_CANDIDATES = 3      # surahs whose riwayat are compared
FREE_START = 300          # heard letters the text may begin after, free (isti'adha, basmala)


def heard_letters(lp, frames: int | None = None) -> list[int]:
    """The model's best path over the first `frames` frames, collapsed: letters only."""
    import numpy as np
    best = np.asarray(lp[:frames]).argmax(1)
    out, prev = [], -1
    for t in best.tolist():
        if t != prev and t not in (BLANK, SPACE):
            out.append(t)
        prev = t
    return out


@lru_cache(maxsize=None)
def surah_letters(surah: int, riwayah: str) -> tuple[int, ...]:
    words = mushaf_words(riwayah)
    out: list[int] = []
    n = 1
    while (surah, n) in words:
        for _, text in words[(surah, n)]:
            out += letters(text)
        n += 1
    return tuple(out)


def _triples(seq) -> Counter:
    return Counter(zip(seq, seq[1:], seq[2:]))


def _cosine(a: Counter, b: Counter) -> float:
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _find(pattern, heard, lo: int, hi: int) -> float:
    """Edit distance of `pattern` against its best match anywhere in heard[lo:hi]."""
    import numpy as np
    h = np.asarray(heard[max(lo, 0): hi])
    n = len(h)
    if not n:
        return float(len(pattern))
    ramp = np.arange(n + 1)
    row = np.zeros(n + 1)                     # the match may begin anywhere
    for i, c in enumerate(pattern, 1):
        cur = np.empty(n + 1)
        cur[0] = i
        cur[1:] = np.minimum(row[:-1] + (h != c), row[1:] + 1)
        row = np.minimum.accumulate(cur - ramp) + ramp
    return float(row.min())                   # and end anywhere


CONTEXT_LETTERS = 14      # letters either side of a difference, to find its place in the recording
SEARCH = 0.06             # how far from its expected place (share of the recording) a difference is looked for


def differences(surah: int, a: str, b: str) -> list[tuple[tuple[int, ...], tuple[int, ...], float]]:
    """Where riwayat `a` and `b` differ in a surah's letters: (a's letters, b's letters, place 0..1),
    each with some letters of context. The surah's first letters are left out (the basmala is an ayah
    of al-Fatiha in Hafs only)."""
    import difflib
    A, B = surah_letters(surah, a), surah_letters(surah, b)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == "equal" or i1 < 60:
            continue
        c = CONTEXT_LETTERS
        out.append((A[max(i1 - c, 0): i2 + c], B[max(j1 - c, 0): j2 + c], i1 / max(len(A), 1)))
    return out


def riwayah_votes(heard: list[int], surah: int, a: str, b: str) -> tuple[int, int]:
    """At each place where `a` and `b` differ, which one the recording is closer to: (for a, for b)."""
    n = len(heard)
    va = vb = 0
    for pa, pb, at in differences(surah, a, b):
        lo, hi = int((at - SEARCH) * n), int((at + SEARCH) * n) + len(pa) + 40
        da, db = _find(pa, heard, lo, hi), _find(pb, heard, lo, hi)
        va += da < db
        vb += db < da
    return va, vb


@dataclass
class Guess:
    surah: int
    score: float               # letter triples shared with the opening, 0..1
    riwayah: str | None        # None: the riwayat read the same letters in this surah, so it cannot be told
    votes: dict                # places of difference won by each riwayah


def detect_surah(lp, seconds: float = HEAR_SECONDS) -> list[tuple[float, int]]:
    """Surahs by how much their opening shares with the recording's, best first."""
    heard = heard_letters(lp, int(seconds / 0.04))
    mine = _triples(heard)
    scores = [(_cosine(mine, _triples(surah_letters(s, "hafs")[: int(len(heard) * 1.3) + 30])), s) for s in range(1, 115)]
    return sorted(scores, reverse=True)


def detect_riwayah(lp, surah: int, riwayat=RIWAYAT) -> tuple[str | None, dict]:
    """The riwayah the whole recording is closest to, at the places where the riwayat differ."""
    heard = heard_letters(lp)
    votes = {r: 0 for r in riwayat}
    for i, a in enumerate(riwayat):
        for b in riwayat[i + 1:]:
            va, vb = riwayah_votes(heard, surah, a, b)
            if va > vb:
                votes[a] += 1
            elif vb > va:
                votes[b] += 1
    best = sorted(votes.items(), key=lambda kv: -kv[1])
    if best[0][1] == 0 or (len(best) > 1 and best[0][1] == best[1][1]):
        return None, votes
    return best[0][0], votes


def detect(lp, riwayat=RIWAYAT) -> Guess:
    score, surah = detect_surah(lp)[0]
    riwayah, votes = detect_riwayah(lp, surah, riwayat)
    return Guess(surah, score, riwayah, votes)
