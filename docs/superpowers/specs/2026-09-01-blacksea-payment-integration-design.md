# BlackSea — вторая платёжка (вебхук + верификация + начисление алмазов)

**Дата:** 2026-09-01
**Статус:** черновик, ждёт ревью владельца перед переходом к implementation plan

## Контекст

NOWPayments (крипта) — единственный способ оплаты сейчас, минимальная сумма
$10. Владелец давно искал фиатную платёжку для карт (Украина, физлицо без
ФОП) и нашёл blacksea.in.ua (укр. аналог Gumroad). Прошлая сессия (#133)
живьём подтвердила пригодность — см. `MEMORY/project_blacksea_payment_gateway.md`
(комиссии, ограничения, структура вебхука). Эта сессия (#134) живьём
подтвердила механизм верификации продажи через API — см.
`MEMORY/project_blacksea_sale_verification_recipe.md`. Обе памяти читать
перед реализацией — там же точные curl-команды, которые эта спека не
дублирует.

Объём этой спеки: серверный эндпоинт вебхука BlackSea + идемпотентность +
верификация + начисление, по образцу уже существующего `server/payments.py`
(NOWPayments). Сайт (кнопка «Купить через карту») и боевой товар на BlackSea
— отдельные некодовые шаги, тоже входят в объём, но не архитектурно значимы.

## Согласованные с владельцем решения

1. **Один пакет на старте** — Ultra, $10 → 5000 ◆. Тот же пакет, что уже есть
   в `PACKAGES` для NOWPayments (`server/payments.py:38`). Lite/Pro на сайте
   сейчас не работают вообще (не в объёме).
2. **Email не найден среди пользователей сайта** → кредиты НЕ начисляются,
   уходит алерт в Telegram/админку с деталями (email, сумма, sale_id) —
   разбирается вручную. Никакого автосоздания аккаунта.
3. **Реферальный каскад применяется** — те же 10%/5%/1%, что и для NOWPayments
   (`_apply_referral_cascade`, `server/payments.py:92`), без изменений.

## Архитектура — принципиальное отличие от NOWPayments

У NOWPayments поток «создать заказ → получить invoice → оплатить →
вебхук» — `Order` создаётся ДО оплаты (`POST /web/payment/create`), у заказа
уже известен `user_id`, вебхук только его находит по `order_id` и помечает
`paid`.

У BlackSea такого шага нет: покупатель уходит на фиксированную ссылку товара
BlackSea напрямую (с сайта, без захода на наш сервер), платит — единственный
сигнал о покупке это входящий вебхук, идентификация только по email внутри
его тела. `Order` в текущем виде (столбцы под NOWPayments — `nowpayments_payment_id`,
`idempotency_key` = наш UUID, генерируемый на шаге create) сюда не ложится
без создания синтетического заказа задним числом. Вместо этого — отдельная
таблица только для идемпотентности и учёта, без стадии `pending`.

### Новая таблица `BlackSeaSale`

```python
class BlackSeaSale(Base):
    __tablename__ = "blacksea_sales"

    id            = Column(Integer, primary_key=True)
    sale_id       = Column(String(50), unique=True, nullable=False, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    credits_total = Column(Integer, nullable=False)
    uah_amount    = Column(Numeric(10, 2), nullable=False)
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", backref="blacksea_sales")
```

Строка пишется ТОЛЬКО при успешном начислении (после прохождения всех
проверок) — сама её наличие по `sale_id` и есть идемпотентность, тем же
паттерном что `Order.status == "paid"` у NOWPayments, но здесь без
промежуточного `pending`-состояния (создавать нечего заранее). Email-промах
(п.2 решений) НЕ создаёт строку — если BlackSea повторно пришлёт тот же
вебхук, алерт уйдёт снова; это осознанный компромисс (редкий кейс, ручной
разбор всё равно нужен).

Миграция alembic — новая ревизия, `head` на момент реализации сверить
(в репо бывают несведённые головы, см. `MEMORY/project_gcloud_local_access.md`).

## Поток обработки вебхука

`POST /web/payment/blacksea/webhook`, `Content-Type: application/x-www-form-urlencoded`
(не JSON, в отличие от NOWPayments) — парсить через `await request.form()`.

```
1. Распарсить form-поля: sale_id, email, price (МИНОРНЫЕ ЕДИНИЦЫ — копейки;
   подтверждено реальным вебхуком: price=100 при цене 1 грн), product_id, test.
2. Быстрый предварительный SELECT sale_id в blacksea_sales — если уже есть,
   200 OK, ничего не делать (оптимизация: не дёргать BlackSea API повторно
   на ретраи одного и того же вебхука). Это НЕ единственная защита от
   двойного начисления — см. п.6 про атомарность.
3. Если product_id не совпадает с известным BLACKSEA_PRODUCT_ID (конфиг,
   как PACKAGES у NOWPayments) → 200 OK, залогировать и не начислять — вебхук
   не от нашего товара Ultra (защита на случай появления другого товара на
   том же аккаунте в будущем).
4. Позвать GET /api/v2/sales/{sale_id}?access_token=... (см. рецепт в
   памяти) — сверить: paid == true, chargedback == false, refunded == false.
   **Плюс сверить email/price/product_id API-ответа (`sale.email`,
   `sale.price`, `sale.product_id` — источник истины) против тела вебхука
   (`email`, `price`, `product_id` из шага 1 — недоверенное, вебхук без
   подписи).**
   - Сетевая ошибка/невалидный ответ → 200 OK (не ретраить бесконечно на
   нашей стороне), залогировать error — ручной разбор.
   - paid == false или chargedback/refunded == true → 200 OK, не начислять.
   - **Любое несовпадение email/price/product_id между API-ответом и телом
     вебхука → 200 OK, залогировать как подозрительную попытку (кто-то
     подделал тело вебхука с чужим email на реальный чужой sale_id —
     ровно тот сценарий, от которого шаг 4 и задуман как защита), НЕ
     начислять.** `test`-поле из вебхука НЕ используется нигде в этой
     логике (осознанно, не забыто) — живая проверка (`MEMORY/project_blacksea_payment_gateway.md`)
     показала, что оно ненадёжно отличает реальную продажу от тестовой
     (`test:true` наблюдался даже на настоящей боевой оплате) — единственный
     критерий начисления: `paid:true` + совпадение email/price/product_id.
5. Найти User по **`sale.email` из API-ответа** (НЕ по `email` из тела
   вебхука — тело недоверенное, см. п.4; после успешной сверки оба значения
   равны, но источником для запроса берётся верифицированное). Прямое
   `User.email == sale.email`, тот же паттерн без `lower()`/case-insensitive
   (в проекте нигде не применяется, `web_routes.py:132,228` матчат так же
   напрямую). Не найден → алерт (см. решение п.2), 200 OK, не начислять.
6. **Атомарная точка идемпотентности.** Шаги 2 и 5 уже выполнили SELECT на
   этой сессии → SQLAlchemy autobegin уже открыл транзакцию → явный
   `async with db.begin():` здесь упадёт `InvalidRequestError: A transaction
   is already begun` (задокументированный антипаттерн проекта,
   `ANTI-PATTERNS.md:842-847`, Хангоф #70). Поэтому — `db.begin_nested()`
   (savepoint), тот же идиом, что уже в проекте (`web_routes.py:335-337`,
   `send_feedback`):
   ```python
   credits = PACKAGES["ultra"]["credits"]  # 5000 — не хардкодить число трижды
   try:
       async with db.begin_nested():
           db.add(BlackSeaSale(
               sale_id=sale_id, user_id=user.id, credits_total=credits,
               uah_amount=Decimal(price) / 100,
           ))
   except IntegrityError:
       # конкурентный вебхук уже обработал этот sale_id — savepoint
       # автоматически откатился САМ, внешняя транзакция осталась валидна.
       # Паттерн try/except СНАРУЖИ async with — как в roy.py:264-287,
       # НЕ ловить исключение изнутри блока (после неудачного flush сессия
       # входит в состояние, где обычный commit() рвётся PendingRollbackError
       # — savepoint именно для того и нужен, чтобы это обойти).
       return JSONResponse({"status": "ok"})
   ```
7. user.credits += credits; db.add(Transaction(user_id=user.id, type="purchase",
   amount=credits, usd_amount=str(PACKAGES["ultra"]["usd"]), package="ultra",
   meta={"blacksea_sale_id": sale_id})) — `credits` из шага 6 (`PACKAGES["ultra"]["credits"]`),
   не хардкод. `str()` вокруг usd_amount, тот же
   приём, что в `payments.py:142` (запись float в Numeric-колонку через
   строку, не напрямую). Те же поля, что заполняет
   NOWPayments-покупка (`payments.py:206-214`: `user_id`/`usd_amount`/`package`
   обязательны по факту, не формально — `/admin/purchases`, `main.py:1049-1070`,
   рендерит `t.package`/`t.usd_amount` напрямую; без них покупки BlackSea
   отображались бы в админке пустыми). `user_id` дополнительно NOT NULL на
   уровне схемы (`models.py:114`) — без него INSERT упадёт.
8. _apply_referral_cascade(db, user, credits) — переиспользовать существующую
   функцию из payments.py как есть (сигнатура не завязана на Order).
9. await db.commit() — сохраняет BlackSeaSale (из savepoint) + credits +
   Transaction + referral cascade одним коммитом внешней (autobegin)
   транзакции. Только ПОСЛЕ успешного commit — notify_balance_changed(user.hwid)
   → BackgroundTasks: send_purchase_alert(name=..., hwid=..., package="ultra",
   usd_amount=str(PACKAGES["ultra"]["usd"]), credits=credits, ip=..., bot_version=...)
   — см. ниже почему не uah_amount.
10. Всегда отвечать 200 OK на синтаксически валидный вебхук (BlackSea не
   должна ретраить бесконечно из-за проблем на нашей стороне) — ошибки
   логируются, не пробрасываются как 4xx/5xx, кроме как в исключительных
   случаях (невалидное тело формы).
```

`_apply_referral_cascade` — существующий код, переиспользуется без изменений
(импорт из `payments.py`).

**`send_purchase_alert` — переиспользуется БЕЗ изменения сигнатуры, но со
специфичными для BlackSea значениями, не с `BlackSeaSale`-полями напрямую.**
Проверено: `tg_channel.py:59-61` — `package: str, usd_amount: str` жёстко
вшиты в текст уведомления с `$`-префиксом (`f"${usd_amount}"`), у
`BlackSeaSale` таких полей нет (`uah_amount` вместо `usd_amount`, `package`
не хранится вовсе). Трогать сигнатуру НЕ нужно — она общая с NOWPayments,
риск регресса не оправдан ради одного нового источника платежа. Раз пакет
на старте всегда один (Ultra), передавать константы: `package="ultra"`,
`usd_amount=str(PACKAGES["ultra"]["usd"])` (т.е. `"10.00"`, тот же словарь,
что уже используется в `payment_create`, `server/payments.py:38`) — это
каталожная цена пакета, а не реально списанная сумма в UAH (которая
плавает по курсу конвертации BlackSea на момент продажи). Фактическая
`uah_amount` из `BlackSeaSale` в Telegram-алерт не идёт — только в БД, для
отчётности/сверки с реальными выплатами.

## Токены доступа BlackSea — конфигурация

**Статичное (никогда не меняется после выпуска приложения на BlackSea)** —
env vars в systemd `override.conf`, по аналогии с `NOWPAYMENTS_API_KEY`
(`server/payments.py:31-32`):

```
BLACKSEA_CLIENT_ID=...
BLACKSEA_CLIENT_SECRET=...
```

**Изменяемое (access_token/refresh_token могут ротироваться при каждом
refresh-обмене)** — НЕ в `override.conf`. Процесс не может переписать
systemd-конфиг сам (нет sudo/systemctl-доступа изнутри приложения), а
после рестарта сервиса (деплой, плановый рестарт) снова читались бы
протухшие статичные значения — интеграция сломалась бы намертво при первом
же рестарте после ротации. Хранить в уже существующей `AppSetting`
(`models.py:185-199`, key-value, тот же паттерн, что `current_version`):
ключи `blacksea_access_token` / `blacksea_refresh_token`. Читать оттуда
перед каждым вызовом `/api/v2/sales/{id}`, перезаписывать (`UPDATE`) сразу
после успешного refresh-обмена — до применения нового токена дальше по коду.

Текущая пара (`access_token`+`refresh_token`), полученная живым OAuth-flow
в сессии #134, лежит в `reference_secrets.md` (раздел BlackSea) — при
реализации записать её начальные значения в `app_settings` (не в env vars),
`client_id`/`client_secret` — в `override.conf`. `client_id`/`client_secret`
используются только для refresh-обмена (fallback при 401 от
`/api/v2/sales/{id}`), не на каждый запрос.

## Идентификация покупателя — нет подписи вебхука

В отличие от NOWPayments (`verify_nowpayments_sig`, HMAC-SHA512 по raw body),
у вебхука BlackSea подписи нет вообще (подтверждено дважды живыми тестами).
Поэтому Шаг 4 потока (сверка через API) — не опциональная подстраховка, а
единственная защита от поддельного POST на наш эндпоинт. Без него любой,
кто узнает URL вебхука, может начислить себе кредиты произвольным POST.
Endpoint URL должен быть непубличным (не логироваться, не светиться в
клиентском коде) - как и IPN URL NOWPayments.

## Что НЕ входит в объём (осознанно)

- Автопроверка лицензионных ключей — недоступна у BlackSea API, путь исключён
  (см. память).
- Автоматический редирект покупателя обратно на сайт — недоступен у BlackSea,
  начисление полностью asynchronous через вебхук, UI на сайте просто должен
  не полагаться на моментальное обновление баланса сразу после клика «Купить»
  (баланс придёт через уже существующий long-poll `vault.py`, с задержкой на
  реальную обработку платежа).
- Retry/пуллинг списка продаж как fallback на случай пропущенного вебхука —
  список `/api/v2/sales` не работает (см. память), полноценного fallback
  сейчас нет. Если вебхук потеряется — потребуется ручной разбор по
  `sale_id`, который покупатель может прислать в поддержку. Не в объёме
  первой итерации, зафиксировать как известное ограничение.

## Тестирование

TDD, по образцу `server/tests/test_payments.py`. Ключевые сценарии:
- Валидный вебхук + успешная API-верификация + известный email → кредиты
  начислены, Transaction записан, реферальный каскад сработал,
  notify_balance_changed вызван.
- Повторная доставка того же sale_id → повторного начисления нет (200 OK,
  no-op).
- Два одновременных вебхука с одним sale_id (`asyncio.gather` двух реальных
  HTTP-вызовов через `AsyncClient`/`ASGITransport` — та же структура теста,
  что `test_claim_trial_concurrent_calls_credit_exactly_once`,
  `server/tests/test_claim_trial.py:82-97`; там гонка закрыта атомарным
  `UPDATE ... RETURNING`, здесь — `INSERT` под `UNIQUE(sale_id)`, механизм
  другой, но тестовая структура и критерий та же: ровно один `success`)
  → кредиты начислены ровно один раз, вторая ветка получает IntegrityError
  и корректно откатывается без 500.
- Email не найден → алерт отправлен, кредиты не начислены, 200 OK.
- **Email в теле вебхука подделан (не совпадает с `sale.email` из API-ответа
  на тот же реальный `sale_id`)** → не начислять НИКОМУ (ни по email из
  вебхука, ни по email из API), 200 OK, залогировано как подозрительная
  попытка — закрывает уязвимость, найденную Stage 8 (см. текст п.4 потока).
- API-верификация вернула paid:false/chargedback:true → не начислять.
- Сетевая ошибка при обращении к BlackSea API → не начислять, не падать
  500-й, залогировать.

API-моки строить на реальном payload из памяти (`project_blacksea_payment_gateway.md`)
и реальном ответе show-by-id (`project_blacksea_sale_verification_recipe.md`)
— фикстуры уже есть, не выдумывать поля заново.
