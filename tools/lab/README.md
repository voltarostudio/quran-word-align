# The lab

A page on this computer for two things the models can't do alone:

- **Word boundaries checked by ear** (the gold set): 40 ayahs, 302 words, from 20 recitations spread
  across the dataset's confidence range, Warsh and Qalun included. Each word starts where the dataset
  put it, and is moved by hand where it is off. The result, `gold.json`, is what later models are
  measured against.
- **Deliberate mistakes**: 40 ayahs from al-Fatiha and juz' 30, each recorded twice, once as usual and
  once with one named mistake in one word: a ghunna dropped, a madd cut short, a qalqala left out, a
  letter said as another, a word skipped or said twice. These test al-Mu'allim on real errors in a
  voice that isn't a professional reciter's.

The Quran text is the dataset's own, from the King Fahd Complex's files; nothing is typed.

```bash
python tools/lab/make_sample.py DATASET ~/.cache/quran-word-align/audio ~/quran-word-align-v3/lab
python tools/lab/server.py ~/quran-word-align-v3/lab
```

Then open http://localhost:8766 in Safari or Chrome (the microphone needs a real browser).
Work is saved as it is done, in the lab folder: `gold.json` and `recordings/`.
