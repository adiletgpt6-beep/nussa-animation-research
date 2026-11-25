#!/usr/bin/env bash
# Сборка MP4: кадры PNG + сведённый звук -> H.264 1920x1080 30 fps, AAC 48 кГц, громкость -15 LUFS.
# assemble.sh FRAMES_DIR MIX_WAV OUT_MP4
set -euo pipefail
ffmpeg -v error -y -framerate 30 -i "$1/%04d.png" -i "$2" \
  -af "loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -r 30 -vf "scale=1920:1080:flags=lanczos,setsar=1" \
  -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$3"
