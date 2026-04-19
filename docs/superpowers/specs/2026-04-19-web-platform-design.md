# Web Platform — Design Spec
**Дата:** 2026-04-19  
**Статус:** Утверждён пользователем

---

## 1. Обзор

Личный кабинет пользователя Total Hunter. Фронтенд на Vercel, API на GCP.

- **URL:** `total-hunter.vercel.app` (бесплатный поддомен)
- **Стек:** React + Vite (фронтенд) · FastAPI GCP :8000 (API) · PostgreSQL (БД)
- **Тема:** Deep Night (палитра из `docs/color_palettes.md`, CSS-переменные 1:1 с ботом)

---

## 2. Авторизация

### Google OAuth поток
1. Пользователь нажимает "Login with Google" на Vercel (HTTPS)
2. `@react-oauth/google` получает ID Token от Google
3. Фронтенд: `POST /web/auth/google` с ID Token
4. FastAPI: верифицирует токен через Google API → создаёт/находит User по email → возвращает JWT
5. JWT хранится в `localStorage`, передаётся как `Authorization: Bearer <token>` во все запросы

### Привязка HWID (Вариант B — код из бота)
1. Бот генерирует 6-значный цифровой код
2. `POST /web/link/generate` (от бота) → код + HWID сохраняются в `link_codes`, TTL = 10 минут
3. Пользователь вводит код в дашборде (уже залогинен через Google)
4. `POST /web/link/verify` → сервер проверяет код, записывает HWID в `users.hwid`
5. Аккаунты связаны; код удаляется

---

## 3. Страницы дашборда

| Раздел | URL | Описание |
|--------|-----|----------|
| Профиль | `/dashboard` | Фото Google, имя, email, статус (trial/pro), дата регистрации |
| Баланс | `/dashboard/balance` | Основной баланс, реф-баланс, кнопка «Перевести», история пополнений |
| История охот | `/dashboard/hunts` | Таблица: дата, тип (биржа/склеп), сводка за сегодня/неделю/всего |
| Рефералы | `/dashboard/referrals` | Мой реф-код (копировать), L1/L2/L3 счётчики, реф-баланс |
| Устройства | `/dashboard/devices` | Привязанный HWID, кнопка «Сбросить» (1×/7 дней), дата следующего сброса |
| Транзакции | `/dashboard/transactions` | Полная лента: покупки, списания, бонусы |
| Инструкция | `/guide` | Публичная страница. Как установить бот, настроить, начать охоту |
| Оферта / Legal | `/legal` | Публичная страница. Оферта, disclaimer (игровые блокировки), оплата/возврат |

---

## 4. Новые API эндпоинты (FastAPI)

Все `/web/*` эндпоинты защищены JWT (кроме `/web/auth/google` и `/web/link/generate`).

| Метод | Путь | Кто вызывает | Описание |
|-------|------|--------------|----------|
| POST | `/web/auth/google` | Фронтенд | ID Token → JWT сессия |
| GET | `/web/me` | Фронтенд | Профиль, баланс, статус привязки HWID |
| GET | `/web/hunts` | Фронтенд | История охот с пагинацией |
| GET | `/web/transactions` | Фронтенд | История транзакций с пагинацией |
| POST | `/web/link/generate` | Бот | Создать 6-значный код привязки (принимает HWID) |
| POST | `/web/link/verify` | Фронтенд | Ввести код → связать email ↔ HWID |
| POST | `/web/hwid/reset` | Фронтенд | Сбросить HWID (лимит 1×/7 дней) |
| POST | `/web/referral/transfer` | Фронтенд | ref_credits → credits |

---

## 5. Изменения БД

### Новая таблица: `link_codes`
```
id          SERIAL PRIMARY KEY
hwid        VARCHAR(16) NOT NULL
code        VARCHAR(6)  NOT NULL UNIQUE
expires_at  TIMESTAMP WITH TIME ZONE NOT NULL
created_at  TIMESTAMP WITH TIME ZONE DEFAULT now()
```

### Новая таблица: `hwid_history`
Защита от абуза: если железо уже получало trial — повторно не давать, даже с новой почтой.
```
id          SERIAL PRIMARY KEY
hwid        VARCHAR(16) NOT NULL
user_id     INTEGER REFERENCES users(id)
linked_at   TIMESTAMP WITH TIME ZONE DEFAULT now()
```

### Изменения в таблице `users`
```
hwid_reset_at   TIMESTAMP WITH TIME ZONE  -- дата последнего сброса HWID
```

Новая миграция Alembic: `add_web_platform_tables`

---

## 6. Анти-абуз: hwid_history

- При каждой привязке HWID → запись в `hwid_history`
- При `/claim_trial`: проверяем все HWID, которые были у этого email → если любой из них `trial_used = true` → отказ
- Логика: один физический компьютер = один триал навсегда

---

## 7. HWID Reset

- `POST /web/hwid/reset` проверяет: `now() - hwid_reset_at < 7 дней` → 429 Too Many Requests
- При сбросе: `users.hwid = NULL`, `users.hwid_reset_at = now()`
- После сброса бот при следующем запуске создаёт новую запись (авторегистрация по новому HWID)
- Пользователь снова вводит 6-значный код для привязки нового устройства

---

## 8. Дизайн / UI

- **Тема:** Deep Night — строго из `docs/color_palettes.md`:
  - `--bg: #050810` · `--card: #0A0F1E` · `--elevated: #0F1528`
  - `--primary: #1B3A82` (deep sapphire, кнопки/акценты)
  - `--primary-dim: #2A4A9E` (hover)
  - `--on-surface: #C8D8F0` · `--on-surface2: #8090B8`
  - CSS-класс `[data-theme="deep-night"]` — готов в `docs/color_palettes.md`
- Шрифт: Inter (Google Fonts)
- Адаптив: mobile-first, breakpoint 768px
- Компонент навигации: боковой sidebar на десктопе, bottom bar на мобиле

---

## 9. Что НЕ входит в этот модуль

- Оплата (Free-Kassa) — Модуль 4
- Покупка кредитов — Модуль 4
- Мультиязычность сайта — после MVP
