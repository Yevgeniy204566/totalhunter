# Gemini Buffer — Total Hunter
> Последнее обновление: 2026-06-03 21:00 (Kyiv) — Хангоф #86: ROY синхронизация + баг тюнинга v1.6.9

---

## 🔧 ХАНГОФ #86 — ROY real-time + фикс тюнинга v1.6.7→v1.6.9
> Дата: 2026-06-03 21:00 Kyiv | Версия: **1.6.9** (задеплоено ✅)

### Что сделано

**v1.6.7 — Тюнинг кликов (частично откат)**
- Добавили auto-save на каждый клик D-Pad → оказалось неверным UX
- Откатили: сохранение только через «Сохранить профиль»
- Правильный flow: настраиваешь → выбираешь профиль → нажимаешь Сохранить

**v1.6.8 — ROY пул: кнопка «Обновить пул» удалена**
- SSE уже обновляет пул автоматически (~1.3с от находки биржи)
- Цепочка: YOLO → OCR K/X/Y → report() → сервер → SSE → все клиенты
- Кнопка убрана из GUI и из i18n (19 языков)

**v1.6.9 — КРИТИЧЕСКИЙ БАГ тюнинга устранён**
- Root cause (AP-SWING-OVERRIDE): в `_load_crypt_from_profile` было условие:
  `if coord_manager.get_ui_offset("march_accel") == (0,0) and crypt_swing2 != 0: set_ui_offset(march_accel, swing2)`
- При загрузке профиля старый `crypt_swing2` (legacy) перезаписывал D-Pad тюнинг обратно
- Исправлено: убраны обе строки `coord_manager.set_ui_offset()` из `_load_crypt_from_profile`
- `crypt_swing1/crypt_swing2` — legacy-артефакты, НЕ перезаписывают `ui_offsets`
- `ui_offsets` теперь авторитетны и сохраняются/загружаются через `coord_manager.save/load`

### Аудит ROY (по ТЗ Джемини)
- Polling → SSE (реализован с v1.6.2, работает)
- Глобальный пул без фильтра по ГОСу — правильно
- OCR K/X/Y — числа, работает на всех языках
- Задержка: ~1.3с от находки до отображения у других

### Антипаттерны добавлены в ANTI-PATTERNS.md
- `AP-SWING-OVERRIDE` — crypt_swing НЕ перезаписывает ui_offsets при загрузке
- `AP-TUNE-AUTOSAVE` — auto-save на каждый клик D-Pad неверен

### Следующие задачи
- Живой тест тюнинга: настроить → Сохранить → перезапустить → проверить
- Живой тест ROY на ивенте «Торговые Пути»

---

## 🔧 ХАНГОФ #77 — Фикс калибровки v1.5.12
> Дата: 2026-05-31 22:30 Kyiv | Версия: **1.5.12** (задеплоено ✅)

### Что сделано

**calibration_ui.py + main.py — фикс окна калибровки:**
- Root cause: `_update_dot()` стоял до `win.after()` без try/except → при withdrawn-родителе падал → цикл `_refresh` прерывался → лупа замирала → клик ничего не делал
- `win.after(REFRESH_MS, _refresh)` перенесён В НАЧАЛО функции
- `_update_dot()` и canvas-операции обёрнуты в try/except
- `win.lift()` + `win.focus_force()` перед `win.wait_window()`
- `_calibrate()` в main.py: `self.withdraw()` → `self.iconify()` (withdraw ломает дочерние Toplevel)

### Релиз
- GitHub Release v1.5.12: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.12
- ZIP: 354 MB, плоский ✅, TotalHunter.exe в корне
- Сервер `/version/latest` → `1.5.12` ✅

### Антипаттерн добавлен
- ANTI-PATTERNS.md: `⛔ self.withdraw() В _calibrate() — ЛОМАЕТ ДОЧЕРНИЕ TOPLEVEL`

### Следующие задачи
- Проверить что калибровка работает у клиента (ждём обратную связь)
- Живой тест Системы РОЙ (ивент Торговые Пути, следующий цикл)

---

## 🔧 ХАНГОФ #76 — scale_ui_coord, Ghost YOLO cap, DPI-диагностика
> Дата: 2026-05-31 | Версия: **1.5.11** (задеплоено ✅) | Повод: клиент 1768×992 оконный режим

### Корневая причина багов клиента
Клиент запускал игру в оконном режиме + нестандартное разрешение 1768×992 (кастомное под ТВ по HDMI, DPI=100%). Coord_manager масштабирует координаты КАРТЫ через 2 калибровочные точки — но статичные UI-кнопки (иконка башни, вкладки меню) должны масштабироваться пропорционально разрешению экрана. Раньше они шли через coord_manager → промах.

### Что сделано в v1.5.11

**crypt_hunter.py:**
- Новая функция `scale_ui_coord(ref_x, ref_y)` — пропорциональное масштабирование UI: `int(ref_x * screen_w / 1920), int(ref_y * screen_h / 1080)`
- 8 мест: WT_ICON, WT_CRYPTS_TAB, WT_ARENA_TAB, WT_SCROLL_AREA, WT_GOTO_BTN_X, CARTER_EVENT_BAR, ACCEL_USE_BTN переведены на scale_ui_coord
- `screen_cx, screen_cy = 960, 540` → `pyautogui.size()[0]//2, pyautogui.size()[1]//2`
- CRYPT_STUDY_BTN / CRYPT_OPEN_BTN оставлены на scale_dialog (нужен dialog_offset для браузера)

**navigator.py:**
- Ghost YOLO cap: `time.sleep(min(self._last_yolo_inference_time, max(0.01, self.move_wait * 0.8)))` — не тормозит на медленных CPU
- imgsz=1280 — восстановлено (ЗОЛОТОЕ ПРАВИЛО: 100% экрана в YOLO)

**main.py:**
- Статус-бар калибровки: `экран: tk=W×H / mss=W×H` — диагностика DPI расхождений
- Предупреждение если профиль не загрузился при старте (вместо молчащего pass)
- Авто-сохранение калибровки УБРАНО — ломало поток auto_calibrate (messagebox в неправильный момент)

**calibration_ui.py:**
- Полный откат DPI-изменений — dpi_scale не нужна (DPI=100% у клиента)

### Антипаттерны зафиксированы
- ANTI-PATTERNS.md: `🔴🔴 ЗОЛОТОЕ ПРАВИЛО YOLO` — imgsz=1280, monitors[1], без кропа — НЕРУШИМО
- MEMORY: feedback_yolo_fullscreen.md

### Инструкция клиенту
"Скачайте v1.5.11, разверните игру на весь экран (обязательно!), нажмите КАЛИБРОВАТЬ → выставьте точки → СОХРАНИТЬ."

### Что НЕ изменилось
- imgsz=1280 ✅ (были попытки снизить до 640 — откатили, правило зафиксировано)
- Калибровка: КАЛИБРОВАТЬ + СОХРАНИТЬ — два отдельных шага (как и было)
- GCP сервер — без изменений (server/ не трогали)

### Следующие задачи
- Ждём обратную связь от клиента 1768×992 — помогло ли scale_ui_coord
- Живой тест Системы РОЙ (ивент Торговые Пути)

---

---

## 🔧 ХАНГОФ #75 — Фикс координат Склепов + защита калибровки
> Дата: 2026-05-30 | Версия: **1.5.10** (задеплоено ✅) | Повод: клиент 1768×992

### Что сделано

**Диагностика (3 независимых агента + перекрёстная проверка):**
- Подтверждено: КАЛИБРОВАТЬ и АВТОКАЛИБРОВАТЬ функционально идентичны — оба вызывают `coord_manager.calibrate(point_a, point_b)`
- Найдены 2 реальных бага через аудит кода + Gemini cross-review

**Фикс 1 — crypt_hunter.py (3 координаты без масштабирования):**
- `WT_SCROLL_AREA` в `_pre_skip()` и `_scroll_and_find()` → `scale_coord(*WT_SCROLL_AREA)`
- `MENU_SCAN_REGION` в `_scroll_and_find()` → `scale_region(*MENU_SCAN_REGION)`
- `OIL_DIALOG_REGION` в `_check_oil_dialog()` → `scale_region(*OIL_DIALOG_REGION)`
- Все через `if _VISUAL_NAV_AVAILABLE else` — безопасный fallback

**Фикс 2 — build.spec:**
- Убрано `('profiles', 'profiles')` из datas — ZIP больше не перезаписывает калибровку клиента при обновлении

**Фикс 3 — main.py:**
- Автогенерация дефолтных профилей при старте: `if not os.path.exists(path): coord_manager.save(path)`
- Первый запуск → профили создаются. Обновление → существующие не трогаются.

**Сборка и релиз v1.5.10:**
- Nuitka + PyInstaller, 338 MB, TotalHunter.exe в корне ZIP ✅
- `profiles/` в ZIP отсутствует ✅
- version/latest API → 1.5.10 ✅
- ZIP на GitHub Release загружен, auto-update работает ✅

### Что осталось
- **Клиенту 1768×992:** обновиться → откалибровать один раз → сохранить профиль
- **Живой тест ROY** — ивент Trade Routes 2026-06-01 17:00 UTC
- Остальные задачи из #74 без изменений

---

## 🔧 ХАНГОФ #74 — Откат поломок Gemini + ROY таймер возраста
> Дата: 2026-05-29 | Версия: 1.5.9 (без нового релиза) | Статус: задеплоено ✅

### Что сделано

**Проблема:** Пользователь пытался решить вопрос индексации Google (14 страниц не проиндексированы) с помощью Gemini. Gemini сломал 4 вещи одним коммитом `6278d0a`.

**Фиксы (коммиты `3f30e13` и `f1cb30a`):**
1. `web/.vercelignore` — убран `src` (Gemini добавил → все Vercel-билды падали)
2. `vite.config.js` — убран `base: './'` (сломал ассеты на `/ru/`, `/features/`)
3. `web/index.html` — возвращён `/src/main.jsx` со слэшем
4. `web/public/sitemap.xml` — удалены 4 несуществующих URL (`/legal/privacy`, `/legal/terms` и RU-варианты → soft 404 у Google)

**ROY таймер (main.py `_roy_update_list` + `_tick_pool_countdown`):**
- Было: обратный отсчёт 20:00→0:00 (сколько ОСТАЛОСЬ до истечения)
- Стало: возраст 0:00→20:00 (сколько ПРОШЛО с момента нахождения биржи)
- Цвета: зелёный <10мин (свежая), жёлтый 10-15мин, красный >15мин (старая)

**Объяснение по индексации Google:**
- 8 "обнаружена, не проиндексирована" — очередь Google, норма для нового сайта
- 3 редиректа — вероятно www.→non-www (Vercel автоматически)
- 1 canonical вариант — EN/RU hreflang, норма
- 1 404 — скорее всего `/legal/privacy` или `/legal/terms` (Gemini добавил в sitemap, уже убрано)
- Прогноз: через 1-2 недели при следующем обходе Google картина улучшится

### Коммиты
| Хэш | Что |
|-----|-----|
| `3f30e13` | fix: remove src from .vercelignore |
| `f1cb30a` | fix: revert Gemini's broken changes (vite base, index.html, sitemap) |

### Антипаттерн добавлен в ANTI-PATTERNS.md
- ⛔ Доверять Gemini деплой и изменения конфига Vercel — запрещено

### Вопросы Gemini
- Нет открытых вопросов. v1.5.9 стабилен, релиз не нужен.

---

---

## 🚀 ХАНГОФ #71 — Ghost YOLO + v1.5.8
> Дата: 2026-05-27 | Версия: 1.5.8 | Статус: ВЫПУЩЕН ✅

### Что сделано

**Баг:** Бот после рестарта (обнаружение биржи → 10с пауза → новый старт) двигался в 2x быстрее.

**Корневая причина:** YOLO inference занимает ~1.0с на CPU. `move_wait=0.5с`. Нормальный цикл: sleep(0.01) + YOLO(1.0s) + nav(0.05s) = 1.06s. С блокированной YOLO: sleep(0.01) + sleep(0.45s) + nav(0.05s) = 0.51s = 2x быстрее. Диагностика через лог: ratio 1.059/0.531 = 2.000x.

**Решение — Ghost YOLO (Призрак YOLO):**
- `_last_yolo_inference_time = 1.0` — хранить время последнего реального YOLO
- Когда YOLO заблокирована: `time.sleep(_last_yolo_inference_time)` — симулировать нагрузку
- `_initial_yolo_block_sec = 5.0` при programmatic restart (достаточно чтобы уйти от биржи)

**Дополнительно:**
- `if not self.is_running: break` перед `joystick.step()` — лишний шаг после стопа
- Пауза Step 7 (ожидание диалога): 0.5с → 1.0с (медленные ПК)
- 28 тестов зелёных

**Антипаттерн добавлен в ANTI-PATTERNS.md:** Spatial filter (позиционный cooldown) = День Сурка.

### Коммиты
| Хэш | Что |
|-----|-----|
| de6823f | is_running guard + YOLO block 30s→15s |
| 61f80c2 | Ghost YOLO (_last_yolo_inference_time) |

### Релиз v1.5.8
- GitHub: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.8
- ZIP: 338 MB, плоский ✅
- Server `/version/latest` → `1.5.8` ✅
- Проверено живым тестом пользователем ✅

### Вопросы Gemini
- Нет открытых вопросов. Текущая задача — мониторинг пользователей v1.5.8 на стабильность.

---

---

## 🔍 ОТЧЁТ: ПЕРЕКРЁСТНЫЙ АУДИТ РЕФЕРАЛЬНОЙ СИСТЕМЫ
> Дата: 2026-05-26 | Метод: 2 независимых агента (Agent A — бизнес-логика, Agent B — security/abuse)

### Область проверки
- Начисления при регистрации (ref_welcome): приглашённый +50, пригласитель +100
- Каскад при покупке (ref_earning): L1=10%, L2=5%, L3=1% от credits_total
- Привязка/отвязка устройства: cooldown 7 дней, HWID-история
- Идемпотентность: защита от двойных начислений
- Abuse-векторы: HWID-абьюз, цикличные цепочки, собственный ref_code
- Покрытие тестами

---

### СТАТУС: NEEDS FIXES (2 бага + 9 HIGH тестов отсутствуют)

---

### BUG-1 🔴 ЗНАЧИМЫЙ — `/link/verify`: приглашённый не получает +50 если пригласитель забанен

**Файл:** `server/web_routes.py`, строки 433–444

**Что происходит:**
```python
# ТЕКУЩИЙ КОД (неправильно):
if referrer and not referrer.is_banned:
    web_user.ref_credits += 50      # ← оба начисления внутри одного if
    db.add(Transaction(..., amount=50, meta={"role": "invited"}))
    referrer.ref_credits += 100
    db.add(Transaction(..., amount=100, meta={"role": "inviter"}))
web_user.ref_bonus_claimed = True   # ← выставляется в любом случае
```
Если пригласитель забанен → приглашённый НЕ получает свои 50 ref_credits. При этом `ref_bonus_claimed=True` выставляется безвозвратно — шанс утерян навсегда.

**Что должно быть:**
```python
# ПРАВИЛЬНО:
web_user.ref_credits += 50         # +50 invited — безусловно
db.add(Transaction(..., amount=50, meta={"role": "invited"}))
if not referrer.is_banned:
    referrer.ref_credits += 100    # +100 inviter — только если не забанен
    db.add(Transaction(..., amount=100, meta={"role": "inviter"}))
```

**Расхождение:** В `/referral/activate` (строки 590–597) логика УЖЕ правильная — +50 приглашённому безусловно, +100 пригласителю только если не забанен. Нужно привести `/link/verify` к тому же поведению.

---

### BUG-2 🟡 НИЗКИЙ — Возможны циклические реферальные цепочки в БД

**Файл:** `server/web_routes.py`, `/referral/activate`

**Что происходит:** Нет проверки на цикл при активации кода. Если A пригласил B, B пригласил C, C активирует код A — получается цепочка C→A→B→C. В каскаде покупки это ограничено 3 итерациями (не infinite loop), но семантически неправильно: A зарабатывает от своего же реферала C.

**Исправление:** При `/referral/activate` пройтись вверх по цепочке `inviter.invited_by_id` (до 3 шагов) и убедиться, что `web_user.id` не встречается.

**Реальный риск:** НИЗКИЙ — каскад ограничен 3 уровнями, infinite loop невозможен. Но злоупотребление теоретически возможно в кольцах из 3 пользователей.

---

### ВСЁ ОСТАЛЬНОЕ: PASS ✅

| Проверка | Статус |
|---|---|
| Приглашённый +50 ref_credits при регистрации (незабаненный пригласитель) | ✅ |
| Пригласитель +100 ref_credits при регистрации | ✅ |
| ref_bonus_claimed — идемпотентность (двойного нет) | ✅ |
| Сценарий: код → HWID (одна выплата) | ✅ |
| Сценарий: HWID → код (одна выплата) | ✅ |
| Сценарий: код (без HWID) → потом HWID (одна выплата) | ✅ |
| L1 = 10%, L2 = 5%, L3 = 1% от credits_total | ✅ |
| Забаненный на L2 — пропускается, L3 всё равно получает 1% | ✅ |
| int() округление вниз, amount=0 → транзакция не создаётся | ✅ |
| Короткая цепочка (<3 уровней) — лишние итерации не выполняются | ✅ |
| HWID reset 400 если hwid не привязан | ✅ |
| HWID reset cooldown 7 дней (429 + next_reset_available) | ✅ |
| После reset: hwid=None, hwid_reset_at обновлён | ✅ |
| Повторный trial/ref_bonus после смены устройства невозможен (trial_used persists) | ✅ |
| 10 аккаунтов с одним HWID — только первый получает trial (HwidHistory глобальная) | ✅ |
| Собственный ref_code заблокирован (inviter.id == web_user.id) | ✅ |
| Двойная активация ref_code заблокирована (invited_by_id already set) | ✅ |
| meta транзакции: level (1/2/3) и related_user_id — корректны | ✅ |

---

### ОТСУТСТВУЮЩИЕ ТЕСТЫ (9 HIGH, 9 MEDIUM)

**HIGH приоритет:**
1. `test_trial_bonus_granted_on_first_hwid_link` — credits+=100, trial_used=True после link/verify
2. `test_ref_welcome_via_link_verify` — полный флоу: регистрация с ref_code → link HWID → +50 invited, +100 inviter
3. `test_no_ref_welcome_without_ref_code` — регистрация без кода → link HWID → нет ref_credits
4. `test_ref_bonus_not_doubled_hwid_first_then_activate` — HWID привязан → активация кода → бонус НЕ выплачивается (ref_bonus_claimed=True)
5. `test_ref_bonus_not_doubled_activate_first_then_link` — код активирован (без HWID) → link HWID → ровно одна выплата
6. `test_duplicate_hwid_blocked_transaction` — второй аккаунт с тем же HWID → транзакция hwid_duplicate_blocked
7. `test_hwid_reset_cooldown_enforced` — link, reset, немедленно reset → 429
8. `test_trial_not_repeated_after_hwid_reset_and_relink` — link, reset, relink same HWID → нет повторного trial
9. `test_trial_not_repeated_on_new_hwid_after_reset` — link HWID-A, reset, link HWID-B → нет trial (trial_used persists)
10. `test_referral_activate_with_hwid_pays_immediately` — у пользователя есть HWID, ref_bonus_claimed=False → /activate платит сразу обеим сторонам

**MEDIUM приоритет:**
- `test_hwid_reset_first_time_no_cooldown` — первый сброс без ожидания 7 дней (OK)
- `test_hwid_reset_allowed_after_7_days` — hwid_reset_at = 8 дней назад → сброс разрешён
- `test_referral_activate_own_code_blocked` — собственный ref_code → success=False
- `test_referral_activate_twice_blocked` — активация дважды → success=False
- `test_cascade_l1_l2_l3_amounts` — покупка 5000 cr → L1=+500, L2=+250, L3=+50
- `test_cascade_banned_l2_skipped_chain_continues` — L2 забанен → L2=0, L3 получает
- `test_cascade_no_referrer_stops_walk` — нет invited_by_id → нет ref_earning транзакций
- `test_referral_activate_banned_inviter_sets_chain` — активация кода забаненного → invited_by_id сохраняется, но при link/verify +100 не платится

---

### РЕКОМЕНДАЦИИ (по приоритету)

1. **ИСПРАВИТЬ БУГ-1** (web_routes.py:433–444) — вынести `web_user.ref_credits += 50` за пределы `if not referrer.is_banned`. Простой однострочный фикс.
2. **НАПИСАТЬ 9 HIGH тестов** — самые критичные финансовые пути сейчас без тестового покрытия.
3. **Добавить cycle-check** в `/referral/activate` — walk up ≤3 шагов, убедиться что web_user.id не встречается.

---

> Последнее обновление: 2026-05-25 22:00 (Kyiv) — Хангоф #69

---

## 📢 TELEGRAM POST — v1.5.7

```
⚔️ Total Hunter — обновление v1.5.7

🔧 Мелкий, но важный фикс:

Смена языка теперь обновляет вкладку РОЙ сразу. Раньше при переключении языка иностранные пользователи видели старые русские надписи — теперь всё переключается мгновенно.

🔄 Бот обновится автоматически при следующем запуске.
```

---

## 📢 TELEGRAM POST — v1.5.6

```
⚔️ Total Hunter — обновление v1.5.6

🌍 Система РОЙ теперь говорит на твоём языке!

Вкладка РОЙ полностью переведена на все 19 языков:
🇷🇺 RU · 🇺🇦 UA · 🇬🇧 EN · 🇩🇪 DE · 🇪🇸 ES · 🇫🇷 FR
🇮🇹 IT · 🇳🇱 NL · 🇳🇴 NO · 🇵🇱 PL · 🇧🇷 PT · 🇸🇪 SV
🇹🇷 TR · 🇸🇦 AR · 🇯🇵 JA · 🇨🇳 ZH · 🇹🇼 TW · 🇰🇷 KO · 🇮🇩 ID

Теперь все надписи — название, баланс, статус, кнопки, подсказки — отображаются на языке интерфейса. Больше никакого русского текста для иностранных пользователей.

🔄 Бот обновится автоматически при следующем запуске.
```

---

## ЧТО СДЕЛАНО (Хангоф #68 — v1.5.6 + v1.5.7)

### v1.5.6
- Добавлены 12 ROY-ключей для JA, ZH, ZH_TW, KO, UK, ID — все 19 языков покрыты полностью
- setup_roy_tab, _roy_refresh_pool, _roy_refresh_balance, _roy_update_list — переведены через LANGS[lang]
- GitHub релиз v1.5.6, сервер обновлён ✅

### v1.5.7
- Фикс change_lang: добавлен блок обновления 8 ROY-меток (_roy_title_lb, _roy_subtitle_lb, _roy_balance_title_lb, _roy_join_lb, _roy_kingdom_lb, _roy_coords_lb, _roy_refresh_btn, _roy_no_data_lb)
- Единицы времени мин/сек переключаются при смене языка (повторный вызов _roy_refresh_balance)
- GitHub релиз v1.5.7, сервер обновлён ✅

### GCP (roy_kingdom_members)
- Таблица уже существовала (создана ранее) ✅
- `GRANT ALL ON roy_kingdom_members TO hunter` — выполнен ✅ (роль hunter, не totalhunter)
- `INSERT INTO alembic_version ('m2n3o4p5q6r7')` — INSERT 0 0 (уже был) ✅
- `DELETE FROM roy_kingdom_members WHERE hwid = 'test1234test1234'` — DELETE 0 (записи нет) ✅

---

---

## ЧТО СДЕЛАНО (Хангоф #69 — SEO URL-локализация + Vercel Analytics)

### Vercel Analytics ✅
- `@vercel/analytics@^2.0.1` установлен, `<Analytics />` в main.jsx
- `track('Register_Started', {method})` — в LoginPage (popup + redirect)
- `track('Referral_Link_Copied')` — в ReferralsPage
- **Баг:** аналитика была включена через Dashboard ПОСЛЕ деплоя → script.js = 404 → 0 статистики
- **Фикс:** свежий редеплой (hook + alias `dpl_8VyDAMrYpEa3Ae3Z8McqLHvrEvZi`). Теперь `/_vercel/insights/script.js` = 200 ✅

### URL-based i18n ✅
- EN = дефолт (без префикса): `/`, `/features`, `/guide`, `/download`, `/contacts`, `/legal`, `/login`
- RU = с префиксом `/ru`: `/ru`, `/ru/features` и т.д.
- Dashboard — язык из `localStorage`
- `BrowserRouter` перенесён в `main.jsx` (LangProvider использует useLocation/useNavigate)
- `lang.js` полностью переписан: URL-aware для публичных страниц
- `App.jsx`: добавлены 7 новых RU-маршрутов (те же компоненты, язык из URL)

### prerender.mjs — 12 маршрутов ✅
- 6 EN + 6 RU, каждый с `html[lang]`, title, desc, og, canonical, hreflang, og:locale
- `/` и `/ru` — FAQ JSON-LD в EN и RU соответственно
- Генерирует `dist/ru/*` папки

### hreflang ✅
- Статика: prerender.mjs инжектирует перед `</head>` (x-default + en + ru)
- Динамика: `syncHreflang()` в `useMeta.js` — удаляет/добавляет при SPA-навигации
- `sitemap.xml` — 12 URL с `xhtml:link` парами

### index.html ✅
- `<html lang="en">`, все meta/og/twitter переведены в EN

### useMeta на dashboard-страницах ✅
- HuntsPage, BalancePage, FeedbackPage, DashboardPage, ReferralTreePage — все получили useMeta()

---

## ЧТО СДЕЛАНО (Хангоф #70 — 2026-05-26)

### Реферальная система — TDD-аудит + патчи ✅
- Перекрёстный аудит 2 агентами: бизнес-логика + security/abuse
- **BUG-1** исправлен: `web_user.ref_credits += 50` вынесен за пределы `if not referrer.is_banned` в `/link/verify`
- **BUG-2** исправлен: `db.begin()` → `db.begin_nested()` в `/referral/activate` (было 500 при каждой активации)
- **BUG-3** исправлен: cycle detection в `/referral/activate` — walk ≤3 хопов по `invited_by_id`
- **BUG-4** исправлен: naive/aware datetime в `/hwid/reset` — нормализация tzinfo для SQLite
- `notify_balance_changed(hwid)` добавлен в `/referral/activate` после commit
- `tests/conftest.py`: добавлен fixture `db_session` для прямого доступа к БД в тестах
- `tests/test_referral_system.py`: 16 TDD-тестов (все HIGH + MEDIUM из аудита)
- `tests/test_payments.py`: исправлены 4 webhook-теста — `content=json.dumps(sort_keys=True).encode()` вместо `json=body`
- `tests/test_version_bump.py`: обновлена версия `1.4.2 → 1.5.7`
- **Итог: 57/57 тестов зелёных**
- Задеплоено на GCP ✅

### BitMedia ✅
- Мета-тег `bitmedia-site-verification` добавлен в `web/index.html`
- Vercel задеплоен (hook + alias), тег на продакшене
- Заявка подана в BitMedia, ждём модерации

---

## ЧТО ОСТАЛОСЬ

- **Живое тестирование Системы РОЙ** (ивент «Торговые Пути», цикл 5 дней от 20.05): серый→зелёный кружок, координаты у других участников
- **BitMedia модерация** — ждём одобрения (заявка подана 2026-05-26)
- **Telegram посты** v1.5.6 и v1.5.7 — готовы в буфере выше, опубликовать вручную
