# Changelog

What changed in each version of the `quran-word-align` tool. The dataset has its own
[changelog](dataset/CHANGELOG.md).

## 0.3.0 — First release on PyPI

- **Align:** one surah, part of one (`--from-ayah`), several surahs in a row, or one file per ayah (`ayahs`).
- **Find:** which surah a recording begins with, from the audio alone.
- **Readings:** Hafs, Warsh and Qalun (`--riwayah`).
- **mp3quran.net:** `reads` lists the recordings, and `mp3quran` aligns them by id. `--ayah-timings` aligns inside mp3quran's ayah windows, and `--resume` carries on where a run stopped.
- **Output:** JSON, CSV, SRT and VTT. Each word has a confidence score.
- **Openings:** the isti'adha and basmala before ayah 1 are heard and skipped. Al-Fatiha's basmala is timed as its first ayah.
- **Recordings that are hard to decode:**
  - a recording whose two channels cancel out when mixed to mono, in all of it or only part, is heard from one channel;
  - an mp3 that ffmpeg takes for another format is read as mp3.
- **Model:** quran-asr-tiny, 19 MB, fetched once from Hugging Face and checked against its SHA-256. It runs on a laptop without a GPU.
