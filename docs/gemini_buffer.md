# Gemini Buffer — Хангоф #30
**Дата:** 2026-05-03 | Сессия: веб-платформа, SEO, иконки, деплой

---

## Что сделано сегодня

| # | Задача | Статус |
|---|--------|--------|
| 1 | SEO: `index.html` — title, meta description, OG, Twitter Card, JSON-LD SoftwareApplication, hreflang ru/en/x-default, canonical | ✅ |
| 2 | Legal page: полный профессиональный текст на RU+EN (5 разделов: Условия, Конфиденциальность, Отказ, Возврат, Контакты), кнопка ← Назад, переключатель языка | ✅ |
| 3 | Слоган лендинга: «Total Hunter — умный поиск и автоматизация в Total Battle» (RU+EN) | ✅ |
| 4 | Убрано слово «боль» из заголовков лендинга → «Что решает Total Hunter» | ✅ |
| 5 | Убраны emoji-иконки 🏪⚰️⚔️ из блока статистики лендинга | ✅ |
| 6 | LoginPage: убраны ⚔ и 💀, заменены на ◈ | ✅ |
| 7 | GuidePage: полный RU/EN перевод через `G = lang==='en' ? GUIDE_EN : GUIDE_RU` — все разделы, TOC, FAQ, CTA, кнопка языка в навбаре | ✅ |
| 8 | Карточки feature images лендинга: высота 160→220px | ✅ |
| 9 | Иконки: перегенерированы из 1024×1024 оригинала, обрезаны по контуру алмаза, `favicon.svg` удалён | ✅ |
| 10 | `favicon.ico` (web): 16+32+48px. `assets/icon.ico` (бот): 7 размеров 16-256px | ✅ |
| 11 | Vercel deploy баг: `productionBranch="master"` → пуши в `main` уходили в Preview. Создан deploy hook `D0wsErcYcw`, ветка `main` | ✅ |
| 12 | `deploy_web.sh`: правильный деплой через hook + poll-until-READY + alias | ✅ |

---

## Критический баг деплоя (решён)

**Симптом:** коммиты пушатся, Vercel строит, сайт не меняется.  
**Причина:** `productionBranch: "master"` в Vercel dashboard при ветке `main`. Все деплои уходили в Preview.  
**Решение:** deploy hook `POST .../D0wsErcYcw` (ветка `main`) + ручное назначение alias `total-hunter.com` через API после каждого билда.  
**Token:** `/c/Users/Admin/AppData/Roaming/com.vercel.cli/Data/auth.json` (истекает ~ноябрь 2026)

---

## Текущее состояние сайта (total-hunter.com)

| Страница | RU | EN | Статус |
|----------|----|----|--------|
| Лендинг `/` | ✅ | ✅ | Слоган, фичи, статистика без иконок |
| Логин `/login` | ✅ | — | Без мечей/черепов |
| Dashboard `/dashboard` | ✅ | ✅ | i18n подключён |
| Инструкция `/guide` | ✅ | ✅ | Полный перевод |
| Legal `/legal` | ✅ | ✅ | 5 разделов, кнопка Назад |

---

## Что делать дальше (приоритет)

### 🔴 HIGH
1. **Free-Kassa webhook** — зарегистрировать `FK_SECRET_WORD2` в кабинете FK. Без этого платежи принимаются, но алмазы не начисляются автоматически.
2. **Google Search Console** — добавить домен `total-hunter.com`, запросить индексацию. Sitemap: отправить `/sitemap.xml` (нужно создать).

### 🟡 MED
3. **EXE packaging** — PyInstaller `build.spec`, собрать `TotalHunter.exe` с bundled Python + моделями YOLO.
4. **YOLO model protection** — AES-256 шифрование `crypts.pt` → `crypts.pt.enc`, endpoint `/get_model_key`.
5. **Auto-update** — поле `version` в `/check_auth` ответе, `updater.py` модуль.
6. **Coinzilla реклама** — зарегистрироваться на coinzilla.com, вставить embed в `Layout.jsx` вместо заглушки.

### 🟢 LOW
7. **Combo модуль** — разморожен для будущей сессии: заменить `pyautogui.scroll()` на `keyboard.press('pagedown')`, маяк с уникальным max-значением.
8. **Beacon навигатор** — `use_beacon=false` (заморожен), требует полевой тест с правильным `nav_pps`.
9. **Иллюстрации в Guide** — `calib_point_a/b.png` уже есть в `web/public/img/`, нужно проверить отображение в GuidePage.

---

## Деплой (команды для следующей сессии)

```bash
# Стандартный деплой (Клод делает сам):
git add <файлы>
git commit -m "описание"
git push origin main
# Затем: hook → poll READY → alias (см. deploy_web.sh)

# Проверка что деплой дошёл:
curl -sI https://total-hunter.com/index.html | grep etag
```

**Deploy hook:** `POST https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw`  
**Project:** `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj` | **Team:** `team_CkkRPXdwtRtsL9YCk8n4Fzla`
