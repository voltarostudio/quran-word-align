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

# Quran word timings on mp3quran.net recordings (v3.1)

When each word of the Quran starts and ends in 111 recitations from
[mp3quran.net](https://www.mp3quran.net): 103 in the reading of Hafs (some of them mujawwad),
5 of Warsh and 3 of Qalun, about 8.86 million timed words. With them an app can light up each word of the mushaf as the reciter
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

| Reciter | Riwayah | Surahs | Words timed | Median confidence | Confidence ≥ 0.7 | Ayahs where mp3quran puts them |
|---|---|---|---|---|---|---|
| Mishary Alafasy | Hafs | 114 | 100.0% | 0.85 | 84.7% | 99.52% |
| Mahmoud Khalil Al-Husary | Hafs | 114 | 100.0% | 0.86 | 91.1% | 99.17% |
| Muhammad Siddiq Al-Minshawi | Hafs | 114 | 100.0% | 0.85 | 84.5% | 96.92% |
| Abdul Basit Abdul Samad | Hafs | 114 | 100.0% | 0.86 | 86.4% | 99.87% |
| Abdul Rahman Al-Sudais | Hafs | 114 | 100.0% | 0.85 | 80.6% | 98.7% |
| Saud Al-Shuraim | Hafs | 114 | 100.0% | 0.85 | 81.6% | 93.66% |
| Saad Al-Ghamdi | Hafs | 114 | 100.0% | 0.85 | 82.7% | 99.02% |
| Yasser Al-Dosari | Hafs | 114 | 100.0% | 0.86 | 84.3% | 98.52% |
| Nasser Al-Qatami | Hafs | 114 | 100.0% | 0.84 | 81.1% | 98.01% |
| Ahmad Al-Ajmi | Hafs | 114 | 100.0% | 0.83 | 78.9% | 96.49% |
| Muhammad Ayyub | Hafs | 114 | 100.0% | 0.88 | 89.2% | 99.73% |
| Abu Bakr Al-Shatri | Hafs | 114 | 100.0% | 0.83 | 79.8% | 99.26% |
| Abdullah Awad Al-Juhani | Hafs | 114 | 100.0% | 0.87 | 83.3% | 93.82% |
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
| Ibrahim Al-Akdar | Hafs | 114 | 100.0% | 0.85 | 86.8% | 99.92% |
| Ibrahim Al-Asiri | Hafs | 114 | 100.0% | 0.80 | 73.8% | 93.6% |
| Ahmad Al-Hawashi | Hafs | 114 | 100.0% | 0.79 | 70.5% | 96.42% |
| Ahmad Saber | Hafs | 114 | 100.0% | 0.82 | 79.2% | 99.13% |
| Ahmad Nauina | Hafs | 114 | 100.0% | 0.88 | 90.0% | 99.82% |
| Akram Alalaqmi | Hafs | 114 | 100.0% | 0.85 | 83.6% | 98.85% |
| Alzain Mohammad Ahmad | Hafs | 114 | 100.0% | 0.83 | 79.0% | 99.01% |
| Tawfeeq As-Sayegh | Hafs | 114 | 100.0% | 0.84 | 82.8% | 99.28% |
| Khaled Al-Qahtani | Hafs | 114 | 100.0% | 0.85 | 82.1% | 97.53% |
| Khalid Abdulkafi | Hafs | 114 | 100.0% | 0.83 | 80.4% | 98.27% |
| Khalifa Altunaiji | Hafs | 114 | 100.0% | 0.84 | 83.0% | 99.28% |
| Dawood Hamza | Hafs | 114 | 100.0% | 0.85 | 81.6% | 97.69% |
| Sahl Yassin | Hafs | 114 | 100.0% | 0.85 | 81.1% | 97.69% |
| Zaki Daghistani | Hafs | 114 | 100.0% | 0.84 | 84.4% | 98.91% |
| Shirazad Taher | Hafs | 114 | 100.0% | 0.83 | 79.6% | 99.15% |
| Saber Abdulhakm | Hafs | 114 | 100.0% | 0.85 | 80.7% | 98.83% |
| Saleh Alsahood | Hafs | 114 | 100.0% | 0.83 | 79.8% | 98.28% |
| Saleh Al-Habdan | Hafs | 114 | 100.0% | 0.82 | 77.9% | 97.1% |
| Salah Albudair | Hafs | 114 | 100.0% | 0.84 | 82.2% | 97.92% |
| Salah Alhashim | Hafs | 114 | 100.0% | 0.83 | 82.9% | 99.28% |
| Adel Ryyan | Hafs | 114 | 100.0% | 0.84 | 79.7% | 97.56% |
| Abdelbari Al-Toubayti | Hafs | 114 | 100.0% | 0.83 | 78.3% | 99.01% |
| Abdulbari Mohammad | Hafs | 114 | 100.0% | 0.83 | 82.1% | 99.45% |
| Abdulbasit Abdulsamad (Mujawwad) | Hafs | 114 | 100.0% | 0.83 | 87.9% | 97.93% |
| Abdul Aziz Al-Ahmad | Hafs | 114 | 100.0% | 0.88 | 84.9% | 97.43% |
| Abdulaziz Az-Zahrani | Hafs | 114 | 100.0% | 0.84 | 81.3% | 96.91% |
| Abdullah Albuajan | Hafs | 114 | 99.96% | 0.86 | 83.5% | 98.97% |
| Abdullah Al-Mattrod | Hafs | 114 | 100.0% | 0.85 | 84.6% | 99.17% |
| Abdullah Khayyat | Hafs | 114 | 100.0% | 0.79 | 68.9% | 99.1% |
| Abdulmohsin Al-Harthy | Hafs | 114 | 100.0% | 0.82 | 77.0% | 99.13% |
| Abdulmohsen Al-Qasim | Hafs | 114 | 100.0% | 0.86 | 83.6% | 92.1% |
| Abdulmohsin Al-Obaikan | Hafs | 114 | 99.99% | 0.80 | 71.3% | 98.08% |
| Abdulhadi Kanakeri | Hafs | 114 | 100.0% | 0.86 | 85.0% | 99.28% |
| Abdulwadood Haneef | Hafs | 114 | 100.0% | 0.84 | 79.6% | 98.54% |
| Abdulwali Al-Arkani | Hafs | 114 | 99.99% | 0.85 | 82.8% | 99.21% |
| Ali Alhuthaifi | Hafs | 114 | 100.0% | 0.83 | 82.1% | 87.16% |
| Ali Hajjaj Alsouasi | Hafs | 114 | 100.0% | 0.87 | 88.9% | 99.84% |
| Emad Hafez | Hafs | 114 | 100.0% | 0.86 | 87.5% | 100.0% |
| Nabil Al Rifay | Hafs | 114 | 100.0% | 0.82 | 78.5% | 98.94% |
| Neamah Al-Hassan | Hafs | 114 | 100.0% | 0.81 | 74.2% | 98.32% |
| Hani Arrifai | Hafs | 114 | 99.99% | 0.84 | 81.1% | 99.05% |
| Mohammad Saleh Alim Shah | Hafs | 114 | 100.0% | 0.84 | 80.5% | 99.09% |
| Mohammad Abdullkarem | Hafs | 114 | 100.0% | 0.87 | 83.0% | 95.04% |
| Mahmoud Khalil Al-Hussary (Mujawwad) | Hafs | 114 | 100.0% | 0.85 | 91.7% | 99.6% |
| Mahmoud Ali  Albanna (Mujawwad) | Hafs | 114 | 99.99% | 0.76 | 66.9% | 97.23% |
| Maher Al Meaqli (Mujawwad) | Hafs | 114 | 100.0% | 0.86 | 87.3% | 99.84% |
| Mohammad Saayed (Warsh) | Warsh | 114 | 100.0% | 0.81 | 77.1% | 8.95% |
| Abdulrahman Alsuwayid | Hafs | 114 | 100.0% | 0.81 | 75.9% | 14.22% |
| Ahmad Talib bin Humaid | Hafs | 114 | 100.0% | 0.83 | 79.8% | 11.4% |
| Majed Al-Zamil | Hafs | 114 | 100.0% | 0.83 | 78.8% | 94.76% |
| Khalid Almohana | Hafs | 114 | 100.0% | 0.87 | 88.0% | 95.62% |
| Jamaan Alosaimi | Hafs | 114 | 100.0% | 0.83 | 79.2% | 97.64% |
| Yousef Bin Noah Ahmad | Hafs | 114 | 100.0% | 0.84 | 80.7% | 93.6% |
| Mohammad Rashad Alshareef | Hafs | 114 | 100.0% | 0.84 | 83.7% | 99.55% |
| Ahmed Al-trabulsi | Hafs | 114 | 100.0% | 0.83 | 81.2% | 99.36% |
| Ahmed Amer | Hafs | 114 | 100.0% | 0.85 | 83.8% | 98.52% |
| Wadeea Al-Yamani | Hafs | 114 | 99.99% | 0.85 | 84.3% | 99.23% |
| Raad Al Kurdi | Hafs | 114 | 100.0% | 0.82 | 78.1% | 95.61% |
| Abdulrahman Aloosi | Hafs | 114 | 100.0% | 0.86 | 85.1% | 98.88% |
| Mohammad Khalil Al-Qari | Hafs | 114 | 100.0% | 0.82 | 75.4% | 98.89% |
| Ibrahim Aldosari | Hafs | 114 | 100.0% | 0.86 | 86.5% | 98.69% |
| Abdulrahman Al-Majed | Hafs | 114 | 100.0% | 0.82 | 77.7% | 99.07% |
| Abdullah Al-Mousa | Hafs | 114 | 100.0% | 0.83 | 78.4% | 94.76% |
| Abdullah Al-Khalaf | Hafs | 114 | 100.0% | 0.84 | 80.9% | 99.01% |
| Mansour Al-Salemi | Hafs | 114 | 100.0% | 0.80 | 74.5% | 98.64% |
| Mohammad Albukheet | Hafs | 114 | 100.0% | 0.85 | 85.5% | 99.82% |
| Ahmad Shaheen | Hafs | 114 | 100.0% | 0.84 | 83.7% | 99.65% |
| Abdulrasheed Soufi | Hafs | 114 | 100.0% | 0.83 | 79.6% | 98.75% |
| Ahmad Al Nufais | Hafs | 114 | 100.0% | 0.83 | 79.0% | 94.15% |
| Ahmad Deban | Hafs | 114 | 100.0% | 0.82 | 80.6% | 99.29% |
| Peshawa Qadr Al-Kurdi | Hafs | 114 | 100.0% | 0.84 | 82.0% | 97.82% |
| Haitham Aldukhain | Hafs | 114 | 100.0% | 0.83 | 80.1% | 97.71% |
| Abdulaziz Alturki | Hafs | 114 | 100.0% | 0.86 | 82.8% | 98.89% |
| Mustafa Ismail (Mujawwad) | Hafs | 114 | 100.0% | 0.76 | 66.0% | 96.3% |
| Ahmad Issa Al Maasaraawi | Hafs | 114 | 100.0% | 0.83 | 81.2% | 99.21% |
| Sayed Ahmad Hashemi | Hafs | 114 | 100.0% | 0.83 | 81.2% | 99.47% |
| Khalid Mohammadi | Hafs | 114 | 100.0% | 0.82 | 79.8% | 99.09% |
| Hasan Saleh | Hafs | 114 | 100.0% | 0.84 | 79.7% | 86.29% |
| Saleh Alshamrani | Hafs | 114 | 100.0% | 0.80 | 72.5% | 96.31% |
| Issa Omar Sanankoua | Hafs | 114 | 100.0% | 0.83 | 80.2% | 98.75% |
| Anas Alemadi | Hafs | 114 | 100.0% | 0.85 | 82.1% | 99.34% |
| Muhammad Burhaji | Hafs | 114 | 100.0% | 0.83 | 79.3% | 98.86% |
| Hassan Aldaghriri | Hafs | 114 | 100.0% | 0.85 | 83.8% | 99.15% |

"Ayahs where mp3quran puts them": the share of ayahs whose start we found inside the span mp3quran's
ayah timing gives that ayah. Most of the rest are mp3quran's mistakes, not ours: their timings are off
by an ayah or more in some surahs (Mohammad Saayed (Warsh), surah 2: 284 ayahs, Ahmad Talib bin Humaid, surah 2: 283 ayahs, Ahmad Al Nufais, surah 2: 283 ayahs, Abdulrahman Alsuwayid, surah 2: 280 ayahs, Ahmad Talib bin Humaid, surah 26: 227 ayahs, Mohammad Saayed (Warsh), surah 26: 225 ayahs). We checked such surahs by what the model hears at
each place: at our ayah starts it hears the ayah's first words, at theirs it does not. The 29,997
ayahs (of 691,741) are listed in `differs-from-mp3quran.csv`.

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

توقيتُ كلِّ كلمةٍ من كلمات القرآن، متى تبدأ ومتى تنتهي، في 111 تلاوةً من موقع mp3quran.net:
103 برواية حفص (منها المجوَّد)، و5 برواية ورش، و3 برواية قالون. يُعلِّم بها التطبيقُ الكلمةَ في المصحف
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
