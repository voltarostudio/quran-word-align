---
license: cc-by-4.0
language:
- ar
pretty_name: Quran word timings on mp3quran.net recordings
tags:
- quran
- forced-alignment
- word-timings
- arabic
size_categories:
- 1M<n<10M
configs:
- config_name: default
  data_files: words.csv
---

# Quran word timings on mp3quran.net recordings (v2.0)

When each word of the Quran starts and ends in 28 complete recitations from
[mp3quran.net](https://www.mp3quran.net): 21 in the reading of Hafs, 4 of Warsh and 3 of Qalun,
about 2.23 million timed words. With them an app can light up each word of the mushaf as the reciter
reads it, cut a recitation word by word, or subtitle it.

The timings are ours, made with [quran-word-align](https://github.com/voltarostudio/quran-word-align),
and free under **CC-BY 4.0**. The recordings are not in the dataset: each timing file points to its
recording on mp3quran.net, and `audio-sha256.csv` fingerprints the exact file we aligned.

## What is in it

| File | What it holds |
|---|---|
| `timings/<reciter>/<surah>.json` | `{"ayah": [[word, start_ms, end_ms, confidence], ...]}`, the words in the order heard |
| `words.csv` | the same, one row a word: `reciter, riwayah, surah, ayah, word, start_ms, end_ms, confidence` |
| `reciters.csv` | each reciter: mp3quran read id, riwayah, names, the folder of the recordings |
| `audio-sha256.csv` | each recording aligned: its URL, size and SHA-256 |
| `quality.csv` | the table below |
| `differs-from-mp3quran.csv` | ayahs we place outside mp3quran's ayah timing, to check |
| `hafs-words.json`, `warsh-words.json`, `qalun-words.json` | the words: `{"surah:ayah": [[word, text], ...]}`, the King Fahd Complex's text of each riwayah |

- **Times** are milliseconds from the start of the surah's recording on mp3quran.net
  (`<audio_folder><surah:03>.mp3`).
- **Words** are numbered as the King Fahd Complex's mushaf of the riwayah numbers them, from 1 in each
  ayah; **ayahs** as that mushaf counts them (Warsh and Qalun count 6,214, and their al-Fatiha does not
  count the basmala as an ayah).
- **A word starts** where its first letter is heard; after a pause, where the voice comes back. It
  **ends** where the next word starts, or where the voice stops if the reciter pauses first.
- **Confidence**, from 0 to 1, is how clearly the model heard the word's letters where they were placed.
  It tracks accuracy: against Quran.com's timings, 90% of words above 0.85 agree within a quarter of
  a second, and 15% of words under 0.3. Words under 0.5 (about 2% of them) are worth checking.
- **A reciter who goes back** and reads words again is followed: the words repeated are listed again,
  in the order heard. So an ayah may list a word twice.
- The basmala before the surahs (but al-Fatiha in Hafs) and the isti'adha are not timed.

## How good it is

There is no exact reference for word timings, so these are checks, not an error rate. On a sample of
these recordings, measured by `eval/evaluate.py` in the repository (see `eval/RESULTS.md`):

- **Ayahs:** all 10,871 ayahs of 203 surahs were found, and where mp3quran's ayah timings fit the
  recording, the ayah starts we found are within one second of theirs for 98.6% of ayahs (Hafs),
  100% (Warsh) and 99.6% (Qalun).
- **Words after a pause** begin within 80 ms of where the voice comes back for 97.5% to 99.3% of them.
- **Against Quran.com's word timings**, for reciters whose Quran.com recording is the same performance,
  word starts within each ayah agree within a quarter of a second for 90% to 96% of words (Abdul Basit
  92%, al-Husary 90%, al-Shatri 96%). Quran.com's timings were used only to measure; none are in here.

Reciter by reciter, on the whole dataset:

| Reciter | Riwayah | Surahs | Words timed | Median confidence | Confidence ≥ 0.7 | Ayahs where mp3quran puts them |
|---|---|---|---|---|---|---|
| Mishary Alafasy | Hafs | 114 | 100.0% | 0.85 | 84.7% | 99.52% |
| Mahmoud Khalil Al-Husary | Hafs | 114 | 100.0% | 0.86 | 91.1% | 99.17% |
| Muhammad Siddiq Al-Minshawi | Hafs | 114 | 100.0% | 0.85 | 84.5% | 96.92% |
| Abdul Basit Abdul Samad | Hafs | 114 | 100.0% | 0.86 | 86.4% | 99.87% |
| Abdul Rahman Al-Sudais | Hafs | 114 | 100.0% | 0.85 | 80.6% | 98.69% |
| Saud Al-Shuraim | Hafs | 114 | 100.0% | 0.85 | 81.6% | 93.66% |
| Saad Al-Ghamdi | Hafs | 114 | 100.0% | 0.85 | 82.7% | 99.01% |
| Yasser Al-Dosari | Hafs | 114 | 100.0% | 0.86 | 84.3% | 98.52% |
| Nasser Al-Qatami | Hafs | 114 | 100.0% | 0.84 | 81.1% | 98.01% |
| Ahmad Al-Ajmi | Hafs | 114 | 100.0% | 0.83 | 78.9% | 96.47% |
| Muhammad Ayyub | Hafs | 114 | 100.0% | 0.88 | 89.2% | 99.71% |
| Abu Bakr Al-Shatri | Hafs | 114 | 100.0% | 0.83 | 79.8% | 99.25% |
| Abdullah Awad Al-Juhani | Hafs | 114 | 100.0% | 0.87 | 83.3% | 93.8% |
| Ali Jaber | Hafs | 114 | 100.0% | 0.84 | 83.1% | 99.28% |
| Khalid Al-Jaleel | Hafs | 114 | 100.0% | 0.83 | 79.3% | 94.16% |
| Bandar Baleela | Hafs | 114 | 100.0% | 0.83 | 78.4% | 98.52% |
| Idris Abkar | Hafs | 114 | 100.0% | 0.82 | 78.3% | 97.05% |
| Fares Abbad | Hafs | 114 | 100.0% | 0.87 | 86.8% | 99.23% |
| Salah Bukhatir | Hafs | 114 | 100.0% | 0.83 | 78.7% | 98.6% |
| Abdullah Basfar | Hafs | 114 | 100.0% | 0.85 | 84.1% | 98.08% |
| Muhammad Al-Tablawi | Hafs | 114 | 100.0% | 0.85 | 84.8% | 98.11% |
| Yassin Al-Jazairi | Warsh | 114 | 100.0% | 0.84 | 81.7% | 99.07% |
| Laayoun El Kouchi | Warsh | 114 | 100.0% | 0.83 | 78.4% | 98.58% |
| Omar Al-Kazabri | Warsh | 114 | 100.0% | 0.83 | 81.5% | 99.32% |
| Mahmoud Khalil Al-Husary (Warsh) | Warsh | 114 | 100.0% | 0.84 | 87.8% | 99.79% |
| Ali Al-Hudhaifi (Qalun) | Qalun | 114 | 100.0% | 0.83 | 82.7% | 99.74% |
| Mahmoud Khalil Al-Husary (Qalun) | Qalun | 114 | 100.0% | 0.86 | 90.6% | 99.42% |
| Al-Dokali Muhammad Al-Alim (Qalun) | Qalun | 114 | 100.0% | 0.85 | 85.1% | 99.11% |

"Ayahs where mp3quran puts them": the share of ayahs whose start we found inside the span mp3quran's
ayah timing gives that ayah. Most of the rest are mp3quran's mistakes, not ours: their timings are off
by an ayah or more in some surahs (Khalid Al-Jaleel, surah 3: 200 ayahs, Muhammad Siddiq Al-Minshawi, surah 9: 128 ayahs, Saud Al-Shuraim, surah 9: 128 ayahs, Abdullah Awad Al-Juhani, surah 2: 118 ayahs, Saud Al-Shuraim, surah 12: 90 ayahs, Abdullah Awad Al-Juhani, surah 4: 74 ayahs). We checked such surahs by what the model hears at
each place: at our ayah starts it hears the ayah's first words, at theirs it does not. The 3,074
ayahs (of 174,439) are listed in `differs-from-mp3quran.csv`.

## How it was made

1. [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) (MIT, by Abdou), a small model
   trained on Quran recitations, hears each 40 ms of the recording as letter probabilities.
2. The whole surah is followed a minute at a time, by CTC forced alignment of the ayahs' words,
   letter by letter, to find where each ayah is. No ayah timings are used.
3. Each ayah is aligned again in its own window, with a few words of the ayahs either side, and each
   word gets its confidence. Word ends before a pause come from the recording's loudness.

`dataset/align.sh` and `dataset/build.py` in the repository make the dataset from scratch.

**Version 1.0** (21 Hafs reciters) was aligned in mp3quran's ayah windows, and so went wrong wherever
those windows are off; version 2.0 finds the ayahs itself, adds confidence, Warsh and Qalun.

## Credit and licence

The timings: **CC-BY 4.0**, Voltaro Studio. A credit that is enough:

> Word timings: quran-word-align by Voltaro Studio (CC-BY 4.0), on recordings from mp3quran.net.

The recordings and ayah timings are from mp3quran.net, which allows any use of its material; the
recordings belong to their reciters. The Quran text is the King Fahd Glorious Quran Printing Complex's,
unchanged. Nothing here comes from Quran.com. See `LICENSE.md`.

---

## بالعربية

توقيتُ كلِّ كلمةٍ من كلمات القرآن، متى تبدأ ومتى تنتهي، في 28 ختمةً كاملة من موقع mp3quran.net:
إحدى وعشرون برواية حفص، وأربعٌ برواية ورش، وثلاثٌ برواية قالون. يُعلِّم بها التطبيقُ الكلمةَ في المصحف
حين يقرؤها القارئ، أو يقطع بها التلاوة كلمةً كلمة.

التوقيت من عملنا، صنعناه بأداة quran-word-align، وهو مباحٌ برخصة **CC-BY 4.0**: انقله وانشره وعدّله
لأي غرض، تجاريًّا كان أو غيره، واذكر مصدره. والتلاوات ليست فيه: يشير كلُّ ملفٍّ إلى تسجيله في
mp3quran.net، ومعه بصمةُ الملف الذي وقّتناه.

- **الأزمنة** بالجزء من ألف من الثانية، من أول تسجيل السورة.
- **الكلمات والآيات** مرقّمةٌ كما يرقّمها مصحف مجمع الملك فهد لكل رواية.
- **الثقة** لكل كلمة، من صفر إلى واحد: مقدار وضوح حروفها للنموذج في موضعها.
- **إذا رجع القارئ فأعاد كلمات** ذُكرت الكلمات المعادة مرةً ثانية بترتيب سماعها.
- **وجدنا مواضع الآيات بأنفسنا** من التسجيل، فصحّت حيث أخطأ توقيت الآيات في mp3quran، وهو خاطئٌ بآيةٍ أو
  أكثر في بعض السور.

**الإسناد:** التلاوات من موقع mp3quran.net، ونصّ المصحف من مجمع الملك فهد لطباعة المصحف الشريف،
والتوقيت من Voltaro Studio. وليس فيه شيءٌ من Quran.com.
