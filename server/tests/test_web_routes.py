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
