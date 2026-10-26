# quran-word-align

Word-by-word timings for Quran recitations: when each word of the mushaf starts and ends in a
recording. [العربية أدناه](#بالعربية)

It is the aligner [Midad](https://voltarostudio.com) builds its word timings with, which highlight
each word in the mushaf as the reciter reads it. It runs on a laptop, without a GPU.

## How it works

1. **Listening.** [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) (MIT, by Abdou), a
   16-million-parameter Conformer-CTC trained on Quran recitations, gives each 40 ms of audio the
   likelihood of each Arabic letter. Each moment is heard in several overlapping six-second pieces and
   their likelihoods averaged, since the model alone is unsteady on long stretches.
2. **Placing.** CTC forced alignment fits the ayah's words, letter by letter, to those likelihoods.
   Each ayah is aligned in its own window (the ayah timing the recording comes with, widened by a
   margin). A few words of the ayahs either side are aligned with it, so the window's overlap is not
   taken for the ayah's own words. Silence and sounds that are not the text are left out.
3. **Repeats.** A reciter who goes back and reads words again is followed: the path may return to an
   earlier word, at a cost, and the repeated words are listed again in the order heard.

The words are the King Fahd Glorious Quran Printing Complex's Hafs text, numbered as its mushaf
numbers them (`quran_word_align/data/hafs-words.json`).

## Use

Needs Python 3.10+ and [ffmpeg](https://ffmpeg.org).

```sh
pip install git+https://github.com/voltarostudio/quran-word-align
quran-word-align reads                    # mp3quran recordings that have ayah timings
quran-word-align mp3quran 118 1 112       # al-Fatiha and al-Ikhlas of recording 118
quran-word-align file recitation.mp3 36 yasin-ayahs.json   # a recording of your own
```

The model (19 MB) is fetched once from Hugging Face and checked against its SHA-256.

A recording of your own needs its ayah timings, roughly:
`[{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...]`. Each surah is written as
`{"ayah": [[word, start_ms, end_ms], ...]}`.

## How good it is

Midad measured it against Quran.com's word timings for twelve of the same recordings (114 surahs
each, some 80,000 words per reciter). For nine of the twelve reciters, 75–86% of words start within
a quarter of a second of Quran.com's, with a median gap under a tenth of a second. It does worst on
slow recitations with long madds (Abdul Basit: 45% within a quarter second), on al-Rifai (25%), and on
recordings whose ayah timings are off. Quran.com's own timings are not exact either, so these numbers are agreement, not
error.

## Licence

The code: MIT. The model: MIT ([Abdou/quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny)).
The Quran text: from the King Fahd Glorious Quran Printing Complex, used unchanged. Recordings and
their ayah timings belong to their sources (mp3quran.net and others); this tool does not ship any.

---

## بالعربية

أداةٌ تعرف متى تبدأ كلُّ كلمة من كلمات المصحف ومتى تنتهي في تسجيل التلاوة. وهي التي يبني بها تطبيق
[مِداد](https://voltarostudio.com) توقيت الكلمات، فتُعلَّم الكلمة في المصحف حين يقرؤها القارئ.

**كيف تعمل:** يسمع نموذج [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) التلاوة
حرفًا حرفًا، ثم تُطابَق كلمات الآية على ما سمعه، في نافذة الآية من التسجيل. ويتابع القارئَ إن رجع
فأعاد كلمات، فتُذكر الكلمات المعادة مرةً ثانية بترتيب سماعها.

**الاستعمال:**

```sh
pip install git+https://github.com/voltarostudio/quran-word-align
quran-word-align mp3quran 118 1 112
```

**النص:** نصّ رواية حفص من مجمع الملك فهد لطباعة المصحف الشريف، كما هو دون تعديل.

**الرخصة:** الشيفرة بترخيص MIT، والنموذج كذلك. والتسجيلات وتوقيت آياتها لأصحابها، ولا تحمل الأداة شيئًا منها.
