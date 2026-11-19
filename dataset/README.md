---
license: cc-by-4.0
language:
- ar
pretty_name: Quran word timings on mp3quran.net recordings
tags:
- quran
- forced-alignment
- word-timings
- audio
- arabic
size_categories:
- 1M<n<10M
configs:
- config_name: default
  data_files: words.csv
---

# Quran word timings on mp3quran.net recordings (v1.0)

When each word of the Quran starts and ends in 21 complete recitations from
[mp3quran.net](https://www.mp3quran.net), in the Hafs reading: about 1.67 million timed words. With
them an app can light up each word of the mushaf as the reciter reads it.

The timings are ours, made with [quran-word-align](https://github.com/voltarostudio/quran-word-align),
and free under **CC-BY 4.0**. The recordings are not in the dataset: each timing file points to its
recording on mp3quran.net, and `audio-sha256.csv` fingerprints the exact file we aligned.

## What is in it

| File | What it holds |
|---|---|
| `timings/<reciter>/<surah>.json` | `{"ayah": [[word, start_ms, end_ms], ...]}`, the words in the order heard |
| `words.csv` | the same, one row a word: `reciter, surah, ayah, word, start_ms, end_ms` |
| `reciters.csv` | each reciter: mp3quran read id, names, riwayah, the folder of the recordings |
| `audio-sha256.csv` | each recording aligned: its URL, size and SHA-256 |
| `quality.csv` | the table below |
| `suspect-ayahs.csv` | ayahs whose timings are likely wrong, and why |
| `hafs-words.json` | the words: `{"surah:ayah": [[word, text], ...]}`, the King Fahd Complex's Hafs text |

- **Times** are milliseconds from the start of the surah's recording on mp3quran.net
  (`<audio_folder><surah:03>.mp3`).
- **Words** are numbered as the King Fahd Complex's Hafs mushaf numbers them, from 1 in each ayah
  (`hafs-words.json`). A word made only of a mark is not timed.
- **A reciter who goes back** and reads words again is followed: the words repeated are listed again,
  in the order heard. So an ayah may list a word twice, and its words are not always in order.
- **Ayah 1 of al-Fatiha** is the basmala. The basmala before the other surahs is not timed.

## How good it is

There is no exact reference for word timings, so take these as checks, not as an error rate.

- **Agreement with Quran.com**: where Quran.com's recording is the same performance, the share of
  words whose start (from their ayah's start) is within a quarter or half a second of Quran.com's word
  timings. Quran.com's own timings are not exact either.
- **Suspect ayahs**: ayahs whose words run back into the previous ayah's, or begin more than 2.5 s
  from where mp3quran says the ayah begins. Each ayah was aligned in a window taken from mp3quran's
  ayah timings; where those timings do not fit the recording (they are off by an ayah in some surahs),
  the words found are wrong. These ayahs are listed in `suspect-ayahs.csv`; many of them are in a few
  surahs (Al-Jaleel's Al Imran: 157, Al-Ajmi's an-Nisa': 152, Al-Shuraim's at-Tawbah: 116, Al-Minshawi's at-Tawbah: 104, Al-Juhani's al-Baqarah: 83, Al-Tablawi's az-Zumar: 73).

| Reciter | Words | Median word | Suspect ayahs | vs Quran.com ≤0.25 s | ≤0.5 s |
|---|---|---|---|---|---|
| Mishary Alafasy | 79,321 | 1.08 s | 24 (0.38%) | — | — |
| Mahmoud Khalil Al-Husary | 78,876 | 1.56 s | 76 (1.22%) | 79.9% | 85.4% |
| Muhammad Siddiq Al-Minshawi | 79,389 | 1.12 s | 174 (2.79%) | 61.8% | 82.2% |
| Abdul Basit Abdul Samad | 79,496 | 1.20 s | 69 (1.11%) | 51.0% | 82.0% |
| Abdul Rahman Al-Sudais | 78,354 | 0.84 s | 48 (0.77%) | — | — |
| Saud Al-Shuraim | 78,437 | 0.72 s | 232 (3.72%) | 94.1% | 96.6% |
| Saad Al-Ghamdi | 79,272 | 0.92 s | 32 (0.51%) | — | — |
| Yasser Al-Dosari | 80,808 | 0.96 s | 61 (0.98%) | 68.1% | 83.8% |
| Nasser Al-Qatami | 81,574 | 0.92 s | 82 (1.32%) | — | — |
| Ahmad Al-Ajmi | 80,319 | 0.92 s | 210 (3.37%) | — | — |
| Muhammad Ayyub | 81,103 | 1.12 s | 28 (0.45%) | — | — |
| Abu Bakr Al-Shatri | 79,302 | 0.96 s | 47 (0.75%) | 3.9% | 71.2% |
| Abdullah Awad Al-Juhani | 78,305 | 0.80 s | 165 (2.65%) | — | — |
| Ali Jaber | 78,090 | 1.00 s | 20 (0.32%) | — | — |
| Khalid Al-Jaleel | 81,083 | 0.88 s | 237 (3.8%) | 72.7% | 83.3% |
| Bandar Baleela | 80,379 | 1.00 s | 75 (1.2%) | — | — |
| Idris Abkar | 81,858 | 1.08 s | 201 (3.23%) | — | — |
| Fares Abbad | 77,507 | 0.92 s | 16 (0.26%) | — | — |
| Salah Bukhatir | 80,068 | 0.88 s | 64 (1.03%) | — | — |
| Abdullah Basfar | 79,322 | 1.00 s | 21 (0.34%) | — | — |
| Muhammad Al-Tablawi | 77,876 | 1.12 s | 92 (1.48%) | — | — |

It is weakest on slow recitations with long madds (Abdul Basit, al-Shatri) and on surahs whose ayah
timings are off. Every word has a time for 15 of the 21 reciters; for the other six, 1 to 11 ayahs
are missing (99.7% to 99.99% of words timed), where mp3quran's ayah timings are missing or run past the end of the recording.

## How it was made

1. [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) (MIT, by Abdou), a small model
   trained on Quran recitations, hears each 40 ms of the recording as letter probabilities.
2. CTC forced alignment fits each ayah's words, letter by letter, to them, in the window of the
   ayah's mp3quran timing widened by 3 s each side, with a few words of the ayahs either side.

`dataset/build.py` in the repository packages the files and computes the tables.

## Credit and licence

The timings: **CC-BY 4.0**, Voltaro Studio. A credit that is enough:

> Word timings: quran-word-align by Voltaro Studio (CC-BY 4.0), on recordings and ayah timings from mp3quran.net.

The recordings and ayah timings are from mp3quran.net, which allows any use of its material; the
recordings belong to their reciters. The Quran text is the King Fahd Glorious Quran Printing Complex's,
unchanged. Nothing here comes from Quran.com. See `LICENSE.md`.

---

## بالعربية

توقيتُ كلِّ كلمةٍ من كلمات القرآن، متى تبدأ ومتى تنتهي، في ٢١ ختمةً كاملة من موقع mp3quran.net
برواية حفص: نحو مليون وستمئة وسبعين ألف كلمة. يُعلِّم بها التطبيقُ الكلمةَ في المصحف حين يقرؤها القارئ.

التوقيت من عملنا، صنعناه بأداة quran-word-align، وهو مباحٌ برخصة **CC-BY 4.0**: انقله وانشره وعدّله
لأي غرض، تجاريًّا كان أو غيره، واذكر مصدره. والتلاوات ليست فيه: يشير كلُّ ملفٍّ إلى تسجيله في
mp3quran.net.

- **الأزمنة** بالجزء من ألف من الثانية، من أول تسجيل السورة.
- **الكلمات** مرقّمةٌ كما يرقّمها مصحف مجمع الملك فهد برواية حفص.
- **إذا رجع القارئ فأعاد كلمات** ذُكرت الكلمات المعادة مرةً ثانية بترتيب سماعها.
- **الآيات المشكوك فيها** في `suspect-ayahs.csv`: أكثرها في سورٍ قليلة لا يوافق فيها توقيتُ الآيات في
  mp3quran التسجيلَ.

**الإسناد:** التلاوات وتوقيت الآيات من موقع mp3quran.net، ونصّ المصحف من مجمع الملك فهد لطباعة
المصحف الشريف، والتوقيت من Voltaro Studio. وليس فيه شيءٌ من Quran.com.
