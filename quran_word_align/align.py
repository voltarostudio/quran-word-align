"""CTC forced alignment of a Quran recitation against the mushaf's words, on quran-asr-tiny.

Each ayah is aligned in its own window (the ayah's timing from the recording's source, widened by a
margin); a few words of the ayahs either side are aligned with it so they are not taken for its own,
and the space between words is optional. A word the reciter goes back to is heard again, and listed
again. This is the aligner Midad (voltarostudio.com) builds its word timings with.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

MODEL_URL = "https://huggingface.co/Abdou/quran-asr-tiny/resolve/main/model.int8.onnx"
MODEL_SHA256 = "58de6db034bb4f6516b3bc1c68e7a0ac4e77abffe603a550ee87b39dcd0c7ac6"
MODEL = Path.home() / ".cache" / "quran-word-align" / "quran-asr-tiny.int8.onnx"
WORDS = Path(__file__).parent / "data" / "hafs-words.json"


def model_path() -> Path:
    """quran-asr-tiny (MIT, Abdou), fetched once from Hugging Face and checked against its SHA-256."""
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(MODEL_URL, timeout=300).read()
        if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
            raise RuntimeError("quran-asr-tiny: the downloaded model does not match its SHA-256")
        MODEL.write_bytes(data)
    return MODEL


def hafs_words() -> dict[tuple[int, int], list[tuple[int, str]]]:
    """(surah, ayah) → its words in the Hafs mushaf (the King Fahd Complex's text), numbered from 1."""
    data = json.loads(WORDS.read_text(encoding="utf-8"))
    return {tuple(map(int, k.split(":"))): [(i, t) for i, t in v] for k, v in data.items()}


SAMPLE_RATE = 16_000
# blank, the 29 letters, the word separator: tokens.txt of the model (QuranASR.vocabulary)
VOCAB = ["", "ء", "ا", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع",
         "غ", "ف", "ق", "ك", "ل", "م", "ن", "ه", "و", "ي", " "]
INDEX = {c: i for i, c in enumerate(VOCAB)}
BLANK, SPACE = 0, 30
# As ASRText.normalizeWord in the app: harakat and marks dropped, letter forms folded.
FOLD = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا", "ى": "ي", "ئ": "ي", "ے": "ي", "ی": "ي",
        "ؤ": "و", "ة": "ه", "ک": "ك"}
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
    FRAME = 0.04

    def log_probs(self, wave):
        """Per-frame log-probabilities (40 ms frames) for `wave`, each frame heard in several pieces."""
        import numpy as np
        seconds = len(wave) / SAMPLE_RATE
        total = max(int(round(seconds / self.FRAME)), 1)
        probs, count = None, np.zeros(total)
        starts = [0.0] if seconds <= self.PIECE else list(np.arange(0.0, seconds - self.PIECE + self.HOP, self.HOP))
        for start in starts:
            end = min(start + self.PIECE, seconds)
            lp = self._log_probs(wave[int(start * SAMPLE_RATE): int(end * SAMPLE_RATE)])
            if probs is None:
                probs = np.zeros((total, lp.shape[1]))
            step = (end - start) / len(lp)
            index = np.minimum(((start + np.arange(len(lp)) * step) / self.FRAME).astype(int), total - 1)
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


def align(lp, words: list[list[int]], repeat_from: int = 0, repeat_to: int | None = None) -> list[tuple[int, int]]:
    """Each word as heard, in order: (word index, frame its first letter is first heard). A word a
    reciter goes back to is heard again: from the end of a word the path may return to the start of
    it or of an earlier one, both among words[repeat_from:repeat_to] (REPEAT_PENALTY keeps it from
    inventing repeats). Words with no letters are left out."""
    import numpy as np
    spoken = [i for i, w in enumerate(words) if w]
    labels, firsts, lasts = [BLANK], [], []
    for k, i in enumerate(spoken):
        if k:
            labels += [SPACE, BLANK]
        firsts.append(len(labels))
        for c in words[i]:
            labels += [c, BLANK]
        lasts.append(len(labels) - 2)
    lab = np.array(labels)
    firsts_a, lasts_a = np.array(firsts), np.array(lasts)
    within = np.array([repeat_from <= i < (len(words) if repeat_to is None else repeat_to) for i in spoken])
    S, T, K = len(labels), len(lp), len(spoken)
    can_repeat = within.copy()
    # Words before repeat_from and after repeat_to are context: the path may begin at any of the words
    # up to the first of its own, and end after any from the last of its own, so context the window
    # doesn't reach is skipped rather than forced onto the ayah's own words.
    own_last = max([k for k, i in enumerate(spoken) if i < (len(words) if repeat_to is None else repeat_to)], default=K - 1)
    own_first = min([k for k, i in enumerate(spoken) if i >= repeat_from], default=0)
    entries = sorted({x for k in range(own_first + 1) for x in (firsts[k] - 1, firsts[k])})
    exits = sorted({x for k in range(own_last, K) for x in (lasts[k], lasts[k] + 1)})
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
        # to the start of any word i <= j.
        end_state = np.where(score[lasts_a] >= score[lasts_a + 1], lasts_a, lasts_a + 1)
        end_score = np.where(within, score[end_state], NEG)
        order = np.maximum.accumulate(end_score[::-1])[::-1]
        src = np.empty(K, np.int64)
        best_j = K - 1
        for k in range(K - 1, -1, -1):
            if end_score[k] >= end_score[best_j]:
                best_j = k
            src[k] = best_j
        again = np.where(can_repeat, order - REPEAT_PENALTY, NEG)
        take = again > new[firsts_a]
        new[firsts_a] = np.where(take, again, new[firsts_a])
        best[firsts_a] = np.where(take, 6, best[firsts_a])
        jump_from[t] = end_state[src]
        for s0 in entries:
            if lead > new[s0]:
                new[s0], best[s0] = lead, 5
        end = max(exits, key=lambda x: score[x])
        if score[end] > tail:
            tail, tail_from, tail_start = score[end], end, t
        if tail > NEG / 2:
            tail += filler[t]
        score = new + lp[t, lab]
        back[t] = best
        lead += filler[t]
    end = max(exits, key=lambda x: score[x])
    if tail > score[end]:
        t, s = tail_start - 1, tail_from
    else:
        t, s = T - 1, end
    word_of = {f: k for k, f in enumerate(firsts)}
    heard: list[tuple[int, int]] = []
    while t >= 0:
        b = int(back[t, s])
        if s in word_of and b != 0:
            heard.append((spoken[word_of[s]], t))
        if b == 5:
            break
        s = int(jump_from[t, word_of[s]]) if b == 6 else s - b
        t -= 1
    return heard[::-1]


def decode(path: Path):
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def align_recording(surah: int, audio: Path, windows: list[tuple[int, float, float, int]], words, model: Model,
                     margin: float) -> dict:
    """Each ayah of a recording, aligned in its window (ayah, start s, end s, end ms) widened by `margin`."""
    wave = decode(audio)
    length = len(wave) / SAMPLE_RATE
    result = {}
    for n, start, end, end_ms in windows:
        tokens = words[(surah, n)]
        # Al-Fatiha's basmala is heard only in a window that ends with it: the model leaves a basmala
        # out when more follows (as the basmala before a surah is not part of it).
        basmala = (surah, n) == (1, 1)
        a, b = max(start - margin, 0.0), min(end + (0.3 if basmala else margin), length)
        if b - a < 0.5:
            continue
        # The window reaches into the ayahs either side: their nearest words are aligned too, so they
        # are not taken for this ayah's (or for a repeat of them), and then left out.
        before = words.get((surah, n - 1), [])[-CONTEXT:]
        after = [] if basmala else words.get((surah, n + 1), [])[:CONTEXT]
        lp = model.log_probs(wave[int(a * SAMPLE_RATE): int(b * SAMPLE_RATE)])
        step = (b - a) / len(lp)
        heard = align(lp, [letters(t) for _, t in before + tokens + after], repeat_from=len(before),
                      repeat_to=len(before) + len(tokens))
        own = range(len(before), len(before) + len(tokens))
        starts = [(tokens[i - len(before)][0], round((a + f * step) * 1000)) for i, f in heard if i in own]
        ends = [s for _, s in starts[1:]] + [end_ms]
        result[n] = [[token, s, max(e, s + 40)] for (token, s), e in zip(starts, ends)]
    return result


