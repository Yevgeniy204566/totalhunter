# Gemini Buffer — Total Hunter
**Дата:** 2026-05-19 (сессия 2) | **Версия:** 1.3.1 | **Хангоф #58**

---

## ✅ Сделано в сессии 2026-05-19 (вторая половина дня)

### Discord Community — запуск с нуля

**Сервер:**
- Создан Discord-сервер Total Hunter
- Carl-bot настроен: reaction roles, роль «Охотник» выдаётся после нажатия ✅ в #правила
- Структура каналов: #правила / #анонсы / #скачать-бота / #общение / #ошибки-и-баги / #предложения / #скрины-охоты
- Инвайт: https://discord.gg/7dJQdF2pBG (бессрочный, безлимитный)

**GitHub → Discord автоматика:**
- Webhook настроен: при `gh release create` → автопост в #анонсы
- URL: `https://discordapp.com/api/webhooks/.../github` (суффикс /github обязателен для форматирования)
- Проверен: статус 204 ✅

**Чейнджлог:**
- Запощены все версии (v1.1 → v1.2 → v1.3.0 → v1.3.1) с правильной UTF-8 кодировкой
- Важно: PowerShell + ConvertTo-Json → кодировка уплывает. Решение: `[System.Text.Encoding]::UTF8.GetBytes(json)` + WebClient.UploadData

**Сайт:**
- Иконка Discord (pngwing.com.png) добавлена:
  - Лендинг: футер между «Контакты» и «Legal»
  - Кабинет: шапка рядом с переключателем языка
- Файл: `web/public/img/discord.png`
- Ссылка → https://discord.gg/7dJQdF2pBG

**Правило для Discord:**
- Пользователей на скачивание вести ТОЛЬКО на total-hunter.com, не на GitHub напрямую
- На v1.3.2: в авто-пост GitHub добавить кнопку скачать → total-hunter.com/download

---

## 🔴 Что осталось (приоритет)

### 1. 🎮 Живой тест v1.3.1 во время ивента
- Следующий ивент «Торговые Пути»: **2026-05-20 20:00 Киев**
- Проверить: event_active флаг переключается, scan() засчитывается, AFK защита срабатывает
- Проверить: debug скрины приходят в Telegram при находке биржи

### 2. 🎰 Fortune Wheel — финализация визуала
- Unsplash CORS — текстуры не грузятся. Решение: локальные PNG в `web/public/img/wheel/`
- v6 исправил яркость — ждём финальной оценки пользователя

### 3. 📢 Реклама
- Adsterra — нативные баннеры, вывод от $5. Позиционировать как "Game Tools"

### 4. 🔧 Технический долг
- Баг «бот выкидывает в магазин» — не диагностирован, следить

### 5. 📣 Продвижение Discord
- Первые пользователи: пригласить через Telegram-канал и сайт
- Закрепить в #скачать-бота ссылку: https://total-hunter.com/download

---

## Ключевые параметры инфраструктуры

| Параметр | Значение |
|---|---|
| GCP | total-hunter-backend, us-central1-f, 34.68.86.57:8000 |
| Telegram Debug | @total_hunter_debug_bot, chat_id в override.conf |
| Vercel | prj_mWtcb6hJCkl40YLWheeIlxD5NmXj, team_CkkRPXdwtRtsL9YCk8n4Fzla |
| GitHub | Yevgeniy204566/totalhunter (ПУБЛИЧНЫЙ) |
| Discord | discord.gg/7dJQdF2pBG, webhook в #анонсы |
| Версия | 1.3.1 (выпущена 2026-05-19) |
| Следующая | 1.3.2 (после живого теста РОЯ 2026-05-20 20:00 Киев) |
