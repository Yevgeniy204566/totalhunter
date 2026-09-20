# Публикация находок Биржи 2.0 в РОЙ — План, часть 27: GET /roy/scout-finds и клиент

> Индекс, цель, архитектура, Global Constraints и карта файлов — в [`exchange-scout-roy-publication-plan-24.md`](exchange-scout-roy-publication-plan-24.md). Исполнять inline, **без субагентов** (золотое правило `CLAUDE.md` §4); код — только после одобрения плана владельцем.
> Задачи этой части: Task 3, Task 4. Части плана: [25](exchange-scout-roy-publication-plan-model-25.md) · [26](exchange-scout-roy-publication-plan-post-endpoint-26.md) · [27](exchange-scout-roy-publication-plan-read-client-27.md) · [28](exchange-scout-roy-publication-plan-web-deploy-check-28.md). Спека: `docs/superpowers/specs/exchange-scout-roy-publication-design-01.md` (файлы 01–06).

---

### Task 3: `GET /roy/scout-finds`

**Invariant:** P-09 (публичный список без hwid, новые первыми), P-13 (только находки младше 30 минут;
ровно 30:00 уже не показывается — `found_at > now − 30 мин`, contracts-03.md P-09).
**Files:** Modify `server/roy.py`; Test `server/tests/test_roy_scout.py`.
**Produces:** `GET /roy/scout-finds` → `{"finds": [{"kingdom","x","y","found_at"}, ...]}`, новые первыми.

- [ ] **Step 1: Failing tests** — дописать:

```python
@pytest.mark.asyncio
async def test_scout_finds_empty():
    r = await _get()
    assert r.status_code == 200 and r.json() == {"finds": []}


@pytest.mark.asyncio
async def test_scout_finds_response_has_no_hwid(db_session):
    db_session.add(RoyScoutFind(kingdom=7, x=1, y=2, reporter_hwid="SECRETHWID0001"))
    await db_session.commit()
    body = (await _get()).json()
    assert list(body["finds"][0].keys()) == ["kingdom", "x", "y", "found_at"]
    assert "SECRETHWID0001" not in (await _get()).text


@pytest.mark.asyncio
async def test_scout_finds_newest_first(db_session):
    now = datetime.now(timezone.utc)
    for k, mins in ((1, 10), (2, 1), (3, 5)):
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H",
                                    found_at=now - timedelta(minutes=mins)))
    await db_session.commit()
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [2, 3, 1]


@pytest.mark.asyncio
async def test_scout_finds_excludes_older_than_ttl(db_session, monkeypatch):
    """P-13, PT-15: граница детерминирована — часы roy.datetime зафиксированы (образец test_roy.py)."""
    import roy
    frozen = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    for k, age in ((1, timedelta(minutes=29, seconds=59)),
                   (2, timedelta(minutes=30)),
                   (3, timedelta(minutes=30, seconds=1))):
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H", found_at=frozen - age))
    await db_session.commit()
    # видна только запись младше 30:00; ровно 30:00 и старше — нет (found_at > now - 30 мин)
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [1]


@pytest.mark.asyncio
async def test_scout_endpoints_use_timezone_aware_utc_now(db_session, monkeypatch):
    """P-13, PT-19: now — строго aware UTC. SQLite наивное время не отвергает, прод (timestamptz) отвергнет."""
    import roy
    frozen = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    seen = []

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            seen.append(tz)
            return frozen

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y=1)).status_code == 200
    assert (await _get()).status_code == 200
    assert seen and all(tz is timezone.utc for tz in seen)


@pytest.mark.asyncio
async def test_scout_finds_returns_at_most_limit_newest(db_session, monkeypatch):
    """P-09, PT-12: не более SCOUT_FINDS_LIMIT самых новых (малый лимит подставлен для теста)."""
    import roy
    monkeypatch.setattr(roy, "SCOUT_FINDS_LIMIT", 3)
    now = datetime.now(timezone.utc)
    for k in range(1, 6):  # k=5 — самая новая
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H",
                                    found_at=now - timedelta(minutes=10 - k)))
    await db_session.commit()
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [5, 4, 3]


@pytest.mark.asyncio
async def test_scout_finds_tie_break_by_id_desc(db_session):
    """P-09, PT-12: при равном found_at более новая запись (больший id) идёт первой.
    Проверено эмпирически (sqlite3, in-memory): без ORDER BY id DESC ties отдаются в порядке
    вставки (id ASC) детерминированно, не «случайно» — поэтому поведенческий тест здесь надёжен
    и не привязан к тексту сгенерированного SQLAlchemy SQL (который ломается от рефакторинга/алиасов)."""
    now = datetime.now(timezone.utc)
    for k in (1, 2, 3):
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H", found_at=now))
    await db_session.commit()
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [3, 2, 1]
```

- [ ] **Step 2: Run** → FAIL (404/405 на `GET /roy/scout-finds`).
- [ ] **Step 3: Implement** — сразу после `scout_find` в `server/roy.py`:

```python
# ── GET /roy/scout-finds ──────────────────────────────────────────────────────

@router.get("/scout-finds")
async def scout_finds(db: AsyncSession = Depends(get_db)):
    """Публичный список находок Биржи 2.0 не старше SCOUT_FIND_TTL_MIN. hwid не отдаём."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=SCOUT_FIND_TTL_MIN)
    rows = (await db.execute(
        select(RoyScoutFind.kingdom, RoyScoutFind.x, RoyScoutFind.y, RoyScoutFind.found_at)
        .where(RoyScoutFind.found_at > cutoff)
        .order_by(RoyScoutFind.found_at.desc(), RoyScoutFind.id.desc())
        .limit(SCOUT_FINDS_LIMIT)
    )).all()
    return {"finds": [
        {"kingdom": r.kingdom, "x": r.x, "y": r.y, "found_at": r.found_at.isoformat()}
        for r in rows
    ]}
```

- [ ] **Step 4: Run** `cd server && python -m pytest tests/test_roy_scout.py tests/test_roy.py -v` → PASS. Если
  `test_scout_finds_excludes_older_than_ttl` падает из-за сравнения aware/naive datetime в SQLite — остановиться и
  разобраться (не подгонять тест): в `test_roy.py` такое сравнение с `expires_at > now` уже работает.
- [ ] **Step 5: Commit** `git add server/roy.py server/tests/test_roy_scout.py` →
  `git commit -m "feat(roy): GET /roy/scout-finds — публичный список находок Биржи 2.0"`.

---

### Task 4: Клиент `RoyClient.report_scout_find`

**Invariant:** P-06 (kingdom<=0 -> без запроса, лог), P-07 (отдельный тред, timeout 5, не блокирует), P-08 (сбой
проглатывается). **Existing:** `RoyClient.report` (`roy/roy_client.py:27-48`, не меняем) — образец треда;
`_TIMEOUT = 5` (`roy/roy_client.py:9`) — существующая константа клиента, используется во всех текущих методах
(`report`, `scan`, `idle`, `balance` и др.); Task 4 переиспользует её как есть, отдельную константу не вводит.

**Files:** Modify `roy/roy_client.py` (метод добавить после `report`); Create `test_roy_scout_client.py` (корень).
**Produces:** `RoyClient(hwid).report_scout_find(kingdom:int, x:int, y:int) -> bool` — `True`, если тред запущен;
`False`, если публикация пропущена (kingdom<=0).

- [ ] **Step 1: Failing tests** — создать `test_roy_scout_client.py`:

```python
"""Клиент публикации находок Биржи 2.0 (спека ...-roy-publication-design.md, P-06/P-07/P-08)."""
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from roy.roy_client import RoyClient


def _spy_threads():
    created = []
    def make(*a, **kw):
        t = threading.Thread(*a, **kw)
        created.append(t)
        return t
    return created, SimpleNamespace(Thread=make)


def test_skips_publish_when_kingdom_zero():
    with patch("roy.roy_client.requests.post") as post:
        assert RoyClient("HW").report_scout_find(0, 10, 20) is False
        assert RoyClient("HW").report_scout_find(-3, 10, 20) is False
    post.assert_not_called()


def test_posts_kingdom_x_y_to_scout_find():
    created, fake_threading = _spy_threads()
    resp = MagicMock(); resp.json.return_value = {"success": True}
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", return_value=resp) as post:
        assert RoyClient("HW1").report_scout_find(7, 512, 318) is True
        for t in created:
            t.join(5)
    args, kwargs = post.call_args
    assert args[0].endswith("/roy/scout-find")
    assert kwargs["json"] == {"hwid": "HW1", "kingdom": 7, "x": 512, "y": 318}
    assert kwargs["timeout"] == 5


def test_publish_does_not_block_caller():
    """P-07: медленный сервер не задерживает consumer — метод возвращается сразу."""
    created, fake_threading = _spy_threads()
    release = threading.Event()
    def slow_post(*a, **k):
        release.wait(5)
        return MagicMock()
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", side_effect=slow_post):
        t0 = time.monotonic()
        assert RoyClient("HW").report_scout_find(7, 1, 2) is True
        elapsed = time.monotonic() - t0
        release.set()
        for t in created:
            t.join(5)
    assert elapsed < 0.5


def test_publish_failure_is_swallowed():
    """P-08: сеть (ConnectionError, тот же except Exception что Timeout/битый JSON) не выбрасывает
    исключение из треда."""
    created, fake_threading = _spy_threads()
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", side_effect=ConnectionError("down")), \
         patch("threading.excepthook") as hook:
        assert RoyClient("HW").report_scout_find(7, 1, 2) is True
        for t in created:
            t.join(5)
    hook.assert_not_called()


def test_publish_rejected_response_does_not_raise():
    """P-08: сервер ответил без исключения (HTTP 500 + валидный JSON success=false) — это ДРУГАЯ ветка
    кода (не except, а `if not r.json().get("success")`), её ConnectionError-тест не покрывает."""
    created, fake_threading = _spy_threads()
    resp = MagicMock(status_code=500)
    resp.json.return_value = {"success": False}
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", return_value=resp), \
         patch("threading.excepthook") as hook:
        assert RoyClient("HW").report_scout_find(7, 1, 2) is True
        for t in created:
            t.join(5)
    hook.assert_not_called()
```

- [ ] **Step 2: Run** `python -m pytest test_roy_scout_client.py -v` (из `C:\BattleBot`) → FAIL (`AttributeError: report_scout_find`).
- [ ] **Step 3: Implement** — в `roy/roy_client.py` после метода `report`:

```python
    def report_scout_find(self, kingdom: int, x: int, y: int) -> bool:
        """Публикует находку Биржи 2.0 на сайт (раздел РОЙ). Fire-and-forget в отдельном треде,
        consumer не ждёт ответа. kingdom<=0 (поле в GUI пусто) — сервер такое не показывает,
        запрос не шлём. Возвращает True, если тред запущен."""
        if kingdom <= 0:
            print(f"[ROY] scout-find skipped: kingdom={kingdom}")
            return False

        def _send():
            try:
                r = requests.post(f"{SERVER_URL}/roy/scout-find", json={
                    "hwid": self.hwid, "kingdom": kingdom, "x": x, "y": y,
                }, timeout=_TIMEOUT)
                if not r.json().get("success"):
                    print(f"[ROY] scout-find rejected: HTTP {r.status_code}")
            except Exception as e:
                print(f"[ROY] scout-find ERROR: {e!r}")
        t = threading.Thread(target=_send)
        t.daemon = False  # как в report(): запрос должен завершиться до выхода процесса; timeout requests — 5 с на подключение и на чтение отдельно, суммарного лимита нет
        t.start()
        return True
```

- [ ] **Step 4: Run** `python -m pytest test_roy_scout_client.py -v` → 5 PASS.
- [ ] **Step 5: Commit** `git add roy/roy_client.py test_roy_scout_client.py` →
  `git commit -m "feat(roy): RoyClient.report_scout_find — клиентская публикация находки 2.0"`.

---
