// Runs the model and the alignment off the page's thread, so the page stays smooth.
import * as ort from "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/ort.wasm.min.mjs";
import { Model, loudness, findAyahs, alignAyahs, setBasmala } from "./aligner.js";

const MODEL_URL = "https://huggingface.co/Abdou/quran-asr-tiny/resolve/main/model.int8.onnx";
ort.env.wasm.wasmPaths = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/";
ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;

let model = null;
const say = (stage, progress = null) => postMessage({ type: "progress", stage, progress });

async function loadModel() {
  if (model) return model;
  say("model", 0);
  const res = await fetch(MODEL_URL);
  const total = Number(res.headers.get("content-length")) || 19_000_000;
  const reader = res.body.getReader();
  const parts = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value); got += value.length;
    say("model", Math.min(got / total, 1));
  }
  const bytes = new Uint8Array(got);
  let at = 0;
  for (const p of parts) { bytes.set(p, at); at += p.length; }
  model = await Model.load(ort, bytes);
  return model;
}

onmessage = async ({ data }) => {
  try {
    const { wave, surah, words, hafs } = data;
    setBasmala(hafs);
    const m = await loadModel();
    say("hear", 0);
    const lp = await m.logProbs(wave, (p) => say("hear", p));
    const rec = { lp: lp.data, T: lp.T, db: loudness(wave) };
    say("find", 0);
    const found = findAyahs(surah, rec, words, (p) => say("find", p));
    say("align", null);
    const result = alignAyahs(surah, rec, found, words, 1.0);
    postMessage({ type: "done", result });
  } catch (e) {
    postMessage({ type: "error", message: String(e?.message || e) });
  }
};
