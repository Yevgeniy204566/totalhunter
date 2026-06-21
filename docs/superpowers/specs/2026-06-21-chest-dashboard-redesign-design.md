# Сундуки — редизайн кабинета + словарь игроков

Дата: 2026-06-21

## Контекст

`/dashboard/chests` (Фаза 4) функционален, но визуально это голый HTML (белые
инпуты, чекбоксы, `<table>` без стилей) — владелец явно просил современный вид.
Gemini прислал ТЗ на полный рефакторинг (`docs/Входящие_Gemini.md`), но часть
требований (выбор «паттерна» T9/T7 с отдельным Load/Save) противоречит
архитектуре Фазы 4, где у каждого клана один набор настроек без профилей —
эта часть ТЗ отклонена явно владельцем. Бага с несохранением кнопки «Сохранить»
на сервере уже не существует — исправлен сегодня (`0960a3c`, `5e63cb3`).

Попутно найден и устранён независимый баг: `_get_or_create_collector` сравнивал
`clan`/`kingdom` регистрозависимо, из-за чего один клан (229/BERS) задвоился —
данные смержены вручную, код пофикшен (`9984cbc`). Не относится к этой спеке,
упомянуто для контекста STATE.md.

## Что делаем

1. Премиальный тёмный дизайн страницы на существующей теме сайта
   (`web/src/styles/theme.css` — Deep Night, `--bg`/`--card`/`--accent`),
   без новой палитры.
2. Новая вкладка «Игроки» внутри карточки клана — словарь `player_aliases`,
   аналогично существующему словарю типов сундуков (авто-подтяжка
   неисправленных `sender_raw`, ручной ввод правильного имени, full-replace
   на «Сохранить имена»).
3. Toggle-switch вместо чекбокса для «В паттерне».
4. Проверка/фикс бага с «040» в поле очков при живом тесте в браузере.

## Backend

### `GET /web/dashboard/chests` (server/chest_dashboard.py)

Добавить в ответ на каждый `collector` новое поле `player_alias_rows`:
список `{raw_name, canonical_name}` — построено аналогично `_collector_rows`:
существующие `PlayerAlias` коллектора + `DISTINCT sender_raw` из `Chest`,
которых нет среди `raw_name` алиасов (`canonical_name: null` для них).
Новая функция `_player_alias_rows(db, collector)`, вызывается в той же ручке,
где сейчас собирается `rows`/`catalog_options`.

### `POST /web/dashboard/chests/player-aliases` (новый роут)

```
class PlayerAliasRowIn(BaseModel):
    raw_name: str
    canonical_name: Optional[str] = None

class PlayerAliasesPayload(BaseModel):
    collector_slug: str
    rows: List[PlayerAliasRowIn] = []
```

- Авторизация и владение — как у `/rows` (`_get_own_collector`).
- Full-replace: `DELETE FROM player_aliases WHERE collector_id=...`, затем
  `INSERT` по одной строке на каждый `row`, где `canonical_name` непусто
  (`.strip()`, как в существующем `chest_aliases.py`-паттерне). Строки с
  пустым/None `canonical_name` пропускаются — не создаём алиас «в никуда».
- Без проверки `raw_name` на дубли в payload — последняя строка с одинаковым
  `raw_name` победит за счёт `INSERT`, ограничение `uq_player_aliases_raw_name`
  гарантирует консистентность БД (если фронт случайно пришлёт дубль — 500,
  это сигнал бага на фронте, не штатный сценарий, в тестах не покрываем
  отдельно).

### Тесты (server/tests/test_chest_dashboard.py)

- `test_get_dashboard_includes_unmapped_sender_as_player_alias_row`
- `test_get_dashboard_includes_existing_player_alias_with_canonical_name`
- `test_post_player_aliases_full_replace_deletes_missing_rows`
- `test_post_player_aliases_skips_empty_canonical_name`
- `test_post_player_aliases_rejects_foreign_collector` (403, как у `/rows`)

## Frontend

### Структура `ChestsPage.jsx`

- Состояние на каждый collector: `activeTab` (`'chests' | 'players'`),
  по умолчанию `'chests'`.
- Новое поле в состоянии `playerRowsByCollector` (аналог `rowsByCollector`),
  заполняется из `data.collectors[].player_alias_rows` в `refresh()`.
- Над таблицей — два таб-кнопки (`.chest-tab`, `.chest-tab--active`),
  переключают видимую таблицу внутри той же карточки.
- Вкладка «Игроки»: таблица `Сырое имя (OCR) | Правильное имя` — текстовый
  инпут на обе колонки (без select, имена не из каталога). Кнопки
  «+ строка» и «Сохранить имена» — переиспользуют `addRow`/`save`-паттерн,
  но через отдельные функции `addPlayerRow(slug)` / `savePlayerAliases(slug)`,
  бьющие в новый `api.dashboardChestsPlayerAliases(slug, rows)`.
- `api.js`: новая функция
  `dashboardChestsPlayerAliases: (slug, rows) => request('POST', '/web/dashboard/chests/player-aliases', { collector_slug: slug, rows })`.

### Визуальный стиль (`web/src/styles/theme.css`)

Новые классы, без инлайн-стилей в JSX:

```css
.chest-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--outline); }
.chest-tab { background: transparent; border: none; padding: 10px 18px; color: var(--on-surface2);
             font-size: 14px; font-weight: 600; cursor: pointer; border-bottom: 2px solid transparent; }
.chest-tab:hover { color: var(--on-surface); }
.chest-tab--active { color: var(--on-surface); border-bottom-color: var(--accent); }

.chest-table { width: 100%; border-collapse: collapse; }
.chest-table th { text-align: left; padding: 10px 12px; color: var(--on-surface2);
                  font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px;
                  border-bottom: 1px solid var(--outline); }
.chest-table td { padding: 8px 12px; border-bottom: 1px solid var(--separator); }
.chest-table tr:hover td { background: var(--accent-faint); }

.input-dark, select.input-dark {
  background: var(--elevated); color: var(--on-surface); border: 1px solid var(--outline);
  border-radius: 6px; padding: 8px 10px; font-size: 14px; font-family: inherit; width: 100%;
}
.input-dark:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }

.toggle-switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-switch .slider { position: absolute; inset: 0; background: var(--outline);
                          border-radius: 22px; cursor: pointer; transition: background 0.15s; }
.toggle-switch .slider::before { content: ''; position: absolute; width: 16px; height: 16px;
                                  left: 3px; top: 3px; background: var(--on-surface);
                                  border-radius: 50%; transition: transform 0.15s; }
.toggle-switch input:checked + .slider { background: var(--accent); }
.toggle-switch input:checked + .slider::before { transform: translateX(18px); }
```

Карточки клана остаются `.card` (уже есть в теме). Кнопки «Сохранить»/«Загрузить
(перезагрузить)» — существующие `.btn-primary`/`.btn-secondary`.

### Баг «040» в поле очков

Текущий код: `value={row.points}` с `type="number"`. Живая проверка в браузере
перед/во время реализации — если воспроизводится (вероятно при ручном вводе
поверх `0`), фикс: `value={row.points === 0 ? '' : row.points}` +
`onChange` оставляет `parseInt(...) || 0` как есть. Если НЕ воспроизводится —
ничего не трогаем (не чинить то, что не ломалось).

### i18n

Новые строки в `dashboard_content.js`/`dashboard_content.en.js` под `chests`:
`playersTab`, `chestsTab`, `playerRawCol`, `playerCanonicalCol`, `savePlayerAliases`,
`addPlayerRow`.

## Вне рамок

- Выбор «паттерна» (T9/T7) с отдельными Load/Save — отклонено явно, противоречит
  архитектуре Фазы 4.
- Глобальный Chest Catalog/Localizations Sheets — не трогаются, отдельный поток
  (владелец правит вручную через Claude по запросу).
- Регистронезависимый мердж старых дублей-коллекторов у других кланов (если
  найдутся) — делается вручную SQL по обращению, не автоматизируется.

## Тестирование

- Backend: pytest на новые/изменённые ручки `chest_dashboard.py`.
- Frontend: живая проверка в браузере (dev-сервер) — переключение вкладок,
  сохранение обеих таблиц, toggle, проверка бага с очками, отображение на
  реальных данных клана 229/BERS после деплоя.
