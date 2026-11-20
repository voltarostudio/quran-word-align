# Telling the surah and riwayah from the audio

`python eval/detect_eval.py`: 224 recordings of the dataset's 28 reads, surahs 1, 12, 18, 36, 55, 67, 78, 112, the surah told from the opening, the riwayah from the whole recording.

The surah is what the tool uses. The riwayah is an experiment only: the riwayat share the mushaf's letters and differ in about 690 of its 325,000 letters as the model hears them (none in 41 surahs, al-Fatiha and the short surahs among them), and the model leans to Hafs, so Warsh and Qalun recordings are often taken for Hafs. "Cannot tell": the riwayat read the same letters in that surah. The tool asks for the riwayah.

| Riwayah | Recordings | Surah right | Riwayah right | Riwayah wrong | Cannot tell |
|---|---|---|---|---|---|
| Hafs | 168 | 168 (100.0%) | 112 | 2 | 54 |
| Warsh | 32 | 32 (100.0%) | 13 | 5 | 14 |
| Qalun | 24 | 24 (100.0%) | 5 | 12 | 7 |

Wrong guesses:

- read 20 (hafs), surah 55: guessed surah 55, warsh (votes {'hafs': 0, 'warsh': 2, 'qalun': 1})
- read 106 (hafs), surah 55: guessed surah 55, qalun (votes {'hafs': 0, 'warsh': 0, 'qalun': 2})
- read 14 (warsh), surah 18: guessed surah 18, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 16 (warsh), surah 55: guessed surah 55, hafs (votes {'hafs': 2, 'warsh': 1, 'qalun': 0})
- read 16 (warsh), surah 78: guessed surah 78, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 80 (warsh), surah 55: guessed surah 55, hafs (votes {'hafs': 2, 'warsh': 1, 'qalun': 0})
- read 80 (warsh), surah 78: guessed surah 78, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 75 (qalun), surah 12: guessed surah 12, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 75 (qalun), surah 18: guessed surah 18, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 75 (qalun), surah 55: guessed surah 55, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 75 (qalun), surah 67: guessed surah 67, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 75 (qalun), surah 78: guessed surah 78, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 270 (qalun), surah 18: guessed surah 18, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 270 (qalun), surah 55: guessed surah 55, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 270 (qalun), surah 67: guessed surah 67, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 208 (qalun), surah 18: guessed surah 18, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 208 (qalun), surah 55: guessed surah 55, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 1})
- read 208 (qalun), surah 67: guessed surah 67, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
- read 208 (qalun), surah 78: guessed surah 78, hafs (votes {'hafs': 2, 'warsh': 0, 'qalun': 0})
