# Конвейер исследования

Видео, аудио и полные транскрипты **никогда не коммитятся**:
- `.gitignore` исключает медиафайлы;
- workflow удаляет рабочую папку;
- материалы для визуального разбора (транскрипт, контактные листы) пишутся только в локальную папку `--review-dir` и в репозиторий не попадают — даже в зашифрованном виде.

## Вариант 1: GitHub Actions (нужен доступ на запись)

1. Изменить файл `research/pipeline/requests/catalog.request` и запушить его. Запустится `catalog.yml`, который закоммитит `research/catalog.csv`.
2. Локально выполнить `python research/pipeline/select_top15.py`, проверить `research/data/top15_selection_log.csv`. Ручные поправки внести в `research/data/top15_overrides.json`, закоммитить `research/top15.csv`.
3. Изменить `research/pipeline/requests/analyze.request` и запушить. Запустится `analyze.yml`, который закоммитит только числовые метрики `research/data/episodes/*.metrics.json`.

⚠ На практике (24–25.11.2026) YouTube отвечал облачным адресам проверкой «не бот», поэтому видео не скачивалось; исследование 15 серий выполнено по субтитрам и раскадровкам (см. `research/FINAL_REPORT.md`).

## Вариант 2: локально (компьютер с доступом к YouTube)

```bash
pip install -U "yt-dlp[default]" "opencv-python-headless<5" "scenedetect[opencv-headless]" librosa soundfile faster-whisper numpy
# нужны ffmpeg и node (JS-runtime для yt-dlp)
python research/pipeline/collect_catalog.py
python research/pipeline/select_top15.py
python - <<'PY'
import csv, subprocess
for r in csv.DictReader(open("research/top15.csv")):
    subprocess.run(["python", "research/pipeline/analyze_episode.py", "--ns", r["ns_id"], "--video-id", r["video_id"],
                    "--out", "research/data/episodes", "--asr", "--review-dir", "/tmp/nussa-review"])
PY
```

## Вариант 3: видео от заказчика (BalaGo Studio, VID-xxx)

```bash
pip install "scenedetect[opencv-headless]" opencv-python-headless numpy pandas soundfile torch transformers faster-whisper
NODE_USE_ENV_PROXY=1 node studio-fetch.mjs <owner/repo> VID-001 /tmp/vid/source.mp4   # нужен STUDIO_SOURCE_TOKEN
python research/pipeline/video_shot_metrics.py /tmp/vid/source.mp4 research/vid001/segments.json research/vid001/shots.csv
python research/pipeline/frame_cadence.py /tmp/vid/source.mp4 research/vid001/frame_cadence.json --window 100:60
python research/pipeline/audio_analysis.py /tmp/vid/source.mp4 research/vid001/segments.json /tmp/vid/audio   # --reuse: только пересчёт сводки
```

| Скрипт | Что считает | Что можно коммитить |
|---|---|---|
| `video_shot_metrics.py` | Планы (PySceneDetect), движение, почти статичные пары кадров, панорама и зум камеры (Farneback) | CSV с числами |
| `frame_cadence.py` | Повторы кадров в движении → «на единицах / двойках», конвертация 24→25 fps | JSON с числами |
| `audio_analysis.py` | EBU R128, AudioSet AST (речь, музыка, смех, SFX), ASR faster-whisper с метками слов | только `audio_summary.json`; `audio_tags.csv` и `asr_words.json` — локально |

Видео, WAV, кадры и распознанный текст в git не добавлять.

## Правило

Папку `--review-dir` не добавлять в git. В карточки серий — только короткие цитаты (≤ 2 предложений).
