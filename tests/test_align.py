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


def test_detect_surah_tells_apart_surahs_that_open_alike():
    from quran_word_align.detect import detect_surah
    W = A.hafs_words()
    # Al Imran opens as al-Baqarah does (الم), then goes its own way.
    flat = [A.letters(t) for key in [(1, 1), (3, 1), (3, 2), (3, 3)] for _, t in W[key]]
    spans, _, frames = speak(flat)
    (score, surah), (_, second) = detect_surah(synthetic(spans, frames))[:2]
    assert surah == 3
    assert second != surah and score > 0.5


def test_follow_runs_on_into_the_next_surah():
    W = A.hafs_words()
    keys = [(1, 1)] + [(112, n) for n in range(1, 5)] + [(1, 1)] + [(113, n) for n in range(1, 6)]
    flat = [A.letters(t) for key in keys for _, t in W[key]]
    spans, firsts, frames = speak(flat, gap=8)
    rec = A.Recording(synthetic(spans, frames), np.zeros(frames))
    found = A.follow(rec, W, 112)
    assert {s: [a for a, _, _ in f] for s, f in found.items()} == {112: [1, 2, 3, 4], 113: [1, 2, 3, 4, 5]}
    assert round(found[113][0][1] / A.FRAME) == firsts[4 + 15 + 4]      # after al-Ikhlas and the basmala


def test_locate_finds_a_start_inside_a_surah():
    from quran_word_align.detect import locate
    W = A.hafs_words()
    flat = [A.letters(t) for n in range(10, 16) for _, t in W[(36, n)]]
    spans, _, frames = speak(flat)
    _, surah, ayah = locate(synthetic(spans, frames))[0]
    assert (surah, ayah) in [(36, 9), (36, 10), (36, 11)]


class _Hears:
    """A model that hears, in a part cut alone, what the whole recording's hearing left out."""
    def __init__(self, lp):
        self.lp = lp

    def log_probs(self, wave):
        return self.lp[: len(wave) // A.FRAME_SAMPLES]


def test_fatiha_basmala_unheard_is_heard_alone():
    W = A.hafs_words()
    words = [A.letters(t) for key in [(1, 1), (1, 2)] for _, t in W[key]]
    spans, firsts, frames = speak(words, gap=8)
    alone = synthetic(spans, frames)
    unheard = synthetic([(t, c) for t, c in spans if t >= firsts[4]], frames)   # the basmala left out
    wave = np.zeros(frames * A.FRAME_SAMPLES, np.float32)
    windows = [(1, 0.0, (firsts[4] - 2) * A.FRAME), (2, firsts[4] * A.FRAME, frames * A.FRAME)]
    rec = A.Recording(unheard, np.zeros(frames), wave, _Hears(alone))
    out = A.align_ayahs(1, rec, windows, W, margin=0.0)
    assert [round(s / 1000 / A.FRAME) for _, s, _, _ in out[1]] == firsts[:4]
    assert min(c for *_, c in out[1]) > 0.6
    # And a recording with no basmala at all (it begins at al-hamdu) gets none.
    rec = A.Recording(unheard, np.zeros(frames), wave, _Hears(unheard))
    assert 1 not in A.align_ayahs(1, rec, windows, W, margin=0.0)


def test_decode_keeps_voice_in_antiphase_stereo(tmp_path):
    """A recording whose two channels cancel out when mixed is still heard (hassan-saleh, surah 55)."""
    import subprocess
    import numpy as np
    from quran_word_align.align import decode
    f = tmp_path / "antiphase.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-af", "pan=stereo|c0=c0|c1=-1*c0", str(f)], check=True)
    assert np.abs(decode(f)).mean() > 0.05


def test_decode_keeps_voice_when_channels_cancel_in_part(tmp_path):
    """Channels in phase, then in antiphase for the rest (hassan-saleh, surahs 23 and 42) are still heard."""
    import subprocess
    import numpy as np
    from quran_word_align.align import decode
    f = tmp_path / "part.mp3"
    a = tmp_path / "a.wav"; b = tmp_path / "b.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
                    "-af", "pan=stereo|c0=c0|c1=c0", str(a)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=25",
                    "-af", "pan=stereo|c0=c0|c1=-1*c0", str(b)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(a), "-i", str(b), "-filter_complex", "concat=n=2:v=0:a=1",
                    str(f)], check=True)
    wave = decode(f)
    assert np.abs(wave[-16000:]).mean() > 0.05


def test_basmala_words_are_given_only_when_clear():
    """A basmala is lit word by word only where each word was heard clearly and all four end before
    ayah 1: a light must never run ahead of the reciter."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "dataset"))
    from basmala import lit_basmala
    words = [[1, 400, 900, 0.9], [2, 900, 1500, 0.9], [3, 1500, 2300, 0.9], [4, 2300, 3200, 0.9]]
    row = {"has_basmala": 1, "first_word_ms": 3600, "basmala_words": words}
    assert lit_basmala(row) == words
    assert lit_basmala({**row, "basmala_words": words[:2] + [[3, 1500, 2300, 0.3]] + words[3:]}) is None
    assert lit_basmala({**row, "first_word_ms": 3000}) is None          # runs into ayah 1
    assert lit_basmala({**row, "has_basmala": None}) is None


def test_basmala_in_another_voice_is_caught():
    """A basmala is taken as the reciter's own only when its voice is like the surah after it in the same
    file, or like the reciter's voice over all their files; else it is another reader's and is dropped."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "dataset"))
    from voice import SAME_VOICE, same_voice
    assert same_voice({"basmala": SAME_VOICE + 0.3, "reciter": SAME_VOICE - 0.2})
    assert same_voice({"basmala": SAME_VOICE - 0.2, "reciter": SAME_VOICE + 0.3})
    assert not same_voice({"basmala": 0.05, "reciter": 0.1})               # yasser-dosari's files open so
    assert same_voice({"basmala": None, "reciter": None})                   # not heard: nothing to judge


def test_voice_features_put_a_tone_in_its_own_mel_bin():
    """The speaker model takes Kaldi's log mel filterbank; a 1 kHz tone must land in the bin centred
    nearest 1 kHz, or every voice comparison is made on the wrong features."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "dataset"))
    from voice import fbank
    t = np.arange(A.SAMPLE_RATE) / A.SAMPLE_RATE
    tone = 0.3 * np.sin(2 * np.pi * 1000 * t) * (t < 0.5)       # the tone, then near silence: the mean is taken out
    feats = fbank(tone + 1e-4 * np.random.default_rng(0).standard_normal(len(t)))
    assert feats.shape == (98, 80)
    mel = lambda f: 1127 * np.log(1 + f / 700)                     # Kaldi's mel scale, 80 bins from 20 Hz
    centre = mel(20) + (np.argmax(feats[10]) + 1) * (mel(8000) - mel(20)) / 81
    assert abs(700 * (np.exp(centre / 1127) - 1) - 1000) < 40
