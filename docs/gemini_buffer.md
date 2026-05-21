# Хангоф #66 — 2026-05-21 (v1.5.0 выпущен, ZIP сломан)

## ПЕРВОЕ ДЕЙСТВИЕ — ФИКС ZIP v1.5.0

**Проблема:** ZIP в релизе v1.5.0 упакован неплоско. Клиенты в петле автообновлений.

**Причина:** `7z a TotalHunter.zip "dist/TotalHunter/*"` из корня → пути `dist/TotalHunter/TotalHunter.exe` внутри архива → xcopy не заменяет exe → петля.

**Фикс:** Запустить `python build_release.py` — скрипт теперь сам создаёт плоский ZIP из `dist/TotalHunter/` и проверяет структуру. Потом залить ZIP в Release v1.5.0 через браузер (Edit release).

**Порядок:**
1. `python build_release.py` (пересборка + правильный ZIP автоматически)
2. Открыть https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.0
3. Edit release → удалить старый TotalHunter.zip → перетащить новый → Update release
4. Версию на сервере НЕ менять (уже 1.5.0)
5. Петля у клиентов прекратится

---

## Что было сделано в этой сессии

### Backtracking в _exchange_detected (navigator.py)
- `CoastalSnakeNavigator._click_vec`: записывает `_last_move_vec = (ndx, ndy)` после каждого клика
- `PacmanEngine._backtrack_step()`: инвертирует `_last_move_vec`, делает один клик назад
- `PacmanEngine._exchange_detected`: рефактор с `_fresh_scan()` helper + ветка backtrack:
  - sleep(0.5) → YOLO #1 → нашли: клик
  - не нашли → `_backtrack_step()` → sleep(0.3) → YOLO #2 → нашли: клик
  - оба пустые → return (ложное срабатывание)
- 5 новых TDD тестов `test_exchange_backtrack.py` (5/5 ✅)
- Все 13 тестов ✅

### Инфраструктура сборки (исправление ошибки)
- `build_release.py` шаг 6: теперь сам создаёт плоский ZIP из `dist/TotalHunter/` (`cwd=dist_dir`)
- Валидация: если `TotalHunter.exe` не в корне архива — FATAL, сборка падает
- `CLAUDE.md`: добавлено критическое правило ZIP
- `ANTI-PATTERNS.md`: добавлен AP-UPDATER-NESTING
- `MEMORY/feedback_zip_flat_packing.md`: новая запись в память

### Релиз
- version.py: 1.4.3 → 1.5.0
- GitHub Release v1.5.0 создан, ZIP загружен (но НЕПЛОСКИЙ — требует замены)
- Сервер: /version/latest = 1.5.0

---

## Коммиты этой сессии

| Хэш | Описание |
|---|---|
| a656426 | feat: backtracking в _exchange_detected (5 TDD тестов) |
| 410f40e | chore: bump version 1.4.3 → 1.5.0 |
| d83f0d5 | fix: ZIP плоская упаковка — AP-UPDATER-NESTING + автовалидация |

---

## Известные проблемы / следующие задачи

| Приоритет | Задача |
|---|---|
| 🔴 СРОЧНО | Фикс ZIP v1.5.0 (инструкция выше) |
| Средний | ROY OCR координат из диалога — проверить что именно читается (уже работает в engine.py) |
| Средний | Fortune Wheel — финальный визуал (Unsplash CORS, real PNG ассеты) |
| Низкий | Реклама: Adsterra нативные баннеры |
| Низкий | Баг «выкидывает в магазин» — не диагностирован |
