# Спека №1 (публикация находок в «Рой»), часть 1e — Матрица тестов PT-01…PT-18, самоаудит, Final Gate (Стадии 6, 7, 9)

> Индекс и статус спеки: [`exchange-scout-roy-publication-design-1.md`](exchange-scout-roy-publication-design-1.md). Части: [1a](exchange-scout-roy-publication-context-1a.md) · [1b](exchange-scout-roy-publication-contracts-1b.md) · [1c](exchange-scout-roy-publication-architecture-1c.md) · [1d](exchange-scout-roy-publication-adversarial-1d.md) · [1e](exchange-scout-roy-publication-tests-gate-1e.md).
> Нумерация контрактов P-, находок PA-, тестов PT- сквозная по всей спеке №1; ссылки вида «4.0», «2.6a», «PA-5» — на разделы других частей.

---

## Стадия 6. Test Matrix

Серверные тесты — `server/tests/test_roy_scout.py`; клиентские — рядом с существующими тестами клиента
(точное место определит план); ручная проверка сайта — PT-13.

| Тест | Инвариант | Normal | Boundary | Failure | Concurrent | Recovery |
|---|---|---|---|---|---|---|
| PT-01 `publish_not_called_when_charge_failed` | P-01 | — | ответ `low_credits` | 402/сеть | — | — |
| PT-02 `publish_not_called_without_coords` | P-01 | — | `coords_ok=false` | — | — | — |
| PT-03 `scout_find_validates_xy_type_and_integer_range` | P-02, PA-2, PA-11 | int → 200 | `0`, отрицательные, `2147483647` и `-2147483648` → 200; `2147483648` и `-2147483649` → 422 | строка (в т. ч. `"123"`), float, bool → 422 | — | — |
| PT-04 `scout_finds_response_has_no_hwid` | P-02, PA-1 | поля ровно {kingdom,x,y,found_at} | пустой список | — | — | — |
| PT-05 `scout_find_does_not_touch_roy_pool` | P-03, P-12 | `roy_pool` count не меняется | — | — | — | — |
| PT-06 `scout_find_allows_repeated_identical_posts` | P-04 | 2 запроса подряд с одинаковыми K/X/Y → 2 строки | <1 с между запросами | — | — (для P-04 конкурентная проверка не требуется: отсутствие лимита и `UNIQUE` проверяется последовательными вызовами) | — |
| PT-07 `scout_find_unknown_hwid_404` / `banned_403` / `hwid_longer_than_16_404` | P-05, 2.6a | существующий → 200 | hwid длиннее 16 символов → 404, вставки нет | 404, 403 | — | — |
| PT-08 `scout_find_kingdom_lt_1_rejected` | P-05 | K=1 → 200 | K=0, K=-1 → 422 | `"1"`, `1.0`, `true` → 422 (строгий int) | — | — |
| PT-09 `client_skips_publish_when_kingdom_zero` | P-06 | K>0 → запрос | K=0 → нет запроса | — | — | лог пишется |
| PT-10 `client_publish_does_not_block_consumer` | P-07 | — | сервер отвечает 5 с | сервер висит | — | consumer не ждёт завершения HTTP-вызова; при штатном завершении `requests` тред завершается после ответа, исключения или timeout (жёсткого предела в 5 с нет — PA-7) |
| PT-11 `client_publish_failure_is_swallowed` | P-08 | — | — | ConnectionError, 500, таймаут | — | consumer продолжает |
| PT-12 `scout_finds_lists_newest_first` | P-09 | порядок по `found_at` desc | 0 записей | — | — | — |
| PT-13 ручная проверка страницы | P-10, P-11 | блок виден, тексты RU/EN | пустой список | сервер недоступен | — | «Обновить» перечитывает |
| PT-14 `roy_report_and_pool_unchanged` | P-12, PA-9 | регрессия существующих `test_roy.py` зелёные | — | — | — | — |
| PT-15 `scout_finds_excludes_older_than_ttl` | P-13 | запись 19 мин 59 с видна | ровно 20 мин 00 с и 20 мин 01 с — не видны; часы `roy.datetime` зафиксированы (frozen clock, образец `test_roy.py`), граница детерминирована | — | — | — |
| PT-16 `scout_find_insert_deletes_expired` | P-13, PA-6 | запись возрастом ≥ 20 мин удалена при вставке | — | — | — | — |
| PT-19 `scout_endpoints_use_timezone_aware_utc_now` | P-13 | `roy.datetime.now` в POST и GET вызывается с `timezone.utc` | наивный `datetime.now()` → тест падает (SQLite наивное время не отвергает, прод отвергнет) | — | — | — |
| PT-17 `consumer_writes_journal_before_publish` (план consumer'а, Часть A/B) | P-08 | строка журнала записана до вызова `report_scout_find` | до вызова `report_scout_find` строка журнала уже зафиксирована с `fsync`; отсутствие записи журнала исключает публикацию | — | — | — |
| PT-18 `consumer_publishes_kingdom_captured_at_find` (план consumer'а, Часть A/B) | P-06, PA-8 | опубликован K, зафиксированный при создании результата | GUI сменили на другой K между находкой и публикацией → публикуется прежний K | — | — | — |

## Стадия 7. Self-Audit

Триаж слов-триггеров (`ровно / всегда / никогда / не ... нельзя / atomic`):
- «Публично ровно {kingdom,x,y,found_at}» (P-02) — категория (a), механизм: явный `select` + PT-04.
- «Одна транзакция» (4.2) — (a), `async with db.begin()`, паттерн `roy.py:265`.
- «Поведение 1.0 не изменяется» (P-12) — (a); runtime-enforcement нет, поведение доказывается регрессионными тестами PT-14 + дисциплиной изменений (только добавления символов); проверка `git diff` плана на отсутствие удалений — процессная проверка разработки, а не enforcement контракта.
- «Повтора нет» (P-08) — (b), non-goal, не требование.
- «Не блокирует consumer» (P-07) — (a), PT-10.

Найдено при самопроверке (содержательное): (1) PA-5 — серверная связь публикации со списанием отсутствует и сознательно не реализуется (Stage 1 п. 7); это принятый остаточный риск этой версии; (2) очистку таблицы нельзя класть в общий `_cleanup_loop` —
изменила бы поведение 1.0; (3) `kingdom = 0` в GUI → публикация молча не выполнится; вынесено в P-06 как
контракт с логом, а не «на усмотрение».

Requirements coverage: цепочка владельца — каждый шаг после «показать пользователю» покрыт (P-01, P-06-P-10);
шаги «списать» и «показать» — в спеке монетизации и Части A.

## Стадия 9. Final Gate

Проверено: каждое утверждение о существующем коде — из файлов, открытых лично в этой сессии (`server/roy.py`
1-300, `server/models.py` RoyPool, `roy/roy_client.py`, `web/src/pages/RoyPage.jsx`, фрагменты `main.py`,
`server/main.py` 288-357, `server/models.py` User/RoyPool, `auth.py:30-36`). Каждый контракт имеет определённый механизм реализации либо явно обозначенную межспековую зависимость (P-01, P-06, P-08 — реализует consumer, Части A/B) и verification; где runtime-enforcement не применяется (P-12 — поведение 1.0 доказывается регрессионными тестами и дисциплиной изменений; P-01 — контракт штатного клиента, PA-5), это указано явно. Stage 8 — «не запрошен владельцем».
