// quran-word-align in the browser: the same steps as quran_word_align/align.py, ported line by line.
// The model runs with onnxruntime-web; nothing leaves the page.

export const SAMPLE_RATE = 16000;
export const FRAME = 0.04;
const FRAME_SAMPLES = 640;
export const VOCAB = ["", "ء", "ا", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع",
  "غ", "ف", "ق", "ك", "ل", "م", "ن", "ه", "و", "ي", " "];
const V = VOCAB.length;
const INDEX = Object.fromEntries(VOCAB.map((c, i) => [c, i]));
const BLANK = 0, SPACE = 30;
const FOLD = { "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا", "ى": "ي", "ئ": "ي", "ے": "ي", "ی": "ي",
  "ۑ": "ي", "ؤ": "و", "ة": "ه", "ک": "ك" };
for (let c = 0x0870; c < 0x087a; c++) FOLD[String.fromCharCode(c)] = "ا";
const FILLER_PENALTY = 1.0, REPEAT_PENALTY = 8.0, CONTEXT = 4;
const NEG = -1e30;

export function letters(word) {
  const out = [];
  for (const ch0 of word) {
    const v = ch0.codePointAt(0);
    if ((v >= 0x064b && v <= 0x065f) || v === 0x0670 || (v >= 0x06d6 && v <= 0x06ed) || v === 0x0640 || v === 0x200f
      || (v >= 0x0660 && v <= 0x0669) || (v >= 0x30 && v <= 0x39)) continue;
    const ch = FOLD[ch0] ?? ch0;
    if (ch in INDEX && ch !== " ") out.push(INDEX[ch]);
  }
  return out;
}

// ---- Features: Kaldi's 80-bin log mel filterbank, as kaldi-native-fbank computes it (dither 0,
// snip_edges false, high_freq -400, povey window, pre-emphasis 0.97, 512-point FFT).

const FB = (() => {
  const N = 400, NFFT = 512, BINS = 80, low = 20, high = SAMPLE_RATE / 2 - 400;
  const window = new Float64Array(N);
  for (let i = 0; i < N; i++) window[i] = Math.pow(0.5 - 0.5 * Math.cos(2 * Math.PI * i / (N - 1)), 0.85);
  const mel = (f) => 1127 * Math.log(1 + f / 700);
  const mlow = mel(low), mhigh = mel(high), delta = (mhigh - mlow) / (BINS + 1);
  const width = SAMPLE_RATE / NFFT;
  const banks = [];
  for (let b = 0; b < BINS; b++) {
    const left = mlow + b * delta, center = mlow + (b + 1) * delta, right = mlow + (b + 2) * delta;
    const w = [];
    for (let i = 0; i < NFFT / 2; i++) {
      const m = mel(width * i);
      if (m > left && m < right) w.push([i, m <= center ? (m - left) / (center - left) : (right - m) / (right - center)]);
    }
    banks.push(w);
  }
  // FFT tables
  const cos = new Float64Array(NFFT / 2), sin = new Float64Array(NFFT / 2);
  for (let i = 0; i < NFFT / 2; i++) { cos[i] = Math.cos(2 * Math.PI * i / NFFT); sin[i] = -Math.sin(2 * Math.PI * i / NFFT); }
  const rev = new Uint32Array(NFFT);
  for (let i = 0, bits = Math.log2(NFFT); i < NFFT; i++) {
    let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r;
  }
  return { N, NFFT, BINS, window, banks, cos, sin, rev };
})();

function fft(re, im) {
  const n = FB.NFFT;
  for (let i = 0; i < n; i++) { const j = FB.rev[i]; if (j > i) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
  for (let size = 2; size <= n; size *= 2) {
    const half = size / 2, step = n / size;
    for (let i = 0; i < n; i += size) {
      for (let j = 0; j < half; j++) {
        const k = j * step, a = i + j, b = a + half;
        const tr = re[b] * FB.cos[k] - im[b] * FB.sin[k], ti = re[b] * FB.sin[k] + im[b] * FB.cos[k];
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
      }
    }
  }
}

export function fbank(wave) {
  const n = wave.length, shift = 160, { N, NFFT, BINS } = FB;
  const frames = Math.floor((n + shift / 2) / shift);
  const out = new Float32Array(frames * BINS);
  const x = new Float64Array(N), re = new Float64Array(NFFT), im = new Float64Array(NFFT);
  for (let f = 0; f < frames; f++) {
    const start = f * shift + shift / 2 - N / 2;
    let mean = 0;
    for (let i = 0; i < N; i++) {
      let s = start + i;
      while (s < 0 || s >= n) s = s < 0 ? -s - 1 : 2 * n - 1 - s;
      x[i] = wave[s]; mean += x[i];
    }
    mean /= N;
    for (let i = 0; i < N; i++) x[i] -= mean;
    for (let i = N - 1; i > 0; i--) x[i] -= 0.97 * x[i - 1];
    x[0] -= 0.97 * x[0];
    re.fill(0); im.fill(0);
    for (let i = 0; i < N; i++) re[i] = x[i] * FB.window[i];
    fft(re, im);
    for (let b = 0; b < BINS; b++) {
      let e = 0;
      for (const [i, w] of FB.banks[b]) e += w * (re[i] * re[i] + im[i] * im[i]);
      out[f * BINS + b] = Math.log(Math.max(e, 1.1920928955078125e-7));
    }
  }
  return { data: out, frames };
}

// ---- The model: each moment heard in several 6 s pieces, their probabilities averaged.

export class Model {
  constructor(ort, session) { this.ort = ort; this.session = session; }

  static async load(ort, url, executionProviders = ["wasm"]) {
    const session = await ort.InferenceSession.create(url, { executionProviders });
    return new Model(ort, session);
  }

  async pieceLogProbs(wave) {
    const { data, frames } = fbank(wave);
    const x = new this.ort.Tensor("float32", data, [1, frames, 80]);
    const lens = new this.ort.Tensor("int64", BigInt64Array.from([BigInt(frames)]), [1]);
    const r = await this.session.run({ x, x_lens: lens });
    const T = Number(r.log_probs_len.data[0]);
    return { lp: r.log_probs.data.subarray(0, T * V), T };
  }

  async logProbs(wave, onProgress = () => {}) {
    const PIECE = 6.0, HOP = 2.0;
    const seconds = wave.length / SAMPLE_RATE;
    const total = Math.max(Math.round(seconds / FRAME), 1);
    const probs = new Float64Array(total * V), count = new Float64Array(total);
    const starts = [];
    if (seconds <= PIECE) starts.push(0);
    else for (let s = 0; s < seconds - PIECE + HOP - 1e-9; s += HOP) starts.push(s);
    for (let p = 0; p < starts.length; p++) {
      const start = starts[p], end = Math.min(start + PIECE, seconds);
      const { lp, T } = await this.pieceLogProbs(wave.subarray(Math.floor(start * SAMPLE_RATE), Math.floor(end * SAMPLE_RATE)));
      const step = (end - start) / T;
      for (let j = 0; j < T; j++) {
        const index = Math.min(Math.floor((start + j * step) / FRAME), total - 1);
        for (let c = 0; c < V; c++) probs[index * V + c] += Math.exp(lp[j * V + c]);
        count[index] += 1;
      }
      onProgress((p + 1) / starts.length);
    }
    const out = new Float32Array(total * V);
    for (let t = 0; t < total; t++) {
      const k = count[t] || 1;
      for (let c = 0; c < V; c++) out[t * V + c] = Math.log(Math.max(probs[t * V + c] / k, 1e-12));
    }
    return { data: out, T: total };
  }
}

export function loudness(wave) {
  const n = Math.floor(wave.length / FRAME_SAMPLES), db = new Float64Array(n);
  for (let f = 0; f < n; f++) {
    let e = 0;
    for (let i = f * FRAME_SAMPLES; i < (f + 1) * FRAME_SAMPLES; i++) e += wave[i] * wave[i];
    db[f] = 10 * Math.log10(Math.max(e / FRAME_SAMPLES, 1e-10));
  }
  return db;
}

// ---- CTC forced alignment (align.align)

export function align(lp, from, to, words, repeatFrom = 0, repeatTo = null, freeEnd = false) {
  const T = to - from;
  const spoken = [];
  words.forEach((w, i) => { if (w.length) spoken.push(i); });
  const labels = [BLANK], owner = [-1], firsts = [], lasts = [];
  spoken.forEach((i, k) => {
    if (k) { labels.push(SPACE, BLANK); owner.push(-1, -1); }
    firsts.push(labels.length);
    for (const c of words[i]) { labels.push(c, BLANK); owner.push(k, -1); }
    lasts.push(labels.length - 2);
  });
  const S = labels.length, K = spoken.length;
  const stop = repeatTo ?? words.length;
  const within = spoken.map((i) => i >= repeatFrom && i < stop);
  let ownLast = K - 1, ownFirst = 0;
  { const a = spoken.map((i, k) => (i < stop ? k : -1)).filter((k) => k >= 0); if (a.length) ownLast = Math.max(...a); }
  { const a = spoken.map((i, k) => (i >= repeatFrom ? k : -1)).filter((k) => k >= 0); if (a.length) ownFirst = Math.min(...a); }
  if (freeEnd) ownLast = ownFirst;
  const entries = [...new Set(firsts.slice(0, ownFirst + 1).flatMap((f) => [f - 1, f]))].sort((a, b) => a - b);
  const exits = [...new Set(lasts.slice(ownLast).flatMap((l) => [l, l + 1]))].sort((a, b) => a - b);
  const skip2 = new Uint8Array(S), first = new Uint8Array(S);
  for (let s = 2; s < S; s++) skip2[s] = labels[s] !== BLANK && labels[s] !== labels[s - 2] ? 1 : 0;
  for (const f of firsts.slice(1)) first[f] = 1;
  let score = new Float64Array(S).fill(NEG), next = new Float64Array(S);
  const back = new Int8Array(T * S), jumpFrom = new Int32Array(T * K);
  const endState = new Int32Array(K), endScore = new Float64Array(K), order = new Float64Array(K), src = new Int32Array(K);
  let lead = 0, tail = NEG, tailFrom = -1, tailStart = -1;
  for (let t = 0; t < T; t++) {
    const row = (from + t) * V;
    for (let s = 0; s < S; s++) {
      let best = 0, v = score[s];
      if (s >= 1 && score[s - 1] > v) { v = score[s - 1]; best = 1; }
      if (s >= 2 && skip2[s] && score[s - 2] > v) { v = score[s - 2]; best = 2; }
      if (s >= 3 && first[s] && score[s - 3] > v) { v = score[s - 3]; best = 3; }
      if (s >= 4 && first[s] && score[s - 4] > v) { v = score[s - 4]; best = 4; }
      next[s] = v; back[t * S + s] = best;
    }
    for (let k = 0; k < K; k++) {
      endState[k] = score[lasts[k]] >= score[lasts[k] + 1] ? lasts[k] : lasts[k] + 1;
      endScore[k] = within[k] ? score[endState[k]] : NEG;
    }
    for (let k = K - 1; k >= 0; k--) {
      const after = k + 1 < K ? order[k + 1] : NEG;
      order[k] = Math.max(endScore[k], after);
      src[k] = endScore[k] >= after ? k : src[k + 1];
    }
    for (let k = 0; k < K; k++) {
      const again = within[k] ? order[k] - REPEAT_PENALTY : NEG;
      if (again > next[firsts[k]]) { next[firsts[k]] = again; back[t * S + firsts[k]] = 6; }
      jumpFrom[t * K + k] = endState[src[k]];
    }
    for (const s0 of entries) if (lead > next[s0]) { next[s0] = lead; back[t * S + s0] = 5; }
    let end = exits[0];
    for (const e of exits) if (score[e] > score[end]) end = e;
    if (score[end] > tail) { tail = score[end]; tailFrom = end; tailStart = t; }
    let mx = -Infinity;
    for (let c = 0; c < V; c++) mx = Math.max(mx, lp[row + c]);
    if (tail > NEG / 2) tail += mx - FILLER_PENALTY;
    for (let s = 0; s < S; s++) next[s] += lp[row + labels[s]];
    [score, next] = [next, score];
    lead += mx - FILLER_PENALTY;
  }
  let end = exits[0];
  for (const e of exits) if (score[e] > score[end]) end = e;
  let t, s;
  if (tail > score[end]) { t = tailStart - 1; s = tailFrom; } else { t = T - 1; s = end; }
  const wordOf = new Map(firsts.map((f, k) => [f, k]));
  const heard = [];
  let bestP = new Map(), lastT = -1;
  while (t >= 0) {
    const b = back[t * S + s];
    if (owner[s] >= 0) {
      if (!bestP.size) lastT = t;
      bestP.set(s, Math.max(bestP.get(s) ?? 0, Math.exp(lp[(from + t) * V + labels[s]])));
    }
    if (wordOf.has(s) && b !== 0) {
      const k = wordOf.get(s);
      let sum = 0; for (const p of bestP.values()) sum += p;
      heard.push({ word: spoken[k], start: t, end: lastT, confidence: Math.round(1000 * sum / words[spoken[k]].length) / 1000 });
      bestP = new Map();
    }
    if (b === 5) break;
    s = b === 6 ? jumpFrom[t * K + wordOf.get(s)] : s - b;
    t -= 1;
  }
  return heard.reverse();
}

// ---- Words: {"surah:ayah": [[word, text], ...]}

export function ayahsOf(words, surah) {
  const out = [];
  for (let n = 1; words[`${surah}:${n}`]; n++) out.push(n);
  return out;
}

let BASMALA = null;
export function setBasmala(hafsWords) { BASMALA = hafsWords["1:1"]; }
const sameLetters = (a, b) => JSON.stringify(a.map(([, t]) => letters(t))) === JSON.stringify(b.map(([, t]) => letters(t)));
export const isBasmala = (tokens) => sameLetters(tokens, BASMALA);

export function findAyahs(surah, rec, words, onProgress = () => {}) {
  const ayahs = ayahsOf(words, surah), T = rec.T;
  const tok = (n) => words[`${surah}:${n}`];
  const basmala = surah === 9 || isBasmala(tok(ayahs[0])) ? [] : BASMALA;
  const found = new Map();
  const W0 = Math.floor(60 / FRAME);
  let k = 0, t0 = 0, window = W0;
  while (k < ayahs.length) {
    const t1 = Math.min(t0 + window, T);
    const need = (t1 - t0) * FRAME * 16;
    const own = [];
    let have = 0, j = k;
    while (j < ayahs.length && (have < need || j <= k + 1)) {
      for (const w of tok(ayahs[j])) { own.push([ayahs[j], w]); have += letters(w[1]).length; }
      j++;
    }
    const before = k === 0 ? basmala : tok(ayahs[k - 1]).slice(-CONTEXT);
    const heard = align(rec.lp, t0, t1, [...before.map(([, t]) => letters(t)), ...own.map(([, w]) => letters(w[1]))],
      before.length, before.length + own.length, true);
    const mine = heard.filter((h) => h.word >= before.length).map((h) => [own[h.word - before.length][0], h]);
    if (!mine.length) break;
    const reached = Math.max(...mine.map(([a]) => a));
    const done = t1 >= T || (j === ayahs.length && mine[mine.length - 1][1].word === before.length + own.length - 1);
    const last = done ? ayahs.length : ayahs.indexOf(reached);
    for (const a of ayahs.slice(k, last)) {
      const hs = mine.filter(([b]) => b === a).map(([, h]) => h);
      if (hs.length) found.set(a, [t0 + Math.min(...hs.map((h) => h.start)), t0 + Math.max(...hs.map((h) => h.end))]);
    }
    onProgress(Math.min(t1 / T, 1));
    if (done) break;
    if (last === k) { if (t1 >= T) break; window *= 2; continue; }
    const startLast = t0 + Math.min(...mine.filter(([b]) => b === reached).map(([, h]) => h.start));
    t0 = Math.max(startLast - Math.floor(1.0 / FRAME), t0 + 1);
    k = last; window = W0;
  }
  return [...found.keys()].sort((a, b) => a - b).map((a) => [a, found.get(a)[0] * FRAME, found.get(a)[1] * FRAME]);
}

function voiceEnd(db, start, limit, loud) {
  let quiet = 0;
  for (let t = start; t < Math.min(limit, db.length); t++) {
    quiet = db[t] < loud - 30 ? quiet + 1 : 0;
    if (quiet >= 5) return t - 5 + 1;
  }
  return limit;
}

export function alignAyahs(surah, rec, windows, words, margin = 1.0) {
  const length = rec.T * FRAME, result = {};
  const nexts = new Map(windows.slice(0, -1).map(([n], i) => [n, windows[i + 1][1]]));
  for (const [n, start, end] of windows) {
    const tokens = words[`${surah}:${n}`];
    if (!tokens) continue;
    const basmala = n === 1 && isBasmala(tokens);
    const a = Math.max(start - margin, 0), b = Math.min(end + (basmala ? 0.3 : margin), length);
    if (b - a < 0.5) continue;
    const before = (words[`${surah}:${n - 1}`] ?? []).slice(-CONTEXT);
    const after = basmala ? [] : (words[`${surah}:${n + 1}`] ?? []).slice(0, CONTEXT);
    const f0 = Math.floor(a / FRAME), f1 = Math.floor(b / FRAME);
    const all = [...before, ...tokens, ...after].map(([, t]) => letters(t));
    const heard = align(rec.lp, f0, f1, all, before.length, before.length + tokens.length);
    const own = heard.filter((h) => h.word >= before.length && h.word < before.length + tokens.length);
    if (!own.length) continue;
    const limit = Math.floor((nexts.get(n) ?? length) / FRAME);
    let last = own[0];
    for (const h of own) if (h.end > last.end) last = h;
    const span = Array.from(rec.db.subarray(f0 + own[0].start, f0 + last.end + 1)).sort((x, y) => x - y);
    const loud = span.length ? span[Math.floor(span.length * 0.9)] : 0;
    const stop = voiceEnd(rec.db, f0 + last.end + 1, Math.max(limit, f0 + last.end + 1), loud);
    const starts = own.map((h) => f0 + h.start);
    const ends = own.slice(0, -1).map((h, i) => voiceEnd(rec.db, f0 + h.end + 1, starts[i + 1], loud)).concat([stop]);
    result[n] = own.map((h, i) => [tokens[h.word - before.length][0], Math.round(starts[i] * FRAME * 1000),
      Math.round(Math.max(ends[i], starts[i] + 1) * FRAME * 1000), h.confidence]);
  }
  return result;
}

// ---- Output formats (formats.py)

const textOf = (words, surah, ayah, word) => (words[`${surah}:${ayah}`] ?? []).find(([i]) => i === word)?.[1] ?? "";
const clock = (ms, sep) => {
  const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60;
  const p = (x, n = 2) => String(x).padStart(n, "0");
  return `${p(h)}:${p(m)}:${p(s)}${sep}${p(ms % 1000, 3)}`;
};
const rows = (result) => Object.keys(result).map(Number).sort((a, b) => a - b).filter((a) => result[a].length).map((a) => [a, result[a]]);
const span = (ws) => [Math.min(...ws.map((w) => w[1])), Math.max(...ws.map((w) => w[2]))];

export const FORMATS = {
  json: (surah, result) => JSON.stringify(result),
  csv: (surah, result, words) => ["surah,ayah,word,start_ms,end_ms,confidence,text",
    ...rows(result).flatMap(([a, ws]) => ws.map((w) => `${surah},${a},${w[0]},${w[1]},${w[2]},${w[3]},${textOf(words, surah, a, w[0])}`))].join("\n") + "\n",
  srt: (surah, result, words) => rows(result).map(([a, ws], i) => {
    const [s, e] = span(ws);
    return `${i + 1}\n${clock(s, ",")} --> ${clock(e, ",")}\n${words[`${surah}:${a}`].map(([, t]) => t).join(" ")} (${a})\n`;
  }).join("\n"),
  vtt: (surah, result, words) => "WEBVTT\n\n" + rows(result).map(([a, ws]) => {
    const [s, e] = span(ws);
    const body = ws.map((w, i) => (i ? `<${clock(w[1], ".")}>` : "") + textOf(words, surah, a, w[0])).join(" ");
    return `${surah}:${a}\n${clock(s, ".")} --> ${clock(e, ".")}\n${body}\n`;
  }).join("\n"),
  segments: (surah, result) => JSON.stringify({ chapter_id: surah, verse_timings: rows(result).map(([a, ws]) => {
    const [s, e] = span(ws);
    return { verse_key: `${surah}:${a}`, timestamp_from: s, timestamp_to: e, segments: ws.map((w) => [w[0], w[1], w[2]]) };
  }) }),
};

// ---- which surah a recording is (as quran_word_align/detect.py: detect_surah)
const HEAR_SECONDS = 180;
function heardLetters(rec, frames) {
  const V = VOCAB.length, out = [];
  let prev = -1;
  for (let t = 0; t < Math.min(frames, rec.T); t++) {
    let best = 0, bv = -Infinity;
    for (let v = 0; v < V; v++) { const x = rec.lp[t * V + v]; if (x > bv) { bv = x; best = v; } }
    if (best !== prev && best !== BLANK && best !== SPACE) out.push(best);
    prev = best;
  }
  return out;
}
const triples = (seq, n = seq.length) => {
  const m = new Map();
  for (let i = 0; i + 2 < n; i++) { const k = (seq[i] * 32 + seq[i + 1]) * 32 + seq[i + 2]; m.set(k, (m.get(k) || 0) + 1); }
  return m;
};
const norm2 = (m) => Math.sqrt([...m.values()].reduce((s, v) => s + v * v, 0));
const surahLettersCache = new Map();
function surahLetters(hafsWords, surah) {
  if (!surahLettersCache.has(surah)) {
    const out = [];
    for (let n = 1; hafsWords[`${surah}:${n}`]; n++) for (const [, text] of hafsWords[`${surah}:${n}`]) out.push(...letters(text));
    surahLettersCache.set(surah, out);
  }
  return surahLettersCache.get(surah);
}
/** Surahs by the letter triples their opening shares with the recording's, best first: [[score, surah], ...]. */
export function detectSurah(rec, hafsWords) {
  const heard = heardLetters(rec, Math.round(HEAR_SECONDS / FRAME));
  const mine = triples(heard), nm = norm2(mine);
  const scores = [];
  for (let s = 1; s <= 114; s++) {
    const text = surahLetters(hafsWords, s);
    const theirs = triples(text, Math.min(text.length, Math.floor(heard.length * 1.3) + 30));
    let dot = 0;
    for (const [k, v] of mine) dot += v * (theirs.get(k) || 0);
    const nt = norm2(theirs);
    scores.push([nm && nt ? dot / (nm * nt) : 0, s]);
  }
  return scores.sort((a, b) => b[0] - a[0]);
}
