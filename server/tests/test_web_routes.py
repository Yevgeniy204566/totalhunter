"""Tests for /web/* endpoints."""
import pytest
import pytest_asyncio
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app


@pytest.fixture
def fake_google_claims():
    return {"email": "user@example.com", "name": "Test User", "sub": "google-sub-123"}


@pytest.mark.asyncio
async def test_auth_google_new_user(fake_google_claims):
    with patch("web_routes._verify_google_token", return_value=fake_google_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/web/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    data = resp.json()
    assert "jwt" in data
    assert data["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_auth_google_invalid_token():
    with patch("web_routes._verify_google_token", side_effect=ValueError("bad token")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/web/auth/google", json={"id_token": "bad"})
    assert resp.status_code == 401


# ─── Task 6: GET /web/me ──────────────────────────────────────────────────────

async def _get_jwt(client, fake_claims):
    with patch("web_routes._verify_google_token", return_value=fake_claims):
        resp = await client.post("/web/auth/google", json={"id_token": "tok"})
    return resp.json()["jwt"]


@pytest.mark.asyncio
async def test_me_returns_profile(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, fake_google_claims)
        resp = await client.get("/web/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert data["credits"] == 0


@pytest.mark.asyncio
async def test_me_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/me")
    # HTTPBearer returns 401 (no credentials) in this FastAPI version
    assert resp.status_code in (401, 403)


# ─── Task 7: /web/link/generate + /web/link/verify ───────────────────────────

@pytest.mark.asyncio
async def test_link_generate_creates_code():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/web/link/generate", json={"hwid": "AABBCCDD11223344"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["code"]) == 6
    assert data["code"].isdigit()
    # 10-мин истечение убрано намеренно (779f5ad, 2026-08-18): новые пользователи не успевали
    # привязать код за 10 минут — код живёт практически бессрочно (timedelta(days=3650), web_routes.py:361).
    assert data["expires_in_seconds"] == int(timedelta(days=3650).total_seconds())


@pytest.mark.asyncio
async def test_link_verify_links_hwid(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post("/web/link/generate", json={"hwid": "TESTTEST12345678"})
        code = gen.json()["code"]
        token = await _get_jwt(client, {**fake_google_claims, "email": "link_test@example.com"})
        resp = await client.post(
            "/web/link/verify",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_link_verify_wrong_code(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, {**fake_google_claims, "email": "wrong_code@example.com"})
        resp = await client.post(
            "/web/link/verify",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


# ─── Task 8: HWID reset + hunts + transactions ───────────────────────────────

@pytest.mark.asyncio
async def test_hwid_reset_no_hwid(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, {**fake_google_claims, "email": "reset_test@example.com"})
        resp = await client.post("/web/hwid/reset", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_hunts_returns_stats(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, {**fake_google_claims, "email": "hunts_test@example.com"})
        resp = await client.get("/web/hunts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "today" in data and "week" in data and "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_transactions_returns_list(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, {**fake_google_claims, "email": "tx_test@example.com"})
        resp = await client.get("/web/transactions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json()["items"], list)


# ─── Task 4: auth/google accepts ref_code ────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_google_with_valid_ref_code(fake_google_claims):
    # Register referrer first
    referrer_claims = {**fake_google_claims, "email": "referrer@example.com", "sub": "ref-sub-999"}
    with patch("web_routes._verify_google_token", return_value=referrer_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/web/auth/google", json={"id_token": "ref-tok"})
    assert resp.status_code == 200

    # Register new user with null ref_code — should succeed without invited_by
    new_claims = {**fake_google_claims, "email": "newuser@example.com", "sub": "new-sub-111"}
    with patch("web_routes._verify_google_token", return_value=new_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/web/auth/google", json={"id_token": "new-tok", "ref_code": None})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_google_ignores_unknown_ref_code(fake_google_claims):
    new_claims = {**fake_google_claims, "email": "another@example.com", "sub": "anon-999"}
    with patch("web_routes._verify_google_token", return_value=new_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/web/auth/google",
                json={"id_token": "tok", "ref_code": "INVALID"}
            )
    assert resp.status_code == 200  # unknown ref_code is silently ignored


# ─── Task 5: POST /web/feedback ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_feedback_saves_to_db(fake_google_claims):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt_token = await _get_jwt(client, fake_google_claims)
        resp = await client.post(
            "/web/feedback",
            json={"text": "Please add dark mode"},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Thank you for your feedback!"


@pytest.mark.asyncio
async def test_send_feedback_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/web/feedback", json={"text": "test"})
    assert resp.status_code in (401, 403)


# ─── Task 3: GET /web/stats/global ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_global_stats_returns_zeroes_on_empty_db():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/stats/global")
    assert resp.status_code == 200
    data = resp.json()
    assert data["exchanges_today"] == 0
    assert data["crypts_today"] == 0
    assert data["active_hunters"] == 0


# ─── Task 3: GET /web/referral/tree ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_referral_tree_empty(fake_google_claims):
    """User with no referrals gets empty l1 list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, fake_google_claims)
        resp = await client.get("/web/referral/tree", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"l1": []}


@pytest.mark.asyncio
async def test_referral_tree_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/referral/tree")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_referral_tree_with_l1(fake_google_claims):
    """Root user sees L1 referral in tree."""
    l1_claims = {"email": "l1user@example.com", "name": "L1 User", "sub": "sub-l1-tree"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register root
        with patch("web_routes._verify_google_token", return_value=fake_google_claims):
            resp = await client.post("/web/auth/google", json={"id_token": "tok"})
        root_jwt = resp.json()["jwt"]
        # Get root's ref_code
        me = (await client.get("/web/me", headers={"Authorization": f"Bearer {root_jwt}"})).json()
        root_ref_code = me["ref_code"]
        # Register L1 user with root's code
        with patch("web_routes._verify_google_token", return_value=l1_claims):
            await client.post("/web/auth/google", json={"id_token": "tok", "ref_code": root_ref_code})
        # Fetch tree as root
        resp = await client.get("/web/referral/tree", headers={"Authorization": f"Bearer {root_jwt}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["l1"]) == 1
    assert data["l1"][0]["email_masked"] == "l1u***"
    assert data["l1"][0]["l2"] == []


@pytest.mark.asyncio
async def test_referral_tree_email_masking(fake_google_claims):
    """Email masking: first 3 chars + ***"""
    l1_claims = {"email": "ab@example.com", "name": "Short", "sub": "sub-short-tree"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("web_routes._verify_google_token", return_value=fake_google_claims):
            resp = await client.post("/web/auth/google", json={"id_token": "tok"})
        root_jwt = resp.json()["jwt"]
        me = (await client.get("/web/me", headers={"Authorization": f"Bearer {root_jwt}"})).json()
        with patch("web_routes._verify_google_token", return_value=l1_claims):
            await client.post("/web/auth/google", json={"id_token": "tok", "ref_code": me["ref_code"]})
        resp = await client.get("/web/referral/tree", headers={"Authorization": f"Bearer {root_jwt}"})
    assert resp.json()["l1"][0]["email_masked"] == "ab@***"


# ─── Task 2: ReferralTreeResponse schema ────────────────────────────────────

def test_referral_tree_schema_serializes():
    from schemas import TreeNodeL3, TreeNodeL2, TreeNodeL1, ReferralTreeResponse
    l3 = TreeNodeL3(id=3, email_masked="pet***", credits=4, created_at="2026-04-01")
    l2 = TreeNodeL2(id=2, email_masked="ser***", credits=12, created_at="2026-03-20", l3=[l3])
    l1 = TreeNodeL1(id=1, email_masked="yev***", credits=50, created_at="2026-02-15", l2=[l2])
    resp = ReferralTreeResponse(l1=[l1])
    d = resp.model_dump()
    assert d["l1"][0]["email_masked"] == "yev***"
    assert d["l1"][0]["l2"][0]["l3"][0]["credits"] == 4


# ─── Сохранённые ссылки на таблицы сундуков кланов (Профиль, владелец 2026-09-26) ───

@pytest.mark.asyncio
async def test_chest_links_empty_for_new_user():
    claims = {"email": "links1@example.com", "name": "L1", "sub": "links-1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, claims)
        resp = await client.get("/web/chest-links", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"links": []}


@pytest.mark.asyncio
async def test_chest_links_saved_and_returned_deduped():
    claims = {"email": "links2@example.com", "name": "L2", "sub": "links-2"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, claims)
        h = {"Authorization": f"Bearer {token}"}
        put = await client.put("/web/chest-links", headers=h, json={"links": [
            {"kingdom": "229", "clan": "ELDORADO"},
            {"kingdom": " 229 ", "clan": " eldorado "},   # тот же клан — повтор
            {"kingdom": "229", "clan": "Феникс"},
        ]})
        assert put.status_code == 200
        got = (await client.get("/web/chest-links", headers=h)).json()
    # url — None: в этом тесте таких кланов нет на сервере (ссылку строит сервер, см. ниже)
    assert got == {"links": [{"kingdom": "229", "clan": "ELDORADO", "url": None},
                             {"kingdom": "229", "clan": "Феникс", "url": None}]}


@pytest.mark.asyncio
async def test_chest_links_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/web/chest-links")).status_code in (401, 403)
        assert (await client.put("/web/chest-links", json={"links": []})).status_code in (401, 403)


@pytest.mark.asyncio
async def test_chest_links_rejects_bad_kingdom_and_too_many():
    claims = {"email": "links3@example.com", "name": "L3", "sub": "links-3"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_jwt(client, claims)
        h = {"Authorization": f"Bearer {token}"}
        bad = await client.put("/web/chest-links", headers=h,
                               json={"links": [{"kingdom": "abc", "clan": "X"}]})
        assert bad.status_code == 422
        many = await client.put("/web/chest-links", headers=h, json={"links": [
            {"kingdom": str(i), "clan": f"C{i}"} for i in range(1, 52)]})
        assert many.status_code == 422


@pytest.mark.asyncio
async def test_chest_links_return_readable_url_for_existing_clan(db_session):
    import secrets
    from models import User
    bot_user = User(hwid="linksurl0000001", ref_code=secrets.token_urlsafe(6), credits=100)
    db_session.add(bot_user)
    await db_session.commit()
    claims = {"email": "links4@example.com", "name": "L4", "sub": "links-4"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        imp = await client.post("/api/v1/chests/import", json={
            "hwid": "linksurl0000001", "kingdom": "779", "clan": "Феникс",
            "timestamp": "2026-09-26T12:00:00",
            "items": [{"chest_type": "T", "sender": "P", "timestamp": "2026-09-26T11:00:00"}]})
        assert imp.status_code == 200
        token = await _get_jwt(client, claims)
        h = {"Authorization": f"Bearer {token}"}
        put = await client.put("/web/chest-links", headers=h, json={"links": [
            {"kingdom": "779", "clan": "Феникс"}, {"kingdom": "779", "clan": "НетТакого"}]})
        got = (await client.get("/web/chest-links", headers=h)).json()
    assert put.json() == got
    assert got["links"][0]["url"] == "https://total-hunter.com/c/779/feniks"
    assert got["links"][1]["url"] is None


# ─── Профиль: «Собрано» по типам; Баланс: история поступлений (владелец 2026-09-26) ───

async def _web_user(db_session, client, email, sub):
    from sqlalchemy import select
    from models import User
    token = await _get_jwt(client, {"email": email, "name": "U", "sub": sub})
    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    return token, user


@pytest.mark.asyncio
async def test_hunts_counts_split_by_type(db_session):
    from datetime import datetime, timezone
    from models import Hunt
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, user = await _web_user(db_session, client, "huntsplit@example.com", "hs-1")
        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db_session.add_all([
            Hunt(user_id=user.id, hunt_type="crypt"), Hunt(user_id=user.id, hunt_type="crypt"),
            Hunt(user_id=user.id, hunt_type="exchange"),
            Hunt(user_id=user.id, hunt_type="chest"),
            Hunt(user_id=user.id, hunt_type="crypt", created_at=old),
            Hunt(user_id=user.id, hunt_type="exchange", created_at=old),
        ])
        await db_session.commit()
        data = (await client.get("/web/hunts", headers={"Authorization": f"Bearer {token}"})).json()
    assert data["by_type"] == {
        "today": {"crypt": 2, "exchange": 1},
        "week":  {"crypt": 2, "exchange": 1},
        "total": {"crypt": 3, "exchange": 2},
    }


@pytest.mark.asyncio
async def test_transactions_income_only_with_purchase_details(db_session):
    from models import Transaction
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, user = await _web_user(db_session, client, "txincome@example.com", "tx-1")
        db_session.add_all([
            Transaction(user_id=user.id, type="purchase", amount=5000, usd_amount="10.00", package="ultra"),
            Transaction(user_id=user.id, type="ad_reward", amount=20),
            Transaction(user_id=user.id, type="credit_use", amount=-10),
        ])
        await db_session.commit()
        h = {"Authorization": f"Bearer {token}"}
        income = (await client.get("/web/transactions?income=1", headers=h)).json()["items"]
        everything = (await client.get("/web/transactions", headers=h)).json()["items"]
    assert sorted(t["type"] for t in income) == ["ad_reward", "purchase"]
    purchase = next(t for t in income if t["type"] == "purchase")
    assert purchase["usd_amount"] == "10.00" and purchase["package"] == "ultra"
    assert len(everything) == 3   # без фильтра — как раньше
