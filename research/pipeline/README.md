# Конвейер исследования

Видео, аудио и полные транскрипты **никогда не коммитятся**:
- `.gitignore` исключает медиафайлы;
- workflow удаляет рабочую папку;
- приватные материалы шифруются.

## Вариант 1: GitHub Actions (нужен доступ на запись)

1. Изменить файл `research/pipeline/requests/catalog.request` и запушить его. Запустится `catalog.yml`, который закоммитит `research/catalog.csv`.
2. Локально выполнить `python research/pipeline/select_top30.py`, проверить `research/data/top30_selection_log.csv`. Ручные поправки внести в `research/data/top30_overrides.json`, закоммитить `research/top30.csv`.
3. Изменить `research/pipeline/requests/analyze.request` и запушить. Запустится `analyze.yml`, который закоммитит `research/data/episodes/*.metrics.json` и `research/data/private/*.age`.
4. Расшифровать вне репозитория: `research/pipeline/decrypt_private.sh <ключ> <папка>`.

## Вариант 2: локально (компьютер с доступом к YouTube)

```bash
pip install -U "yt-dlp[default]" "opencv-python-headless<5" "scenedetect[opencv-headless]" librosa soundfile faster-whisper numpy
# нужны ffmpeg, age, node (JS-runtime для yt-dlp)
python research/pipeline/collect_catalog.py
python research/pipeline/select_top30.py
python - <<'PY'
import csv, subprocess
for r in csv.DictReader(open("research/top30.csv")):
    subprocess.run(["python", "research/pipeline/analyze_episode.py", "--ns", r["ns_id"], "--video-id", r["video_id"],
                    "--out", "research/data/episodes", "--asr",
                    "--age-recipient", "age17s0943yf387pqy2ksk6fqmre2azrmq2e6zhjqlx9nqllvc7tuaasjdxten"])
PY
```

## Ключ шифрования

- Публичный ключ (recipient) указан в `.github/workflows/analyze.yml`.
- Приватный ключ хранится только у исследователя и **не должен попадать в репозиторий**.
- Если приватный ключ утерян (например, облачная сессия завершилась), нужно:
  1. создать новую пару ключей: `age-keygen -o key.txt`;
  2. заменить recipient в workflow;
  3. перезапустить анализ.
