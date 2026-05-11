# Хангоф #45 — 2026-05-11 23:xx

## Версия: v1.2.0 (выпущена ✅)

---

## Что сделано в сессии

### 🔥 Главный баг — устранён
- **Причина:** `crypt_hunter.cp313-win_amd64.pyd` — Nuitka бинарник со старым кодом лежал в корне. Python всегда берёт `.pyd` вместо `.py`. Все правки в исходнике игнорировались.
- **Фикс:** Удалён `.pyd`. Из `crypt_hunter.py` полностью вырезан `_EXP_DIALOG_GATE`, `template_finder`, `_images_differ`.
- **Постоянное решение:** `build_release.py` теперь шаг 7/7 — автоочистка `.pyd` из корня после каждой сборки (try/finally + предупреждение при старте).

### Новые фичи v1.2.0

**Swing 1 / Swing 2** (вкладка Склепы):
- Swing 1 → вертикальная подстройка клика «Исследовать» (кнопки ±5px)
- Swing 2 → вертикальная подстройка клика «Использовать» (ускорение)
- Независимые, сохраняются в профиль

**Слайдер скорости кликов:**
- Диапазон: −2.0 .. +2.0 сек, шаг 0.1
- Влево = медленнее, вправо = быстрее
- Применяется к `_random_pause()` в `crypt_hunter.py`
- Не влияет на марш и YOLO

**Профили = полная конфигурация аккаунта:**
- Каждый из 3 профилей хранит: калибровку + настройки Склепов + настройки Бирж + Swing1/2 + скорость кликов
- Переключение профиля → автозагрузка всего
- Кнопка «Сохранить» в любой вкладке → сохраняет всё в активный профиль

**Убрано:**
- Oil check UI (три цветных точки 🟢🔵🟣)
- `on_crypt_oil` callback
- Общая «Микроподстройка кликов» → заменена на Swing1/2

**Прочее:**
- `import threading` добавлен в `main.py` (был NameError)
- Гайд на сайте обновлён: профили, Swing1/2, скорость кликов
- Nuitka обязательна — AP-59 добавлен в ANTI-PATTERNS

---

## Архитектура профилей (финальная)

```json
profile_client.json / profile_chrome.json / profile_firefox.json:
{
  "point_a", "point_b", "scale_x", "scale_y", "dialog_offset_y",
  "crypt_selected", "crypt_conf", "crypt_accelerations",
  "crypt_break_sec", "crypt_scroll_speed", "crypt_max_march_min",
  "crypt_swing1", "crypt_swing2", "crypt_speed_delta",
  "step", "conf", "scan_interval", "move_wait",
  "max_inland_steps", "ocean_land_ratio", "min_water_px",
  "diagonal_blind_coeff", "nav_footprint_ttl", "return_delta_px", "smooth_alpha"
}
```

---

## Деплой v1.2.0
- ✅ GitHub Release: Setup.exe (315MB) + TotalHunter.zip (392MB)
- ✅ total-hunter.com обновлён (Vercel)
- ✅ API сервер: version/latest = 1.2.0

---

## AP-58/59 (новые в ANTI-PATTERNS)
- AP-59: Nuitka обязательна для каждого релиза
- AP-58 обновлён: `.pyd` в корне = удалить немедленно. Постоянный фикс в `build_release.py` шаг 7/7.
