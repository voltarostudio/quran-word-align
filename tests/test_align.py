"""The aligner on letter probabilities made by hand, so the tests need neither the model nor audio."""

import hashlib
import json

import numpy as np
import pytest

from quran_word_align import align as A
from quran_word_align.formats import FORMATS

# The words files are the King Fahd Complex's text, split by tools/mushaf_words.py and never edited
# by hand. A change to any of them must be made by that script and the hash updated here on purpose.
WORDS_SHA256 = {
    "hafs": "f5e3d64b1e3979989b2851a3e3eab5cd50fdcc30e1b1c131f77dfefc29f9be69",
    "warsh": "813eec0ddb6bb4adf94fbec80397536f6c3731c6b03b2da88a3563a0dd6cce9c",
    "qalun": "3ba8a47f9574582d887d17e024c6784b28b452caf4fde6acc37b21ff0dda7331",
}


def test_words_files_are_the_complexs():
    for riwayah, digest in WORDS_SHA256.items():
        data = (A.DATA / f"{riwayah}-words.json").read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, f"{riwayah}-words.json changed"


@pytest.mark.parametrize("riwayah,ayahs,words", [("hafs", 6236, 77432), ("warsh", 6214, 77427), ("qalun", 6214, 77427)])
def test_mushaf_counts(riwayah, ayahs, words):
    w = A.mushaf_words(riwayah)
    assert len(w) == ayahs
    assert sorted({s for s, _ in w}) == list(range(1, 115))
    if words:
        assert sum(len(v) for v in w.values()) == words
    for tokens in w.values():
        assert [i for i, _ in tokens] == list(range(1, len(tokens) + 1))
        assert all(A.letters(t) for _, t in tokens), "every word has letters the model knows"


def test_letters_fold_every_riwayah():
    assert A.letters("ٱلرَّحۡمَٰنِ") == [A.INDEX[c] for c in "الرحمن"]
    assert A.letters("ࡴ۬لْحَمْدُ") == [A.INDEX[c] for c in "الحمد"]       # Warsh's alef wasl
    assert A.is_basmala(A.mushaf_words("hafs")[(1, 1)])
    assert not A.is_basmala(A.mushaf_words("warsh")[(1, 1)])           # Warsh counts it no ayah


def synthetic(spans: list[tuple[int, int]], frames: int) -> np.ndarray:
    """Log-probabilities that hear label `l` at frame `t` for each (t, l), and blank elsewhere."""
    p = np.full((frames, len(A.VOCAB)), 0.01 / (len(A.VOCAB) - 1))
    p[:, A.BLANK] = 0.99
    for t, label in spans:
        p[t] = 0.01 / (len(A.VOCAB) - 1)
        p[t, label] = 0.99
    return np.log(p).astype(np.float32)


def speak(words: list[list[int]], start: int = 10, gap: int = 6, step: int = 3):
    """Frames at which each word's letters are heard, one after another."""
    spans, firsts, t = [], [], start
    for w in words:
        firsts.append(t)
        for c in w:
            spans.append((t, c))
            t += step
        t += gap
    return spans, firsts, t + 20


def test_align_places_each_word():
    words = [A.letters(t) for _, t in A.hafs_words()[(112, 1)]]
    spans, firsts, frames = speak(words)
    heard = A.align(synthetic(spans, frames), words)
    assert [h.word for h in heard] == list(range(len(words)))
    assert [h.start for h in heard] == firsts
    assert all(h.confidence > 0.9 for h in heard)


def test_align_follows_a_repeat():
    words = [A.letters(t) for _, t in A.hafs_words()[(112, 1)]]   # قل هو الله أحد
    spans, firsts, frames = speak(words[:3] + words[1:])          # ... الله، هو الله أحد
    heard = A.align(synthetic(spans, frames), words)
    assert [h.word for h in heard] == [0, 1, 2, 1, 2, 3]


def test_low_confidence_where_letters_are_not_heard():
    words = [A.letters(t) for _, t in A.hafs_words()[(112, 1)]]
    spans, _, frames = speak(words)
    spans = [(t, c) for t, c in spans if t < 20 or t > 40]        # the middle not heard clearly
    heard = A.align(synthetic(spans, frames), words)
    assert min(h.confidence for h in heard) < 0.5


def test_find_ayahs_without_timings():
    W = A.hafs_words()
    ayahs = [W[(112, n)] for n in range(1, 5)]
    flat = [A.letters(t) for a in [W[(1, 1)]] + ayahs for _, t in a]  # the basmala first
    spans, firsts, frames = speak(flat, gap=8)
    db = np.zeros(frames)
    rec = A.Recording(synthetic(spans, frames), db)
    found = A.find_ayahs(112, rec, W)
    starts = [firsts[4], firsts[8], firsts[10], firsts[14]]       # after the basmala's 4 words
    assert [a for a, _, _ in found] == [1, 2, 3, 4]
    assert [round(s / A.FRAME) for _, s, _ in found] == starts


def test_voice_end():
    db = np.array([-5.0] * 10 + [-60.0] * 10 + [-5.0] * 5)
    assert A.voice_end(db, 0, 25, loud=-5.0) == 10
    assert A.voice_end(db, 0, 8, loud=-5.0) == 8                  # no later than the limit


def test_formats():
    W = A.hafs_words()
    result = {"1": [[1, 1000, 1500, 0.9], [2, 1500, 2100, 0.8]], "2": [[1, 2500, 3000, 0.95], [2, 3000, 3600, 0.7]]}
    out = {name: f(112, result, W) for name, f in FORMATS.items()}
    assert json.loads(out["json"])["1"][0] == [1, 1000, 1500, 0.9]
    assert out["csv"].splitlines()[1] == "112,1,1,1000,1500,0.9,قُلۡ"
    assert out["srt"].startswith("1\n00:00:01,000 --> 00:00:02,100\nقُلۡ هُوَ")
    assert "<00:00:01.500>هُوَ" in out["vtt"]
    seg = json.loads(out["segments"])["verse_timings"][0]
    assert seg["verse_key"] == "112:1" and seg["segments"][0] == [1, 1000, 1500]
