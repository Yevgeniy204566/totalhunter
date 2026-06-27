# Спека: Звание и Состав войск игрока в системе Сундуков

**Дата:** 2026-06-27  
**Статус:** Approved

---

## Цель

Добавить два поля на игрока — **Звание** и **Состав войск (G/S/M)** — в систему сундуков:
- Вкладка «Игроки» в кабинете лидера (`/dashboard/chests`)
- Публичная страница клана (`/chests/:slug`)

Данные единые: одна запись на игрока, используется также в калькуляторе «Древний».

---

## Константы домена

### Звания (rank)
```
Глава, Старший, Офицер, Ветеран, Рядовой
```
Пустое значение ("") = не задано.

### Состав войск (troop_level)
13 значений из `TROOP_STEPS` в `server/ancient_quota.py`:
```
G5 S5 M5, G5 S5 M6, G5 S6 M6,
G6 S6 M6, G6 S6 M7, G6 S7 M7,
G7 S7 M7, G7 S7 M8, G7 S8 M8,
G8 S8 M8, G8 S8 M9, G8 S9 M9,
G9 S9 M9
```
Пустое значение ("") = не задано.

---

## 1. База данных

### Новая таблица `player_profiles`

```sql
CREATE TABLE player_profiles (
    id              SERIAL PRIMARY KEY,
    collector_id    INTEGER NOT NULL REFERENCES chest_collectors(id) ON DELETE CASCADE,
    canonical_name  VARCHAR(100) NOT NULL,
    rank            VARCHAR(20)  DEFAULT NULL,
    troop_level     VARCHAR(20)  DEFAULT NULL,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (collector_id, canonical_name)
);
```

**Ключ:** `(collector_id, canonical_name)` — canonical_name из `PlayerAlias.canonical_name`.  
**Миграция:** новый Alembic revision, без изменения существующих таблиц.

---

## 2. Backend

### 2.1. Модель SQLAlchemy `PlayerProfile` (models.py)

```python
class PlayerProfile(Base):
    __tablename__ = "player_profiles"
    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey("chest_collectors.id", ondelete="CASCADE"), nullable=False)
    canonical_name = Column(String(100), nullable=False)
    rank           = Column(String(20), nullable=True)
    troop_level    = Column(String(20), nullable=True)
    updated_at     = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("collector_id", "canonical_name", name="uq_player_profile"),)
```

### 2.2. Эндпоинт: кабинет лидера (chest_dashboard.py)

```
POST /web/dashboard/chests/player-profiles
```

- Auth: `get_web_user` (владелец коллектора)
- Payload: `{ collector_slug, rows: [{canonical_name, rank, troop_level}] }`
- Логика: upsert по `(collector_id, canonical_name)` — INSERT … ON CONFLICT DO UPDATE

### 2.3. Эндпоинт: публичная страница (chest_dashboard.py)

```
POST /api/v1/chests/public/player-profile
```

- Auth: **нет** (анонимный, данные не критичные)
- Payload: `{ collector_slug, canonical_name, rank, troop_level }`
- Логика: upsert по `(collector_id, canonical_name)`, slug → collector lookup

### 2.4. Расширение `GET /api/v1/chests/summary/{slug}`

Добавить в каждый объект игрока поля `rank` и `troop_level` через LEFT JOIN с `player_profiles`:

```python
# В каждом player-объекте ответа добавить:
"rank":        profile.rank        or None,
"troop_level": profile.troop_level or None,
```

### 2.5. Интеграция с Ancient-калькулятором

`GET /web/dashboard/ancients/{slug}` — при сборке ростера игроков подтягивать `troop_level` из `player_profiles` через LEFT JOIN по `canonical_name` (в пределах того же `collector_id`). Если `AncientRoster.troop_level` уже задан вручную — оставлять его (приоритет ручного ввода лидера).

---

## 3. Frontend

### 3.1. Кабинет лидера — `ChestsPage.jsx`, вкладка «Игроки»

Существующая таблица `[raw_name → canonical_name]` получает **2 новые колонки**:

| OCR имя | Исправленное имя | Звание | Состав |
|---|---|---|---|
| Marishka | Маришка | `<select>` | `<select>` |

- `<select>` для Звания: `["", "Глава", "Старший", "Офицер", "Ветеран", "Рядовой"]`
- `<select>` для Состава: `["", ...TROOP_STEPS]`
- Данные загружаются вместе с алиасами при открытии вкладки
- Сохраняются **одной кнопкой «Сохранить»** — единый вызов двух POST (алиасы + профили)

### 3.2. Публичная страница — `ChestSummaryPage.jsx`

**Кнопка вверху таблицы:**
```
[✏️ Ввести состав]   ← при нажатии показывает колонки
```

**В режиме редактирования** — в таблицу добавляются 2 колонки слева от «Очков»:

| # | Игрок | Звание | Состав | Очки | ... |
|---|---|---|---|---|---|
| 1 | Маришка | `[Офицер ▼]` | `[G8 S8 M9 ▼]` | 14 715 | |
| 2 | Niduel | `[Ветеран ▼]` | `[G7 S7 M8 ▼]` | 12 300 | |

Рядом с каждой строкой — кнопка **💾**. При нажатии:
1. `POST /api/v1/chests/public/player-profile` с данными строки
2. После успешного ответа — колонки скрываются (режим редактирования выключается)

**В обычном режиме** колонки Звание/Состав **не отображаются** — таблица остаётся чистой.

---

## 4. Что НЕ входит в скоуп

- Валидация/модерация анонимных данных (лидер правит в кабинете)
- История изменений
- Отображение Звания/Состава в обычном (не-edit) режиме публичной таблицы
- Сортировка по Званию или Составу

---

## 5. Порядок реализации

1. Alembic-миграция + `PlayerProfile` модель
2. Backend: 2 POST-эндпоинта + расширение summary
3. Backend: интеграция с Ancient (LEFT JOIN)
4. Frontend: `ChestsPage.jsx` — колонки в Players
5. Frontend: `ChestSummaryPage.jsx` — кнопка + edit-режим
