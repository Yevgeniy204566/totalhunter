# Gemini Buffer — Хангоф #30
**Дата:** 2026-05-03 | Сессия: веб-платформа, SEO, иконки, деплой

---

## Три источника монетизации Total Hunter

| # | Источник | Статус | Приоритет |
|---|----------|--------|-----------|
| 1 | **Free-Kassa** — прямые продажи алмазов | ✅ Работает | FK_SECRET_WORD2 не настроен |
| 2 | **Coinzilla** — рекламный баннер в дашборде | ⏳ Заглушка `AD` в Layout.jsx:152 | 🔴 HIGH |
| 3 | **Рефералы** — L1(10%) L2(5%) L3(1%) от покупок | ✅ Работает | — |

---

## Coinzilla — что нужно сделать

**Слот уже есть:** `web/src/components/Layout.jsx` строка 152 — sticky bottom bar высотой 72px, показывается во всём дашборде.

**Шаги:**
1. Зарегистрироваться на **coinzilla.com** как publisher (сайт: total-hunter.com)
2. Создать ad unit **728×90 Leaderboard** (идеально под 72px)
3. Получить embed-код (`<script>` + `<ins>` или `<div>`)
4. Передать код Клоду → вставим в `Layout.jsx:152` вместо `AD`
5. Деплой — готово

**Почему Coinzilla:** специализируется на crypto/gaming аудитории — точное попадание в игроков Total Battle.

---

## Что сделано сегодня (Хангоф #30)

| # | Задача | Статус |
|---|--------|--------|
| 1 | SEO: index.html — title, meta, OG, JSON-LD, hreflang, canonical | ✅ |
| 2 | Legal page: 5 разделов RU+EN, кнопка Назад, переключатель языка | ✅ |
| 3 | Слоган: «Total Hunter — умный поиск и автоматизация в Total Battle» | ✅ |
| 4 | GuidePage: полный перевод RU/EN через guide_content.js/.en.js | ✅ |
| 5 | Лендинг: убраны 🏪⚰️⚔️ из статистики, «боль» убрана из текстов | ✅ |
| 6 | LoginPage: убраны ⚔ и 💀, заменены на ◈ | ✅ |
| 7 | Иконки: перегенерированы из 1024×1024, favicon.svg удалён, алмаз крупнее | ✅ |
| 8 | Vercel баг: productionBranch=master → deploy hook + alias workflow | ✅ |

---

## Что делать дальше (строго по приоритету)

### 🔴 HIGH — делать первым
1. **Free-Kassa webhook** — зарегистрировать `FK_SECRET_WORD2` в кабинете FK. Без этого алмазы не начисляются после оплаты автоматически.
2. **Coinzilla** — зарегистрироваться, получить embed-код, вставить в `Layout.jsx:152`

### 🟡 MED
3. **Google Search Console** — добавить total-hunter.com, создать sitemap.xml, запросить индексацию
4. **EXE packaging** — PyInstaller build.spec, собрать TotalHunter.exe с Python + YOLO моделями
5. **YOLO model protection** — AES-256 шифрование crypts.pt, endpoint /get_model_key
6. **Auto-update** — version в /check_auth, updater.py

### 🟢 LOW
7. **Combo модуль** — `pyautogui.scroll()` → `keyboard.press('pagedown')`, маяк с max-значением
8. **Beacon навигатор** — use_beacon=false, нужен полевой тест

---

## Технические данные деплоя

**Deploy hook:** `POST https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw`  
**Project:** `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj` | **Team:** `team_CkkRPXdwtRtsL9YCk8n4Fzla`  
**Token:** `/c/Users/Admin/AppData/Roaming/com.vercel.cli/Data/auth.json` (истекает ~ноябрь 2026)  
**Backend:** https://api.total-hunter.com → GCP 34.68.86.57:8000
