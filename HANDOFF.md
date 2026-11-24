# HANDOFF

Последнее обновление: 2026-11-24.

## Где остановились
- Все документы и конвейер созданы локально.
- Коммит в ветке `ccr-b666c1db-g02zqa` **не отправлен**: push → 403, нет прав (B2).
- Если читаете это в GitHub, значит, B2 уже снят.

## Следующие шаги
1. Проверить push-доступ: `git push -u origin ccr-b666c1db-g02zqa`.
2. Запустить сбор каталога: изменить `research/pipeline/requests/catalog.request`, запушить и дождаться коммита от `research-bot`.
3. `python research/pipeline/select_top30.py`.
   - Проверить `research/data/top30_selection_log.csv`: эвристики исключения, особенно песни и сборники.
   - Поправки внести в `research/data/top30_overrides.json`.
4. Запустить анализ: изменить `research/pipeline/requests/analyze.request` и запушить.
5. Расшифровать пакеты **вне репозитория**, заполнить `research/episodes/NS-xxx.md` по `_TEMPLATE.md`, проверить гипотезы H1–H12.
6. Обновить `COMPARATIVE_ANALYSIS.md`, `FINAL_REPORT.md`, `STATUS.md`. Создать PR в `main`.

## Важно
- Ключ age (приватный) остался только в облачном контейнере сессии.
  - Если сессия закончилась, сгенерируйте новую пару (`research/pipeline/README.md`) и замените recipient в `analyze.yml`.
  - Старые зашифрованные пакеты при этом станут нечитаемыми — это нормально, их можно пересоздать.
- Если YouTube блокирует скачивание видео с раннеров GitHub, метаданные и субтитры обычно доступны. Видео тогда анализируется локально (вариант 2 в `research/pipeline/README.md`).
