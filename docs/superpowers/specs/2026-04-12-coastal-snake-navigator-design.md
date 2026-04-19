# Coastal Snake Navigator — Design Spec
**Date:** 2026-04-12  
**Feature:** Замена CompassNavigator на CoastalSnakeNavigator для поиска Бирж вдоль побережья  
**Files affected:** `navigator.py` (основной), `engine.py` (без изменений)

---

## Проблема

Текущий `CompassNavigator` ходит от берега до берега через весь ГОС (`MAX_STEPS_SAFETY=80`).
Биржи появляются только по периметру — поэтому ~90% пути тратится впустую.
Бот уходит в центр ГОСа и пересекает океан, попадая в чужой ГОС.

---

## Решение: CoastalSnakeNavigator

Змейка вдоль береговой линии. Бот всегда остаётся в полосе 3–5 экранов от воды.
Навигация опирается на **анализ мини-карты** (180×180px), а не только на счётчик шагов.

---

## Ключевой принцип: читаем мини-карту

Мини-карта снимается через `pyautogui.screenshot(region=(cx-90, cy-90, 180, 180))`.
Уже есть `get_land_water_masks(minimap)` → возвращает `(land_mask, water_mask)`.

Из одного снимка мини-карты извлекаем три вещи:

1. **Угол берега** — PCA по пикселям границы вода/суша → главная ось = направление берега (угол `θ`)
2. **Вектор нырка** — `inland_dir = (cos(θ+90°), sin(θ+90°))`, нормализованный
3. **Тип воды впереди** — `land_ratio` в конусе по `inland_dir`: ≥3% суши = река/залив (переступаем), <3% = океан (стоп)

---

## Состояния (State Machine)

```
HOMING ──► DIVING ──► RETURNING
  ▲                       │
  └────── shift ──────────┘
```

### HOMING
Цель: выйти к береговой линии.

- Каждый шаг: снимаем мини-карту, проверяем есть ли вода в конусе по `coast_dir`
- Если граница вода/суша видна на мини-карте В НАПРАВЛЕНИИ `coast_dir` → мы у берега → переход в DIVING
- Максимум `homing_max_steps=10` шагов (страховка)
- При старте и после каждого SHIFT: пересчитываем `coast_angle` свежим снимком

### DIVING
Цель: нырнуть перпендикулярно берегу вглубь на N экранов.

- Направление: `inland_dir = perpendicular(coast_angle)` в сторону суши
- Каждый шаг: проверяем мини-карту по `inland_dir`
  - `land_ratio >= 0.03` → река/залив → идём дальше (перешагиваем)
  - `land_ratio < 0.03` И `water_pixels > MIN_WATER_PX` → океан → СТОП → переход в RETURNING
- Счётчик: `inland_steps >= max_inland_steps` → тоже СТОП → переход в RETURNING
- `max_inland_steps = 5` по умолчанию

### RETURNING
Цель: вернуться к берегу.

- Направление: `-inland_dir` (обратно к берегу)
- Каждый шаг: проверяем мини-карту — видна ли граница вода/суша по `coast_dir`
- Граница видна → мы у берега → SHIFT → переход в HOMING
- Максимум `max_inland_steps + 3` шагов (страховка от зависания)

### SHIFT
Один клик по `shift_dir = coast_angle_dir` (вдоль берега).  
После сдвига: пересчитываем `coast_angle` → переход в HOMING.

---

## Функции

### `detect_coast_angle(minimap_bgr) -> float`
```
Вход: BGR-снимок мини-карты 180×180px
Выход: угол θ в радианах (направление берега)

Алгоритм:
1. get_land_water_masks() → water_mask
2. Морфо-дилатация water_mask → находим границу water ∩ dilated_land
3. Точки границы → numpy array (N, 2)
4. Если < 10 точек → возвращаем предыдущий угол (нет данных)
5. PCA: np.linalg.eigh(cov(points)) → eigenvector с макс. eigenvalue = главная ось
6. angle = atan2(v[1], v[0])
7. inland_dir = angle + π/2  (перпендикуляр, в сторону меньшего кол-ва воды)
```

### `analyze_forward_zone(minimap_bgr, direction_vec, radius=60) -> dict`
```
Вход: мини-карта, вектор направления (dx, dy), радиус зоны проверки
Выход: {'water_px': int, 'land_px': int, 'land_ratio': float, 'is_ocean': bool}

Алгоритм:
1. Центр мини-карты = (90, 90)
2. Строим маску конуса: пиксели в радиусе `radius` по направлению ±45°
3. Применяем get_land_water_masks()
4. Считаем water_px и land_px в конусе
5. land_ratio = land_px / (water_px + land_px + 1)
6. is_ocean = (water_px > MIN_WATER_PX) and (land_ratio < OCEAN_LAND_RATIO)
```

### `_click_vector(dx_norm, dy_norm)`
```
Клик джойстика по произвольному вектору:
  x = center_x + dx_norm * p_range_x
  y = center_y + dy_norm * p_range_y
(поддерживает диагональные направления)
```

---

## Параметры

| Параметр | Значение | Описание |
|---|---|---|
| `max_inland_steps` | 5 | Макс. шагов вглубь |
| `ocean_land_ratio` | 0.03 | Порог суши (ниже = океан) |
| `min_water_px` | 500 | Мин. пикселей воды для ocean check |
| `homing_max_steps` | 10 | Макс. шагов к берегу при HOMING |
| `coast_angle_smoothing` | 5 | Скользящее среднее для угла (стабилизация) |

---

## Что НЕ меняется

- `CompassNavigator` — остаётся в коде, не удаляем
- `PacmanEngine` — без изменений, только подставляем `CoastalSnakeNavigator`
- `HuntEngine`, `engine.py` — без изменений
- `is_water_center_screen()`, `get_land_water_masks()` — используются as-is
- GUI-параметры: `center_x/y`, `step`, `scan_interval`, `reset_minutes`, `move_wait` — без изменений

---

## Подключение в PacmanEngine

```python
# navigator.py — добавить импорт внутри PacmanEngine.__init__:
from navigator import CoastalSnakeNavigator  # вместо CompassNavigator
self.joystick = CoastalSnakeNavigator(
    center_x=center_x,
    center_y=center_y,
    step=step,
    max_inland_steps=5,
)
```

---

## Тесты (TDD)

- `test_detect_coast_angle()` — синтетические мини-карты с известным углом берега
- `test_analyze_forward_zone_ocean()` — чисто синяя зона → is_ocean=True
- `test_analyze_forward_zone_river()` — синяя зона с зелёными вкраплениями → is_ocean=False
- `test_coastal_snake_state_machine()` — mock-снимки, проверка переходов состояний
- `test_click_vector_diagonal()` — проверка математики клика по произвольному вектору

---

## Открытые вопросы (решим при реализации)

- `coast_angle_smoothing`: если угол скачет (изрезанный берег) — использовать EMA (экспоненциальное скользящее среднее)
- Если при HOMING за 10 шагов берег не найден → сбросить в INIT, определить угол заново
