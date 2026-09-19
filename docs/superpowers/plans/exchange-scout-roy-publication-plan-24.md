# Публикация находок Биржи 2.0 в РОЙ — План реализации

> **Для исполнителя:** исполнять inline в основном диалоге (`superpowers:executing-plans`), шаги с чекбоксами.
> **Субагентов НЕ запускать** без явного «да» владельца (золотое правило 2026-09-18, `CLAUDE.md` §4).
> Код начинать только после того, как владелец одобрил этот план **и** спека №1 прошла внешнее ревью (GPT, Gemini).

**Цель:** находка Биржи 2.0 (kingdom + X/Y) появляется на странице РОЙ сайта и исчезает через 20 минут.

**Архитектура:** отдельная таблица `roy_scout_finds` + два новых эндпоинта в `server/roy.py` (`POST /roy/scout-find`,
`GET /roy/scout-finds`) + новый метод `RoyClient.report_scout_find()` + новый блок в `RoyPage.jsx`. Существующие
`/roy/report`, `roy_pool`, SSE, `_cleanup_loop` не меняются (Биржа 1.0 неприкосновенна).

**Стек:** FastAPI + SQLAlchemy async + Alembic (server), pytest-asyncio + httpx + SQLite in-memory (тесты),
`requests` (клиент бота), React + Vite (сайт).

**Спека:** `docs/superpowers/specs/exchange-scout-roy-publication-design-01.md` (P-01…P-13, PT-01…PT-20).

## Global Constraints

- Биржа 1.0 не меняется: НИ ОДНА существующая строка `/roy/report`, `roy_pool`, `_report_rate`, `_broadcast`,
  `_cleanup_loop`, `POOL_TTL_MIN`, `RoyClient.report/get_pool` не редактируется — только добавления (P-12).
- Срок жизни находки — **20 минут**, своя константа `SCOUT_FIND_TTL_MIN = 20`, не `POOL_TTL_MIN` (P-13).
- Нет rate limit и нет дедупликации на публикацию 2.0 (P-04). Нет Telegram. Нет картинок (только K/X/Y).
- Публично наружу не отдаётся hwid (P-02). Тексты на сайте — только факты, RU/EN (P-11).
- Файлы на GCP не хранить, Alembic-миграция — только код через git (`CLAUDE.md`).
- Тесты сервера: `cd server && python -m pytest tests/<file> -v`; клиента: из корня `python -m pytest <file> -v`.
- Один коммит на задачу; коммитить только перечисленные файлы (в корне много чужого untracked-мусора).

**Вне плана:** вызов `report_scout_find` из consumer-потока 2.0 и контракты P-01, P-08 (журнал до публикации), P-06 (kingdom фиксируется при создании результата), PT-01, PT-02, PT-17, PT-18 (порядок
«списание → OCR → публикация») — принадлежат плану реализации Части A/B (consumer ещё не написан); здесь
создаётся только вызываемый метод.

---

## Карта файлов

| Файл | Действие | Ответственность |
|---|---|---|
| `server/models.py` | Modify | модель `RoyScoutFind` |
| `server/alembic/versions/s3c4o5u6t7f8_add_roy_scout_finds.py` | Create | миграция таблицы (down_revision `b1a2c3k4s5e6` — единственный head, проверено скриптом 2026-09-18) |
| `server/roy.py` | Modify | константа, схема, два эндпоинта |
| `server/tests/test_roy_scout.py` | Create | серверные тесты PT-03…PT-08, PT-12, PT-15, PT-16, PT-04, PT-05, PT-06 |
| `roy/roy_client.py` | Modify | метод `report_scout_find` |
| `test_roy_scout_client.py` | Create | клиентские тесты PT-09, PT-10, PT-11 |
| `web/src/pages/RoyPage.jsx` | Modify | блок «Находки Биржи 2.0» |

---

---

## Части плана (каждая ≤300 строк, исполнять по порядку; буква после цифры — номер части)

| Часть | Файл | Задачи |
|---|---|---|
| 25 | [`exchange-scout-roy-publication-plan-model-25.md`](exchange-scout-roy-publication-plan-model-25.md) | Task 1 модель + миграция |
| 26 | [`exchange-scout-roy-publication-plan-post-endpoint-26.md`](exchange-scout-roy-publication-plan-post-endpoint-26.md) | Task 2 `POST /roy/scout-find` |
| 27 | [`exchange-scout-roy-publication-plan-read-client-27.md`](exchange-scout-roy-publication-plan-read-client-27.md) | Task 3 `GET /roy/scout-finds`, Task 4 клиент `report_scout_find` |
| 28 | [`exchange-scout-roy-publication-plan-web-deploy-check-28.md`](exchange-scout-roy-publication-plan-web-deploy-check-28.md) | Task 5 сайт, Task 6 деплой (ГЕЙТ), SPEC→PLAN check, самопроверка |
