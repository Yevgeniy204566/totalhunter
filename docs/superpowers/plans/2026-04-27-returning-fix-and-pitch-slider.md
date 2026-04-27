# Returning Water Recovery + Pitch Slider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Бот перестаёт теряться в воде при возврате — читает миникарту при 2+ водяных шагах в RETURNING; слайдер «Угол нырка» (5–30°, default 15°) добавлен в GUI.

**Architecture:** Минимальные изменения в трёх местах: `navigator.py` (water streak + recovery), `navigator.py` (defaults 15°), `main.py` (новый слайдер). Задачи независимы, каждая даёт рабочий коммит.

**Tech Stack:** Python 3.13, CustomTkinter, pytest, unittest.mock

---

## File Map

| Файл | Что меняется |
|------|-------------|
| `navigator.py` | `_return_water_streak` state var, recovery code в RETURNING, defaults 10→15° |
| `test_coastal_snake.py` | 4 новых теста `TestReturningWaterRecovery` |
| `main.py` | слайдер, label, save/load/start wiring |

---

### Task 1: RETURNING water recovery (TDD)

**Files:**
- Modify: `C:\BattleBot\navigator.py` (RETURNING блок + `__init__` + `reset`)
- Modify: `C:\BattleBot\test_coastal_snake.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в конец `test_coastal_snake.py` (после `TestAngularDamper`):

```python
class TestReturningWaterRecovery:
    def _nav(self):
        nav = make_navigator()
        nav._state              = 'RETURNING'
        nav._return_blind_steps = 0
        nav._return_steps       = 10
        nav._inland_vec         = (1.0, 0.0)
        return nav

    def test_two_water_steps_trigger_minimap(self):
        """2 consecutive water steps in RETURNING → _read_minimap called once."""
        nav = self._nav()
        with patch.object(nav, '_is_at_coast_now', return_value=False):
            with patch.object(nav, '_read_minimap', return_value=_info()) as mock_mm:
                nav.step(is_water=True)   # streak = 1 → no read
                nav.step(is_water=True)   # streak = 2 → READ + reset
        mock_mm.assert_called_once()

    def test_one_water_step_no_minimap(self):
        """1 water step alone → _read_minimap NOT called."""
        nav = self._nav()
        with patch.object(nav, '_is_at_coast_now', return_value=False):
            with patch.object(nav, '_read_minimap', return_value=_info()) as mock_mm:
                nav.step(is_water=True)   # streak = 1
        mock_mm.assert_not_called()

    def test_land_resets_streak(self):
        """Water → land → water: streak resets, no minimap on 3rd step."""
        nav = self._nav()
        with patch.object(nav, '_is_at_coast_now', return_value=False):
            with patch.object(nav, '_read_minimap', return_value=_info()) as mock_mm:
                nav.step(is_water=True)    # streak = 1
                nav.step(is_water=False)   # streak = 0 (reset)
                nav.step(is_water=True)    # streak = 1, not 2
        mock_mm.assert_not_called()

    def test_blind_phase_unaffected(self):
        """Blind phase: is_water=True does NOT trigger minimap read."""
        nav = self._nav()
        nav._return_blind_steps = 3   # still in blind phase
        with patch.object(nav, '_read_minimap', return_value=_info()) as mock_mm:
            nav.step(is_water=True)
            nav.step(is_water=True)
        mock_mm.assert_not_called()
```

- [ ] **Step 2: Запустить — убедиться что падают**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestReturningWaterRecovery -v
```

Ожидание: **4 FAILED** — `AttributeError: _return_water_streak` или тест не видит изменений.

- [ ] **Step 3: Добавить `_return_water_streak` в `__init__`**

В `CoastalSnakeNavigator.__init__()`, после `self._prev_inland_vec = None` (~строка 479):

```python
        self._return_water_streak: int = 0
```

- [ ] **Step 4: Добавить сброс в `reset()`**

В `reset()`, после `self._prev_inland_vec = None` (~строка 516):

```python
        self._return_water_streak = 0
```

- [ ] **Step 5: Добавить сброс при входе в RETURNING**

В DIVING-блоке `step()`, рядом с `self._return_steps = self.max_inland_steps + 15` (~строка 788):

```python
                self._return_water_streak = 0
```

(вставить следующей строкой после `self._return_steps = ...`)

- [ ] **Step 6: Добавить recovery logic в RETURNING non-blind phase**

В `step()`, RETURNING блок, **перед строкой** `at_coast = self._is_at_coast_now()` (~строка 821):

```python
            # Symmetric water recovery: re-read minimap if stuck in water 2+ steps
            if is_water:
                self._return_water_streak += 1
            else:
                self._return_water_streak = 0
            if self._return_water_streak >= 2:
                self._read_minimap()          # updates _inland_vec toward visible land
                self._return_water_streak = 0
```

- [ ] **Step 7: Запустить новые тесты**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py::TestReturningWaterRecovery -v
```

Ожидание: **4 PASSED**

- [ ] **Step 8: Полная регрессия**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py -v
```

Ожидание: **57 passed** (53 старых + 4 новых), 0 failed.

> Особо проверить: `test_returning_does_not_update_inland_vec` — он использует `step()` без `is_water=True`, поэтому streak=0 и `_read_minimap` не вызывается → тест должен пройти ✅

- [ ] **Step 9: Коммит**

```
cd C:\BattleBot && git add navigator.py test_coastal_snake.py && git commit -m "fix: symmetric water recovery in RETURNING phase"
```

---

### Task 2: Defaults 10° → 15°

**Files:**
- Modify: `C:\BattleBot\navigator.py` (два места: CoastalSnakeNavigator + PacmanEngine)

- [ ] **Step 1: Изменить default в CoastalSnakeNavigator**

Найти в `CoastalSnakeNavigator.__init__()`:
```python
        max_pitch_delta: float  = 10.0,  # degrees; 0 = disabled
```
Заменить на:
```python
        max_pitch_delta: float  = 15.0,  # degrees; 0 = disabled
```

- [ ] **Step 2: Изменить default в PacmanEngine**

Найти в `PacmanEngine.__init__()`:
```python
        max_pitch_delta: float  = 10.0,
```
Заменить на:
```python
        max_pitch_delta: float  = 15.0,
```

- [ ] **Step 3: Проверить регрессию**

```
cd C:\BattleBot && python -m pytest test_coastal_snake.py -q --tb=no
```

Ожидание: **57 passed**

- [ ] **Step 4: Коммит**

```
cd C:\BattleBot && git add navigator.py && git commit -m "fix: raise max_pitch_delta default to 15 degrees"
```

---

### Task 3: GUI слайдер «Угол нырка»

**Files:**
- Modify: `C:\BattleBot\main.py` (5 мест)

- [ ] **Step 1: Добавить слайдер в карточку Навигация**

В `main.py` найти строку:
```python
        self.nav_inland_slider.pack(padx=12, pady=(2, 4), fill="x")
```

После неё добавить:

```python
        # Угол нырка (угловой демпфер)
        self.nav_pitch_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_pitch_frame.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(self.nav_pitch_frame, text="Угол нырка (°):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
        self.nav_pitch_val = ctk.CTkLabel(self.nav_pitch_frame, text="15°",
                                           font=ctk.CTkFont(size=14, weight="bold"),
                                           text_color=MD3["value_text"])
        self.nav_pitch_val.pack(side="right")
        self.nav_pitch_slider = ctk.CTkSlider(
            nav_main_frame, from_=5, to=30, number_of_steps=25,
            command=self._update_nav_labels,
            button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_pitch_slider.set(15)
        self.nav_pitch_slider.pack(padx=12, pady=(2, 4), fill="x")
```

- [ ] **Step 2: Добавить в `_update_nav_labels()`**

Найти метод `_update_nav_labels` и в конец его тела добавить:

```python
        self.nav_pitch_val.configure(text=f"{int(self.nav_pitch_slider.get())}°")
```

- [ ] **Step 3: Добавить в `_save_config()`**

Найти в `_save_config()` блок с `cfg["max_inland_steps"]` (~строка 1167), добавить рядом:

```python
            cfg["max_pitch_delta"]       = int(self.nav_pitch_slider.get())
```

- [ ] **Step 4: Добавить в `_load_config()`**

Найти в `_load_config()` строку `self.nav_inland_slider.set(...)` (~строка 1199), добавить после:

```python
            self.nav_pitch_slider.set(cfg.get("max_pitch_delta", 15))
```

- [ ] **Step 5: Добавить в `_start_hunt()`**

Найти в `_start_hunt()` строку `max_inland_steps=int(self.nav_inland_slider.get()),` (~строка 1238), добавить после:

```python
                    max_pitch_delta=int(self.nav_pitch_slider.get()),
```

- [ ] **Step 6: Проверить импорт**

```
cd C:\BattleBot && python -c "import main; print('OK')"
```

Ожидание: `OK` (без ошибок)

- [ ] **Step 7: Коммит**

```
cd C:\BattleBot && git add main.py && git commit -m "feat: add pitch angle slider (5-30 deg) to Navigation card"
```
