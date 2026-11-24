"""CTC forced alignment of a Quran recitation against the mushaf's words, on quran-asr-tiny.

The recording is heard once, as letter probabilities every 40 ms. Each ayah is then aligned in its
own window: the ayah's timing from the recording's source, or, without one, the ayah's place as found
by following the whole surah (`find_ayahs`). A few words of the ayahs either side are aligned with it
so they are not taken for its own, and the space between words is optional. A word the reciter goes
back to is heard again, and listed again. This is the aligner Midad (voltarostudio.com) builds its
word timings with.
"""

from __future__ import annotations

from dataclasses import dataclass
import functools
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

MODEL_URL = "https://huggingface.co/Abdou/quran-asr-tiny/resolve/main/model.int8.onnx"
MODEL_SHA256 = "58de6db034bb4f6516b3bc1c68e7a0ac4e77abffe603a550ee87b39dcd0c7ac6"
MODEL = Path.home() / ".cache" / "quran-word-align" / "quran-asr-tiny.int8.onnx"
DATA = Path(__file__).parent / "data"


def model_path() -> Path:
    """quran-asr-tiny (MIT, Abdou), fetched once from Hugging Face and checked against its SHA-256."""
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(MODEL_URL, timeout=300).read()
        if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
            raise RuntimeError("quran-asr-tiny: the downloaded model does not match its SHA-256")
        MODEL.write_bytes(data)
    return MODEL


Words = dict[tuple[int, int], list[tuple[int, str]]]


@functools.lru_cache(maxsize=None)
def mushaf_words(riwayah: str = "hafs") -> Words:
    """(surah, ayah) → its words in the King Fahd Complex's mushaf of `riwayah`, numbered from 1."""
    data = json.loads((DATA / f"{riwayah}-words.json").read_text(encoding="utf-8"))
    return {tuple(map(int, k.split(":"))): [(i, t) for i, t in v] for k, v in data.items()}


def hafs_words() -> Words:
    return mushaf_words("hafs")


RIWAYAT = ("hafs", "warsh", "qalun")


def basmala_words() -> list[tuple[int, str]]:
    """The basmala, as the Hafs mushaf writes it (its first ayah): heard before every surah but
    at-Tawbah, in every riwayah, and an ayah only of Hafs's al-Fatiha."""
    return hafs_words()[(1, 1)]


def is_basmala(tokens: list[tuple[int, str]]) -> bool:
    return [letters(t) for _, t in tokens] == [letters(t) for _, t in basmala_words()]


SAMPLE_RATE = 16_000
FRAME = 0.04                       # seconds per frame of the model's output
FRAME_SAMPLES = int(FRAME * SAMPLE_RATE)
# blank, the 29 letters, the word separator: tokens.txt of the model (QuranASR.vocabulary)
VOCAB = ["", "ء", "ا", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع",
         "غ", "ف", "ق", "ك", "ل", "م", "ن", "ه", "و", "ي", " "]
INDEX = {c: i for i, c in enumerate(VOCAB)}
BLANK, SPACE = 0, 30
# As ASRText.normalizeWord in the app: harakat and marks dropped, letter forms folded. The alefs of
# the Warsh and Qalun mushafs (U+0870–U+0879, wasl and the like) are alefs, and ۑ a ya.
FOLD = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا", "ى": "ي", "ئ": "ي", "ے": "ي", "ی": "ي",
        "ۑ": "ي", "ؤ": "و", "ة": "ه", "ک": "ك", **{chr(c): "ا" for c in range(0x0870, 0x087A)}}
FILLER_PENALTY = 1.0
REPEAT_PENALTY = 8.0
# Words of the ayahs either side aligned with each ayah (left out after).
CONTEXT = 4


def letters(word: str) -> list[int]:
    out = []
    for ch in word:
        v = ord(ch)
        if (0x064B <= v <= 0x065F or v == 0x0670 or 0x06D6 <= v <= 0x06ED or v in (0x0640, 0x200F)
                or 0x0660 <= v <= 0x0669 or 0x30 <= v <= 0x39):
            continue
        ch = FOLD.get(ch, ch)
        if ch in INDEX and ch != " ":
            out.append(INDEX[ch])
    return out


class Model:
    def __init__(self):
        import kaldi_native_fbank as knf
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(model_path()), options)
        self.fbank = knf.FbankOptions()
        self.fbank.frame_opts.dither = 0
        self.fbank.frame_opts.snip_edges = False
        self.fbank.mel_opts.num_bins = 80
        self.fbank.mel_opts.high_freq = -400
        self.knf = knf

    # The model is unsteady on its own: the same opening heard in 7 s is perfect, in 8 s garbled, in
    # 9 s left out. So each moment is heard in several pieces that start at different points, and
    # their letter probabilities are averaged.
    PIECE = 6.0
    HOP = 2.0

    def log_probs(self, wave):
        """Per-frame log-probabilities (40 ms frames) for `wave`, each frame heard in several pieces."""
        import numpy as np
        seconds = len(wave) / SAMPLE_RATE
        total = max(int(round(seconds / FRAME)), 1)
        probs, count = None, np.zeros(total)
        starts = [0.0] if seconds <= self.PIECE else list(np.arange(0.0, seconds - self.PIECE + self.HOP, self.HOP))
        for start in starts:
            end = min(start + self.PIECE, seconds)
            lp = self._log_probs(wave[int(start * SAMPLE_RATE): int(end * SAMPLE_RATE)])
            if probs is None:
                probs = np.zeros((total, lp.shape[1]))
            step = (end - start) / len(lp)
            index = np.minimum(((start + np.arange(len(lp)) * step) / FRAME).astype(int), total - 1)
            np.add.at(probs, index, np.exp(lp))
            np.add.at(count, index, 1)
        count[count == 0] = 1
        return np.log(np.maximum(probs / count[:, None], 1e-12)).astype(np.float32)

    def _log_probs(self, wave):
        import numpy as np
        fb = self.knf.OnlineFbank(self.fbank)
        fb.accept_waveform(SAMPLE_RATE, wave.tolist())
        fb.input_finished()
        feats = np.stack([fb.get_frame(i) for i in range(fb.num_frames_ready)]).astype(np.float32)
        lp, n = self.session.run(["log_probs", "log_probs_len"],
                                 {"x": feats[None], "x_lens": np.array([len(feats)], dtype=np.int64)})
        return lp[0][: n[0]]


@dataclass
class Heard:
    word: int          # index into the words aligned
    start: int         # frame its first letter is first heard
    end: int           # last frame of its last letter
    confidence: float  # how clearly its letters were heard, 0–1


def align(lp, words: list[list[int]], repeat_from: int = 0, repeat_to: int | None = None,
          free_end: bool = False) -> list[Heard]:
    """Each word as heard, in order. A word a reciter goes back to is heard again: from the end of a
    word the path may return to the start of it or of an earlier one, both among
    words[repeat_from:repeat_to] (REPEAT_PENALTY keeps it from inventing repeats). Words outside
    that range are context: the path may begin at any of them up to the first of its own, and end
    after any from the last of its own (with `free_end`, after any of its own). Words with no letters
    are left out.

    A word's confidence is the mean, over its letters, of the highest probability the model gave the
    letter while the path was on it: near 1 when every letter was clearly heard where it was placed."""
    import numpy as np
    spoken = [i for i, w in enumerate(words) if w]
    labels, firsts, lasts, owner = [BLANK], [], [], [-1]
    for k, i in enumerate(spoken):
        if k:
            labels += [SPACE, BLANK]
            owner += [-1, -1]
        firsts.append(len(labels))
        for c in words[i]:
            labels += [c, BLANK]
            owner += [k, -1]
        lasts.append(len(labels) - 2)
    lab = np.array(labels)
    owner_a = np.array(owner)
    firsts_a, lasts_a = np.array(firsts), np.array(lasts)
    stop = len(words) if repeat_to is None else repeat_to
    within = np.array([repeat_from <= i < stop for i in spoken])
    S, T, K = len(labels), len(lp), len(spoken)
    own_last = max([k for k, i in enumerate(spoken) if i < stop], default=K - 1)
    own_first = min([k for k, i in enumerate(spoken) if i >= repeat_from], default=0)
    if free_end:
        own_last = own_first
    entries = sorted({x for k in range(own_first + 1) for x in (firsts[k] - 1, firsts[k])})
    exits = np.array(sorted({x for k in range(own_last, K) for x in (lasts[k], lasts[k] + 1)}))
    NEG = -1e30
    skip2 = np.zeros(S, bool)
    skip2[2:] = (lab[2:] != BLANK) & (lab[2:] != lab[:-2])
    first = np.zeros(S, bool)
    first[firsts[1:]] = True
    filler = lp.max(1) - FILLER_PENALTY
    score = np.full(S, NEG)
    back = np.zeros((T, S), np.int8)
    jump_from = np.zeros((T, K), np.int32)
    lead = 0.0                                 # still in the filler before the words
    tail, tail_from, tail_start = NEG, -1, -1  # in the filler after them
    arange_k = np.arange(K)
    for t in range(T):
        shifted = np.full((5, S), NEG)
        shifted[0] = score
        shifted[1, 1:] = score[:-1]
        shifted[2, 2:] = np.where(skip2[2:], score[:-2], NEG)
        shifted[3, 3:] = np.where(first[3:], score[:-3], NEG)
        shifted[4, 4:] = np.where(first[4:], score[:-4], NEG)
        best = shifted.argmax(0).astype(np.int8)
        new = shifted.max(0)
        # Back to a word already heard: from the end of word j (its last letter or the blank after)
        # to the start of any word i <= j; src[i] is the j with the best end (the first, on a tie).
        end_state = np.where(score[lasts_a] >= score[lasts_a + 1], lasts_a, lasts_a + 1)
        end_score = np.where(within, score[end_state], NEG)
        order = np.maximum.accumulate(end_score[::-1])[::-1]
        after = np.append(order[1:], NEG)
        src = np.minimum.accumulate(np.where(end_score >= after, arange_k, K)[::-1])[::-1]
        again = np.where(within, order - REPEAT_PENALTY, NEG)
        take = again > new[firsts_a]
        new[firsts_a] = np.where(take, again, new[firsts_a])
        best[firsts_a] = np.where(take, 6, best[firsts_a])
        jump_from[t] = end_state[src]
        for s0 in entries:
            if lead > new[s0]:
                new[s0], best[s0] = lead, 5
        end = exits[np.argmax(score[exits])]
        if score[end] > tail:
            tail, tail_from, tail_start = score[end], end, t
        if tail > NEG / 2:
            tail += filler[t]
        score = new + lp[t, lab]
        back[t] = best
        lead += filler[t]
    end = exits[np.argmax(score[exits])]
    if tail > score[end]:
        t, s = tail_start - 1, int(tail_from)
    else:
        t, s = T - 1, int(end)
    word_of = {f: k for k, f in enumerate(firsts)}
    heard: list[Heard] = []
    best_p: dict[int, float] = {}   # letter state → its highest probability on the path, this word
    last_t = -1
    while t >= 0:
        b = int(back[t, s])
        if owner_a[s] >= 0:
            if not best_p:
                last_t = t
            best_p[s] = max(best_p.get(s, 0.0), float(np.exp(lp[t, lab[s]])))
        if s in word_of and b != 0:
            k = word_of[s]
            confidence = sum(best_p.values()) / len(words[spoken[k]])
            heard.append(Heard(spoken[k], t, last_t, round(confidence, 3)))
            best_p = {}
        if b == 5:
            break
        s = int(jump_from[t, word_of[s]]) if b == 6 else s - b
        t -= 1
    return heard[::-1]


def decode(path: Path):
    import numpy as np
    def run(*force):
        return subprocess.run(["ffmpeg", "-v", "error", *force, "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE),
                               "-f", "f32le", "-"], capture_output=True, check=True).stdout
    try:
        pcm = run()
    except subprocess.CalledProcessError:
        if path.suffix.lower() != ".mp3":
            raise
        pcm = run("-f", "mp3")    # some mp3s are taken by ffmpeg's probe for another format
    return np.frombuffer(pcm, dtype=np.float32)


def loudness(wave):
    """Each frame's loudness in dB."""
    import numpy as np
    n = len(wave) // FRAME_SAMPLES
    frames = wave[: n * FRAME_SAMPLES].reshape(n, FRAME_SAMPLES)
    return 10 * np.log10(np.maximum((frames ** 2).mean(1), 1e-10))


# The voice is taken to have stopped where the recording falls this far below the ayah's loud
# frames, for this long.
QUIET_DB = 30.0
QUIET_FRAMES = 5


def voice_end(db, start: int, limit: int, loud: float) -> int:
    """The frame the voice stops after `start` (the last letter heard), and no later than `limit`."""
    quiet = 0
    for t in range(start, min(limit, len(db))):
        quiet = quiet + 1 if db[t] < loud - QUIET_DB else 0
        if quiet >= QUIET_FRAMES:
            return t - QUIET_FRAMES + 1
    return limit


KEEP_SECONDS = 600.0


@dataclass
class Recording:
    """A recording heard by the model: its letter log-probabilities and loudness, frame by frame."""
    lp: object
    db: object
    wave: object = None        # kept only for short recordings (al-Fatiha), to hear a part again alone
    model: object = None

    @classmethod
    def hear(cls, audio: Path, model: Model) -> "Recording":
        wave = decode(audio)
        keep = len(wave) < KEEP_SECONDS * SAMPLE_RATE
        return cls(model.log_probs(wave), loudness(wave), wave if keep else None, model if keep else None)

    def hear_again(self, f0: int, f1: int):
        """Frames f0..f1 heard by the model on their own, or None when the wave was not kept."""
        if self.wave is None or self.model is None:
            return None
        return self.model.log_probs(self.wave[f0 * FRAME_SAMPLES: f1 * FRAME_SAMPLES])

    @property
    def seconds(self) -> float:
        return len(self.lp) * FRAME


# Following a whole surah: windows of this many seconds, with letters enough for the fastest reciter.
FOLLOW_WINDOW = 60.0
LETTERS_PER_SECOND = 16


def next_words(surah: int, words: Words) -> list[tuple[int, str]]:
    """What a recording of several surahs has after `surah`: the basmala and the next surah's
    opening, aligned as context so what follows the surah is not taken for a repeat of its end."""
    if surah >= 114:
        return []
    opening = [w for n in (1, 2) for w in words.get((surah + 1, n), [])][: 2 * CONTEXT]
    if surah + 1 == 9 or is_basmala(words.get((surah + 1, 1), [])):
        return opening
    return basmala_words() + opening


def find_ayahs(surah: int, rec: Recording, words: Words, first: int = 1, start: float = 0.0,
               then: list[tuple[int, str]] | None = None) -> list[tuple[int, float, float]]:
    """Each ayah's place in a recording of the surah from ayah `first`, heard from `start` seconds,
    found without ayah timings: (ayah, start s, end s). The recording may stop before the surah does.
    The surah is followed a window at a time: the window is aligned with the ayahs
    from the first not yet placed, its path free to end after any word, and every ayah but the last
    it reached is placed; the next window starts a second before that last ayah. A window that places
    no ayah (one longer than the window) is doubled. The basmala before the surah, and anything else
    before its first ayah, is taken in as context or filler; `then`, what follows the surah in the
    recording (`next_words`), as context after its last ayah."""
    ayahs = sorted(n for (s, n) in words if s == surah and n >= first)
    T = len(rec.lp)
    if not ayahs:
        return []
    basmala = [] if first > 1 or surah == 9 or is_basmala(words[(surah, ayahs[0])]) else basmala_words()
    found: dict[int, tuple[int, int]] = {}
    k, t0, window = 0, int(start / FRAME), int(FOLLOW_WINDOW / FRAME)
    while k < len(ayahs):
        t1 = min(t0 + window, T)
        need = (t1 - t0) * FRAME * LETTERS_PER_SECOND
        own, have, j = [], 0, k
        while j < len(ayahs) and (have < need or j <= k + 1):
            for w in words[(surah, ayahs[j])]:
                own.append((ayahs[j], w))
                have += len(letters(w[1]))
            j += 1
        before = (basmala or words.get((surah, first - 1), [])[-CONTEXT:]) if k == 0 else words[(surah, ayahs[k - 1])][-CONTEXT:]
        after = (then or []) if j == len(ayahs) else []
        heard = align(rec.lp[t0:t1], [letters(t) for _, t in before] + [letters(w[1]) for _, w in own] + [letters(t) for _, t in after],
                      repeat_from=len(before), repeat_to=len(before) + len(own), free_end=True)
        mine = [(own[h.word - len(before)][0], h) for h in heard if len(before) <= h.word < len(before) + len(own)]
        if not mine:
            break
        reached = max(a for a, _ in mine)
        # Done when the audio is, or when the path reached the surah's last word.
        done = t1 >= T or (j == len(ayahs) and mine[-1][1].word == len(before) + len(own) - 1)
        last = len(ayahs) if done else ayahs.index(reached)
        for a in ayahs[k:last]:
            hs = [h for b, h in mine if b == a]
            if hs:
                found[a] = (t0 + min(h.start for h in hs), t0 + max(h.end for h in hs))
        if done:
            break
        if last == k:
            if t1 >= T:
                break
            window *= 2
            continue
        start_last = t0 + min(h.start for b, h in mine if b == reached)
        t0 = max(start_last - int(1.0 / FRAME), t0 + 1)
        k, window = last, int(FOLLOW_WINDOW / FRAME)
    return [(a, found[a][0] * FRAME, found[a][1] * FRAME) for a in sorted(found)]


def follow(rec: Recording, words: Words, surah: int, first: int = 1) -> dict[int, list[tuple[int, float, float]]]:
    """A recording that begins at ayah `first` of `surah` and may run on into the surahs after it (a
    juz, say): {surah: [(ayah, start s, end s), ...]}, each surah followed as `find_ayahs` does."""
    out, start = {}, 0.0
    while surah <= 114 and start < rec.seconds - 2.0:
        found = find_ayahs(surah, rec, words, first, start, then=next_words(surah, words))
        if not found:
            break
        out[surah] = found
        last = max(n for (s, n) in words if s == surah)
        if found[-1][0] != last:          # the recording stopped inside this surah
            break
        start, surah, first = found[-1][2], surah + 1, 1
    return out


def align_ayahs(surah: int, rec: Recording, windows: list[tuple[int, float, float]], words: Words,
                margin: float, then: list[tuple[int, str]] | None = None) -> dict:
    """Each ayah aligned in its window (ayah, start s, end s) widened by `margin`:
    {ayah: [[word, start_ms, end_ms, confidence], ...]} in the order heard."""
    length = rec.seconds
    result = {}
    nexts = {n: windows[i + 1][1] for i, (n, _, _) in enumerate(windows[:-1])}
    for n, start, end in windows:
        tokens = words.get((surah, n))
        if not tokens:
            continue
        # Al-Fatiha's basmala is heard only in a window that ends with it: the model leaves a basmala
        # out when more follows (as the basmala before a surah is not part of it).
        basmala = n == 1 and is_basmala(tokens)
        a, b = max(start - margin, 0.0), min(end + (0.3 if basmala else margin), length)
        if b - a < 0.5:
            continue
        # The window reaches into the ayahs either side: their nearest words are aligned too, so they
        # are not taken for this ayah's (or for a repeat of them), and then left out.
        before = words.get((surah, n - 1), [])[-CONTEXT:]
        after = [] if basmala else (words.get((surah, n + 1)) or then or [])[:CONTEXT]
        f0, f1 = int(a / FRAME), int(b / FRAME)
        heard = align(rec.lp[f0:f1], [letters(t) for _, t in before + tokens + after], repeat_from=len(before),
                      repeat_to=len(before) + len(tokens))
        own = [h for h in heard if len(before) <= h.word < len(before) + len(tokens)]
        if not own:
            continue
        # The last word ends where the voice stops, before the next ayah begins.
        limit = int(nexts.get(n, length) / FRAME)
        last = max(own, key=lambda h: h.end)
        span = rec.db[f0 + own[0].start: f0 + last.end + 1]
        loud = float(sorted(span)[int(len(span) * 0.9)]) if len(span) else 0.0
        stop = voice_end(rec.db, f0 + last.end + 1, max(limit, f0 + last.end + 1), loud)
        starts = [f0 + h.start for h in own]
        # A word ends where the next begins, or where the voice stops if the reciter pauses first.
        ends = [voice_end(rec.db, f0 + h.end + 1, nxt, loud) for h, nxt in zip(own, starts[1:])] + [stop]
        result[n] = [[tokens[h.word - len(before)][0], round(s * FRAME * 1000), round(max(e, s + 1) * FRAME * 1000),
                      h.confidence] for h, s, e in zip(own, starts, ends)]
        if basmala and sum(h.confidence for h in own) / len(tokens) < UNHEARD:
            alone = basmala_alone(rec, f0, stop, tokens, loud)
            if alone:
                result[n] = alone
            elif sum(h.confidence for h in own) / len(tokens) < ABSENT:
                del result[n]          # not heard even alone: the recording begins at al-hamdu
    return result


# Al-Fatiha's basmala is sometimes not heard where the surah follows it (about one recording in ten),
# or heard in the isti'adha before it. Heard again on its own, cut from the recording, it is.
UNHEARD = 0.6
ABSENT = 0.2


# The isti'adha some reciters say before it, so its words are not taken for the basmala's (letters
# as the model spells them; not Quran text).
ISTIADHA = "اعوذ بالله من الشيطان الرجيم"
LONGEST_WORD = 2.5         # seconds a basmala word but the last (which holds the madd) may last


def basmala_alone(rec: Recording, f0: int, f1: int, tokens: list[tuple[int, str]], loud: float) -> list[list] | None:
    f1 = min(f1, len(rec.lp))
    lp = rec.hear_again(f0, f1)
    if lp is None:
        return None
    own = [letters(t) for _, t in tokens]
    best = None
    for before in ([], [letters(t) for t in ISTIADHA.split()]):
        heard = [h for h in align(lp, before + own) if h.word >= len(before)]
        if len(heard) != len(own):
            continue
        score = sum(h.confidence for h in heard) / len(heard)
        if best is None or score > best[0]:
            best = (score, heard)
    if best is None or best[0] < UNHEARD:
        return None
    heard = best[1]
    if any((h.end - h.start) * FRAME > LONGEST_WORD for h in heard[:-1]):
        return None
    starts = [f0 + h.start for h in heard]
    ends = [voice_end(rec.db, f0 + h.end + 1, nxt, loud) for h, nxt in zip(heard, starts[1:])]
    ends.append(voice_end(rec.db, f0 + heard[-1].end + 1, f1, loud))
    return [[w, round(s * FRAME * 1000), round(max(e, s + 1) * FRAME * 1000), h.confidence]
            for (w, _), h, s, e in zip(tokens, heard, starts, ends)]


def align_recording(surah: int, audio: Path, words: Words, model: Model,
                    windows: list[tuple[int, float, float]] | None = None, margin: float = 1.0) -> dict:
    """A recording of a whole surah, aligned word by word. With `windows` (ayah, start s, end s), the
    recording's own ayah timings, each ayah is aligned in its window widened by `margin`; without,
    the ayahs are found first (`find_ayahs`)."""
    rec = Recording.hear(audio, model)
    if windows is None:
        windows = find_ayahs(surah, rec, words)
    return align_ayahs(surah, rec, windows, words, margin)
