# Gemini Buffer — Хангоф #31
**Дата:** 2026-05-03 | Сессия: авто-калибровка реализована и протестирована ✅

---

## Что сделано сегодня (Хангоф #31)

| # | Задача | Статус |
|---|--------|--------|
| 1 | `auto_calibration.py` — новый модуль: `scale_ref`, `detect_point_a_in_region`, `detect_point_b_from_diff`, `auto_detect_point_a`, `auto_detect_point_b` | ✅ |
| 2 | `calibration_ui.py` — `run_calibration(start_a, start_b)` + `calibrate_one_point` публичная | ✅ |
| 3 | `main.py` — кнопка **АВТОКАЛИБРОВАТЬ** (синяя, над КАЛИБРОВАТЬ) | ✅ |
| 4 | Два независимых этапа: сначала Point A полностью, потом Point B | ✅ |
| 5 | `test_auto_calibration.py` — 13 тестов, все зелёные | ✅ |
| 6 | Пользователь протестировал, всё работает | ✅ |

---

## Архитектура авто-калибровки

### Поток выполнения
```
АВТОКАЛИБРОВАТЬ нажата
  │
  ├─ Этап 1: auto_detect_point_a(screen_w, screen_h)
  │    └─ scale_ref(REF_A) → _grab_region → detect_point_a_in_region (white rect contour)
  │    └─ fallback = scaled REF_A
  │    └─ calibrate_one_point(self, start_a, "Точка А...")  ← лупа A
  │    └─ пользователь подтверждает
  │
  └─ Этап 2: auto_detect_point_b(screen_w, screen_h)
       └─ scale_ref(REF_B) → pyautogui.moveTo → sleep(0.4s)
       └─ возвращает ПОЗИЦИЮ КУРСОРА (не diff-bounding-box!)
       └─ calibrate_one_point(self, start_b, "Точка Б...")  ← лупа B с "+" в кадре
       └─ пользователь подтверждает
       
coord_manager.calibrate(point_a, point_b) → _update_status()
```

### Ключевые решения
- **Point A**: OpenCV findContours белого прямоугольника + aspect-ratio guard (max/min > 3 → skip)
- **Point B**: курсор едет на scaled REF_B, ждём hover, **start_b = позиция курсора** (не diff-результат)
- **Coord fix**: `x1 + img_x` вместо `cx - r + img_x` (устранили до 60px ошибку у REF_A[0]=90)
- **Два этапа**: пользователь не портит позицию курсора для Point B при работе с лупой Point A

### Workflow сохранения (ВАЖНО)
```
Откалибровал → выбрать профиль (Client / Browser 1 / Browser 2) → 💾 Сохранить
```
- Без «Сохранить» — калибровка только в RAM, теряется при перезапуске
- После сохранения — профиль автозагружается при следующем старте
- `gui_config.json` хранит `last_calibration_profile`

---

## Статус профилей
| Слот | Файл | Описание |
|------|------|----------|
| Client | `profiles/profile_client.json` | Нативный клиент |
| Browser 1 | `profiles/profile_chrome.json` | Chrome |
| Browser 2 | `profiles/profile_firefox.json` | Firefox / другой браузер |

---

## Что делать дальше (строго по приоритету)

### 🔴 HIGH
1. **Free-Kassa webhook** — зарегистрировать `FK_SECRET_WORD2` в кабинете FK
2. **Coinzilla** — зарегистрироваться, получить embed-код, вставить в `Layout.jsx:152`

### 🟡 MED
3. **Google Search Console** — добавить total-hunter.com, sitemap.xml
4. **EXE packaging** — PyInstaller build.spec, TotalHunter.exe
5. **YOLO model protection** — AES-256 crypts.pt
6. **Auto-update** — version в /check_auth, updater.py

### 🟢 СЛЕДУЮЩАЯ СЕССИЯ
7. **Доработка бота по склепам (CryptHunter)** — пользователь озвучил как приоритет

---

## Технические данные деплоя

**Deploy hook:** `POST https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw`
**Project:** `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj` | **Team:** `team_CkkRPXdwtRtsL9YCk8n4Fzla`
**Token:** `C:/Users/Admin/AppData/Roaming/com.vercel.cli/Data/auth.json` (истекает ~ноябрь 2026)
**Backend:** https://api.total-hunter.com → GCP 34.68.86.57:8000
