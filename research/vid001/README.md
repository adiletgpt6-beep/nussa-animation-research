# VID-001 — контрольные данные и состав папки

Задание: GitHub Issue #3. Дата разбора: 2026-11-25.

## Исходник (в репозиторий НЕ загружается)

| Поле | Значение |
|---|---|
| Хранилище | Приватный Cloudflare R2 (BalaGo Studio); загрузка брокером `studio-fetch.mjs` по `STUDIO_SOURCE_TOKEN`. Подписанная ссылка не печаталась и не сохранялась |
| Размер | 285 020 864 байт — совпадает с Issue #3 |
| SHA-256 | `caa178ed38e8f7b783f73e1c877c4f97469d7139fa9e8e1cbd44897a4c2d8aff` — совпадает с Issue #3, проверено брокером и повторно |
| Контейнер | MP4, 4292,09 с (71:32), общий битрейт ≈ 531 кбит/с |
| Видео | AV1 Main, 1920×1080, yuv420p, BT.709, **25 fps (CFR)**, 107 302 кадра, ≈ 398 кбит/с |
| Аудио | AAC LC, стерео, 44,1 кГц, ≈ 128 кбит/с |
| Метаданные | Название «Nussa : Episode Compilation VOL. 15», YouTube-ID `MYLxENuMk5w`, дата 2021-04-22; встроены главы (SponsorBlock). Это скачанный с YouTube **сборник 13 серий 3-го сезона**, а не одна серия |

Локальная копия хранилась только в рабочем каталоге сессии (scratchpad) и удаляется вместе с контейнером.

## Файлы папки (только производные числовые данные и текст)

| Файл | Что внутри |
|---|---|
| [VID001_ANALYSIS.md](VID001_ANALYSIS.md) | **Главный документ**: технический, художественный и режиссёрский разбор по 10 пунктам задания, сравнение с исследованием 15 серий, ограничения |
| [SCENES.md](SCENES.md) | Разбор по сериям и сценам с тайм-кодами |
| [segments.json](segments.json) | Границы 13 серий в файле (секунды) |
| [shots.csv](shots.csv) | 682 плана: начало, конец, длина, движение, доля почти статичных пар кадров, панорама и зум камеры |
| [color.json](color.json) | Яркость, насыщенность, тёплая и синяя гамма по сериям (1 кадр/с) |
| [frame_cadence.json](frame_cadence.json) | Проверка частоты кадров: повторы кадров в движении через каждые 25 кадров |
| [audio_summary.json](audio_summary.json) | Громкость (EBU R128), доли окон с речью, музыкой, смехом и SFX, темп речи по ASR — **только числа, без текста реплик** |

Не коммитятся (остались локально):
- видео, прокси, кадры и сетки кадров;
- WAV;
- `audio_tags.csv` с метками по окнам;
- `asr_words.json` — распознанные слова, то есть чужой диалог.

## Как воспроизвести

```bash
NODE_USE_ENV_PROXY=1 node studio-fetch.mjs adiletgpt6-beep/nussa-animation-research VID-001 /tmp/vid001/source.mp4
python research/pipeline/video_shot_metrics.py /tmp/vid001/source.mp4 research/vid001/segments.json research/vid001/shots.csv
python research/pipeline/frame_cadence.py /tmp/vid001/source.mp4 research/vid001/frame_cadence.json --window 100:60 --window 1800:60 --window 3300:60
python research/pipeline/audio_analysis.py /tmp/vid001/source.mp4 research/vid001/segments.json /tmp/vid001/audio
cp /tmp/vid001/audio/audio_summary.json research/vid001/
```

`shots.csv` в репозитории посчитан на прокси 640×360 H.264, чтобы ускорить декодирование AV1. Границы планов от этого не зависят.
