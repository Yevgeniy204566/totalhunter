# Спека: Сопоставление имён Ancient ↔ Сундуки

**Дата:** 2026-06-28  
**Статус:** Approved  
**Файлы затронуты:** `server/models.py`, `server/ancients_dashboard.py`, `web/src/pages/AncientsPage.jsx`, `web/src/api.js`

---

## Проблема

Модуль «Древний» распознаёт имена игроков через OCR (pytesseract). Качество распознавания низкое:
- Кириллица читается как латиница («Маришка» → «Marisha?»)
- Артефакты, шум, обрезка букв
- Каждую сессию лидер тратит время на ручную правку

В модуле «Сундуки» уже есть вручную откорректированные `canonical_name` в таблице `PlayerAlias` — источник истины для имён клана.

**Цель:** связать OCR-имена из Древнего с правильными именами из Сундуков. Один раз настроил — всегда работает.

---

## Решение

### Уровни сопоставления (приоритет по убыванию)

1. **Подтверждённый маппинг** (`confirmed=True` в `AncientNameMapping`) — абсолютный приоритет, применяется автоматически
2. **Авто-предложение** (fuzzy-match ≥ порогу) — показывается в дропдауне как пред-выбранный вариант, требует подтверждения
3. **Сырое OCR-имя** — если нет ни маппинга, ни достаточного совпадения

---

## Секция 1 — База данных

### Новая таблица `ancient_name_mappings`

```sql
CREATE TABLE ancient_name_mappings (
    id            SERIAL PRIMARY KEY,
    collector_id  INTEGER NOT NULL REFERENCES chest_collectors(id) ON DELETE CASCADE,
    raw_ocr_name  VARCHAR(200) NOT NULL,
    canonical_name VARCHAR(200) NOT NULL,
    confirmed     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (collector_id, raw_ocr_name)
);
CREATE INDEX ix_ancient_name_mappings_lookup
    ON ancient_name_mappings (collector_id, raw_ocr_name);
```

**Примечание Gemini:** составной индекс `(collector_id, raw_ocr_name)` — обязателен, обеспечивает O(1) поиск при загрузке даже при тысячах записей.

### Модель `AncientNameMapping` в `models.py`

```python
class AncientNameMapping(Base):
    __tablename__ = 'ancient_name_mappings'
    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey('chest_collectors.id', ondelete='CASCADE'), nullable=False)
    raw_ocr_name   = Column(String(200), nullable=False)
    canonical_name = Column(String(200), nullable=False)
    confirmed      = Column(Boolean, nullable=False, default=False)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('collector_id', 'raw_ocr_name'),
        Index('ix_ancient_name_mappings_lookup', 'collector_id', 'raw_ocr_name'),
    )
```

---

## Секция 2 — Бэкенд

### GET `/web/dashboard/ancients` — расширение ответа

К каждому коллектору в поле `tournament_rows` добавить:
```json
{
  "player_name": "Marisha?",          // сырое OCR-имя
  "mapped_name": "Маришка",           // из AncientNameMapping (confirmed=True) или null
  "suggested_name": "Маришка",        // fuzzy-match авто-предложение или null
  "mapping_confirmed": true           // есть подтверждённый маппинг
}
```

**Логика на сервере при GET:**
1. Загрузить все `PlayerAlias.canonical_name` для этого коллектора (источник — Сундуки)
2. Загрузить все `AncientNameMapping` для этого коллектора
3. Для каждого уникального `player_name` в `tournament_rows`:
   - Есть подтверждённый маппинг → `mapped_name = mapping.canonical_name`, `mapping_confirmed = True`
   - Нет маппинга → fuzzy-match (`difflib.get_close_matches(name, canonical_names, n=1, cutoff=0.75)`) → `suggested_name`

**Параметр порога fuzzy:** сервер использует фиксированный дефолт `0.75`. Клиент передаёт `?fuzzy_threshold=0.XX` при запросе (от 0.5 до 1.0). Сервер применяет переданное значение вместо дефолта.

### PATCH `/web/dashboard/ancients/{slug}/name-mappings`

Батч-сохранение маппингов. Тело:
```json
{
  "mappings": [
    { "raw_ocr_name": "Marisha?", "canonical_name": "Маришка", "confirmed": true },
    { "raw_ocr_name": "PL4YER",   "canonical_name": "PLAYER",  "confirmed": true }
  ]
}
```

Логика: upsert по `(collector_id, raw_ocr_name)` — INSERT если нет, UPDATE если есть.
Авторизация: `get_web_user` + проверка владения коллектором через `_get_own_collector`.

### DELETE `/web/dashboard/ancients/{slug}/name-mappings/{raw_ocr_name}`

Разблокировка — удаляет запись, OCR-имя снова становится «несопоставленным».

### Публичная страница — GET `/api/v1/ancients/summary/{slug}`

При формировании публичного ответа применять подтверждённые маппинги: если для `player_name` есть `confirmed=True` запись → использовать `canonical_name` в выводе вместо сырого имени.

---

## Секция 3 — Фронтенд (`AncientsPage.jsx`)

### Ползунок порога fuzzy-match

Над таблицей Ancient — ползунок «Точность распознавания» (0.50 – 1.00, шаг 0.05, дефолт 0.75).
При изменении → повторный GET с `?fuzzy_threshold=<значение>` → таблица обновляется.

Подпись: `«Точность совпадения: {value * 100}%» — чем выше, тем строже подбор».`

### Новая колонка «Правильное имя»

В таблице игроков Ancient добавить колонку после «Игрок (OCR)»:

**Состояние A — маппинг подтверждён (`mapping_confirmed = true`):**
```
Маришка  [🔒 Разблокировать]
```
Текст не редактируется. Кнопка «Разблокировать» — отправляет DELETE → строка переходит в состояние B.

**Состояние B — нет маппинга, есть авто-предложение (`suggested_name != null`):**
```
[Маришка ▼]  ← дропдаун пред-выбран из fuzzy
```
Дропдаун = все `canonical_name` коллектора + пустое «не сопоставлять».

**Состояние C — нет ничего:**
```
[Выбрать имя ▼]  ← пустой дропдаун
```

### Кнопка «Сохранить маппинги»

Отдельная кнопка рядом с ползунком (не та же что «Сохранить» в Players).
Собирает все изменённые строки → `PATCH .../name-mappings`.
После успеха → `refresh()`.

### Публичная страница (`AncientsPage.jsx` или отдельный компонент)

Без изменений на UI. Данные приходят уже с правильными именами через сервер (секция 2, публичный GET).

---

## Секция 4 — Что НЕ входит в спеку

- Автоматическая транслитерация (кириллица↔латиница) — сознательно отложено, риск ложных совпадений
- История изменений маппингов — не нужна
- Маппинги между кланами — каждый `collector_id` независим
- Импорт маппингов из CSV — не нужен

---

## Тесты

- `test_get_ancients_returns_suggested_name` — fuzzy-match работает, возвращает `suggested_name`
- `test_get_ancients_returns_mapped_name_confirmed` — подтверждённый маппинг возвращает `mapped_name`, `mapping_confirmed=True`
- `test_patch_name_mappings_upsert` — повторный PATCH обновляет, не дублирует
- `test_delete_name_mapping_unlocks` — DELETE → строка возвращается в несопоставленное состояние
- `test_public_ancients_uses_confirmed_mapping` — публичный GET выдаёт `canonical_name`, не OCR-имя
- `test_fuzzy_threshold_param` — GET с `?fuzzy_threshold=0.9` не возвращает совпадение которое дало бы 0.75
