# Angular Damper — Design Spec
**Date:** 2026-04-27
**Status:** Approved

---

## Problem

На изогнутом берегу `CoastalSnakeNavigator` вычисляет вектор нырка строго перпендикулярно текущему `coast_angle`. При резком изгибе берега угол между соседними нырками может быть 30–45°, что вызывает геометрическое перекрытие проходов начиная с глубины 4–5 экранов (эффект спирографа).

---

## Solution: Angular Damper

Ограничить угол поворота вектора нырка между двумя последовательными проходами параметром `max_pitch_delta`. Если новый вектор отклоняется от предыдущего больше допустимого — зажать его в лимит.

**Затрагивает только:** начало нырка (HOMING→DIVING).
**Не затрагивает:** DIVING, RETURNING, HOMING движение, `_inland_vec` во время нырка.

---

## Changes

### 1. Новый параметр `CoastalSnakeNavigator.__init__()`

```python
max_pitch_delta: float = 10.0,  # degrees; 0 = disabled
```

Хранится как `self._max_pitch_delta = math.radians(max_pitch_delta)`.

### 2. Новая state-переменная

В `__init__()` и `reset()`:
```python
self._prev_inland_vec: tuple | None = None
```

### 3. Вспомогательная функция (module-level)

```python
def _clamp_vec(v_new: tuple, v_prev: tuple, max_delta: float) -> tuple:
    """
    Clamp rotation of v_new relative to v_prev to max_delta radians.
    Returns unit vector.
    """
    import math
    dot   = max(-1.0, min(1.0, v_prev[0]*v_new[0] + v_prev[1]*v_new[1]))
    angle = math.acos(dot)
    if angle <= max_delta:
        return v_new
    # Rotate v_prev by max_delta toward v_new
    cross = v_prev[0]*v_new[1] - v_prev[1]*v_new[0]
    theta = math.copysign(max_delta, cross)
    c, s  = math.cos(theta), math.sin(theta)
    return (v_prev[0]*c - v_prev[1]*s, v_prev[0]*s + v_prev[1]*c)
```

### 4. Применение в `step()` — оба перехода HOMING→DIVING

Вставить **перед** каждым `self._state = 'DIVING'` (две точки: `is_at_coast` и `homing_max_steps` fallback):

```python
# Angular damper: limit dive angle change between passes
if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
    self._inland_vec = _clamp_vec(
        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
    )
self._prev_inland_vec = self._inland_vec
self._state = 'DIVING'
```

### 5. `reset()` — сбросить prev вектор

```python
self._prev_inland_vec = None
```

### 6. `PacmanEngine.__init__()` — пробросить параметр

Добавить `max_pitch_delta: float = 10.0` и передать в `CoastalSnakeNavigator(...)`.

---

## Behaviour

| Ситуация | Результат |
|----------|-----------|
| Первый нырок сессии | `_prev_inland_vec = None` → зажима нет, свободный угол |
| Берег прямой, δ ≤ 10° | угол не зажимается, поведение идентично текущему |
| Берег изогнут, δ = 30° | зажимается до 10°, нырок отклоняется плавно |
| `max_pitch_delta = 0` | демпфер отключён, поведение прежнее |
| `reset()` вызван | `_prev_inland_vec = None`, демпфер сбрасывается |

---

## Parameters

| Параметр | Тип | Default | Диапазон |
|----------|-----|---------|----------|
| `max_pitch_delta` | float | 10.0 | 0–15° (0 = выкл) |

---

## Tests Required

- `test_damper_clamps_large_angle` — δ > max_pitch_delta → вектор зажат
- `test_damper_passes_small_angle` — δ ≤ max_pitch_delta → вектор не изменён
- `test_damper_skips_first_dive` — первый нырок → `_prev_inland_vec` был None → зажима нет
- `test_damper_disabled_at_zero` — `max_pitch_delta=0` → вектор не изменён
- `test_clamp_vec_unit_length` — результат всегда unit-вектор
- Регрессия: все 44 существующих теста зелёные
