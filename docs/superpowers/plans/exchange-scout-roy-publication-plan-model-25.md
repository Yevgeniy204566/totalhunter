# Публикация находок Биржи 2.0 в РОЙ — План, часть 25: модель и миграция

> Индекс, цель, архитектура, Global Constraints и карта файлов — в [`exchange-scout-roy-publication-plan-24.md`](exchange-scout-roy-publication-plan-24.md). Исполнять inline, **без субагентов** (золотое правило `CLAUDE.md` §4); код — только после одобрения плана владельцем.
> Задачи этой части: Task 1. Части плана: [25](exchange-scout-roy-publication-plan-model-25.md) · [26](exchange-scout-roy-publication-plan-post-endpoint-26.md) · [27](exchange-scout-roy-publication-plan-read-client-27.md) · [28](exchange-scout-roy-publication-plan-web-deploy-check-28.md). Спека: `docs/superpowers/specs/exchange-scout-roy-publication-design-01.md` (файлы 01–06).

---

### Task 1: Модель `RoyScoutFind` и миграция

**Invariant:** P-03 (отдельная таблица), P-02 (только kingdom/x/y/время + hwid для трассировки). **Existing:**
`RoyPool` (`server/models.py:267-289`) — образец типов; миграция-образец `b1a2c3k4s5e6_add_blacksea_sales.py`.

**Files:**
- Modify: `server/models.py` (вставить после класса `RoyKingdomMember`, перед баннером `# Orders — payment records`)
- Create: `server/alembic/versions/s3c4o5u6t7f8_add_roy_scout_finds.py`
- Test: `server/tests/test_roy_scout.py`

**Produces:** `models.RoyScoutFind(id, kingdom, x, y, reporter_hwid, found_at)`.

- [ ] **Step 1: Failing test** — создать `server/tests/test_roy_scout.py`:

```python
"""Публикация находок Биржи 2.0 в РОЙ (спека exchange-scout-roy-publication-design-01.md)."""
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from models import RoyPool, RoyScoutFind, User


async def _make_user(db, hwid="SCOUTUSER00001", banned=False):
    db.add(User(hwid=hwid, credits=10, ref_code=hwid[-8:], is_banned=banned))
    await db.commit()


async def _post(**payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post("/roy/scout-find", json=payload)


async def _get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.get("/roy/scout-finds")


@pytest.mark.asyncio
async def test_scout_find_model_roundtrip(db_session):
    db_session.add(RoyScoutFind(kingdom=7, x=512, y=318, reporter_hwid="SCOUTUSER00001"))
    await db_session.commit()
    row = (await db_session.execute(select(RoyScoutFind))).scalar_one()
    assert (row.kingdom, row.x, row.y) == (7, 512, 318)
    assert row.found_at is not None


@pytest.mark.asyncio
async def test_scout_find_found_at_is_indexed():
    """PT-20, P-13: DELETE/SELECT по found_at не должны сканировать всю таблицу."""
    indexed = {c.name for idx in RoyScoutFind.__table__.indexes for c in idx.columns}
    assert {"found_at", "kingdom"} <= indexed
```

- [ ] **Step 2: Run** `cd server && python -m pytest tests/test_roy_scout.py::test_scout_find_model_roundtrip -v` → FAIL
  (`ImportError: cannot import name 'RoyScoutFind'`).

- [ ] **Step 3: Model** — вставить в `server/models.py` после `RoyKingdomMember`:

```python
class RoyScoutFind(Base):
    """
    Находка Биржи 2.0 (Exchange Scout), выложенная на сайт в разделе РОЙ.
    x, y — позиция экрана бота в момент кадра (OCR), НЕ точные координаты биржи.
    kingdom вводит участник добровольно. Живёт SCOUT_FIND_TTL_MIN минут (roy.py).
    reporter_hwid наружу не отдаётся. Без UNIQUE: дедупликация не нужна (решение владельца).
    """
    __tablename__ = "roy_scout_finds"

    id            = Column(Integer, primary_key=True)
    kingdom       = Column(Integer, nullable=False, index=True)
    x             = Column(Integer, nullable=False)
    y             = Column(Integer, nullable=False)
    reporter_hwid = Column(String(16), nullable=False)
    found_at      = Column(TIMESTAMP(timezone=True), nullable=False,
                           server_default=func.now(), index=True)
```

- [ ] **Step 4: Migration** — создать `server/alembic/versions/s3c4o5u6t7f8_add_roy_scout_finds.py`:

```python
"""add_roy_scout_finds

Revision ID: s3c4o5u6t7f8
Revises: b1a2c3k4s5e6
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa


revision = 's3c4o5u6t7f8'
down_revision = 'b1a2c3k4s5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roy_scout_finds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kingdom', sa.Integer(), nullable=False),
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('reporter_hwid', sa.String(16), nullable=False),
        sa.Column('found_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roy_scout_finds')),
    )
    op.create_index(op.f('ix_roy_scout_finds_kingdom'), 'roy_scout_finds', ['kingdom'])
    op.create_index(op.f('ix_roy_scout_finds_found_at'), 'roy_scout_finds', ['found_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_roy_scout_finds_found_at'), table_name='roy_scout_finds')
    op.drop_index(op.f('ix_roy_scout_finds_kingdom'), table_name='roy_scout_finds')
    op.drop_table('roy_scout_finds')
```

- [ ] **Step 5: Run** тест из шага 2 → PASS. Проверить единственный head миграций:
  выполнить из `C:\BattleBot`:

```bash
python - <<'PY'
import re, glob
revs, downs = {}, set()
for f in glob.glob('server/alembic/versions/*.py'):
    s = open(f, encoding='utf-8').read()
    r = re.search(r"^revision(?:\s*:\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", s, re.M)
    d = re.search(r"^down_revision[^=]*=\s*(.+)$", s, re.M)
    if r: revs[r.group(1)] = f
    if d: downs.update(re.findall(r"['\"]([^'\"]+)['\"]", d.group(1)))
print([revs[k] for k in revs if k not in downs])
PY
```

  Ожидание: список из одного файла `s3c4o5u6t7f8_add_roy_scout_finds.py`.
- [ ] **Step 6: Commit** `git add server/models.py server/alembic/versions/s3c4o5u6t7f8_add_roy_scout_finds.py server/tests/test_roy_scout.py`
  → `git commit -m "feat(roy): таблица roy_scout_finds для находок Биржи 2.0"`.

---
