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

# Quran word timings on mp3quran.net recordings (v{version})

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
  surahs ({worst_surahs}).

{quality_table}

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
