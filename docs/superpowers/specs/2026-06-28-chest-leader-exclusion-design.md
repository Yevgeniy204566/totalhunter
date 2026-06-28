# Спека: Исключение типов сундуков для Главы клана

**Дата:** 2026-06-28  
**Статус:** Approved  
**Файлы:** `server/models.py`, `server/chest_summary.py`, `server/chest_dashboard.py`, `web/src/pages/ChestsPage.jsx`

---

## Проблема

После окончания турнира игра автоматически начисляет Главе клана большое количество сундуков — не за личный вклад, а как системные награды клана. Это искажает рейтинг: Глава оказывается на первом месте без реального участия.

---

## Решение (Подход A)

Два новых nullable-поля на `ChestCollector`. Фильтрация в Python в `pivot_summary()` — SQL не меняется.

---

## Секция 1 — База данных

### Удаляем мёртвую миграцию — точный алгоритм

`z9z8z7z6z5z4` стоит в середине цепочки: на неё ссылаются **две** миграции одновременно:
- `c4d5e6f7g8h9_chest_configuration.py` → `down_revision = 'z9z8z7z6z5z4'`
- `a1b2c3d4e5f6_add_custom_slug_to_chest_collectors.py` → `down_revision = 'z9z8z7z6z5z4'`

`z9z8z7z6z5z4` сама ссылается на `down_revision = 'q1w2e3r4t5y6'`.

**Шаги:**
1. В `c4d5e6f7g8h9_chest_configuration.py` заменить `down_revision = 'z9z8z7z6z5z4'` → `'q1w2e3r4t5y6'`
2. В `a1b2c3d4e5f6_add_custom_slug_to_chest_collectors.py` заменить `down_revision = 'z9z8z7z6z5z4'` → `'q1w2e3r4t5y6'`
3. Физически удалить `z9z8z7z6z5z4_add_chest_alias_enabled.py`
4. Запустить `alembic heads` — убедиться что `z9z8z7z6z5z4` больше не упоминается

### Новая миграция

Сгенерировать через `alembic revision` (ID будет автоматический — **не использовать `a1b2c3d4e5f6`**, этот ID уже занят миграцией `add_custom_slug_to_chest_collectors`).  
Down revision: текущий head после `alembic heads` (скорее всего multi-head — указать все через список).

```sql
ALTER TABLE chest_collectors
  ADD COLUMN leader_canonical_name VARCHAR(200),
  ADD COLUMN leader_excluded_catalog_ids JSONB NOT NULL DEFAULT '[]';
```

### Модель `ChestCollector` в `models.py`

Добавить два поля:
```python
leader_canonical_name       = Column(String(200), nullable=True)
leader_excluded_catalog_ids = Column(JSON, nullable=False, server_default=text("'[]'"))
```

---

## Секция 2 — Бэкенд

### `chest_summary.py` — `pivot_summary()`

Добавить два опциональных параметра:
```python
def pivot_summary(kingdom, clan, rows, *, leader_name=None, leader_excluded=frozenset()):
```

В цикле `for sender, chest_type_en, ... in rows:` добавить первой строкой:
```python
if leader_name and sender == leader_name and chest_type_en in leader_excluded:
    continue
```

Сигнатура вызовов из `chests.py` и `chest_history.py` обновляется передачей:
```python
leader_name=collector.leader_canonical_name,
leader_excluded=set(collector.leader_excluded_catalog_ids or []),
```

### `chest_dashboard.py` — новый эндпоинт

```
PATCH /web/dashboard/chests/{slug}/leader
```

Тело запроса:
```json
{
  "leader_canonical_name": "ИмяГлавы",      // null = снять лидера
  "leader_excluded_catalog_ids": ["Tournament Chest", "Clan Bounty"]
}
```

- Авторизация: `get_web_user` + проверка владения коллектором (паттерн как у `PATCH .../season`)
- Валидация: если `leader_canonical_name` не null — он должен присутствовать в `PlayerAlias` этого коллектора (или быть одним из raw-имён в `Chest`). Если не найден — `400`.
- Сохранение: прямой UPDATE на `ChestCollector`.

### `chest_dashboard.py` — GET ответ

В `GET /web/dashboard/chests` добавить в ответ коллектора поля:
```json
"leader_canonical_name": "ИмяГлавы" | null,
"leader_excluded_catalog_ids": ["Tournament Chest"]
```

---

## Секция 3 — Фронтенд (`ChestsPage.jsx`, вкладка «Игроки»)

### Таблица игроков

Новый столбец **«Глава»** после текущих колонок — радиокнопка `<input type="radio" name="leader">`.

- Только одна активна одновременно (семантика radio).
- Клик на уже активную = снять лидера (обрабатывается через `onClick`: если `leaderName === row.canonical_name` → `setLeaderName(null)`).
- Начальное значение берётся из `collector.leader_canonical_name` при загрузке страницы.

### Inline-секция исключений

Когда `leaderName !== null` — **под строкой выбранного игрока** появляется inline-блок (без модалки):

```
Не считать в статистику:
[ ] Tournament Chest
[ ] Clan Bounty
[x] Epic Crypt 35
```

Список = все `rows` из кабинета где `is_in_pattern === true`. Тоглы — `checkbox`.  
Снятая галочка = этот `catalog_id` попадёт в `leader_excluded_catalog_ids`.

Начальные значения берутся из `collector.leader_excluded_catalog_ids` при загрузке.

### Сохранение

Кнопка «Сохранить» (уже существующая в Players-секции) выполняет два запроса последовательно:
1. `POST /web/dashboard/chests/{slug}/player-aliases` (уже существует, без изменений)
2. `PATCH /web/dashboard/chests/{slug}/leader` — новый запрос с `{ leader_canonical_name, leader_excluded_catalog_ids }`

При ошибке любого из них — показать `setMsg(e.message)` (паттерн уже есть в компоненте).

### Публичная страница (`ChestSummaryPage.jsx`)

Без изменений. Сервер уже возвращает правильно отфильтрованные данные через `pivot_summary()`.

---

## Тесты

- `test_pivot_summary_leader_exclusion_filters_specific_types` — лидер с исключённым типом не получает очки за него, остальные игроки получают
- `test_pivot_summary_no_leader_unchanged` — без `leader_name` поведение идентично текущему
- `test_patch_leader_unknown_player_returns_400` — невалидное имя → 400
- `test_patch_leader_null_clears_leader` — передать null → поле очищается

---

## Что НЕ входит в эту спеку

- Несколько «специальных» игроков одновременно — за рамками, один лидер достаточно
- Отображение на публичной странице факта «этот игрок — Глава» — не требуется
- История изменений лидера — не требуется
