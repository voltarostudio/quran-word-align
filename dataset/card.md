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

# Quran word timings on mp3quran.net recordings (v{version})

When each word of the Quran starts and ends in {reciters} recitations from
[mp3quran.net](https://www.mp3quran.net): {hafs} in the reading of Hafs (some of them mujawwad),
{warsh} of Warsh and {qalun} of Qalun, about {words} timed words. With them an app can light up each word of the mushaf as the reciter
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
| `ayah-timings.csv` | each ayah's start and end, `reciter, surah, ayah, start_ms, end_ms`: ayah timings found from the audio, right where mp3quran's are off |
| `basmala.csv` | each reciter's own basmala, `reciter, surah, start_ms, end_ms, confidence`: where it is in that surah's file, the clearest found, for apps that play it before a surah whose recording lacks one |
| `istiadha.csv` | the isti'adha, for the reciters who say it (before al-Fatiha or al-Baqarah), same columns: for apps that play it once when listening begins |
| `openings.csv` | how each surah's file opens, `reciter, surah, has_istiadha, has_basmala, first_word_ms, istiadha_end_ms`: 1 or 0 when it can be told, empty when not (a 0 is given only when sure, so an app that adds the reciter's basmala where it is 0 never doubles one); `first_word_ms`, where ayah 1 begins; `istiadha_end_ms`, where a clearly heard isti'adha ends |
| `basmala_words.csv` | the basmala's four words in each surah's file that opens with one, `reciter, surah, word, start_ms, end_ms, confidence` (word 1 to 4: بسم، الله، الرحمن، الرحيم), to light them as they are heard: given only where each word is heard clearly (confidence 0.5 or more, 0.75 on average) and the four end before ayah 1, so a light never runs ahead of the voice; other files are left out |
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
- **Checked by ear:** {checked} words were checked by listening and corrected where needed (with the
  demo page's review); their confidence is 1.
- **A reciter who goes back** and reads words again is followed: the words repeated are listed again,
  in the order heard. So an ayah may list a word twice.
- The basmala before the surahs (but al-Fatiha in Hafs) and the isti'adha are not in the timing files:
  the basmala's words are in `basmala_words.csv`, where heard clearly, and the isti'adha's end in `openings.csv`.
- One recording is noisy throughout (Mohammad Khalil Al-Qari, surah 13, ar-Ra'd): its ayahs are placed
  within mp3quran's ayah timing, but its words have low confidence (median 0.34).

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

{quality_table}

"Ayahs where mp3quran puts them": the share of ayahs whose start we found inside the span mp3quran's
ayah timing gives that ayah. Most of the rest are mp3quran's mistakes, not ours: their timings are off
by an ayah or more in some surahs ({worst_surahs}). We checked such surahs by what the model hears at
each place: at our ayah starts it hears the ayah's first words, at theirs it does not. The {differ}
ayahs (of {compared}) are listed in `differs-from-mp3quran.csv`.

## How it was made

1. [quran-asr-tiny](https://huggingface.co/Abdou/quran-asr-tiny) (MIT, by Abdou), a small model
   trained on Quran recitations, hears each 40 ms of the recording as letter probabilities.
2. The whole surah is followed a minute at a time, by CTC forced alignment of the ayahs' words,
   letter by letter, to find where each ayah is. No ayah timings are used.
3. Each ayah is aligned again in its own window, with a few words of the ayahs either side, and each
   word gets its confidence. Word ends before a pause come from the recording's loudness.

`dataset/align.sh` and `dataset/build.py` in the repository make the dataset from scratch.

**Version 1.0** (21 Hafs reciters) was aligned in mp3quran's ayah windows, and so went wrong wherever
those windows are off; version 2.0 finds the ayahs itself, adds confidence, Warsh and Qalun; version
3.0 has every mp3quran recording with ayah timings in these riwayat, mujawwad ones too, ayah timings
of its own, and words checked by ear.

## Credit and licence

The timings: **CC-BY 4.0**, Voltaro Studio. A credit that is enough:

> Word timings: quran-word-align by Voltaro Studio (CC-BY 4.0), on recordings from mp3quran.net.

The recordings and ayah timings are from mp3quran.net, which allows any use of its material; the
recordings belong to their reciters. The Quran text is the King Fahd Glorious Quran Printing Complex's,
unchanged. Nothing here comes from Quran.com. See `LICENSE.md`.

---

## بالعربية

توقيتُ كلِّ كلمةٍ من كلمات القرآن، متى تبدأ ومتى تنتهي، في {reciters} تلاوةً من موقع mp3quran.net:
{hafs} برواية حفص (منها المجوَّد)، و{warsh} برواية ورش، و{qalun} برواية قالون. يُعلِّم بها التطبيقُ الكلمةَ في المصحف
حين يقرؤها القارئ، أو يقطع بها التلاوة كلمةً كلمة.

التوقيت من عملنا، صنعناه بأداة quran-word-align، وهو مباحٌ برخصة **CC-BY 4.0**: انقله وانشره وعدّله
لأي غرض، تجاريًّا كان أو غيره، واذكر مصدره. والتلاوات ليست فيه: يشير كلُّ ملفٍّ إلى تسجيله في
mp3quran.net، ومعه بصمةُ الملف الذي وقّتناه.

- **الأزمنة** بالجزء من ألف من الثانية، من أول تسجيل السورة.
- **الكلمات والآيات** مرقّمةٌ كما يرقّمها مصحف مجمع الملك فهد لكل رواية.
- **الثقة** لكل كلمة، من صفر إلى واحد: مقدار وضوح حروفها للنموذج في موضعها.
- **إذا رجع القارئ فأعاد كلمات** ذُكرت الكلمات المعادة مرةً ثانية بترتيب سماعها.
- **وفيه توقيت الآيات أيضًا** (`ayah-timings.csv`)، وجدناه من التلاوة نفسها.
- **وبسملة كل قارئ بصوته** (`basmala.csv`): مكانها في أوضح سورةٍ عنده، لمن يشغّلها قبل سورةٍ ليس في تسجيلها بسملة.
- **والتعوّذ بصوت القارئ** (`istiadha.csv`) لمن قرأه منهم، لمن يشغّله مرةً عند بدء الاستماع.
- **وبداية كل سورة** (`openings.csv`): هل يبدأ ملفها بتعوّذ أو ببسملة (1 أو 0، وفارغٌ إن لم نستطع الحكم)، وأين تبدأ كلمتها الأولى، وأين ينتهي التعوّذ إن سُمع واضحًا.
- **وكلمات البسملة في كل ملف** (`basmala_words.csv`): متى تبدأ كل كلمة من كلماتها الأربع وتنتهي، لتُضاء مع القراءة. لا تُذكر إلا حيث سُمعت كل كلمة بوضوح، حتى لا يسبق الضوءُ صوتَ القارئ.
- **وجدنا مواضع الآيات بأنفسنا** من التسجيل، فصحّت حيث أخطأ توقيت الآيات في mp3quran، وهو خاطئٌ بآيةٍ أو
  أكثر في بعض السور.

**الإسناد:** التلاوات من موقع mp3quran.net، ونصّ المصحف من مجمع الملك فهد لطباعة المصحف الشريف،
والتوقيت من Voltaro Studio. وليس فيه شيءٌ من Quran.com.
