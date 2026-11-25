"""Whose voice says each basmala: a basmala is kept only when it is said in the voice of the reciter who
reads the surah after it. Some of mp3quran's files open with a basmala in another voice.

    python dataset/voice.py PLACES.json AUDIO SPEAKER.onnx OUT.json

PLACES.json: what dataset/basmala.py wrote; AUDIO: the mp3 cache, a folder mp3quran-<id> per read;
SPEAKER.onnx: WeSpeaker's ResNet34 speaker model (voxceleb_resnet34_LM.onnx, from
huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM). OUT.json: {read id: {"files": {surah:
{"basmala": similarity to the voice after it in the same file, "reciter": similarity to the reciter's
voice}}, "basmala": ..., "istiadha": ... (the clips chosen for the reciter)}}.

A voice is a speaker embedding of the clip; two clips' voices are compared by the cosine of their
embeddings. The reciter's voice is the mean over their files of the SURAH_SECONDS after each first word.
"""

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from quran_word_align.align import SAMPLE_RATE, decode

SURAH_SECONDS = 12.0     # how much of the surah, from its first word, stands for the reciter's voice
SAME_VOICE = 0.35        # a basmala is in the reciter's voice when like the surah after it, or the reciter, at least this much


def mel_banks(bins: int = 80, fft: int = 512, low: float = 20.0) -> np.ndarray:
    """Kaldi's triangular mel filters over the fft's first fft/2 bins."""
    mel = lambda f: 1127.0 * np.log(1.0 + f / 700.0)
    lo, hi = mel(low), mel(SAMPLE_RATE / 2)
    edges = lo + np.arange(bins + 2) * (hi - lo) / (bins + 1)
    f = mel(np.arange(fft // 2) * SAMPLE_RATE / fft)
    left, centre, right = edges[:-2, None], edges[1:-1, None], edges[2:, None]
    up, down = (f - left) / (centre - left), (right - f) / (right - centre)
    return np.maximum(0.0, np.minimum(up, down)) * ((f > left) & (f < right))


BANKS = mel_banks()
WINDOW = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(400) / 399)) ** 0.85     # Kaldi's povey window


def fbank(wave: np.ndarray) -> np.ndarray:
    """Kaldi-style log mel filterbank (25 ms frames, 10 ms apart, 80 bins), mean removed, as WeSpeaker takes it."""
    x = wave.astype(np.float64) * 32768
    n = 1 + (len(x) - 400) // 160
    frames = x[np.arange(400)[None, :] + 160 * np.arange(n)[:, None]]
    frames -= frames.mean(1, keepdims=True)
    frames[:, 1:] -= 0.97 * frames[:, :-1].copy()
    frames[:, 0] *= 0.03
    power = np.abs(np.fft.rfft(frames * WINDOW, 512)[:, :256]) ** 2
    feats = np.log(np.maximum(power @ BANKS.T, np.finfo(np.float32).eps))
    return (feats - feats.mean(0)).astype(np.float32)


class Voices:
    def __init__(self, model: Path):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(model), opts)

    def __call__(self, wave: np.ndarray) -> np.ndarray | None:
        if len(wave) < SAMPLE_RATE // 2:
            return None
        e = self.session.run(None, {"feats": fbank(wave)[None]})[0][0]
        return e / np.linalg.norm(e)


def cut(wave: np.ndarray, start_ms: float, end_ms: float) -> np.ndarray:
    return wave[int(start_ms * SAMPLE_RATE / 1000): int(end_ms * SAMPLE_RATE / 1000)]


def same_voice(v: dict) -> bool:
    """Whether a clip's voice is the reciter's: like the surah after it in its file, or the reciter's mean voice."""
    known = [x for x in (v.get("basmala"), v.get("reciter")) if x is not None]
    return not known or max(known) >= SAME_VOICE


def cos(a, b) -> float | None:
    return None if a is None or b is None else round(float(a @ b / np.linalg.norm(b)), 3)


def read_voices(job) -> tuple[str, dict]:
    read, places, audio, model = job
    voices, folder = Voices(model), audio / f"mp3quran-{read}"
    surahs, basmalas, waves = {}, {}, {}
    for surah, row in places["openings"].items():
        mp3, first = folder / f"{int(surah):03d}.mp3", row.get("first_word_ms")
        if first is None or not mp3.exists():
            continue
        wave = decode(mp3, first / 1000 + SURAH_SECONDS)
        waves[surah] = wave
        surahs[surah] = voices(cut(wave, first, first + SURAH_SECONDS * 1000))
        if row.get("basmala_words"):
            w = row["basmala_words"]
            basmalas[surah] = voices(cut(wave, w[0][1], w[-1][2]))
    known = [e for e in surahs.values() if e is not None]
    reciter = np.mean(known, 0) if known else None
    out = {"files": {s: {"basmala": cos(b, surahs.get(s)), "reciter": cos(b, reciter)} for s, b in basmalas.items()}}
    for kind in ("basmala", "istiadha"):
        chosen = places.get(kind)
        if chosen:
            s = str(chosen["surah"])
            wave = waves.get(s)
            if wave is None:
                wave = decode(folder / f"{int(s):03d}.mp3", chosen["end_ms"] / 1000 + 1)
            out[kind] = {"surah": chosen["surah"], "reciter": cos(voices(cut(wave, chosen["start_ms"], chosen["end_ms"])), reciter)}
    return read, out


def main() -> None:
    places_path, audio, model, out = (Path(a) for a in sys.argv[1:5])
    places = json.loads(places_path.read_text())
    only = sys.argv[5:]
    jobs = [(r, p, audio, model) for r, p in places.items() if not only or r in only]
    found = {}
    with Pool(4) as pool:
        for read, voices in pool.imap_unordered(read_voices, jobs):
            found[read] = voices
            low = [s for s, v in voices["files"].items() if not same_voice(v)]
            print(read, {k: voices.get(k) for k in ("basmala", "istiadha")}, "files:", len(voices["files"]),
                  "other voice:", low, flush=True)
    out.write_text(json.dumps(found, indent=1))


if __name__ == "__main__":
    main()
