# Древний — условное форматирование недобора квоты

## Контекст

Запрошено владельцем 2026-06-23 (см. [[project_ancient_quota_shortfall_formatting]]),
уточнено 2026-07-01: подсветка строки ростера, если игрок недобрал свою квоту.
Формула: `недобор% = (quota − points) / quota × 100`, где `quota` — уже реализованная
колонка (см. [[project_ancient_quota_calculator]] и недавнюю фичу
«колонка Квота + звание»), `points` — уже реализованное поле `AncientRoster.points`,
это ФАКТ по конкретному Древнему через `tournament_reader.py` (не турнирные очки
другого события, см. [[project_ancient_points_is_fact]]).

Пороги градации (3 уровня: лёгкий/средний/критический) — НЕ хардкод, лидер вводит
проценты сам через поля на странице «Древний» (подтверждено владельцем явно: «это
задаваемое значение, оставь поля для ввода процентов»).

Цветовая палитра переиспользуется из уже существующего паттерна Сундуков
(`web/src/components/ChestSummaryTable.jsx`, классы `row-success`/`row-lagging`/
`row-danger`, `web/src/styles/theme.css:427-429`) — не изобретаем новую систему цветов.

## Хранение порогов

Три новых nullable-поля на `ChestCollector` (`server/models.py`, рядом с
`ancient_hidden_at` на строке 413 — тот же паттерн, что и другие per-collector
Ancient-настройки):

```python
ancient_shortfall_light_pct    = Column(Float, nullable=True)
ancient_shortfall_medium_pct   = Column(Float, nullable=True)
ancient_shortfall_critical_pct = Column(Float, nullable=True)
```

Если поле `None` — используется дефолт (10 / 30 / 60 соответственно), чтобы подсветка
работала «из коробки» до того, как лидер явно настроит проценты.

Alembic-миграция: `down_revision = "m1n2u3a4l5r6"` (текущий единственный head, проверено
`alembic heads`), добавляет три nullable `Float`-колонки на `chest_collectors`.

## Формула и защита от краёв (уточнено владельцем 2026-07-01)

```python
def shortfall_pct(quota: float | None, points: int | None) -> float | None:
    if quota is None or points is None:
        return None          # нет данных — подсветки нет
    if quota == 0:
        return None          # деление на ноль невозможно — нет базы для сравнения
    return (quota - points) / quota * 100.0
```

**Явно зафиксировано в TDD (по требованию владельца):**
- `quota == 0` → `None`, никакого `ZeroDivisionError`, никакой подсветки строки.
- Перевыполнение квоты (`points > quota`) → `shortfall_pct` отрицательный
  (например `quota=100, points=150` → `-50.0`) → математически корректно
  подпадает под «≤ light%» → зона **без подсветки** (не отдельный «супер-успех» цвет,
  YAGNI — не запрошено). Тест явно проверяет отрицательное значение, а не только
  положительные недоборы, чтобы это поведение не сломалось молча в будущем.

## Зоны и цвета

Где `light`/`medium`/`critical` — проценты из настроек коллектора (или дефолты
10/30/60, если не заданы):

| Условие | CSS-класс | Цвет |
|---|---|---|
| `shortfall_pct` is `None` | (нет подсветки) | — |
| `shortfall_pct <= light` | (нет подсветки) | — |
| `light < shortfall_pct <= medium` | `row-quota-light` (новый) | светло-жёлтый |
| `medium < shortfall_pct <= critical` | `row-lagging` (существующий) | `#FFB347` |
| `shortfall_pct > critical` | `row-danger` (существующий) | `#FF6961` |

Новый класс в `web/src/styles/theme.css` (рядом с `row-lagging`/`row-danger`,
строка ~429):
```css
.row-quota-light td { color: #F5D76E; }
```

## Backend

### `server/ancient_quota.py`
Добавить чистую функцию `shortfall_pct` (код выше) — без побочных эффектов, как и
остальной модуль.

### `server/ancients_dashboard.py`
- Новый эндпоинт `PATCH /{slug}/quota-thresholds` — принимает
  `{light_pct, medium_pct, critical_pct}` (все `Optional[float]`), сохраняет на
  `ChestCollector`, требует владельца (не редактора — это настройка коллектора
  целиком, а не правка одной строки ростера — тот же паттерн, что у
  `ancient-visibility`, который тоже owner-only).
- `_roster_rows` — добавить `shortfall_pct` в возвращаемый dict каждой строки (вызов
  новой функции `shortfall_pct(quota, r.AncientRoster.points)`).
- `get_dashboard_ancients` — отдавать в ответ по коллектору текущие пороги (или
  дефолты, если `None`): `"quota_thresholds": {"light_pct": ..., "medium_pct": ...,
  "critical_pct": ...}`.

## Frontend (`AncientsPage.jsx`)

- Три новых числовых `<input type="number">` на странице (рядом с калькулятором,
  в блоке настроек коллектора) — «Лёгкий недобор %», «Средний недобор %»,
  «Критический недобор %», сохранение по `onChange`/`onBlur` через новый
  `PATCH /quota-thresholds` (аналогично остальным настройкам страницы).
- Функция `rowShortfallClass(shortfallPct, thresholds)` — чистая JS-функция,
  зеркалирует таблицу зон выше, возвращает `''`/`'row-quota-light'`/`'row-lagging'`/
  `'row-danger'`.
- `<tr className={rowShortfallClass(p.shortfall_pct, c.quota_thresholds)}>` — класс
  строки ростера.

## Тестирование (TDD)

`server/tests/test_ancient_quota.py`:
- `shortfall_pct(100, 50) == 50.0`.
- `shortfall_pct(100, 0) == 100.0`.
- `shortfall_pct(0, 50) is None` — деление на ноль исключено (владелец явно попросил
  этот тест).
- `shortfall_pct(100, 150) == -50.0` — перевыполнение квоты даёт отрицательный
  недобор, не бросает исключение (владелец явно попросил зафиксировать этот кейс).
- `shortfall_pct(None, 50) is None`, `shortfall_pct(100, None) is None`.

`server/tests/test_ancients_dashboard.py`:
- `PATCH /{slug}/quota-thresholds`: успешное сохранение, доступно только владельцу
  (403 для редактора — по аналогии с `ancient-visibility`), 401 без токена.
- `GET /dashboard/ancients`: `quota_thresholds` отдаёт дефолты (10/30/60), когда поля
  `None`; отдаёт сохранённые значения после `PATCH`.
- Roster row: `shortfall_pct` присутствует и корректен при наличии `quota`+`points`;
  `None` при отсутствии одного из них (включая `quota == 0`, если такой сценарий
  вообще алгоритмически достижим — учтено по прямому требованию владельца).

Frontend — без отдельного автоматического тестового слоя (как и остальные страницы
`/dashboard`), верификация через `npm run build`.

## Явно не входит в эту спеку

- Отдельный «супер-успех» цвет для перевыполнения квоты — не запрошено, YAGNI.
- Уведомления/алерты о недоборе (email, Telegram) — не запрошено.
- История изменений порогов — не запрошено, поля просто перезаписываются.
