# Returning Water Recovery + Pitch Slider — Design Spec
**Date:** 2026-04-27
**Status:** Approved

---

## Part 1: Симметричный RETURNING (water recovery)

### Problem

В non-blind фазе RETURNING бот считает шаги назад вслепую (векторы заморожены).
Если нырок прошёл через широкий водяной канал, `return_steps` заканчиваются до
достижения берега → `cap_hit` → shift + HOMING. В HOMING бот в воде, `inland_vec`
смотрит вглубь → бот идёт **дальше от берега** и теряется.

### Solution

В non-blind фазе RETURNING: считать подряд идущие шаги в воде (`_return_water_streak`).
При ≥2 шагах в воде — вызвать `_read_minimap()` чтобы обновить `_inland_vec` по
ближайшей суше. Следующий `_move_perpendicular(toward_water=True)` развернёт бота
к обновлённому берегу.

### New state variable

В `__init__()` и `reset()`:
```python
self._return_water_streak: int = 0
```

Сброс при переходе DIVING→RETURNING (рядом с `self._return_steps = ...`):
```python
self._return_water_streak = 0
```

### Change in `step()` — RETURNING non-blind phase

Вставить **перед** `at_coast = self._is_at_coast_now()`:

```python
            # Symmetric water recovery: if stuck in water 2+ steps → re-read minimap
            if is_water:
                self._return_water_streak += 1
            else:
                self._return_water_streak = 0
            if self._return_water_streak >= 2:
                self._read_minimap()          # updates _inland_vec toward visible land
                self._return_water_streak = 0
```

### Behaviour

| Ситуация | Результат |
|----------|-----------|
| Нормальный возврат по суше | `is_water=False` → streak=0 → minimap не читается, поведение прежнее |
| 1 шаг воды (река) | streak=1 → minimap не читается, проходим |
| 2+ шага воды подряд | streak≥2 → `_read_minimap()` → `_inland_vec` к суше → бот корректирует курс |
| Blind phase | Не затрагивается (код до blind phase) |

### Не изменяется

- Blind фаза
- `cap_hit`, `at_coast`, shift логика
- `_move_perpendicular(toward_water=True)` — остаётся, теперь с обновлённым вектором

---

## Part 2: Default 15° и GUI слайдер

### navigator.py — изменить default

В `CoastalSnakeNavigator.__init__()`:
```python
max_pitch_delta: float = 15.0,   # было 10.0
```

В `PacmanEngine.__init__()`:
```python
max_pitch_delta: float = 15.0,   # было 10.0
```

### main.py — добавить слайдер "Угол нырка"

**Место:** в `nav_main_frame` (карточка «Навигация»), после слайдера «Глубина нырка»
(после строки `self.nav_inland_slider.pack(...)`).

**Паттерн** (идентичен существующим слайдерам):

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

**`_update_nav_labels()`** — добавить строку:
```python
self.nav_pitch_val.configure(text=f"{int(self.nav_pitch_slider.get())}°")
```

**`_save_config()`** (~строка 1167) — добавить:
```python
cfg["max_pitch_delta"] = int(self.nav_pitch_slider.get())
```

**`_load_config()`** (~строка 1199) — добавить:
```python
self.nav_pitch_slider.set(cfg.get("max_pitch_delta", 15))
```

**`_start_hunt()`** (~строка 1238) — добавить в kwargs движка:
```python
max_pitch_delta=int(self.nav_pitch_slider.get()),
```

---

## Files Changed

| Файл | Что меняется |
|------|-------------|
| `navigator.py` | `_return_water_streak` state var + recovery logic в RETURNING, defaults 15° |
| `main.py` | слайдер «Угол нырка», `_update_nav_labels`, `_save_config`, `_load_config`, `_start_hunt` |

---

## Tests Required

- `test_returning_water_recovery_triggers_minimap` — 2 шага воды в RETURNING → `_read_minimap` вызван
- `test_returning_one_water_step_no_minimap` — 1 шаг воды → `_read_minimap` НЕ вызван
- `test_returning_land_resets_streak` — после воды суша → streak сброшен
- `test_returning_blind_phase_unaffected` — blind phase не затронута
- Регрессия: все 53 теста зелёные
