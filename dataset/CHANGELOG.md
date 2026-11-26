# Changelog

What changed in each version of the dataset. What the files hold, and the licence, are in the
[dataset card](README.md).

## v3.4 — Where the reciter's voice begins

- `openings.csv`: new column `reciter_starts_ms`, where the reciter's own voice begins in each surah's file.
  - It is 0 when the file opens in the reciter's voice. Otherwise it is the end of the isti'adha or basmala said before it in another voice.
  - It is empty when this cannot be told.
- With it, an app that plays its own basmala can skip the file's.

## v3.3 — The isti'adha's voice

- `openings.csv`: new column `istiadha_own_voice`, whether each file's isti'adha is in the reciter's own voice.
- `istiadha.csv`: where a reciter's isti'adha was in another voice, one in their own voice is given instead. 71 reciters now have one, up from 55.

## v3.2 — The basmala's voice

- Many of mp3quran's files open with a short clip in another voice, the same clip in each of a reciter's files: 3,883 of 11,112 files.
- `openings.csv`: new column `basmala_own_voice`. `basmala_words.csv`: new column `own_voice`.
- `basmala.csv` and `istiadha.csv` give only clips in the reciter's own voice.

## v3.1 — The basmala's words

- New file `basmala_words.csv`: when each of the basmala's four words begins and ends, in 10,054 surah files.
- `openings.csv`: new column `istiadha_end_ms`.

## v3.0 — 111 recitations

- 111 recitations, up from 28: 103 Hafs, 5 Warsh, 3 Qalun, about 8.9 million words.
- New files:
  - `basmala.csv` and `istiadha.csv`: where each reciter's basmala and isti'adha are.
  - `openings.csv`: how each surah's file opens.

## v2.0 — Warsh and Qalun, ayahs found from the audio

- 28 recitations: 21 Hafs, 4 Warsh, 3 Qalun, about 2.2 million words.
- Each word has a confidence score.
- Ayahs are found from the audio, so they are right where mp3quran's ayah timings are off. `differs-from-mp3quran.csv` lists those ayahs.

## v1.0 — First release

- 21 Hafs recitations, about 1.7 million words.
