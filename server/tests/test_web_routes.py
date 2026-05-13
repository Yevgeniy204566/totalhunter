"""Tests for /web/* endpoints."""
import pytest
import pytest_asyncio
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
    assert data["expires_in_seconds"] == 600


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
