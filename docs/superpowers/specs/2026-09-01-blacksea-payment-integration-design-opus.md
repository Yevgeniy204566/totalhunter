# BlackSea — вторая платёжка: вебхук, верификация продажи, начисление алмазов

**Дата:** 2026-09-01
**Статус:** черновик спеки, ждёт ревью владельца перед implementation plan
**Протокол:** написана по `docs/РАБОТА-С-ДОКУМЕНТАМИ.md` (Context → Code Archaeology →
Contract Extraction → Design → Adversarial Review → Test Matrix → Self-Audit → Final Gate)

> Все ссылки вида `файл:строка` в этом документе проверены чтением реального кода в сессии
> написания спеки (SQLAlchemy 2.0.49, Starlette из текущего окружения). Утверждения о поведении
> BlackSea — результат живых вызовов API в сессиях #133/#134, зафиксированных в
> `MEMORY/project_blacksea_payment_gateway.md` и `MEMORY/project_blacksea_sale_verification_recipe.md`.

---

## 1. Контекст и согласованные решения

### 1.1. Зачем

NOWPayments (крипта) — единственный способ оплаты сейчас. BlackSea (`blacksea.in.ua`, украинский
аналог Gumroad) добавляется как второй, карточный. Пригодность подтверждена живьём: EUR не
поддерживается (USD/UAH), комиссия с налогами ≈30.7%, цену можно задать в USD и BlackSea сама
конвертирует в UAH по курсу на момент транзакции. Эти экономические детали не влияют на
архитектуру эндпоинта и здесь не разбираются — они в `MEMORY/project_blacksea_payment_gateway.md`.

### 1.2. Объём спеки

Входит: серверный эндпоинт вебхука BlackSea, идемпотентность, верификация продажи через API
BlackSea, начисление алмазов, реферальный каскад, уведомления. Не входит: страница «купить
картой» на сайте, заведение боевого товара на BlackSea, эндпоинт `oauth_callback` (токены
заводятся вручную один раз, см. 2.3).

**Стадия 0 (декомпозиция), оценка:** документ длиннее ориентировочного порога в 300 строк, но
описывает ОДИН связный функционал — один эндпоинт, одна новая таблица, один внешний API. Разных
архитектурных слоёв или независимых исполнителей внутри нет; длина набрана деталями одной и той же
задачи (транзакционные границы, конкурентность, тестовая матрица). Решение — не делить.

**Стадия 8 (внешнее адверсариальное ревью), фиксация:** находки предыдущего внешнего ревью
(подмена email в теле вебхука, единицы измерения `price`, транзакционная граница токенов) учтены и
разобраны здесь — 4.3, 3.2, 4.5. Эта редакция написана заново одним проходом и на новое внешнее
ревью не отправлялась; решение о его назначении остаётся за сессией-заказчиком. Класс работы —
architectural (деньги, конкурентность, новый внешний API), поэтому «пропуск по условиям для
bounded» здесь неприменим, и это именно фиксация, а не обоснование пропуска.

### 1.3. Принципиальное отличие от NOWPayments

У NOWPayments поток «создать заказ → invoice → оплата → вебхук»: `Order` создаётся ДО оплаты в
`POST /web/payment/create` (`server/payments.py:128-161`), у заказа уже известен `user_id`, вебхук
находит его по `order_id` и переводит `status` в `paid` (`server/payments.py:188-217`).

У BlackSea такого шага нет: покупатель уходит на фиксированную ссылку товара, минуя наш сервер.
Единственный сигнал о покупке — входящий вебхук. Прокинуть свой идентификатор через ссылку нельзя:
живьём проверено, что `?ref=...` до вебхука не доходит, поля `url_params` в payload нет. Значит:

- предварительного `Order`-подобного объекта не существует и создавать его задним числом незачем;
- идентификация покупателя возможна ТОЛЬКО по email;
- подписи у вебхука нет — тело недоверенное, единственная защита это перепроверка через API.

### 1.4. Решения владельца (согласованы, не пересматриваются)

1. **Один пакет на старте — Ultra, $10 → 5000 ◆.** Тот же элемент словаря, что уже используется
   NOWPayments, `server/payments.py:38-40`:
   ```python
   PACKAGES: dict[str, dict] = {
       "ultra": {"usd": 10.00, "credits": 5000, "description": "Total Hunter — 5000 diamonds"},
   }
   ```
   Ни `credits`, ни `usd` в коде BlackSea не хардкодятся — читаются из этого словаря.
2. **Email из вебхука не найден среди пользователей → кредиты НЕ начисляются**, уходит алерт с
   деталями (email, сумма, `sale_id`), разбирается вручную. Автосоздание аккаунта не делается.
3. **Реферальный каскад применяется** — та же существующая функция `_apply_referral_cascade`
   (`server/payments.py:92-125`, уровни `LEVELS = [(1, 0.10), (2, 0.05), (3, 0.01)]`),
   импортируется и вызывается БЕЗ изменений: её сигнатура `(db, buyer: User, credits_total: int)`
   не завязана на `Order`.

### 1.5. Спорные места, решённые в этой спеке (не бизнес-решения, а корректность)

| Вопрос | Решение | Раздел |
|---|---|---|
| Что авторизует начисление — сумма или товар? | `product_id` из API. Сумма в UAH плавает по курсу и сверяется только на согласованность вебхук↔API | 3.5 |
| `quantity != 1` | Не начислять автоматически, алерт на ручной разбор | 3.6 |
| Email в другом регистре | Точное совпадение, при промахе — один повтор без учёта регистра; неоднозначность → алерт | 3.7 |
| Ошибка BlackSea API | 200 OK + лог (решение владельца: не провоцировать бесконечные ретраи) | 3.9 |
| Внутренняя ошибка (БД и т.п.) | 500, не подавляется — идемпотентность делает повторную доставку безопасной | 3.9 |

---

## 2. Данные и конфигурация

### 2.1. Новая таблица `blacksea_sales`

```python
class BlackSeaSale(Base):
    """Факт успешно обработанной продажи BlackSea. Пишется ТОЛЬКО при начислении —
    само наличие строки по sale_id и есть идемпотентность (стадии pending нет:
    заранее создавать нечего, заказ до оплаты у BlackSea не существует)."""
    __tablename__ = "blacksea_sales"

    id            = Column(Integer, primary_key=True)
    sale_id       = Column(String(50), unique=True, nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    credits_total = Column(Integer, nullable=False)
    uah_amount    = Column(Numeric(10, 2), nullable=False)
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", backref="blacksea_sales")
```

- `sale_id` — значение из вебхука, вид `v1N13bcVloNleQc9iKMeTg==` (24 символа). `String(50)` с
  запасом; длина валидируется до обращения к БД (шаг 3.2), чтобы переполнение не превращалось в
  500-ю ошибку. Отдельный `index=True` не ставится: `unique=True` уже создаёт индекс, по которому
  идёт единственный запрос к этой колонке (`Order.nowpayments_payment_id`, `server/models.py:352`,
  объявлен так же).
- `credits_total` — всегда `PACKAGES["ultra"]["credits"]`. По тексту документа Python-переменная
  этого же значения называется `credits`; это одно и то же число, разные имена только потому, что
  колонка таблицы названа по образцу `Order.credits_total` (`server/models.py:351`).
- `uah_amount` — реально уплаченная сумма: `Decimal(price_kopecks) / 100`. Numeric, не float.
  Нужна только для сверки с выплатами BlackSea; в начислении и в алерте не участвует (2.4).
- `UNIQUE(sale_id)` — не «оптимизация», а единственный механизм атомарности начисления (4.4).
- Миграция: новая alembic-ревизия. `head` сверять на момент реализации — в репозитории бывают
  несведённые головы (`MEMORY/project_gcloud_local_access.md`), последний merge —
  `server/alembic/versions/p1q2r3s4t5u6_merge_all_heads.py`.

Строка НЕ создаётся, когда начисление не состоялось (неизвестный email, неоплаченная продажа,
несовпадение полей). Следствие: повторная доставка такого вебхука повторит алерт. Принято
осознанно — случай редкий, ручной разбор всё равно нужен, а «отрицательная» строка потребовала бы
второго состояния и второй ветки идемпотентности.

### 2.2. Статичная конфигурация — env vars

По образцу `server/payments.py:31-32` (`NP_API_KEY = os.environ.get("NOWPAYMENTS_API_KEY", "")`),
в systemd `override.conf` на GCP:

```
BLACKSEA_CLIENT_ID=...
BLACKSEA_CLIENT_SECRET=...
BLACKSEA_PRODUCT_ID=...
```

Значения `client_id`/`client_secret` уже получены и лежат в `MEMORY/reference_secrets.md`
(раздел BlackSea) — в этом документе они намеренно не приводятся; `BLACKSEA_PRODUCT_ID` —
идентификатор боевого товара Ultra, известен станет при его заведении на BlackSea (шаг вне объёма). `client_id`/`client_secret`
используются ТОЛЬКО в refresh-обмене, не в каждом запросе. Эти три значения не меняются в ходе
работы приложения, поэтому env vars для них безопасны.

### 2.3. Ротируемые токены — `app_settings`, а не env vars

`access_token` и `refresh_token` могут смениться в любой момент работы приложения (при
refresh-обмене BlackSea вправе выдать новую пару). В `override.conf` их держать НЕЛЬЗЯ: процесс не
может переписать systemd-конфиг сам, и после ближайшего рестарта сервиса читались бы статичные
протухшие значения — интеграция сломалась бы намертво.

Хранение — в уже существующей key-value таблице `AppSetting` (`server/models.py:185-199`), тем же
приёмом, что `latest_version` (`server/main.py:575-583`), ключи:

| Ключ | Содержимое |
|---|---|
| `blacksea_access_token` | текущий `access_token` (scope `view_sales`) |
| `blacksea_refresh_token` | текущий `refresh_token` |

**Инвариант: обе строки создаются ОДИН раз при развёртывании (значения из
`MEMORY/reference_secrets.md`) и в рантайме только читаются и обновляются — код никогда не делает
для них `INSERT`.** Enforcement: чтение через `select(...).where(key == ...)`, при отсутствии строки
— ошибка конфигурации (лог ERROR + 500), а не молчаливое создание; отсутствие `INSERT`-ветки
доказывается тестом `test_blacksea_missing_token_setting_does_not_insert_row`. Why: `INSERT` в
рантайме дал бы вторую гонку (два вебхука создают одну и ту же строку) и, что хуже, заводил бы
токен-строку с непонятно откуда взятым значением. Плюс `SELECT ... FOR UPDATE` (4.5) требует, чтобы
строка уже существовала.

Redirect URI `https://api.total-hunter.com/web/payment/blacksea/oauth_callback` зарегистрирован на
стороне BlackSea, но соответствующего эндпоинта у нас нет и в объём он не входит: первичная выдача
токена делается вручную по рецепту из `MEMORY/project_blacksea_sale_verification_recipe.md`.

### 2.4. Transaction — какие поля обязаны быть заполнены

`Transaction.user_id` объявлен `nullable=False` (`server/models.py:114`) — без него INSERT упадёт.
Сверх формальной схемы обязательны ещё `package` и `usd_amount`: админка `/admin/purchases`
(`server/main.py:1059-1070`) рендерит `t.package` и `t.usd_amount` напрямую, поэтому покупка без
них отобразилась бы в списке пустой. Заполняем ровно тот же набор, что NOWPayments-покупка
(`server/payments.py:207-214`):

```python
db.add(Transaction(
    user_id=user.id,
    type="purchase",
    amount=credits,                              # == PACKAGES["ultra"]["credits"]
    usd_amount=str(PACKAGES["ultra"]["usd"]),    # str() вокруг float — как payments.py:141
    package="ultra",
    meta={"blacksea_sale_id": sale_id},
))
```

`str()` вокруг `PACKAGES["ultra"]["usd"]` — не косметика, а воспроизведение существующего приёма
записи float в `Numeric`-колонку (`server/payments.py:141`: `usd_amount=str(pkg["usd"])`).

**В `usd_amount` идёт каталожная цена пакета ($10.00), а не реально уплаченная сумма в UAH.**
Why: UAH-сумма плавает по курсу конвертации BlackSea и несопоставима с USD-суммами
NOWPayments-покупок в той же колонке и в той же админке. Фактическая UAH-сумма сохраняется в
`BlackSeaSale.uah_amount` и только там.

### 2.5. Telegram-алерт — сигнатура не трогается

`send_purchase_alert` (`server/tg_channel.py:59-75`) — keyword-only, все параметры обязательны:
`name, hwid, package, usd_amount, credits, ip, bot_version`; в тексте жёстко зашит доллар:
`f"📦 Пакет: {package} — ${usd_amount}"` (`server/tg_channel.py:70`). Функция общая с NOWPayments,
менять её сигнатуру ради одного нового источника платежа — неоправданный риск регресса.
Передаём константы: `package="ultra"`, `usd_amount=str(PACKAGES["ultra"]["usd"])` — то же значение
и по той же причине, что в 2.4.

Алерт о ненайденном email (решение 1.4.2) — отдельный вызов `_send_debug_sync`-подобного текста, а
не `send_purchase_alert`: покупки не было, и поля `hwid`/`credits`/`bot_version` заполнить нечем.
Содержимое: email из API-ответа, `sale_id`, `uah_amount`. Реализуется как отдельная функция в
`tg_channel.py` (новая, существующие не меняются).

---

## 3. Поток обработки вебхука

Новый модуль `server/blacksea.py` с `APIRouter(prefix="/web/payment/blacksea")`, регистрируется в
`server/main.py` рядом с остальными (`server/main.py:102-114`). Эндпоинт:
`POST /web/payment/blacksea/webhook`.

**Все внешние HTTP-вызовы к BlackSea — модульного уровня функции** (`fetch_blacksea_sale`,
`refresh_blacksea_token`), чтобы тесты патчили их тем же способом, что уже используется в проекте:
`patch("web_routes._verify_google_token", ...)` (`server/tests/test_web_routes.py:20`).
Таймаут обоих вызовов — 15 секунд, то же значение, что у существующего вызова платёжного
API (`server/payments.py:46`: `httpx.AsyncClient(timeout=15)`); новых чисел не вводится.

### 3.1. Разбор тела

`Content-Type: application/x-www-form-urlencoded` (не JSON, в отличие от NOWPayments), парсинг —
`await request.form()`. Прочитано в Starlette: для form-парсинга обязателен `python-multipart`
(`starlette/requests.py:275-277` — `assert parse_options_header is not None`), он уже в
`server/requirements.txt:12` (`python-multipart==0.0.20`); перед деплоем убедиться, что пакет стоит
в venv на GCP. Чужой Content-Type даёт пустую `FormData` без исключения
(`starlette/requests.py:298-299`) — такой запрос уйдёт в ветку «malformed» шага 3.2.

Используемые поля: `sale_id`, `email`, `price`, `product_id`, `quantity`. Остальные поля payload
(`seller_id`, `fee`, `currency`, `card{...}`, `order_number`, `purchaser_id`, `test`, `refunded`,
`disputed`, `dispute_won`, …) не участвуют в логике.

**Поле `test` не используется НИГДЕ — это осознанное решение, а не забытый висяк.** Живая проверка
показала `test:true` на настоящей боевой оплате, то есть поле не отличает реальную продажу от
тестовой. Единственный критерий начисления — ответ API (3.5).

### 3.2. Валидация формы (до любой работы с БД и сетью)

Отсутствие `sale_id`/`email`/`price`/`product_id`, `sale_id` длиннее 50 символов, `price`, не
приводящийся к `int` → `HTTPException(400)`, ничего не логируется как продажа. Это единственная
ветка, отвечающая не 200 при синтаксически осмысленном запросе.

**`price_kopecks = int(price)` выполняется ЗДЕСЬ, и дальше по потоку используется только
`price_kopecks`.** Why: `request.form()` отдаёт все значения как `str` — прочитано в Starlette,
`unquote_plus(field_value.decode("latin-1"))` (`starlette/formparsers.py:118-120`), а `sale.price` в JSON-ответе
API — Python `int`; без явной нормализации сравнение `price == sale.price` даёт `"100" == 100 →
False` ВСЕГДА, то есть каждая покупка проваливала бы сверку шага 3.5. Единицы — минорные (копейки):
подтверждено реальным вебхуком, `price=100` при цене 1.00 UAH; в ответе API те же минорные единицы.

### 3.3. Быстрая проверка идемпотентности

`SELECT` по `blacksea_sales.sale_id`. Строка есть → 200 OK, ничего не делать. Это оптимизация
(не дёргать API BlackSea на повторных доставках), а НЕ защита от двойного начисления — защита в 3.8.

### 3.4. Верификация продажи через API BlackSea

`GET https://blacksea.in.ua/api/v2/sales/{sale_id}?access_token=...`, `access_token` читается из
`app_settings` (2.3) перед вызовом.

**`sale_id` обязан быть URL-encoded в пути** (`urllib.parse.quote(sale_id, safe="")`): реальные
идентификаторы кончаются на `==`, без кодирования маршрутизация BlackSea уводит запрос не туда
(проверено живьём, `MEMORY/project_blacksea_sale_verification_recipe.md`).

**Список продаж `GET /api/v2/sales` не использовать ни при каких обстоятельствах** — он всегда
возвращает `{"success":true,"sales":[]}` даже на реально оплаченных продажах и с правильным scope
(проверено дважды живыми покупками). Единственный рабочий способ — show-by-id.

Ответ 401 → ветка обновления токена (4.5), затем ровно один повтор этого же запроса.

### 3.5. Сверка API-ответа — что именно авторизует начисление

Из `sale` (источник истины) проверяется:

| Проверка | Провал → |
|---|---|
| `sale.paid is True` | 200 OK, не начислять |
| `sale.chargedback is False` | 200 OK, не начислять |
| `sale.refunded is False` и `sale.partially_refunded is False` | 200 OK, не начислять |
| `sale.product_id == BLACKSEA_PRODUCT_ID` | 200 OK, лог WARNING, не начислять |
| `sale.email == email` из тела вебхука | 200 OK, лог как подозрительная попытка, не начислять |
| `sale.price == price_kopecks` (оба `int`) | 200 OK, лог как подозрительная попытка, не начислять |
| `sale.product_id == product_id` из тела вебхука | 200 OK, лог как подозрительная попытка, не начислять |

**Авторизует начисление товар, а не сумма.** Сумма в UAH плавает по курсу конвертации BlackSea, и
сравнивать её с константой нельзя — поэтому единственная защита от «заплатил 1 грн, получил 5000
алмазов» это равенство `sale.product_id` сконфигурированному `BLACKSEA_PRODUCT_ID` (тестовые и
любые будущие товары того же продавца отсекаются здесь). Сверка `price` — только на согласованность
вебхука с API, не на размер платежа.

### 3.6. `quantity`

`quantity != "1"` → не начислять автоматически, уйти в алерт ручного разбора (тот же путь, что
неизвестный email). Why: умножать пакет на количество — бизнес-правило, которое не согласовано, а
начислить один пакет за оплаченные три означало бы недодать покупателю. `quantity` берётся из
недоверенного тела вебхука, и это допустимо ровно потому, что поле работает ТОЛЬКО как
консервативный гейт «уйти на ручной разбор»: подделка `quantity` не может увеличить начисление, а
может лишь отправить собственную покупку атакующего на ручную проверку. Отсутствие поля трактуется
как `1` с логом WARNING (в реальном payload оно присутствует всегда; его исчезновение — повод
заметить смену формата, но не повод блокировать деньги).

### 3.7. Поиск пользователя — только по верифицированному email

`User` ищется по `sale.email` из API-ответа, НЕ по `email` из тела вебхука. Why: тело не подписано;
если искать по нему, атакующий с собственным настоящим оплаченным `sale_id` подменил бы в теле
`email` на чужой и увёл начисление на чужой аккаунт. После сверки 3.5 оба значения равны, но
источником запроса берётся именно верифицированное.

Порядок поиска:
1. Точное совпадение `User.email == sale.email` — тот же приём, что везде в проекте
   (`server/web_routes.py:132`, `server/web_routes.py:228`).
2. Промах → один повтор без учёта регистра: `func.lower(User.email) == sale.email.lower()`.
   Ровно один результат → он и есть покупатель. Why: Google-логин отдаёт email в нижнем регистре, а
   в форму оплаты BlackSea покупатель вводит его руками — «Ivan@Gmail.com» иначе давал бы ложный
   «неизвестный email» на каждой такой покупке.
3. Ноль результатов → алерт (решение 1.4.2), 200 OK, не начислять, строку `BlackSeaSale` не писать.
4. Больше одного результата (аккаунты, различающиеся только регистром) → алерт как неоднозначность,
   200 OK, не начислять. Автоматически выбирать одного из них нельзя.
5. Найденный пользователь забанен (`user.is_banned`) → алерт, 200 OK, не начислять.

Пользователь загружается с `.with_for_update()` — блокировка строки покупателя до конца транзакции
начисления. Why: `user.credits += credits` — это read-modify-write на стороне Python; две
одновременные покупки одного пользователя без блокировки дали бы потерянное обновление. Приём уже
применяется в проекте для той же цели (`server/payments.py:191-193`).

### 3.8. Атомарное начисление

Шаги 3.3 и 3.7 уже выполнили `SELECT` на этой сессии → SQLAlchemy autobegin уже открыл транзакцию →
явный `async with db.begin():` здесь упал бы `InvalidRequestError: A transaction is already begun`.
Это задокументированный инцидент проекта (`ANTI-PATTERNS.md:842-847`, Хангоф #70: «`db.begin()`
внутри эндпоинта с `get_web_user` — 500 для всех», решение — `begin_nested()` + `commit()` снаружи).
Идиом уже используется, `server/web_routes.py:335-337`:

```python
async with db.begin_nested():
    db.add(Feedback(user_id=web_user.id, text=req.text.strip()))
await db.commit()
```

Здесь:

```python
credits = PACKAGES["ultra"]["credits"]          # 5000 — единственный источник числа
try:
    async with db.begin_nested():               # SAVEPOINT
        db.add(BlackSeaSale(
            sale_id=sale_id, user_id=user.id, credits_total=credits,
            uah_amount=Decimal(price_kopecks) / 100,
        ))
        await db.flush()                        # не обязателен, см. ниже
except IntegrityError:                          # СНАРУЖИ async with — как roy.py:264-287
    logger.info("[BLACKSEA] duplicate sale_id %s — no-op", sale_id)
    return JSONResponse({"status": "ok"})

user.credits += credits
db.add(Transaction(
    user_id=user.id, type="purchase", amount=credits,
    usd_amount=str(PACKAGES["ultra"]["usd"]), package="ultra",
    meta={"blacksea_sale_id": sale_id},
))
await _apply_referral_cascade(db, user, credits)
await db.commit()                               # один коммит внешней (autobegin) транзакции
```

Проверено в исходниках SQLAlchemy 2.0.49:

- выход из `async with db.begin_nested()` сам вызывает flush перед релизом savepoint —
  `SessionTransaction.commit()` → `_prepare_impl()`, где `if not self.session._flushing: ...
  self.session.flush()` (`sqlalchemy/orm/session.py:1282-1286`, вызов из `commit()` —
  `session.py:1308-1311`). То есть `IntegrityError` вылетит и без явного `await db.flush()`.
  Явный `flush()` в коде оставляем как читаемость: без него корректность блока зависит от знания
  этой детали ORM;
- `except IntegrityError` обязан стоять СНАРУЖИ `async with`: откат до savepoint происходит на
  выходе из блока — в `SessionTransaction.rollback()` цикл останавливается на ближайшей вложенной
  транзакции (`if transaction._parent is None or transaction.nested: ... break`,
  `sqlalchemy/orm/session.py:1354-1370`), поэтому внешняя транзакция остаётся живой и последующий
  `commit()` не рвётся `PendingRollbackError`. Тот же паттерн «try/except снаружи блока» уже
  работает в проекте: `server/roy.py:264-287` (конкурентный INSERT в `roy_pool` под
  `UniqueConstraint('kingdom','x','y')`).

Значения, нужные после коммита (`user.hwid`, `user.username`/`email`, `ip_address`, `bot_version`),
захватываются в локальные переменные до `commit()` — как в `server/payments.py:219-225`. Формально
`expire_on_commit=False` и в проде (`server/database.py:31`), и в тестах
(`server/tests/conftest.py:27`), но зависеть от этой настройки не нужно.

### 3.9. После коммита

```python
notify_balance_changed(user_hwid)               # будит long-poll бота, vault.py:24-27
background_tasks.add_task(
    send_purchase_alert,
    name=user_name, hwid=user_hwid, package="ultra",
    usd_amount=str(PACKAGES["ultra"]["usd"]), credits=credits,
    ip=user_ip, bot_version=bot_version,
)
return JSONResponse({"status": "ok"})
```

`notify_balance_changed` вызывается ТОЛЬКО после успешного `commit()` — иначе бот получил бы
пробуждение на не сохранённый баланс. `hwid=None` (веб-аккаунт без привязанного бота) безопасен:
функция сама проверяет `if hwid and hwid in _notifiers` (`server/vault.py:26`).

**Коды ответа:**

| Ситуация | Ответ | Why |
|---|---|---|
| Начислено / дубликат / решение «не начислять» (3.5, 3.6, 3.7) | 200 | Решение принято, ретрай ничего не изменит |
| Повторный 401 после единственного refresh (4.5) | 200 + лог ERROR | Доступ к API отозван/изменён — повтор не поможет, нужен ручной разбор |
| Тело формы невалидно (3.2) | 400 | Такой запрос не станет валидным при повторе |
| Сетевая ошибка/невалидный ответ BlackSea API | 200 + лог ERROR | Решение владельца: не провоцировать неизвестную нам политику ретраев BlackSea. Цена — продажа требует ручного разбора; повторная доставка того же вебхука в будущем безопасна благодаря `UNIQUE(sale_id)` |
| Внутренняя ошибка (БД, deadlock, отсутствие токен-строк) | 500, исключение не подавляется | Исход не определён; 500 — честный сигнал и заметен в логах, а повторная доставка снова безопасна |

Асимметрия двух последних строк намеренная и зафиксирована как решение, а не как недосмотр:
внешний отказ мы гасим (200), внутренний — нет (500).

---

## 4. Безопасность и конкурентность

### 4.1. У вебхука нет подписи

NOWPayments подписывает тело: `hmac.new(NP_IPN_SECRET.encode(), body_bytes, hashlib.sha512)` и
сравнение через `hmac.compare_digest` (`server/payments.py:80-89`), невалидная подпись → 400
(`server/payments.py:173-174`). У BlackSea аналога нет — подтверждено разбором реального payload
(поля с HMAC в нём отсутствуют). Поэтому верификация через API (3.4-3.5) — не «дополнительная
подстраховка», а ЕДИНСТВЕННАЯ граница доверия. Любая ветка кода, начисляющая кредиты, обязана
находиться после успешной верификации; enforcement — порядок шагов 3.4→3.5→3.7→3.8 и тест
`test_blacksea_forged_email_credits_nobody`.

### 4.2. URL вебхука — не граница безопасности

Секретность URL (security through obscurity) защитой не является: он может засветиться в логах,
трафике, ошибках стороннего сервиса. Не публиковать его без нужды — гигиена, ровно как и с IPN URL
NOWPayments. Ни один вывод о безопасности в этом документе не опирается на неизвестность URL.

### 4.3. Модель атаки, которую закрывает 3.5+3.7

Атакующий имеет собственную настоящую оплаченную продажу и, значит, валидный `sale_id`. Он шлёт
нам вебхук, подменив `email` на чужой. Если бы пользователь искался по `email` из тела, кредиты
ушли бы на чужой аккаунт (или, при повторных отправках с разными email — многократно). Защита
двухслойная: (а) поиск идёт по `sale.email` из API; (б) несовпадение `sale.email` с телом само по
себе останавливает обработку и логируется. Обход: подделать ответ API невозможно без компрометации
`access_token`; повторить свой же `sale_id` бессмысленно — `UNIQUE(sale_id)` даёт no-op.

### 4.4. Гонка двух вебхуков с одним `sale_id`

Оба проходят проверку 3.3 (строки ещё нет), оба верифицируют продажу, оба доходят до `INSERT`.
Единственный арбитр — `UNIQUE(sale_id)` на уровне БД: один `INSERT` проходит, второй получает
`IntegrityError`, откатывается до savepoint и отвечает 200 без начисления и без 500. Предварительный
`SELECT` (3.3) арбитром НЕ является и на него в рассуждении о корректности ничего не опирается.

### 4.5. Гонка на обновлении токена — отдельная транзакция

**Инвариант: запись новой пары токенов коммитится в собственной, немедленно подтверждаемой
транзакции, полностью развязанной с транзакцией начисления.**

Why: refresh — внешний НЕОБРАТИМЫЙ побочный эффект. Если BlackSea ротировала `refresh_token`, старая
пара у них невалидна навсегда. Пусть запись токена лежит в той же транзакции, что последующее
начисление; тогда откат этой транзакции по ЛЮБОЙ не связанной с токеном причине (ошибка в каскаде,
конфликт БД, deadlock) вернёт в базу старую, уже мёртвую пару — интеграция сломана до ручного
вмешательства, причём отказ проявится только на следующей продаже.

Последовательность при 401 от `GET /api/v2/sales/{sale_id}`:

`stale_token` — то самое значение `access_token`, с которым запрос продажи только что получил 401.

```python
assert not (db.new or db.dirty or db.deleted)   # в сессии нет бизнес-записей — см. ниже

async with db.begin_nested():
    row = (await db.execute(                       # строка access_token — под локом
        select(AppSetting).where(AppSetting.key == "blacksea_access_token").with_for_update()
    )).scalar_one()
    refresh_row = (await db.execute(               # строка refresh_token — тем же локом
        select(AppSetting).where(AppSetting.key == "blacksea_refresh_token").with_for_update()
    )).scalar_one()

    if row.value != stale_token:
        access_token = row.value          # кто-то обновил, пока мы ждали лок — берём готовое
    else:
        new_access, new_refresh = await refresh_blacksea_token(
            client_id, client_secret, refresh_row.value)   # timeout=15
        row.value = access_token = new_access
        if new_refresh:                   # если ответ без refresh_token — старый не затираем
            refresh_row.value = new_refresh

await db.commit()                          # НЕМЕДЛЕННО, до возврата к обработке продажи
```

Обе строки лочатся в одном и том же порядке (`access` → `refresh`) во всех ветках — при двух
конкурентных 401 взаимной блокировки не возникает.

Разбор механизма:

- `begin_nested()`, а не `begin()` — на сессии уже сработал autobegin от `SELECT`ов шага 3.3
  (`ANTI-PATTERNS.md:842-847`). Изоляцию даёт не savepoint, а блокировка строки плюс немедленный
  коммит; savepoint даёт чистую границу отката, если OAuth-вызов бросит исключение.
- `with_for_update()` — тот же приём, что уже используется в проекте для сериализации конкурентной
  обработки одной строки: `select(Order).where(Order.id == order_id).with_for_update()`
  (`server/payments.py:191-193`).
- **Перечитывание значения под локом обязательно.** Один только `FOR UPDATE` не спасает: оба
  вебхука прочитали бы `T_old` до лока и оба выполнили бы обмен, второй — уже мёртвым
  `refresh_token`. Сравнение `row.value != stale_token` под локом и есть механизм «ровно один
  refresh».
- **Бюджет: не более ОДНОГО refresh и не более ОДНОГО повтора запроса продажи на один входящий
  вебхук.** Доказательство достаточности: после успешного refresh повтор идёт со свежим токеном;
  если и он даёт 401, второй refresh с тем же входом может лишь повторить тот же результат —
  значит проблема не в протухшем токене (отозван доступ, изменён scope), и цикл обязан
  остановиться. Enforcement: флаг «refresh уже выполнялся» в области видимости обработчика; провал
  повтора → лог ERROR + 200. Без этого бюджета взаимный 401 и refresh дали бы неограниченный цикл
  сетевых вызовов на один вебхук.
- **На момент этого `commit()` в сессии не должно быть ни одной незакоммиченной бизнес-записи.**
  Обеспечивается порядком шагов: любые записи (`BlackSeaSale`, `Transaction`, `user.credits`)
  начинаются только после успешной верификации, то есть строго позже. Дополнительное enforcement —
  дешёвая защитная проверка на входе в ветку refresh: `assert not (db.new or db.dirty or
  db.deleted)`; она ловит любую будущую правку, которая переставит запись перед верификацией.
- Лок держится на время сетевого round-trip к BlackSea — это осознанно (иначе сериализации нет).
  Ограничитель — `timeout=15` на OAuth-вызове (значение из `server/payments.py:46`).
- Ответ обмена без `access_token` → refresh считается неудачным, ничего не пишется, 200 + лог
  ERROR. Ответ без `refresh_token` → старый `refresh_token` сохраняется, не затирается.
- Строки `app_settings` заранее существуют (2.3); их отсутствие — ошибка конфигурации: `scalar_one()`
  бросит исключение, обработчик отдаст 500 (см. таблицу 3.9), а не создаст строку.

### 4.6. Потерянное обновление на балансах

Баланс покупателя защищён блокировкой его строки (3.7). Реферальные балансы —
`referrer.ref_credits += amount` внутри `_apply_referral_cascade` (`server/payments.py:110-112`) —
блокировкой не защищены; при двух одновременных покупках у одного реферера теоретически возможно
потерянное обновление. Это поведение существующего общего кода, идентичное текущему
NOWPayments-потоку, и оно НЕ вводится этой спекой; решение владельца 1.4.3 прямо требует
переиспользовать каскад без изменений. Фиксируется как известное ограничение, а не как решённая
проблема; исправление (атомарный `UPDATE ... SET ref_credits = ref_credits + N`) — отдельная
задача, затрагивающая обе платёжки.

### 4.7. Что осознанно не покрыто

- **Возврат/чарджбек после начисления.** Кредиты не отзываются автоматически. Повторный вебхук по
  тому же `sale_id` даст no-op по идемпотентности. Ручной разбор.
- **Потерянный вебхук.** Fallback через список продаж невозможен — `GET /api/v2/sales` не работает.
  Восстановление — вручную по `sale_id`, который покупатель пришлёт в поддержку.
- **Спам алертов.** Атакующий, многократно переотправляя вебхук с неизвестным email, может
  генерировать повторные Telegram-алерты (строка `BlackSeaSale` в этом случае не пишется, 2.1).
  Денег это не двигает, каждая попытка стоит атакующему одного round-trip к API BlackSea. Принято
  как ограничение; при реальном злоупотреблении добавляется rate-limit по `sale_id` — вне объёма.
- **Автопроверка лицензионных ключей и авторедирект покупателя на сайт** — у BlackSea недоступны;
  баланс на сайте догоняется существующим long-poll `vault.py`, UI не должен ждать мгновенного
  обновления сразу после клика «Купить».

---

## 5. Контракты и тестирование

TDD, новый файл `server/tests/test_blacksea.py`, по образцу `server/tests/test_payments.py`.
Фикстуры вебхука и ответа API строить на реальных payload'ах из
`MEMORY/project_blacksea_payment_gateway.md` и
`MEMORY/project_blacksea_sale_verification_recipe.md` — поля не выдумывать.

### 5.1. Контракты и механизмы enforcement

| Требование | Контракт/инвариант | Enforcement | Verification (планируемый тест) |
|---|---|---|---|
| Один `sale_id` = максимум одно начисление | `UNIQUE(sale_id)`, строка пишется только при успехе | Constraint БД + `begin_nested()` + `except IntegrityError` снаружи | `test_blacksea_duplicate_sale_id_no_double_credit`, `test_blacksea_concurrent_same_sale_credits_once` |
| Кредиты только за верифицированную продажу | Начисление строго после успешного API-ответа | Порядок шагов 3.4→3.5→3.8 | `test_blacksea_unpaid_sale_not_credited`, `test_blacksea_refunded_sale_not_credited` |
| Начисление идёт владельцу настоящей продажи | Поиск `User` по `sale.email`, не по телу | Код шага 3.7 | `test_blacksea_forged_email_credits_nobody` |
| Сравнение сумм не ломается на типах | `price_kopecks: int` против `sale.price: int` | Нормализация в 3.2 | `test_blacksea_price_compared_as_int` |
| Начисляется ровно пакет Ultra | Все три числа из `PACKAGES["ultra"]` | Отсутствие литералов 5000/10.00 в модуле | `test_blacksea_credits_amount_from_packages_dict` |
| Покупка видна в админке | `Transaction.package`/`usd_amount` заполнены | Состав полей 2.4 | `test_blacksea_transaction_has_package_and_usd` |
| Не более одного refresh на вебхук | Флаг «refresh выполнялся» + один повтор | Код 4.5 | `test_blacksea_second_401_does_not_refresh_again` |
| Ровно один refresh на два конкурентных 401 | `FOR UPDATE` + перечитывание значения под локом | Код 4.5 | `test_blacksea_concurrent_401_refreshes_once` |
| Токены переживают провал начисления | Отдельный немедленный `commit()` | Код 4.5 + `assert not (db.new or db.dirty or db.deleted)` | `test_blacksea_token_refresh_survives_failed_crediting` |
| Токен-строки не создаются в рантайме | Только чтение/`UPDATE` | Отсутствие `db.add(AppSetting(...))` в модуле | `test_blacksea_missing_token_setting_does_not_insert_row` |
| Баланс бота обновляется сразу | `notify_balance_changed` после `commit()` | Порядок 3.9 | `test_blacksea_notifies_balance_after_commit` |
| Ненайденный email не молчит | Алерт + 200 + отсутствие начисления | Код 3.7 | `test_blacksea_unknown_email_alerts_and_credits_nobody` |

Два enforcement-механизма в этой таблице (`with_for_update()` на строке токена и на строке
покупателя) тестами НЕ доказываются — на SQLite конструкция вырезается диалектом; названные тесты
доказывают логику вокруг них. Граница разобрана в 5.3, это не пробел, а известное свойство среды.

### 5.2. Тестовая матрица

| Сценарий | Класс | Ожидаемый результат | Тест |
|---|---|---|---|
| Валидный вебхук, верификация ок, email известен | Normal | Кредиты начислены, `Transaction` записан (`package`/`usd_amount` заполнены), каскад отработал (L1 10%/L2 5%/L3 1%), `notify_balance_changed` вызван, строка `blacksea_sales` создана, 200 | `test_blacksea_happy_path_credits_and_cascade` |
| Повторная доставка того же `sale_id` | Recovery | Повторного начисления нет, баланс не изменился, 200 | `test_blacksea_duplicate_sale_id_no_double_credit` |
| Два одновременных вебхука с одним `sale_id` (`asyncio.gather` двух реальных HTTP-вызовов через `AsyncClient`/`ASGITransport`) | Concurrent | Кредиты ровно один раз; вторая ветка ловит `IntegrityError`, отвечает 200, не 500 | `test_blacksea_concurrent_same_sale_credits_once` |
| Email из API не найден среди пользователей | Failure | Алерт отправлен, начисления нет, строки `blacksea_sales` нет, 200 | `test_blacksea_unknown_email_alerts_and_credits_nobody` |
| Email найден только без учёта регистра | Boundary | Начислено найденному пользователю | `test_blacksea_email_case_insensitive_fallback` |
| Два пользователя, различающихся регистром email | Boundary | Не начислять никому, алерт, 200 | `test_blacksea_ambiguous_email_case_alerts` |
| В теле вебхука подделан `email` (не совпадает с `sale.email` того же реального `sale_id`) | Failure | Не начислено НИКОМУ (ни адресату из тела, ни владельцу продажи), 200, залогировано как подозрительная попытка | `test_blacksea_forged_email_credits_nobody` |
| API вернул `paid:false` | Failure | Не начислять, 200 | `test_blacksea_unpaid_sale_not_credited` |
| API вернул `chargedback:true` / `refunded:true` / `partially_refunded:true` | Failure | Не начислять, 200 | `test_blacksea_refunded_sale_not_credited` |
| `sale.product_id` не равен `BLACKSEA_PRODUCT_ID` | Failure | Не начислять, WARNING, 200 | `test_blacksea_foreign_product_not_credited` |
| `quantity != 1` | Boundary | Не начислять, алерт на ручной разбор, 200 | `test_blacksea_quantity_not_one_goes_manual` |
| `price` в теле `"100"`, `sale.price` `100` | Boundary | Сверка проходит (сравнение как `int`), начисление есть | `test_blacksea_price_compared_as_int` |
| Сетевая ошибка при вызове BlackSea API | Failure | Не начислять, не 500, лог ERROR, 200 | `test_blacksea_api_network_error_no_credit_no_500` |
| Тело формы без `sale_id`/`price` или с нечисловым `price` | Boundary | 400, никаких записей в БД | `test_blacksea_malformed_form_rejected` |
| Первый вызов API отдал 401, refresh успешен, повтор успешен | Recovery | Начислено, новые токены в `app_settings` | `test_blacksea_401_refresh_then_success` |
| Повтор после refresh снова 401 | Failure | Второго refresh нет, не начислять, лог ERROR, 200 | `test_blacksea_second_401_does_not_refresh_again` |
| Два одновременных вебхука (разные `sale_id`) получают 401 одновременно (мокнутый клиент) | Concurrent | `refresh_blacksea_token` вызван РОВНО один раз; обе продажи верифицированы и начислены | `test_blacksea_concurrent_401_refreshes_once` |
| Refresh успешен, последующее начисление падает исключением | Recovery | Новые токены В БД сохранены (не откатились вместе с начислением); кредиты не начислены; строки `blacksea_sales` нет | `test_blacksea_token_refresh_survives_failed_crediting` |
| Строки `blacksea_access_token` нет в `app_settings` | Failure | 500, строка НЕ создана автоматически | `test_blacksea_missing_token_setting_does_not_insert_row` |
| Пользователь найден, но забанен | Failure | Не начислять, алерт, 200 | `test_blacksea_banned_user_not_credited` |

### 5.3. Что тестовая среда доказать НЕ может — честная граница

Тесты идут на in-memory SQLite (`server/tests/conftest.py:14` — `sqlite+aiosqlite:///:memory:`,
`StaticPool`). Отсюда:

- **`with_for_update()` в тестах не работает вообще.** Диалект SQLite вырезает конструкцию:
  `def for_update_clause(self, select, **kw): # sqlite has no "FOR UPDATE" AFAICT / return ""`
  (`sqlalchemy/dialects/sqlite/base.py:1520-1522`). Значит тесты 4.5 доказывают логику приложения
  (перечитывание значения под локом, единственность вызова refresh, бюджет повторов), но НЕ
  доказывают блокировочную семантику; она обеспечивается PostgreSQL в проде и в тестах не
  проверяется. То же относится к блокировке строки покупателя (3.7).
- **`UNIQUE(sale_id)` в SQLite работает**, поэтому тест на `IntegrityError` и на однократное
  начисление содержателен и в тестовой среде.
- Сервис работает одним процессом (in-process состояние `_notifiers` в `server/vault.py:21`,
  `_oauth_states` в `server/web_routes.py:64-65`), поэтому конкурентность здесь — параллельные
  корутины с разными сессиями и разными соединениями к БД, а не разные воркеры. Появление второго
  воркера потребует пересмотра только 4.5 (блокировка на уровне БД это переживает, in-process
  флаг бюджета — нет; он и не является механизмом корректности, только ограничителем цикла внутри
  одного запроса).

### 5.4. Критерии приёмки

1. Все тесты 5.2 зелёные.
2. В `server/blacksea.py` нет литералов `5000` и `10.00`, нет обращения к `email` из тела вебхука
   после шага 3.5, нет `GET /api/v2/sales` без `sale_id`, нет `db.begin()`.
3. `alembic upgrade` до новой ревизии проходит на GCP (явная ревизия, не `head`).
4. Обе строки токенов заведены в `app_settings` до включения вебхук-URL в настройках BlackSea.
5. Тестовая продажа на минимальную сумму: алмазы начислены, покупка видна в `/admin/purchases`
   с непустыми `package`/`usd_amount`, алерт в Telegram пришёл, повторная доставка того же вебхука
   не начислила второй раз.
