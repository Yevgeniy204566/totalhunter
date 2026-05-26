"""
Tests for referral system — registration bonuses, purchase cascade,
HWID binding/unbinding, idempotency, and abuse prevention.

TDD-first. Tests that FAIL before patches:
  - test_ref_welcome_banned_inviter_invited_still_gets_50 → BUG-1 (link/verify wrong if-block)
  - test_referral_activate_*                              → BUG-2 (db.begin() → 500 on first activation)
  - test_referral_activate_mutual_cycle_blocked           → BUG-3 (no cycle detection)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from sqlalchemy import update as sa_update

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from models import User


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register(client, email, ref_code=None):
    claims = {"email": email, "name": email.split("@")[0], "sub": f"sub-{abs(hash(email))}"}
    with patch("web_routes._verify_google_token", return_value=claims):
        resp = await client.post("/web/auth/google", json={"id_token": "tok", "ref_code": ref_code})
    assert resp.status_code == 200, resp.text
    return resp.json()["jwt"]


async def _link_hwid(client, jwt, hwid):
    gen = await client.post("/web/link/generate", json={"hwid": hwid})
    code = gen.json()["code"]
    return await client.post(
        "/web/link/verify",
        json={"code": code},
        headers={"Authorization": f"Bearer {jwt}"},
    )


async def _me(client, jwt):
    resp = await client.get("/web/me", headers={"Authorization": f"Bearer {jwt}"})
    assert resp.status_code == 200
    return resp.json()


async def _activate(client, jwt, ref_code):
    return await client.post(
        "/web/referral/activate",
        params={"ref_code": ref_code},
        headers={"Authorization": f"Bearer {jwt}"},
    )


async def _reset(client, jwt):
    return await client.post("/web/hwid/reset", headers={"Authorization": f"Bearer {jwt}"})


# ── HIGH: Trial bonus ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trial_bonus_granted_on_first_hwid_link():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "trial@ref.test")
        assert (await _me(c, jwt))["credits"] == 0

        resp = await _link_hwid(c, jwt, "HWID0000TRIAL001")
        assert resp.status_code == 200

        me = await _me(c, jwt)
        assert me["credits"] == 100
        assert me["trial_used"] is True


# ── HIGH: ref_welcome via link/verify ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_ref_welcome_via_link_verify():
    """Register with ref_code → link HWID → inviter +100, invited +50."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        inviter_jwt = await _register(c, "inviter@ref.test")
        code = (await _me(c, inviter_jwt))["ref_code"]

        invited_jwt = await _register(c, "invited@ref.test", ref_code=code)
        await _link_hwid(c, invited_jwt, "HWID0000REFWELC1")

        assert (await _me(c, invited_jwt))["ref_credits"] == 50
        assert (await _me(c, inviter_jwt))["ref_credits"] == 100


@pytest.mark.asyncio
async def test_no_ref_welcome_without_ref_code():
    """Register without code → link HWID → no ref_credits, trial still granted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "noref@ref.test")
        await _link_hwid(c, jwt, "HWID0000NOREF001")
        me = await _me(c, jwt)
        assert me["ref_credits"] == 0
        assert me["credits"] == 100


# ── HIGH: Idempotency — double-pay prevention ─────────────────────────────────
# NOTE: tests below call /referral/activate which has BUG-2 (db.begin() → 500).
# They FAIL until BUG-2 is fixed in web_routes.py.

@pytest.mark.asyncio
async def test_ref_bonus_not_doubled_hwid_first_then_activate():
    """Link HWID (no code) → activate code → no bonus (ref_bonus_claimed=True from link/verify).
    FAILS before BUG-2 fix (db.begin() → InvalidRequestError)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        inviter_jwt = await _register(c, "inv_hf@ref.test")
        code = (await _me(c, inviter_jwt))["ref_code"]

        invited_jwt = await _register(c, "invited_hf@ref.test")
        await _link_hwid(c, invited_jwt, "HWID0000HFIRST01")

        resp = await _activate(c, invited_jwt, code)
        assert resp.status_code == 200
        assert resp.json()["success"] is True  # code was saved but no bonus paid

        assert (await _me(c, invited_jwt))["ref_credits"] == 0
        assert (await _me(c, inviter_jwt))["ref_credits"] == 0


@pytest.mark.asyncio
async def test_ref_bonus_not_doubled_activate_first_then_link():
    """Activate code (no HWID) → link HWID → exactly one payout.
    FAILS before BUG-2 fix."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        inviter_jwt = await _register(c, "inv_af@ref.test")
        code = (await _me(c, inviter_jwt))["ref_code"]

        invited_jwt = await _register(c, "invited_af@ref.test")
        resp = await _activate(c, invited_jwt, code)
        assert resp.status_code == 200          # bonus deferred — no HWID yet
        await _link_hwid(c, invited_jwt, "HWID0000AFIRST01")

        assert (await _me(c, invited_jwt))["ref_credits"] == 50
        assert (await _me(c, inviter_jwt))["ref_credits"] == 100


@pytest.mark.asyncio
async def test_referral_activate_with_hwid_pays_immediately(db_session):
    """User has HWID already (ref_bonus_claimed=False) → /activate pays both immediately.
    FAILS before BUG-2 fix."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        inviter_jwt = await _register(c, "inv_imm@ref.test")
        code = (await _me(c, inviter_jwt))["ref_code"]

        invited_jwt = await _register(c, "invited_imm@ref.test")

        # Simulate user who has HWID but ref_bonus_claimed is still False
        # (legacy user or merged account where trial block was skipped)
        await db_session.execute(
            sa_update(User)
            .where(User.email == "invited_imm@ref.test")
            .values(hwid="DIRECTHWID000001")
        )
        await db_session.commit()

        resp = await _activate(c, invited_jwt, code)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        assert (await _me(c, invited_jwt))["ref_credits"] == 50
        assert (await _me(c, inviter_jwt))["ref_credits"] == 100


# ── HIGH: HWID abuse prevention ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_hwid_blocked_after_reset():
    """User1 links HWID → resets → User2 links same HWID → blocked (no trial, hwid_duplicate_blocked)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt1 = await _register(c, "first_hwid@ref.test")
        await _link_hwid(c, jwt1, "HWID0000DUPL0001")
        await _reset(c, jwt1)  # HWID is now None but HwidHistory row remains

        jwt2 = await _register(c, "second_hwid@ref.test")
        resp = await _link_hwid(c, jwt2, "HWID0000DUPL0001")
        assert resp.status_code == 200

        me2 = await _me(c, jwt2)
        assert me2["credits"] == 0       # hwid_is_new=False → no trial
        assert me2["ref_credits"] == 0

        txns = await c.get("/web/transactions", headers={"Authorization": f"Bearer {jwt2}"})
        types = [t["type"] for t in txns.json()["items"]]
        assert "hwid_duplicate_blocked" in types


@pytest.mark.asyncio
async def test_hwid_reset_cooldown_enforced():
    """Link → reset → re-link new HWID → immediately reset → 429."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "cooldown@ref.test")
        await _link_hwid(c, jwt, "HWID0000COOL0001")

        r1 = await _reset(c, jwt)
        assert r1.status_code == 200

        # Re-link a different HWID so there's something to reset
        await _link_hwid(c, jwt, "HWID0000COOL0002")

        # Cooldown: hwid_reset_at was just set → 429
        r2 = await _reset(c, jwt)
        assert r2.status_code == 429
        assert "next_reset_available" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_trial_not_repeated_after_hwid_reset_and_relink():
    """Link HWID → reset → re-link same HWID → no second trial (HwidHistory blocks)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "repeat_trial@ref.test")
        await _link_hwid(c, jwt, "HWID0000REPEA001")
        assert (await _me(c, jwt))["credits"] == 100

        await _reset(c, jwt)
        await _link_hwid(c, jwt, "HWID0000REPEA001")

        assert (await _me(c, jwt))["credits"] == 100  # still 100, no second +100


@pytest.mark.asyncio
async def test_trial_not_repeated_on_new_hwid_after_reset():
    """Link HWID-A → reset → link HWID-B → no trial (trial_used persists on user row)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "new_hwid@ref.test")
        await _link_hwid(c, jwt, "HWID0000NEWHW0A1")
        assert (await _me(c, jwt))["credits"] == 100

        await _reset(c, jwt)
        await _link_hwid(c, jwt, "HWID0000NEWHW0B1")

        assert (await _me(c, jwt))["credits"] == 100  # trial_used=True blocks second grant


# ── BUG-1: Banned inviter — invited still gets +50 (FAILS before fix) ─────────

@pytest.mark.asyncio
async def test_ref_welcome_banned_inviter_invited_still_gets_50(db_session):
    """
    BUG-1 (web_routes.py:433): Both +50 and +100 are inside `if not referrer.is_banned`.
    If inviter is banned, invited MUST still get +50 — it's their bonus, not inviter's.
    FAILS before fix: move `web_user.ref_credits += 50` outside the banned check.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        inviter_jwt = await _register(c, "banned_inv@ref.test")
        code = (await _me(c, inviter_jwt))["ref_code"]

        await db_session.execute(
            sa_update(User).where(User.email == "banned_inv@ref.test").values(is_banned=True)
        )
        await db_session.commit()

        invited_jwt = await _register(c, "invited_bug1@ref.test", ref_code=code)
        await _link_hwid(c, invited_jwt, "HWID0000BUG10001")

        assert (await _me(c, invited_jwt))["ref_credits"] == 50  # FAILS before BUG-1 fix

    # Banned user gets 401 from /me — check ref_credits directly via DB
    from sqlalchemy import select as sa_select
    row = await db_session.execute(
        sa_select(User.ref_credits).where(User.email == "banned_inv@ref.test")
    )
    inviter_ref_credits = row.scalar_one_or_none()
    assert inviter_ref_credits == 0  # banned inviter gets nothing


# ── BUG-3: Mutual cycle detection (FAILS before fix) ─────────────────────────

@pytest.mark.asyncio
async def test_referral_activate_mutual_cycle_blocked():
    """
    BUG-3: A and B both have no inviter.
    A activates B's code → A.invited_by_id = B.
    B activates A's code → creates cycle A→B AND B→A.
    Must be blocked. FAILS before BUG-2 fix (db.begin) AND before cycle-check added.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt_a = await _register(c, "cycle_a@ref.test")
        code_a = (await _me(c, jwt_a))["ref_code"]

        jwt_b = await _register(c, "cycle_b@ref.test")  # no ref_code at signup
        code_b = (await _me(c, jwt_b))["ref_code"]

        # A activates B's code first
        r1 = await _activate(c, jwt_a, code_b)
        assert r1.status_code == 200
        assert r1.json()["success"] is True

        # B tries to activate A's code → would create cycle
        r2 = await _activate(c, jwt_b, code_a)
        assert r2.json()["success"] is False  # FAILS before cycle-check fix


# ── MEDIUM: Guard rails ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_referral_activate_own_code_blocked():
    """FAILS before BUG-2 fix (db.begin → 500), then passes after fix."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "owncode@ref.test")
        code = (await _me(c, jwt))["ref_code"]
        resp = await _activate(c, jwt, code)
        assert resp.status_code == 200
        assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_referral_activate_twice_blocked():
    """FAILS before BUG-2 fix (db.begin → 500), then passes after fix."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        inviter_jwt = await _register(c, "inv_2x@ref.test")
        code = (await _me(c, inviter_jwt))["ref_code"]
        invited_jwt = await _register(c, "invited_2x@ref.test")

        r1 = await _activate(c, invited_jwt, code)
        r2 = await _activate(c, invited_jwt, code)

        assert r1.json()["success"] is True
        assert r2.json()["success"] is False


@pytest.mark.asyncio
async def test_hwid_reset_first_time_no_cooldown():
    """hwid_reset_at=NULL → first reset always allowed without 7-day wait."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "first_reset@ref.test")
        await _link_hwid(c, jwt, "HWID0000RESET001")
        resp = await _reset(c, jwt)
        assert resp.status_code == 200
        assert (await _me(c, jwt))["hwid"] is None


@pytest.mark.asyncio
async def test_hwid_reset_allowed_after_7_days(db_session):
    """hwid_reset_at = 8 days ago → second reset is allowed (no 429)."""
    from datetime import datetime, timedelta
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        jwt = await _register(c, "reset7d@ref.test")
        await _link_hwid(c, jwt, "HWID0000RST7D001")

        r1 = await _reset(c, jwt)
        assert r1.status_code == 200

        # Backdate hwid_reset_at to 8 days ago
        await db_session.execute(
            sa_update(User)
            .where(User.email == "reset7d@ref.test")
            .values(hwid_reset_at=datetime.utcnow() - timedelta(days=8))
        )
        await db_session.commit()

        # Re-link so there's something to reset
        await _link_hwid(c, jwt, "HWID0000RST7D002")

        r2 = await _reset(c, jwt)
        assert r2.status_code == 200
        assert (await _me(c, jwt))["hwid"] is None
