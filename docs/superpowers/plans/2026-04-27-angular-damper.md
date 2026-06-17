# Angular Damper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ограничить угол поворота вектора нырка между соседними проходами, устранив эффект спирографа на изогнутых берегах.

**Architecture:** Добавить `_clamp_vec()` на уровне модуля в `navigator.py`. В `CoastalSnakeNavigator` — новый параметр `max_pitch_delta` и стейт-переменная `_prev_inland_vec`. При каждом переходе HOMING→DIVING зажимать `_inland_vec` если угол поворота превышает лимит. `PacmanEngine` пробрасывает параметр дальше.

**Tech Stack:** Python 3.13, math (стандартная библиотека), pytest, unittest.mock

---

## File Map

| Файл | Что меняется |
|------|-------------|
| `navigator.py` | `import math`, `_clamp_vec()`, параметр + стейт в `CoastalSnakeNavigator`, применение в `step()` (2 места), `reset()` |
| `engine.py` (PacmanEngine) | добавить `max_pitch_delta` в `__init__()` и передать в `CoastalSnakeNavigator` |
| `test_coastal_snake.py` | 5 новых тестов |

---

### Task 1: `_clamp_vec()` — функция и тесты

**Files:**
- Modify: `navigator.py` (добавить `import math` и функцию после импортов)
- Modify: `test_coastal_snake.py` (добавить тесты)

- [ ] **Step 1: Написать падающие тесты для `_clamp_vec`**

Добавить в `test_coastal_snake.py` (после существующих импортов, новый класс в конце файла):

```python
import math
from navigator import _clamp_vec


class TestClampVec:
    def test_unit_length(self):
        """Result is always a unit vector."""
        result = _clamp_vec((0.0, 1.0), (1.0, 0.0), math.radians(10))
        length = math.sqrt(result[0]**2 + result[1]**2)
        assert abs(length - 1.0) < 1e-9

    def test_passes_small_angle(self):
        """Angle below threshold → v_new returned unchanged."""
        v_prev = (1.0, 0.0)
        v_new  = (math.cos(math.radians(5)), math.sin(math.radians(5)))
        result = _clamp_vec(v_new, v_prev, math.radians(10))
        assert abs(result[0] - v_new[0]) < 1e-9
        assert abs(result[1] - v_new[1]) < 1e-9

    def test_clamps_large_angle(self):
        """Angle above threshold → result is exactly max_delta from v_prev."""
        v_prev = (1.0, 0.0)
        v_new  = (0.0, 1.0)   # 90°
        max_d  = math.radians(10)
        result = _clamp_vec(v_new, v_prev, max_d)
        dot    = max(-1.0, min(1.0, result[0]*v_prev[0] + result[1]*v_prev[1]))
        assert abs(math.acos(dot) - max_d) < 1e-9

    def test_rotates_toward_v_new(self):
        """Clamping rotates toward v_new (CCW when v_new is CCW of v_prev)."""
        v_prev = (1.0, 0.0)   # 0°
        v_new  = (0.0, 1.0)   # 90° CCW
        result = _clamp_vec(v_new, v_prev, math.radians(10))
        assert result[1] > 0   # y > 0 → rotated CCW

    def test_exact_threshold_passes(self):
        """Angle exactly equal to max_delta → v_new unchanged."""
        max_d  = math.radians(10)
        v_prev = (1.0, 0.0)
        v_new  = (math.cos(max_d), math.sin(max_d))
        result = _clamp_vec(v_new, v_prev, max_d)
        assert abs(result[0] - v_new[0]) < 1e-9
        assert abs(result[1] - v_new[1]) < 1e-9
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestClampVec -v
```

Ожидание: `ImportError: cannot import name '_clamp_vec'` или аналогичная ошибка.

- [ ] **Step 3: Добавить `import math` в navigator.py**

В начало файла `navigator.py`, после `import re` (строка 11):

```python
import math
```

- [ ] **Step 4: Добавить `_clamp_vec()` в navigator.py**

Найти первую пустую строку после блока импортов (после строки `import pytesseract`, ~строка 20). Добавить функцию:

```python
def _clamp_vec(v_new: tuple, v_prev: tuple, max_delta: float) -> tuple:
    """
    Clamp rotation of v_new relative to v_prev to max_delta radians.
    Returns unit vector. Used by angular damper in CoastalSnakeNavigator.
    """
    dot   = max(-1.0, min(1.0, v_prev[0]*v_new[0] + v_prev[1]*v_new[1]))
    angle = math.acos(dot)
    if angle <= max_delta:
        return v_new
    cross = v_prev[0]*v_new[1] - v_prev[1]*v_new[0]
    theta = math.copysign(max_delta, cross)
    c, s  = math.cos(theta), math.sin(theta)
    return (v_prev[0]*c - v_prev[1]*s, v_prev[0]*s + v_prev[1]*c)
```

- [ ] **Step 5: Запустить тесты — убедиться что все зелёные**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestClampVec -v
```

Ожидание: **5 PASSED**

- [ ] **Step 6: Коммит**

```
cd C:\BattleBot && git add navigator.py test_coastal_snake.py && git commit -m "feat: add _clamp_vec() for angular damper"
```

---

### Task 2: `CoastalSnakeNavigator` — параметр, стейт, применение

**Files:**
- Modify: `navigator.py:429-496` (`__init__`, `reset`, `step`)
- Modify: `test_coastal_snake.py` (добавить тесты поведения навигатора)

- [ ] **Step 1: Написать падающие тесты поведения**

Добавить в `test_coastal_snake.py` новый класс:

```python
class TestAngularDamper:
    def test_first_dive_no_clamp(self):
        """First dive: _prev_inland_vec is None → inland_vec unchanged."""
        nav = make_navigator()
        nav._max_pitch_delta = math.radians(10)
        nav._inland_vec      = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50)):
            nav.step()
        assert nav._state == 'DIVING'
        # prev_inland_vec must now be set to (0, 1)
        assert abs(nav._prev_inland_vec[0] - 0.0) < 1e-9
        assert abs(nav._prev_inland_vec[1] - 1.0) < 1e-9

    def test_second_dive_clamps_large_angle(self):
        """Second dive with angle > max_pitch_delta → inland_vec clamped."""
        nav = make_navigator()
        nav._max_pitch_delta = math.radians(10)
        nav._prev_inland_vec = (1.0, 0.0)   # previous was 0°
        nav._inland_vec      = (0.0, 1.0)   # new would be 90°
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50)):
            nav.step()
        assert nav._state == 'DIVING'
        # angle from (1,0) to new _prev_inland_vec must be ~10°
        iv  = nav._prev_inland_vec
        dot = max(-1.0, min(1.0, iv[0]*1.0 + iv[1]*0.0))
        assert abs(math.acos(dot) - math.radians(10)) < 1e-9

    def test_damper_disabled_at_zero(self):
        """max_pitch_delta=0 → no clamping regardless of angle."""
        nav = make_navigator()
        nav._max_pitch_delta = 0.0
        nav._prev_inland_vec = (1.0, 0.0)
        nav._inland_vec      = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50)):
            nav.step()
        assert abs(nav._prev_inland_vec[0] - 0.0) < 1e-9
        assert abs(nav._prev_inland_vec[1] - 1.0) < 1e-9

    def test_reset_clears_prev_vec(self):
        """reset() clears _prev_inland_vec."""
        nav = make_navigator()
        nav._prev_inland_vec = (1.0, 0.0)
        nav.reset()
        assert nav._prev_inland_vec is None
```

- [ ] **Step 2: Запустить — убедиться что падают**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestAngularDamper -v
```

Ожидание: **4 FAILED** — `AttributeError: _max_pitch_delta` или аналог.

- [ ] **Step 3: Добавить параметр в `__init__`**

В `CoastalSnakeNavigator.__init__()`, после `coast_detect_radius: int = 50,` (строка ~444):

```python
        max_pitch_delta: float  = 10.0,  # degrees; 0 = disabled
```

В тело `__init__()`, после `self.coast_detect_radius = coast_detect_radius` (~строка 460):

```python
        self._max_pitch_delta   = math.radians(max_pitch_delta)
        self._prev_inland_vec   = None
```

- [ ] **Step 4: Обновить `reset()`**

В методе `reset()` (~строка 483), добавить в конец:

```python
        self._prev_inland_vec = None
```

- [ ] **Step 5: Применить демпфер в `step()` — место 1 (is_at_coast)**

Найти в `step()` блок (строки ~709-713):

```python
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                # fall through to DIVING in same call
```

Заменить на:

```python
                if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
                    self._inland_vec = _clamp_vec(
                        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
                    )
                self._prev_inland_vec   = self._inland_vec
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                # fall through to DIVING in same call
```

- [ ] **Step 6: Применить демпфер в `step()` — место 2 (homing_max_steps fallback)**

Найти в `step()` блок (строки ~730-734):

```python
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                # fall through to DIVING in same call
```

Заменить на:

```python
                if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
                    self._inland_vec = _clamp_vec(
                        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
                    )
                self._prev_inland_vec   = self._inland_vec
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                # fall through to DIVING in same call
```

- [ ] **Step 7: Запустить новые тесты**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestAngularDamper -v
```

Ожидание: **4 PASSED**

- [ ] **Step 8: Коммит**

```
cd C:\BattleBot && git add navigator.py test_coastal_snake.py && git commit -m "feat: angular damper in CoastalSnakeNavigator (max_pitch_delta)"
```

---

### Task 3: PacmanEngine — пробросить параметр

**Files:**
- Modify: `navigator.py` (PacmanEngine `__init__`, строки ~815-848)

- [ ] **Step 1: Добавить параметр в PacmanEngine**

В `PacmanEngine.__init__()`, после `coast_detect_radius: int = 50,` (~строка 829):

```python
        max_pitch_delta: float  = 10.0,
```

В тело — передать в `CoastalSnakeNavigator(...)` (~строка 848):

```python
            coast_detect_radius=coast_detect_radius,
            max_pitch_delta=max_pitch_delta,
```

- [ ] **Step 2: Проверить что нет ошибок импорта**

```
cd C:\BattleBot && python -c "from navigator import PacmanEngine; print('OK')"
```

Ожидание: `OK`

- [ ] **Step 3: Полная регрессия**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py -v
```

Ожидание: **49 passed** (44 старых + 5 новых: TestClampVec×5 + TestAngularDamper×4 = 9 новых → итого 53... )

> Точный счёт: 44 (было) + 5 (TestClampVec) + 4 (TestAngularDamper) = **53 passed**

- [ ] **Step 4: Коммит**

```
cd C:\BattleBot && git add navigator.py && git commit -m "feat: pass max_pitch_delta through PacmanEngine to CoastalSnakeNavigator"
```
