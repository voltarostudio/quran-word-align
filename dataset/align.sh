#!/bin/sh
# Align every recording in the dataset, without ayah timings: sh dataset/align.sh OUT [JOBS]
# Each recording goes to OUT/<read id>/; a run that stops can be started again (--resume).
# About 950 hours of audio: on a 10-core laptop with 5 jobs, some three hours.
OUT=${1:?folder to write to}
JOBS=${2:-5}
READS="123 118 112 53 54 31 30 92 86 5 109 4 62 76 20 217 12 81 46 60 106 14 16 80 120 75 270 208"
printf '%s\n' $READS | xargs -P "$JOBS" -I{} quran-word-align mp3quran {} --out "$OUT/{}" --resume
