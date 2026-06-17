# Ocean March Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить проверку `fwd['land_px'] == 0` перед нырком — бот не ныряет в чистый океан.

**Architecture:** Одно место изменения — блок `if info['is_at_coast']:` в `CoastalSnakeNavigator.step()`. Если `fwd['land_px'] == 0` и `water_px > min_water_px` → `_shift_click()` и остаёмся в HOMING. Всё остальное нетронуто.

**Tech Stack:** Python 3.13, pytest, unittest.mock

---

## File Map

| Файл | Изменение |
|------|-----------|
| `test_coastal_snake.py` | Добавить 2 новых теста (Task 1) |
| `navigator.py:696-713` | Вставить 4 строки в `if info['is_at_coast']:` (Task 2) |

---

### Task 1: Написать падающие тесты

**Files:**
- Modify: `test_coastal_snake.py`

- [ ] **Step 1: Добавить тест — океанная колонка пропускается**

В конец класса `TestCoastalSnakeStateMachine` в `test_coastal_snake.py` добавить:

```python
def test_ocean_column_skips_dive(self):
    """At coast: fwd has no land and lots of water → shift, stay HOMING."""
    nav = make_navigator(min_water=10)
    with patch.object(nav, '_read_minimap',
                      return_value=_info(is_at_coast=True, land_px=0, water_px=500)):
        with patch.object(nav, '_shift_click') as mock_shift:
            nav.step()
    mock_shift.assert_called_once()
    assert nav._state == 'HOMING'

def test_ocean_column_insufficient_water_dives(self):
    """At coast: fwd land_px=0 but water_px <= min_water_px → normal dive."""
    nav = make_navigator(min_water=10)
    with patch.object(nav, '_read_minimap',
                      return_value=_info(is_at_coast=True, land_px=0, water_px=5)):
        nav.step()
    assert nav._state == 'DIVING'
```

- [ ] **Step 2: Запустить тесты — убедиться что оба падают**

```
cd C:\BattleBot
python -m pytest test_coastal_snake.py::TestCoastalSnakeStateMachine::test_ocean_column_skips_dive test_coastal_snake.py::TestCoastalSnakeStateMachine::test_ocean_column_insufficient_water_dives -v
```

Ожидание: **2 FAILED** — `assert nav._state == 'HOMING'` упадёт (сейчас переход в DIVING безусловный).

- [ ] **Step 3: Убедиться что регрессионный тест всё ещё зелёный**

```
cd C:\BattleBot
python -m pytest test_coastal_snake.py::TestCoastalSnakeStateMachine::test_homing_transitions_to_diving_when_at_coast -v
```

Ожидание: **1 PASSED** — этот тест использует `land_px=100` (дефолт), изменений кода ещё нет.

---

### Task 2: Реализовать фикс — 4 строки в navigator.py

**Files:**
- Modify: `navigator.py:696-713`

- [ ] **Step 1: Вставить проверку в блок `if info['is_at_coast']:`**

Найти в `navigator.py` (строка ~696):

```python
            if info['is_at_coast']:
                # Fallback: if detect_coast_angle never returned a real angle,
                # set shift_vec from whatever coast_vec we have now.
                if not self._shift_vec_set:
```

Заменить на:

```python
            if info['is_at_coast']:
                fwd = info['fwd']
                if fwd['land_px'] == 0 and fwd['water_px'] > self.min_water_px:
                    self._shift_click()   # чистый океан → пропустить колонку
                    return True           # остаёмся в HOMING
                # Fallback: if detect_coast_angle never returned a real angle,
                # set shift_vec from whatever coast_vec we have now.
                if not self._shift_vec_set:
```

- [ ] **Step 2: Запустить новые тесты — убедиться что оба зелёные**

```
cd C:\BattleBot
python -m pytest test_coastal_snake.py::TestCoastalSnakeStateMachine::test_ocean_column_skips_dive test_coastal_snake.py::TestCoastalSnakeStateMachine::test_ocean_column_insufficient_water_dives -v
```

Ожидание: **2 PASSED**

---

### Task 3: Регрессия и коммит

**Files:**
- Run: `test_coastal_snake.py` (полный прогон)

- [ ] **Step 1: Запустить весь test_coastal_snake.py**

```
cd C:\BattleBot
python -m pytest test_coastal_snake.py -v
```

Ожидание: **44 passed** (42 старых + 2 новых), 0 failed.

- [ ] **Step 2: Запустить все тесты проекта**

```
cd C:\BattleBot
python -m pytest test_coastal_snake.py test_navigator.py test_minimap_reader.py -q --tb=short
```

Ожидание: все зелёные, нет регрессий.

- [ ] **Step 3: Коммит**

```
git add navigator.py test_coastal_snake.py
git commit -m "fix: skip ocean columns in CoastalSnakeNavigator before diving

If fwd['land_px'] == 0 and water_px > min_water_px at coast transition,
shift laterally and stay in HOMING instead of diving into open ocean."
```
