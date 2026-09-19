# Публикация находок Биржи 2.0 в РОЙ — План, часть 12b: POST /roy/scout-find

> Индекс, цель, архитектура, Global Constraints и карта файлов — в [`exchange-scout-roy-publication-plan-12.md`](exchange-scout-roy-publication-plan-12.md). Исполнять inline, **без субагентов** (золотое правило `CLAUDE.md` §4); код — только после одобрения плана владельцем.
> Задачи этой части: Task 2. Части плана: [12a](exchange-scout-roy-publication-plan-model-12a.md) · [12b](exchange-scout-roy-publication-plan-post-endpoint-12b.md) · [12c](exchange-scout-roy-publication-plan-read-client-12c.md) · [12d](exchange-scout-roy-publication-plan-web-deploy-check-12d.md). Спека: `docs/superpowers/specs/exchange-scout-roy-publication-design-1.md` (части 1a–1e).

---

### Task 2: `POST /roy/scout-find`

**Invariant:** P-02, P-03, P-04, P-05, P-13 (очистка при вставке). **Existing:** `/roy/report` (`server/roy.py:244-294`, НЕ трогаем);
проверка пользователя — образец `server/main.py:324-332`; `async with db.begin()` — `roy.py:265`.

**Files:** Modify `server/roy.py`; Test `server/tests/test_roy_scout.py`.
**Consumes:** `RoyScoutFind` (Task 1). **Produces:** `POST /roy/scout-find` тело `{hwid:str, kingdom:int>=1, x:int, y:int}`
→ `{"success": true}`; 404 `User not found`, 403 `Banned`, 422 при неверных типах; константа `roy.SCOUT_FIND_TTL_MIN = 20`.

- [ ] **Step 1: Failing tests** — дописать в `server/tests/test_roy_scout.py`:

```python
@pytest.mark.asyncio
async def test_scout_find_creates_row(db_session):
    await _make_user(db_session)
    r = await _post(hwid="SCOUTUSER00001", kingdom=7, x=512, y=318)
    assert r.status_code == 200 and r.json()["success"] is True
    row = (await db_session.execute(select(RoyScoutFind))).scalar_one()
    assert (row.kingdom, row.x, row.y, row.reporter_hwid) == (7, 512, 318, "SCOUTUSER00001")


@pytest.mark.asyncio
async def test_scout_find_validates_xy_type_and_integer_range(db_session):
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x="abc", y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y="<b>")).status_code == 422
    # StrictInt: приведение типов запрещено (P-02, PA-2)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x="123", y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=True, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1.5, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom="7", x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=-5, y=0)).status_code == 200
    # P-02/PA-11: границы 32-битного Integer колонки
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=2147483647, y=-2147483648)).status_code == 200
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=2147483648, y=0)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=0, y=-2147483649)).status_code == 422


@pytest.mark.asyncio
async def test_scout_find_kingdom_lt_1_rejected(db_session):
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=0, x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=-1, x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=1, x=1, y=1)).status_code == 200
    # верхняя граница 32-битного Integer колонки (P-02, PA-11)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=2147483647, x=1, y=1)).status_code == 200
    assert (await _post(hwid="SCOUTUSER00001", kingdom=2147483648, x=1, y=1)).status_code == 422
    # строгий int для kingdom (P-05, PT-08)
    assert (await _post(hwid="SCOUTUSER00001", kingdom="1", x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=1.0, x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=True, x=1, y=1)).status_code == 422


@pytest.mark.asyncio
async def test_scout_find_unknown_hwid_404():
    assert (await _post(hwid="NOSUCHHWID00001", kingdom=7, x=1, y=1)).status_code == 404


@pytest.mark.asyncio
async def test_scout_find_hwid_longer_than_16_404(db_session):
    """PT-07/2.6a: hwid длиннее колонки не найден среди users -> 404, вставки нет."""
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001EXTRA", kingdom=7, x=1, y=1)).status_code == 404
    assert (await db_session.execute(select(func.count(RoyScoutFind.id)))).scalar_one() == 0


@pytest.mark.asyncio
async def test_scout_find_banned_403(db_session):
    await _make_user(db_session, banned=True)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y=1)).status_code == 403
    assert (await db_session.execute(select(func.count(RoyScoutFind.id)))).scalar_one() == 0


@pytest.mark.asyncio
async def test_scout_find_allows_repeated_identical_posts(db_session):
    """P-04: два одинаковых вызова подряд без паузы -> две строки (ни лимита, ни дедупа)."""
    await _make_user(db_session)
    for _ in range(2):
        assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=10, y=20)).status_code == 200
    assert (await db_session.execute(select(func.count(RoyScoutFind.id)))).scalar_one() == 2


@pytest.mark.asyncio
async def test_scout_find_does_not_touch_roy_pool(db_session, monkeypatch):
    """P-03/P-12: /roy/report, roy_pool, _report_rate и Telegram не задействованы."""
    import roy
    def _boom(*a, **k):
        raise AssertionError("send_telegram_alert must not be called")
    monkeypatch.setattr(roy, "send_telegram_alert", _boom)
    roy._report_rate.clear()
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y=1)).status_code == 200
    assert (await db_session.execute(select(func.count(RoyPool.id)))).scalar_one() == 0
    assert roy._report_rate == {}


@pytest.mark.asyncio
async def test_scout_find_insert_deletes_expired(db_session):
    """P-13: вставка удаляет находки старше срока жизни, свежие остаются."""
    await _make_user(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(RoyScoutFind(kingdom=1, x=1, y=1, reporter_hwid="OLD", found_at=now - timedelta(minutes=21)))
    db_session.add(RoyScoutFind(kingdom=2, x=2, y=2, reporter_hwid="FRESH", found_at=now - timedelta(minutes=5)))
    await db_session.commit()
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=3, y=3)).status_code == 200
    hwids = sorted((await db_session.execute(select(RoyScoutFind.reporter_hwid))).scalars().all())
    assert hwids == ["FRESH", "SCOUTUSER00001"]
```

- [ ] **Step 2: Run** `cd server && python -m pytest tests/test_roy_scout.py -v` → новые тесты FAIL (404 на `/roy/scout-find`).

- [ ] **Step 3: Implement** в `server/roy.py`:
  (а) импорты: `from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException`;
  `from pydantic import BaseModel, Field, StrictInt`; `from sqlalchemy import delete, select`;
  `from models import RoyBalance, RoyKingdomMember, RoyKingdomStatus, RoyPool, RoyScoutFind, User`.
  (б) после строки `SESSION_TTL_SEC   = 300 ...` добавить:
  `SCOUT_FIND_TTL_MIN = 20   # находка Биржи 2.0 живёт на сайте 20 минут (своя константа, не POOL_TTL_MIN)`.
  Рядом добавить `SCOUT_FINDS_LIMIT = 500   # не более 500 самых новых находок в GET /roy/scout-finds (P-09)`.
  (в) после класса `RegisterRequest` добавить:

```python
class ScoutFindRequest(BaseModel):
    hwid:    str
    kingdom: StrictInt = Field(ge=1, le=2147483647)   # сервер показывает только k > 0 (см. _kingdoms_payload)
    x:       StrictInt = Field(ge=-2147483648, le=2147483647)   # диапазон 32-битного Integer колонки (P-02, PA-11)
    y:       StrictInt = Field(ge=-2147483648, le=2147483647)
```

  (г) после функции `report_exchange` (перед `# ── POST /roy/scan`) добавить:

```python
# ── POST /roy/scout-find ──────────────────────────────────────────────────────

@router.post("/scout-find")
async def scout_find(req: ScoutFindRequest, db: AsyncSession = Depends(get_db)):
    """
    Находка Биржи 2.0 (Exchange Scout). Отдельно от /report и roy_pool: боты 1.0 эти
    данные не видят. Без rate limit и без дедупа (решение владельца). Каждая вставка
    удаляет находки старше SCOUT_FIND_TTL_MIN — общий _cleanup_loop не трогаем.
    """
    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=SCOUT_FIND_TTL_MIN)
    async with db.begin():
        user = (await db.execute(
            select(User).where(User.hwid == req.hwid)
        )).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_banned:
            raise HTTPException(status_code=403, detail="Banned")
        await db.execute(delete(RoyScoutFind).where(RoyScoutFind.found_at <= cutoff))
        db.add(RoyScoutFind(kingdom=req.kingdom, x=req.x, y=req.y,
                            reporter_hwid=req.hwid, found_at=now))
    return {"success": True}
```

- [ ] **Step 4: Run** `cd server && python -m pytest tests/test_roy_scout.py tests/test_roy.py -v` → всё PASS
  (`test_roy.py` — регрессия 1.0, PT-14).
- [ ] **Step 5: Commit** `git add server/roy.py server/tests/test_roy_scout.py` →
  `git commit -m "feat(roy): POST /roy/scout-find — публикация находки Биржи 2.0"`.

---
