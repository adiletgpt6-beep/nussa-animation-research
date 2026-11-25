#!/usr/bin/env bash
# Полный цикл тестовой сцены: голоса -> сцена и рендер (2D и 3D) -> звук -> MP4 -> QC.
# Требования: Python 3.13 + bpy 5.2.x, piper-tts[alignment], onnx, librosa, scipy, soundfile, opencv-python-headless;
#             ffmpeg; для QC — torch, transformers, faster-whisper (системный python3).
# Без GPU: EEVEE через программный OpenGL (EGL_PLATFORM=surfaceless, Mesa llvmpipe).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=${BPY_PYTHON:-/opt/bvenv/bin/python}
VOICES=${VOICES:?каталог с ru_RU-irina-medium.onnx (Piper)}
OUT=${OUT:-/tmp/test_scene_01}
mkdir -p "$OUT"
$PY "$HERE/src/voice.py" "$HERE/config" "$VOICES" "$OUT/audio"
for st in 2d 3d; do
  EGL_PLATFORM=surfaceless $PY "$HERE/src/blender/build.py" --audio "$OUT/audio" --out "$OUT" --style $st --render --res 1920 1080 --save-blend
done
$PY "$HERE/src/sfx_mix.py" "$OUT/audio" "$OUT/events.json" "$OUT/mix.wav"
$PY "$HERE/src/postprocess_2d.py" "$OUT/frames_2d" "$OUT/frames_2d_ink"
bash "$HERE/src/assemble.sh" "$OUT/frames_2d_ink" "$OUT/mix.wav" "$OUT/test_scene_01_2d.mp4"
bash "$HERE/src/assemble.sh" "$OUT/frames_3d" "$OUT/mix.wav" "$OUT/test_scene_01_3d.mp4"
for st in 2d 3d; do
  python3 "$HERE/src/qc.py" "$OUT/test_scene_01_$st.mp4" "$OUT/anim_qc.json" "$HERE/config/dialogue.json" "$OUT/qc_$st.json" --asr
done
