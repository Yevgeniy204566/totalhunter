# Сундуки — backend-фундамент (тенант-изоляция + import API)

Дата: 2026-06-18

## Контекст

Клиентский модуль «Сундуки» реализован и живо-протестирован (см.
`docs/superpowers/specs/2026-06-17-chest-counter-design.md`, `chest_reader.py`). Кнопка
«Отправить на сервер» зовёт `POST /api/v1/chests/import` — эндпоинт пока не существует.

Параллельно Gemini (`docs/Входящие_Gemini.md`, 2026-06-18) прислал три архитектурных
требования к серверной части:
1. **Tenant isolation** — учёт ведётся по тройке `[Королевство, Клан, владелец-сборщик]`,
   у каждого сборщика своя изолированная база и своя публичная ссылка на дашборд.
2. **Alias Dictionary** — серверный словарь автоисправлений OCR-ошибок (для имён игроков
   И для названий сундуков), применяется на лету при импорте.
3. **Ownership Transfer** — передача накопленной истории другому пользователю по PIN-коду.

Это четыре независимые подсистемы (фундамент БД+API, alias-редактор, публичный дашборд,
ownership transfer). Эта спека покрывает **только фундамент**: таблицы + import-эндпоинт +
изоляция + alias-lookup (без веб-UI). Остальные три — отдельные будущие спеки.

## Решённые архитектурные вопросы

- **Тенант = `users.id`.** Не вводим отдельную сущность «Account» — пользователь бота уже
  идентифицируется по `hwid` → `User.id` (как и везде в проекте, `/use_credit` и т.д.).
  Смена железа (новый HWID на тот же email) не требует transfer — `user.id` не меняется,
  это уже решено существующим `/web/link/verify`, который переносит `Hunt`/`Transaction`
  на тот же `web_user.id` при привязке аккаунта.
- **Ownership Transfer ≠ HWID reset.** Transfer (будущая подсистема) — это передача роли
  сборщика другому *человеку* (другой `user.id`), а не смена железа того же человека.
- **Alias Dictionary включается в фундамент сейчас** (таблицы + lookup при импорте), чтобы
  не переделывать схему `chests` после того, как появится веб-редактор. Сам редактор —
  отдельная подсистема.
- **Алиасы нужны для двух полей**, не только для имени игрока: OCR одинаково ошибается и в
  `sender` ("Араiiна" → "Арахна"), и в `chest_type` ("Араiiна" → "Эпическая Арахна" в названии
  типа сундука). Два отдельных словаря, симметричная логика.
- **Идемпотентность импорта.** Если сеть оборвётся после того как сервер записал данные, но
  до получения клиентом `200 OK`, клиент не пометит `is_synced=1` и пришлёт пакет повторно.
  Защита — unique constraint на `chests` по `(collector_id, sender_raw, chest_type_raw,
  collected_at)` + `INSERT ... ON CONFLICT DO NOTHING`.
- **Цена отправки — 10 кредитов**, не 1. Сейчас `CREDIT_COST` на сервере не содержит ключ
  `"chest"`, поэтому списывается `amount` по умолчанию (1) — это будет исправлено в этой же
  работе: `CREDIT_COST["chest"] = 10`.

## Таблицы

```python
class ChestCollector(Base):
    """Один сборщик внутри одного клана/королевства — единица тенант-изоляции.
    slug — непредсказуемый публичный идентификатор для будущего дашборда (подсистема 3)."""
    __tablename__ = "chest_collectors"
    id         = Column(Integer, primary_key=True)
    kingdom    = Column(String(50),  nullable=False)
    clan       = Column(String(100), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    slug       = Column(String(32), nullable=False, unique=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("kingdom", "clan", "user_id", name="uq_collector_tenant"),)


class Chest(Base):
    """Одна открытая сундук-запись. Уникальность по содержимому+времени защищает от
    дублей при повторной отправке после обрыва сети (idempotent import)."""
    __tablename__ = "chests"
    id                   = Column(Integer, primary_key=True)
    collector_id         = Column(Integer, ForeignKey("chest_collectors.id"), nullable=False, index=True)
    chest_type_raw       = Column(String(200), nullable=False)
    chest_type_canonical = Column(String(200), nullable=False)
    sender_raw           = Column(String(100), nullable=False)
    sender_canonical      = Column(String(100), nullable=False)
    collected_at         = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at           = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("collector_id", "sender_raw", "chest_type_raw", "collected_at",
                          name="uq_chest_idempotent"),
    )


class PlayerAlias(Base):
    """Словарь исправлений OCR для имён игроков, отдельно на каждого сборщика."""
    __tablename__ = "player_aliases"
    id              = Column(Integer, primary_key=True)
    collector_id    = Column(Integer, ForeignKey("chest_collectors.id"), nullable=False, index=True)
    raw_name        = Column(String(100), nullable=False)
    canonical_name  = Column(String(100), nullable=False)
    __table_args__ = (UniqueConstraint("collector_id", "raw_name", name="uq_player_alias"),)


class ChestTypeAlias(Base):
    """Словарь исправлений OCR для названий типов сундуков, отдельно на каждого сборщика."""
    __tablename__ = "chest_type_aliases"
    id               = Column(Integer, primary_key=True)
    collector_id     = Column(Integer, ForeignKey("chest_collectors.id"), nullable=False, index=True)
    raw_type         = Column(String(200), nullable=False)
    canonical_type   = Column(String(200), nullable=False)
    __table_args__ = (UniqueConstraint("collector_id", "raw_type", name="uq_chest_type_alias"),)
```

## Эндпоинт `POST /api/v1/chests/import`

Новый роутер `server/chests.py`, по образцу `server/clan.py`, но авторизация по `hwid`
(не Bearer ADMIN_TOKEN — вызывается рядовыми платящими пользователями бота, как
`/use_credit`).

**Payload** (как уже шлёт `chest_reader.export_to_api`):
```json
{
  "hwid": "...",
  "kingdom": "...",
  "clan": "...",
  "timestamp": "...",
  "items": [{"chest_type": "...", "sender": "...", "timestamp": "..."}]
}
```

**Логика:**
1. `items` пуст → 400 (`"items is empty"`, как `clan.py`).
2. Найти `User` по `hwid`. Не найден → 404. `is_banned` → 403.
3. `get_or_create ChestCollector(kingdom, clan, user_id)`; при создании — сгенерировать
   непредсказуемый `slug` (`secrets.token_urlsafe`).
4. Подгрузить все `PlayerAlias`/`ChestTypeAlias` для этого `collector_id` одним запросом
   (словарь raw→canonical в памяти, не по одному запросу на каждую запись).
5. Для каждого `item`: `chest_type_canonical = alias.get(chest_type_raw, chest_type_raw)`,
   аналогично для `sender`. Собрать bulk-insert в `chests` с
   `ON CONFLICT (collector_id, sender_raw, chest_type_raw, collected_at) DO NOTHING`.
6. Один `commit()` на весь батч.
7. Ответ: `{"ok": true, "count": N, "collector_slug": "..."}`.

## Изменение в существующем коде

- `server/main.py`: `CREDIT_COST["chest"] = 10` (было: не задано → списывалось 1 по
  умолчанию). `app.include_router(chests_router)`.
- `server/models.py`: добавить 4 новых класса выше.
- Alembic-миграция: `down_revision = 'c1l2a3n4m5b6'` (текущий head после `add_clan_members`).

## Тесты (TDD)

- Создание `ChestCollector` при первом импорте новой тройки `(kingdom, clan, user_id)`;
  повторный импорт той же тройки не создаёт вторую запись (get-or-create идемпотентен).
- Изоляция: два разных `user_id` с одинаковыми `kingdom`+`clan` получают разные
  `collector_id` и не видят данные друг друга.
- Alias-lookup применяется к `sender` и к `chest_type` независимо; при отсутствии алиаса
  `canonical = raw`.
- Идемпотентность: повторная отправка одного и того же батча (тот же `collected_at` на
  каждую запись) не создаёт дублей в `chests`.
- `items: []` → 400. Неизвестный `hwid` → 404. `is_banned=True` → 403.
- `CREDIT_COST["chest"] == 10` (regression-тест на стоимость).

## Явно не входит в этот фундамент (будущие подсистемы)

- Веб-редактор `player_aliases` / `chest_type_aliases`.
- Публичный дашборд клана по `collector_slug`.
- Ownership Transfer (PIN-код, перепривязка `collector.user_id`).
