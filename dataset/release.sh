#!/bin/zsh
# Builds a dataset version and publishes it: GitHub release, Hugging Face, the README links. Then it reads
# back what was published and checks it is what was built.
#
#   dataset/release.sh VERSION NOTES.txt
#
# VERSION: 3.4 and so on; NOTES.txt: the release notes. The inputs are taken from $V3 (default
# ~/quran-word-align-v3): aligned/, places.json and voices.json there (links or copies of the latest).
set -eu
VERSION=$1
NOTES=$2
REPO=${0:A:h:h}
V3=${V3:-$HOME/quran-word-align-v3}
AUDIO=${AUDIO:-$HOME/.cache/quran-word-align/audio}
MP3QURAN=${MP3QURAN:-"$HOME/ Coding/quran app/content-pipeline/raw/mp3quran"}
HF=voltarostudio/quran-word-timings-mp3quran
NAME=quran-word-timings-mp3quran-v$VERSION
OUT=$V3/$NAME
PY=$REPO/.venv/bin/python
cd $REPO

[[ -s $NOTES ]] || { echo "no release notes in $NOTES"; exit 1 }
grep -q "Quran.com" $NOTES || { echo "the notes must say nothing comes from Quran.com"; exit 1 }
[[ -z $(git status --porcelain -- dataset quran_word_align tests) ]] || { echo "commit the code first"; exit 1 }
gh release view dataset-v$VERSION >/dev/null 2>&1 && { echo "dataset-v$VERSION is already published"; exit 1 }
$PY -m pytest -q tests/

echo "building $NAME"
$PY dataset/build.py $V3/aligned $MP3QURAN $AUDIO $OUT --version $VERSION \
    --basmala $V3/places.json --voices $V3/voices.json > $V3/build-$VERSION.log 2>&1
cmp -s dataset/README.md $OUT/README.md

sed -i '' "s/dataset-v[0-9][0-9.]*[0-9]/dataset-v$VERSION/g" README.md
git add README.md dataset/README.md
git commit -q -m "Dataset v$VERSION

$(cat $NOTES)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q

gh release create dataset-v$VERSION $OUT.zip --title "Quran word timings on mp3quran.net, v$VERSION (CC-BY 4.0)" --notes-file $NOTES
$PY -c "
from huggingface_hub import HfApi
print('Hugging Face', HfApi().upload_folder(folder_path='$OUT', repo_id='$HF', repo_type='dataset',
      commit_message='v$VERSION').oid)"

echo "checking what was published"
[[ $(gh release view dataset-v$VERSION --json assets -q '.assets[0].size') == $(stat -f %z $OUT.zip) ]] || { echo "GitHub zip differs"; exit 1 }
for f in openings.csv basmala.csv istiadha.csv basmala_words.csv reciters.csv README.md; do
    curl -sfL https://huggingface.co/datasets/$HF/resolve/main/$f | cmp -s - $OUT/$f || { echo "Hugging Face $f differs"; exit 1 }
done
echo "published dataset-v$VERSION: https://github.com/voltarostudio/quran-word-align/releases/tag/dataset-v$VERSION"
