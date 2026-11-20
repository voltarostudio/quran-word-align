# quran-word-align

Word-by-word timings for Quran recitations: when each word of the mushaf starts and ends in a
recording. It runs on a laptop without a GPU, or in the browser. [العربية أدناه](#بالعربية)

- **[Try it in your browser](https://voltarostudio.github.io/quran-word-align/)**: pick a reciter from
  mp3quran.net or a recording of your own, watch the words light up, download the timings. Nothing is
  uploaded.
- **[The dataset](https://github.com/voltarostudio/quran-word-align/releases/tag/dataset-v2.0)**: 28 complete
  recitations from mp3quran.net (Hafs, Warsh, Qalun), already timed word by word, CC-BY 4.0.
  [What is in it](dataset/README.md). Also on
  [Hugging Face](https://huggingface.co/datasets/voltarostudio/quran-word-timings-mp3quran).

It is the aligner [Midad](https://voltarostudio.com) builds its word timings with: they highlight each
word of the mushaf as the reciter reads it.

## What it does

- **Any recording of a whole surah.** It finds the ayahs itself; ayah timings are optional.
- **Hafs, Warsh and Qalun**, each on the King Fahd Complex's own text of that riwayah.
- **A confidence for every word**, so you know which timings to trust and which to check.
- **Repeats**: a reciter who goes back and reads words again is followed, and the words are listed
  again in the order heard.
- **Pauses**: a word after a pause starts where the voice comes back; a word before one ends where the
  voice stops.
- **JSON, CSV, SRT, WebVTT** (with word-by-word timestamps) and **Quran.com-style segments**.

## Use

Needs Python 3.10+ and [ffmpeg](https://ffmpeg.org).

```sh
pip install git+https://github.com/voltarostudio/quran-word-align

quran-word-align file yasin.mp3 36                      # a recording of your own (Hafs)
quran-word-align file mulk.mp3 67 --riwayah warsh       # Warsh, or qalun
quran-word-align file fatiha.mp3 1 --format json,srt,vtt
quran-word-align reads                                  # mp3quran.net recordings, with their ids
quran-word-align mp3quran 118 1 112                     # al-Fatiha and al-Ikhlas of recording 118
```

The model (19 MB) is fetched once from Hugging Face and checked against its SHA-256. A recording
must hold one whole surah; what comes before the first ayah (the isti'adha, the basmala) is skipped.

If your recording has ayah timings already, `--timings ayahs.json` aligns each ayah in its window
(`[{"ayah": 1, "start_ms": 0, "end_ms": 6100}, ...]`). For mp3quran.net, `--ayah-timings` uses
theirs; by default the ayahs are found in the recording, which is right also where their timings are
not (they are off by an ayah or more in some surahs).

### Output

Each surah is written to `aligned/<surah>.json`:

```json
{"1": [[1, 6480, 6960, 0.81], [2, 6960, 7640, 0.79], [3, 7640, 8800, 0.68], [4, 8800, 11080, 0.70]],
 "2": [[1, 12400, 13480, 1.0], ...]}
```

Each ayah lists its words as heard: `[word, start_ms, end_ms, confidence]`. Words are numbered from 1
in each ayah, as the King Fahd Complex's mushaf numbers them (`quran_word_align/data/<riwayah>-words.json`).

| `--format` | File | What it is |
|---|---|---|
| `json` | `001.json` | as above |
| `csv` | `001.csv` | `surah, ayah, word, start_ms, end_ms, confidence, text` |
| `srt` | `001.srt` | one subtitle an ayah |
| `vtt` | `001.vtt` | one cue an ayah, with a timestamp before each word, for karaoke-style highlighting |
| `segments` | `001.segments.json` | Quran.com's shape: `verse_timings` with `segments: [[word, start, end], ...]` |

The segments keep the King Fahd mushaf's word numbers, which Quran.com's match in most ayahs but not
in every one; check before mixing the two.

### From Python

```python
from pathlib import Path
from quran_word_align.align import Model, align_recording, mushaf_words

words = mushaf_words("hafs")
result = align_recording(36, Path("yasin.mp3"), words, Model())
```

## How good it is

There is no exact reference for word timings, so these are checks, not an error rate. All but the
last are made by [`eval/evaluate.py`](eval/evaluate.py) on mp3quran.net's recordings, with public data
only; the numbers are in [eval/RESULTS.md](eval/RESULTS.md).

- **Finding the ayahs.** On 203 surahs (28 reciters, three riwayat, 40 hours), every one of the
  10,871 ayahs was found. Where mp3quran's own ayah timings fit the recording, the ayah starts found
  are within one second of theirs for 98.6% of ayahs in Hafs, 100% in Warsh and 99.6% in Qalun. Where they do not (al-Husary's al-Fatiha, al-Shuraim's Yusuf, Idris Abkar's Ya-Sin), the
  model hears the ayah's first words at our start and other words at theirs.
- **Words after a pause** start within 80 ms of where the voice comes back: 99.3% of them in Hafs,
  97.5% in Warsh, 97.9% in Qalun.
- **Against Quran.com's word timings**, where Quran.com's recording is the same performance, word
  starts within each ayah agree within a quarter of a second for 90% to 96% of words, slow reciters
  included (Abdul Basit 92%, al-Husary 90%, al-Shatri 96%). Earlier we reported Abdul Basit at 45%:
  that measure counted Quran.com's convention of starting a word in the silence before it as our
  error, and leaned on mp3quran's ayah timings where they are off. Quran.com's data was used only to
  measure, in Midad's own pipeline; none of it is in this repository or the dataset.
- **Confidence tracks accuracy**: of the words above 0.85 (about half), 90% agree with Quran.com
  within a quarter second; of those under 0.3 (under 1%), 15%.

What is not settled: in flowing speech, our word starts run on average 0.1 s later than Quran.com's
(0.2 s for Abdul Basit). We have not yet checked by ear which of the two is nearer to where a listener
hears the word begin. Recordings of only part of a surah, or of several surahs in one file, are not
supported yet.

## How it works

1. **Listening.** [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) (MIT, by Abdou), a
   16-million-parameter Conformer-CTC model trained on Quran recitations, gives each 40 ms of audio
   the probability of each Arabic letter. Each moment is heard in several overlapping six-second
   pieces and their probabilities averaged, since the model alone is unsteady on long stretches.
2. **Finding the ayahs.** The surah is followed a minute at a time: CTC forced alignment fits the
   words of the ayahs not yet placed to that minute, letter by letter, with the path free to stop
   after any word. Every ayah but the last one reached is placed, and the next minute starts at that
   last ayah.
3. **Placing the words.** Each ayah is aligned again in its own window, with a few words of the ayahs
   either side so they are not taken for its own. Silence and sounds that are not the text are left
   out. A reciter who goes back is followed: the path may return to an earlier word, at a cost.
4. **Confidence** is the mean, over the word's letters, of the highest probability the model gave the
   letter while the path was on it.

The words are the King Fahd Glorious Quran Printing Complex's text of each riwayah, from its developer
packages (version 3.0), split into words by [`tools/mushaf_words.py`](tools/mushaf_words.py) and never
typed by hand. A test pins each words file's SHA-256.

## Development

```sh
pip install -e ".[test]"
pytest                         # the aligner on synthetic letter probabilities; no model, no audio
python eval/evaluate.py        # the accuracy numbers above (downloads ~5 GB of recordings)
sh dataset/align.sh OUT        # align the whole dataset (hours)
```

The tests run on GitHub Actions on every push ([`.github/workflows/test.yml`](.github/workflows/test.yml)).

`demo/` is the browser version: `aligner.js` is `align.py` ported line by line, and gives the same
timings (346 of 348 words within 40 ms on a test surah).

## Licence

The code: MIT. The timings in the dataset: CC-BY 4.0. The model: MIT
([Abdou/quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny)). The Quran text and the mushaf
fonts in `demo/fonts`: the King Fahd Glorious Quran Printing Complex's, unchanged, which allows their
free use and distribution as long as they are not sold or modified. Recordings and their ayah timings
belong to their sources (mp3quran.net and others); this repository holds none.

---

## بالعربية

**quran-word-align** أداةٌ تعرف متى تبدأ كلُّ كلمةٍ من كلمات المصحف ومتى تنتهي في تسجيل التلاوة. تعمل
على حاسوبٍ عادي دون معالجٍ رسومي، وتعمل في المتصفح أيضًا. وهي التي يبني بها تطبيق
[مِداد](https://voltarostudio.com) توقيت الكلمات، فيُعلِّم الكلمة في المصحف حين يقرؤها القارئ.

- **[جرّبها في متصفحك](https://voltarostudio.github.io/quran-word-align/):** اختر قارئًا من mp3quran.net
  أو تلاوةً من جهازك، فترى الكلمات تُعلَّم مع القراءة، ثم نزّل توقيتها. لا يُرفع تسجيلك إلى أي مكان.
- **[مجموعة البيانات](https://github.com/voltarostudio/quran-word-align/releases/tag/dataset-v2.0):** ٢٨ ختمةً كاملة من
  mp3quran.net بروايات حفص وورش وقالون، موقّتةٌ كلمةً كلمة، ومباحةٌ برخصة CC-BY 4.0.
  وهي على [Hugging Face](https://huggingface.co/datasets/voltarostudio/quran-word-timings-mp3quran) أيضًا.

### ما تفعله

- **تقبل تسجيل أي سورةٍ كاملة،** وتجد مواضع الآيات بنفسها، فلا تحتاج إلى توقيتٍ للآيات.
- **تعرف روايات حفص وورش وقالون،** على نصّ مجمع الملك فهد لكل رواية.
- **تعطي كلَّ كلمةٍ درجةَ ثقة** من صفرٍ إلى واحد، فتعرف أيَّ توقيتٍ تطمئن إليه وأيَّه تراجعه.
- **تتابع القارئ إن رجع** فأعاد كلمات، فتذكر الكلمات المعادة مرةً ثانية بترتيب سماعها.
- **تراعي الوقف:** تبدأ الكلمة بعد الوقف حين يعود الصوت، وتنتهي الكلمة قبله حين يسكت القارئ.
- **تكتب التوقيت** بصيغ JSON وCSV وSRT وWebVTT، وبصيغة المقاطع التي يستعملها Quran.com.

### الاستعمال

تحتاج إلى بايثون ٣٫١٠ أو أحدث، وإلى ffmpeg.

```sh
pip install git+https://github.com/voltarostudio/quran-word-align
quran-word-align file yasin.mp3 36                    # تلاوة سورة يس من جهازك
quran-word-align file mulk.mp3 67 --riwayah warsh     # برواية ورش، أو qalun لقالون
quran-word-align mp3quran 118 1 112                   # الفاتحة والإخلاص من تسجيلات mp3quran
```

يُنزَّل النموذج (١٩ م.ب) مرةً واحدة، ويُتحقَّق من بصمته. ويجب أن يحوي التسجيلُ سورةً كاملة، وتُتخطّى
الاستعاذة والبسملة قبل أول آية.

### ما مدى دقتها

ليس لتوقيت الكلمات مرجعٌ دقيق يُقاس عليه، فهذه فحوصٌ لا نسبةُ خطأ. وأكثرها يُعاد بسكربت
`eval/evaluate.py` على تسجيلات mp3quran ببياناتٍ عامة.

- **مواضع الآيات:** وجدنا الآيات كلَّها، ١٠٨٧١ آية في ٢٠٣ سورة لثمانيةٍ وعشرين قارئًا. وحيث يوافق توقيتُ
  الآيات في mp3quran التسجيلَ، تقع بداياتنا على ثانيةٍ أو أقل من بداياتهم في ٩٨٫٦٪ من الآيات برواية حفص،
  و١٠٠٪ برواية ورش، و٩٩٫٦٪ برواية قالون. وحيث لا يوافقه، كفاتحة
  الحصري ويوسف الشريم، يسمع النموذجُ أولَ كلمات الآية عند بدايتنا، وكلماتٍ أخرى عند بدايتهم.
- **الكلمة بعد الوقف** تبدأ على بُعد ٨٠ جزءًا من ألف من الثانية أو أقل من عودة الصوت في ٩٧٫٥٪ إلى ٩٩٫٣٪ منها.
- **موازنةً بتوقيت Quran.com** حيث يكون تسجيلُه التلاوةَ نفسها: تتفق بدايات الكلمات داخل الآية على ربع
  ثانيةٍ أو أقل في ٩٠٪ إلى ٩٦٪ منها، ومنها التلاوات البطيئة (عبد الباسط ٩٢٪، الحصري ٩٠٪، الشاطري ٩٦٪).
  واستعملنا بيانات Quran.com للقياس وحده، وليس منها شيءٌ في هذا المستودع ولا في مجموعة البيانات.
- **درجة الثقة تدلّ على الدقة:** ٩٠٪ من الكلمات التي تزيد ثقتها على ٠٫٨٥ توافق Quran.com، و١٥٪ فقط مما
  تقلّ ثقته عن ٠٫٣.

وما لم نحسمه بعد: في الكلام المتصل تتأخر بداياتنا عن بدايات Quran.com عُشرَ ثانيةٍ في المتوسط (وخُمسَها عند
عبد الباسط)، ولم نتحقق بالسمع أيُّهما أقرب إلى موضع ابتداء الكلمة. ولا تقبل الأداة بعدُ تسجيلًا لجزءٍ من
سورة، ولا تسجيلًا يجمع سورًا عدة.

### كيف تعمل

١. **تسمع:** يسمع نموذج [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) التلاوةَ حرفًا
   حرفًا، كلَّ جزءٍ من خمسةٍ وعشرين من الثانية.
٢. **تجد الآيات:** تتابع السورةَ دقيقةً دقيقة، فتطابق كلماتِ الآيات على ما سمعه النموذج، وتثبّت كلَّ آيةٍ
   اكتملت قبل أن تنتقل.
٣. **تضع الكلمات:** تطابق كلَّ آيةٍ وحدها في نافذتها، ومعها كلماتٌ من الآيتين قبلها وبعدها، فلا تختلط بها.

**النص:** نصُّ مجمع الملك فهد لطباعة المصحف الشريف لكل رواية، من حزم المطوّرين التي نشرها، مقسومًا إلى
كلماتٍ بسكربت، كما هو دون تعديل، ولم تُكتب منه كلمةٌ باليد.

**الرخصة:** الشيفرة بترخيص MIT، والنموذج كذلك، والتوقيت في مجموعة البيانات بترخيص CC-BY 4.0. ونصّ المصحف
وخطوطه من مجمع الملك فهد كما هي. والتسجيلات وتوقيت آياتها لأصحابها، ولا يحمل المستودع شيئًا منها.
