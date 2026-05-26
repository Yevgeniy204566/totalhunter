# Gemini Buffer — Total Hunter
> Последнее обновление: 2026-05-26 (Kyiv) — Перекрёстный аудит реферальной системы

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

## ЧТО ОСТАЛОСЬ

- **Живое тестирование Системы РОЙ** (ближайший ивент «Торговые Пути»): серый→зелёный кружок на сайте, координаты у других участников
- Telegram посты для v1.5.6 и v1.5.7 готовы выше — опубликовать вручную
