# Website Phase 2A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the personal dashboard — Deep Night theme upgrades, global stats widget, Transfer button, referral link with cookie tracking, feedback module, ad slots, and Balance page stubs.

**Architecture:** All frontend changes are in `web/src/`. Backend adds two endpoints and one schema change. One new DB table (Feedback) requires an Alembic migration applied on GCP before frontend deploys.

**Tech Stack:** React + Vite (Vercel), FastAPI + SQLAlchemy async + Alembic (GCP), PostgreSQL

---

## File Map

**Create:**
- `web/src/pages/FeedbackPage.jsx`
- `web/src/pages/RefPage.jsx`
- `server/alembic/versions/f1a2b3c4d5e6_add_feedback.py`

**Modify:**
- `web/src/styles/theme.css` — button sizes, `.ad-slot`, table row height
- `web/src/components/Layout.jsx` — ad slots, guide + feedback nav items
- `web/src/App.jsx` — add `/ref/:code` and `/dashboard/feedback` routes
- `web/src/api.js` — `globalStats()`, `sendFeedback()`, update `authGoogle()`
- `web/src/pages/DashboardPage.jsx` — global stats widget
- `web/src/pages/ReferralsPage.jsx` — Transfer button + referral link display
- `web/src/pages/LoginPage.jsx` — read `th_ref` cookie, pass to authGoogle
- `web/src/pages/BalancePage.jsx` — Daily Bonus stub + Buy Credits stub
- `server/models.py` — add `Feedback` model
- `server/web_routes.py` — `GET /web/stats/global`, `POST /web/feedback`, update `auth_google`
- `server/schemas.py` — add `ref_code` to `GoogleAuthRequest`, add `GlobalStatsResponse`, `FeedbackRequest`

---

## Task 1: Theme CSS — buttons, spacing, ad slot

**Files:**
- Modify: `web/src/styles/theme.css`

- [ ] **Step 1: Update button sizes and add ad-slot class**

Replace the entire `.btn-primary`, `.btn-secondary` blocks and add new classes:

```css
.btn-primary {
  background: var(--primary);
  color: var(--on-surface);
  border: none;
  border-radius: 8px;
  padding: 14px 28px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  transition: background 0.15s;
}
.btn-primary:hover { background: var(--primary-dim); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: transparent;
  color: var(--on-surface2);
  border: 2px solid var(--primary-dim);
  border-radius: 8px;
  padding: 14px 28px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.15s;
}
.btn-secondary:hover { border-color: var(--on-surface); color: var(--on-surface); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-danger {
  background: transparent;
  color: var(--error-text);
  border: 2px solid var(--error);
  border-radius: 8px;
  padding: 14px 28px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.15s;
}
.btn-danger:hover { background: var(--error); color: var(--on-surface); }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-green {
  background: var(--green-btn);
  color: var(--on-surface);
  border: none;
  border-radius: 8px;
  padding: 14px 28px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  transition: background 0.15s;
}
.btn-green:hover { background: var(--green-hover); }
.btn-green:disabled { opacity: 0.5; cursor: not-allowed; }

.ad-slot {
  width: 100%;
  height: 90px;
  background: var(--elevated);
  border-bottom: 1px solid var(--outline);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--on-surface2);
  font-size: 12px;
  letter-spacing: 1px;
}

.ad-slot-footer {
  width: 100%;
  height: 90px;
  background: var(--elevated);
  border-top: 1px solid var(--outline);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--on-surface2);
  font-size: 12px;
  letter-spacing: 1px;
}
```

Also update `.text-muted` font-size to 14px (was 13px) and table row padding via a global rule:

```css
.text-muted { color: var(--on-surface2); font-size: 14px; }
```

- [ ] **Step 2: Commit**

```bash
git add web/src/styles/theme.css
git commit -m "feat: upgrade button sizes for 35+ audience, add ad-slot classes"
```

---

## Task 2: Backend — Feedback model + Alembic migration

**Files:**
- Modify: `server/models.py`
- Create: `server/alembic/versions/f1a2b3c4d5e6_add_feedback.py`

- [ ] **Step 1: Add Feedback model to models.py**

Append at the end of `server/models.py`:

```python
# ─────────────────────────────────────────────
# Feedback — user suggestions & ideas
# ─────────────────────────────────────────────

class Feedback(Base):
    """User-submitted suggestions stored for analysis."""
    __tablename__ = "feedback"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text       = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now())
```

- [ ] **Step 2: Create Alembic migration file**

Create `server/alembic/versions/f1a2b3c4d5e6_add_feedback.py`:

```python
"""add_feedback_table

Revision ID: f1a2b3c4d5e6
Revises: eeaef22b78d1
Create Date: 2026-04-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'eeaef22b78d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_feedback_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_feedback'),
    )
    op.create_index('ix_feedback_user_id', 'feedback', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_feedback_user_id', 'feedback')
    op.drop_table('feedback')
```

- [ ] **Step 3: Commit**

```bash
git add server/models.py server/alembic/versions/f1a2b3c4d5e6_add_feedback.py
git commit -m "feat: add Feedback model and migration"
```

---

## Task 3: Backend — Global stats endpoint

**Files:**
- Modify: `server/schemas.py`
- Modify: `server/web_routes.py`
- Test: `server/tests/test_web_routes.py`

- [ ] **Step 1: Add GlobalStatsResponse schema to schemas.py**

Append to `server/schemas.py`:

```python
class GlobalStatsResponse(BaseModel):
    exchanges_today: int
    crypts_today: int
    active_hunters: int
```

- [ ] **Step 2: Write failing test**

Add to `server/tests/test_web_routes.py`:

```python
@pytest.mark.asyncio
async def test_global_stats_returns_zeroes_on_empty_db():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/stats/global")
    assert resp.status_code == 200
    data = resp.json()
    assert data["exchanges_today"] == 0
    assert data["crypts_today"] == 0
    assert data["active_hunters"] == 0
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
cd server && python -m pytest tests/test_web_routes.py::test_global_stats_returns_zeroes_on_empty_db -v
```
Expected: FAIL with 404 (route not found yet)

- [ ] **Step 4: Add endpoint to web_routes.py**

First, update the sqlalchemy import line at the top of `web_routes.py` to include `func`:
```python
from sqlalchemy import select, update, func
```

Add after the `web_me` endpoint (after line ~145):

```python
# ─────────────────────────────────────────────────────────────────────────────
# GET /web/stats/global  (no auth required)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats/global", response_model=GlobalStatsResponse)
async def global_stats(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    rows = await db.execute(
        select(Hunt.hunt_type, func.count().label("cnt"))
        .where(Hunt.created_at >= today_start)
        .group_by(Hunt.hunt_type)
    )
    counts = {row.hunt_type: row.cnt for row in rows}

    active_row = await db.execute(
        select(func.count(func.distinct(Hunt.user_id)))
        .where(Hunt.created_at >= today_start)
    )
    active_hunters = active_row.scalar() or 0

    return GlobalStatsResponse(
        exchanges_today=counts.get("exchange", 0),
        crypts_today=counts.get("crypt", 0),
        active_hunters=active_hunters,
    )
```

Also add `GlobalStatsResponse` to the import from schemas at the top of `web_routes.py`:
```python
from schemas import (
    ...
    GlobalStatsResponse,
)
```

- [ ] **Step 5: Run test — expect PASS**

```bash
cd server && python -m pytest tests/test_web_routes.py::test_global_stats_returns_zeroes_on_empty_db -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/schemas.py server/web_routes.py server/tests/test_web_routes.py
git commit -m "feat: GET /web/stats/global endpoint"
```

---

## Task 4: Backend — Update auth/google to accept ref_code

**Files:**
- Modify: `server/schemas.py`
- Modify: `server/web_routes.py`
- Test: `server/tests/test_web_routes.py`

- [ ] **Step 1: Update GoogleAuthRequest schema in schemas.py**

Find `class GoogleAuthRequest` and add `ref_code`:

```python
class GoogleAuthRequest(BaseModel):
    """Frontend sends Google ID token; backend verifies and returns JWT."""
    id_token: str
    ref_code: str | None = None
```

- [ ] **Step 2: Write failing test**

Add to `server/tests/test_web_routes.py`:

```python
@pytest.mark.asyncio
async def test_auth_google_with_valid_ref_code(fake_google_claims):
    # Register referrer first
    referrer_claims = {**fake_google_claims, "email": "referrer@example.com", "sub": "ref-sub-999"}
    with patch("web_routes._verify_google_token", return_value=referrer_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/web/auth/google", json={"id_token": "ref-tok"})
    referrer_ref_code = resp.json().get("ref_code")  # not in response yet — will check via /me

    # Register new user with referrer's ref_code via cookie
    new_claims = {**fake_google_claims, "email": "newuser@example.com", "sub": "new-sub-111"}
    with patch("web_routes._verify_google_token", return_value=new_claims):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # We pass None ref_code since we don't know the code; test that null is handled
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
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd server && python -m pytest tests/test_web_routes.py::test_auth_google_with_valid_ref_code tests/test_web_routes.py::test_auth_google_ignores_unknown_ref_code -v
```
Expected: FAIL (schema doesn't accept ref_code yet)

- [ ] **Step 4: Update auth_google in web_routes.py**

Replace the `auth_google` function body (lines 101–125):

```python
@router.post("/auth/google", response_model=WebAuthResponse)
async def auth_google(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = _verify_google_token(req.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email    = claims["email"]
    username = claims.get("name")

    async with db.begin():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            new_ref_code = _secrets.token_urlsafe(6)
            invited_by_id = None
            if req.ref_code:
                ref_row = await db.execute(
                    select(User).where(User.ref_code == req.ref_code)
                )
                referrer = ref_row.scalar_one_or_none()
                if referrer:
                    invited_by_id = referrer.id
            user = User(
                email=email,
                username=username,
                ref_code=new_ref_code,
                invited_by_id=invited_by_id,
            )
            db.add(user)
            await db.flush()
        elif username and user.username != username:
            user.username = username

    return WebAuthResponse(
        jwt=create_jwt(user.id, email),
        email=email,
        username=user.username,
    )
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd server && python -m pytest tests/test_web_routes.py::test_auth_google_with_valid_ref_code tests/test_web_routes.py::test_auth_google_ignores_unknown_ref_code -v
```
Expected: both PASS

- [ ] **Step 6: Run full test suite**

```bash
cd server && python -m pytest tests/test_web_routes.py -v
```
Expected: all existing tests still PASS

- [ ] **Step 7: Commit**

```bash
git add server/schemas.py server/web_routes.py server/tests/test_web_routes.py
git commit -m "feat: auth/google accepts optional ref_code, sets invited_by_id on new users"
```

---

## Task 5: Backend — Feedback endpoint

**Files:**
- Modify: `server/schemas.py`
- Modify: `server/web_routes.py`
- Test: `server/tests/test_web_routes.py`

- [ ] **Step 1: Add FeedbackRequest schema to schemas.py**

```python
class FeedbackRequest(BaseModel):
    text: str
```

- [ ] **Step 2: Write failing test**

```python
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
    assert resp.status_code == 403
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd server && python -m pytest tests/test_web_routes.py::test_send_feedback_saves_to_db tests/test_web_routes.py::test_send_feedback_requires_auth -v
```
Expected: FAIL (route not found)

- [ ] **Step 4: Add feedback endpoint to web_routes.py**

Add after global_stats endpoint. Also add `Feedback` to models import at top of `web_routes.py`:

```python
from models import User, Hunt, LinkCode, HwidHistory, Feedback
```

Then add the endpoint:

```python
# ─────────────────────────────────────────────────────────────────────────────
# POST /web/feedback
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/feedback", response_model=BasicResponse)
async def send_feedback(
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=422, detail="Feedback text cannot be empty")
    async with db.begin():
        db.add(Feedback(user_id=web_user.id, text=req.text.strip()[:1000]))
    return BasicResponse(message="Thank you for your feedback!")
```

Also add `FeedbackRequest` to schemas import at top of `web_routes.py`.

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd server && python -m pytest tests/test_web_routes.py::test_send_feedback_saves_to_db tests/test_web_routes.py::test_send_feedback_requires_auth -v
```
Expected: both PASS

- [ ] **Step 6: Run full test suite**

```bash
cd server && python -m pytest tests/test_web_routes.py -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add server/schemas.py server/web_routes.py server/tests/test_web_routes.py
git commit -m "feat: POST /web/feedback endpoint"
```

---

## Task 6: Deploy backend to GCP

- [ ] **Step 1: Push to git**

```bash
git push
```

- [ ] **Step 2: SSH to GCP and apply migration + restart**

```bash
ssh user@34.68.86.57
cd /opt/totalhunter
git pull
source venv/bin/activate
cd server && alembic upgrade head
sudo systemctl restart totalhunter
sudo systemctl status totalhunter
```

Expected: `Active: active (running)`

- [ ] **Step 3: Smoke test endpoints**

```bash
curl http://34.68.86.57:8000/web/stats/global
```
Expected: `{"exchanges_today":0,"crypts_today":0,"active_hunters":0}`

---

## Task 7: Frontend — api.js updates

**Files:**
- Modify: `web/src/api.js`

- [ ] **Step 1: Update api.js**

Replace the full file:

```js
import { getToken, clearToken } from './auth.js'

const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(method, path, body) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    return
  }

  const data = await res.json()
  if (!res.ok) throw new Error(data.detail?.message || data.detail || 'Request failed')
  return data
}

export const api = {
  authGoogle:       (id_token, ref_code = null) => request('POST', '/web/auth/google', { id_token, ref_code }),
  me:               ()         => request('GET',  '/web/me'),
  hunts:            ()         => request('GET',  '/web/hunts'),
  transactions:     ()         => request('GET',  '/web/transactions'),
  linkVerify:       (code)     => request('POST', '/web/link/verify', { code }),
  hwidReset:        ()         => request('POST', '/web/hwid/reset'),
  referralTransfer: ()         => request('POST', '/web/referral/transfer'),
  globalStats:      ()         => request('GET',  '/web/stats/global'),
  sendFeedback:     (text)     => request('POST', '/web/feedback', { text }),
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/api.js
git commit -m "feat: add globalStats and sendFeedback to api client"
```

---

## Task 8: Frontend — Layout.jsx (ad slots + nav items)

**Files:**
- Modify: `web/src/components/Layout.jsx`

- [ ] **Step 1: Replace Layout.jsx**

```jsx
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { clearToken } from '../auth.js'

const NAV = [
  { to: '/dashboard',              label: 'Profile' },
  { to: '/dashboard/balance',      label: 'Balance' },
  { to: '/dashboard/hunts',        label: 'Hunts' },
  { to: '/dashboard/referrals',    label: 'Referrals' },
  { to: '/dashboard/devices',      label: 'Devices' },
  { to: '/dashboard/transactions', label: 'Transactions' },
  { to: '/dashboard/feedback',     label: 'Feedback' },
]

export default function Layout() {
  const navigate = useNavigate()

  function logout() {
    clearToken()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', flexDirection: 'column' }}>
      <div className="ad-slot">AD</div>
      <div style={{ display: 'flex', flex: 1 }}>
        <nav style={{
          width: 200, background: 'var(--card)', borderRight: '1px solid var(--outline)',
          padding: '24px 0', display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '0 16px 24px', fontWeight: 700, fontSize: 16,
                        color: 'var(--on-surface)' }}>
            ⚔ Total Hunter
          </div>
          {NAV.map(({ to, label }) => (
            <NavLink key={to} to={to} end style={({ isActive }) => ({
              padding: '10px 16px', fontSize: 14,
              color: isActive ? 'var(--on-surface)' : 'var(--on-surface2)',
              background: isActive ? 'var(--primary)' : 'transparent',
              borderLeft: isActive ? '3px solid var(--primary-dim)' : '3px solid transparent',
              textDecoration: 'none',
              transition: 'background 0.1s',
            })}>
              {label}
            </NavLink>
          ))}
          <div style={{ flex: 1 }} />
          <div style={{ padding: '0 16px' }}>
            <a href="/guide" style={{ display: 'block', padding: '10px 0', fontSize: 14,
                                      color: 'var(--on-surface2)', textDecoration: 'none',
                                      marginBottom: 8 }}>
              Guide
            </a>
            <button className="btn-secondary" onClick={logout}
                    style={{ width: '100%', padding: '10px 16px' }}>
              Log out
            </button>
          </div>
        </nav>
        <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1 }}>
            <Outlet />
          </div>
          <div className="ad-slot-footer">AD</div>
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/Layout.jsx
git commit -m "feat: add ad slots top/footer, feedback nav item"
```

---

## Task 9: Frontend — App.jsx (new routes)

**Files:**
- Modify: `web/src/App.jsx`

- [ ] **Step 1: Replace App.jsx**

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { isLoggedIn } from './auth.js'
import Layout from './components/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import BalancePage from './pages/BalancePage.jsx'
import HuntsPage from './pages/HuntsPage.jsx'
import ReferralsPage from './pages/ReferralsPage.jsx'
import DevicesPage from './pages/DevicesPage.jsx'
import TransactionsPage from './pages/TransactionsPage.jsx'
import FeedbackPage from './pages/FeedbackPage.jsx'
import GuidePage from './pages/GuidePage.jsx'
import LegalPage from './pages/LegalPage.jsx'
import RefPage from './pages/RefPage.jsx'

function PrivateRoute({ element }) {
  return isLoggedIn() ? element : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"      element={<LoginPage />} />
        <Route path="/guide"      element={<GuidePage />} />
        <Route path="/legal"      element={<LegalPage />} />
        <Route path="/ref/:code"  element={<RefPage />} />
        <Route path="/dashboard"  element={<PrivateRoute element={<Layout />} />}>
          <Route index             element={<DashboardPage />} />
          <Route path="balance"      element={<BalancePage />} />
          <Route path="hunts"        element={<HuntsPage />} />
          <Route path="referrals"    element={<ReferralsPage />} />
          <Route path="devices"      element={<DevicesPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="feedback"     element={<FeedbackPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/App.jsx
git commit -m "feat: add /ref/:code and /dashboard/feedback routes"
```

---

## Task 10: Frontend — RefPage.jsx (cookie + redirect)

**Files:**
- Create: `web/src/pages/RefPage.jsx`

- [ ] **Step 1: Create RefPage.jsx**

```jsx
import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function RefPage() {
  const { code } = useParams()
  const navigate = useNavigate()

  useEffect(() => {
    if (code) {
      const expires = new Date()
      expires.setDate(expires.getDate() + 30)
      document.cookie = `th_ref=${code}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`
    }
    navigate('/login', { replace: true })
  }, [code, navigate])

  return null
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/RefPage.jsx
git commit -m "feat: /ref/:code saves cookie and redirects to login"
```

---

## Task 11: Frontend — LoginPage.jsx (read cookie)

**Files:**
- Modify: `web/src/pages/LoginPage.jsx`

- [ ] **Step 1: Replace LoginPage.jsx**

```jsx
import { GoogleLogin } from '@react-oauth/google'
import { api } from '../api.js'
import { saveToken } from '../auth.js'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

function getRefCookie() {
  const match = document.cookie.match(/(?:^|;\s*)th_ref=([^;]+)/)
  return match ? match[1] : null
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  const handleSuccess = async (credentialResponse) => {
    try {
      const refCode = getRefCookie()
      const data = await api.authGoogle(credentialResponse.credential, refCode)
      saveToken(data.jwt)
      navigate('/dashboard')
    } catch (e) {
      setError('Login failed: ' + e.message)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                  minHeight: '100vh' }}>
      <div className="card" style={{ textAlign: 'center', maxWidth: 380, width: '100%' }}>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>Total Hunter</h1>
        <p className="text-muted" style={{ marginBottom: 32 }}>
          Sign in to access your dashboard
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={() => setError('Google login failed')}
            theme="filled_black"
            size="large"
            width="320"
          />
        </div>
        {error && <p style={{ color: 'var(--error-text)', fontSize: 13 }}>{error}</p>}
        <div className="separator" />
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
          <a href="/guide">Guide</a>
          <a href="/legal">Legal</a>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/LoginPage.jsx
git commit -m "feat: read th_ref cookie on login for referral tracking"
```

---

## Task 12: Frontend — DashboardPage (global stats widget)

**Files:**
- Modify: `web/src/pages/DashboardPage.jsx`

- [ ] **Step 1: Replace DashboardPage.jsx**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function DashboardPage() {
  const [user, setUser]   = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.me().then(setUser).catch(e => setError(e.message))
    api.globalStats().then(setStats).catch(() => null)
  }, [])

  if (error) return <div className="page-content text-muted" style={{ color: 'var(--error-text)' }}>{error}</div>
  if (!user)  return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
          <StatTile label="Exchanges today" value={stats.exchanges_today} accent />
          <StatTile label="Crypts today"    value={stats.crypts_today} accent />
          <StatTile label="Active hunters"  value={stats.active_hunters} />
        </div>
      )}
      <h2 style={{ marginBottom: 24, fontSize: 22, fontWeight: 700 }}>Profile</h2>
      <div className="card" style={{ maxWidth: 480 }}>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 20, fontWeight: 600 }}>{user.username || 'User'}</div>
          <div className="text-muted">{user.email}</div>
        </div>
        <div className="separator" />
        <Row label="Credits"          value={user.credits} />
        <Row label="Referral balance" value={user.ref_credits} />
        <Row label="Referral code"    value={user.ref_code} />
        <Row label="Status"           value={user.trial_used ? 'Trial used' : 'Trial available'} />
        <Row label="Member since"     value={user.created_at ? user.created_at.slice(0, 10) : '—'} />
      </div>
    </div>
  )
}

function StatTile({ label, value, accent }) {
  return (
    <div className="card" style={{ minWidth: 140, textAlign: 'center',
                                   borderColor: accent ? 'var(--primary-dim)' : 'var(--outline)' }}>
      <div className="text-muted" style={{ marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 700,
                    color: accent ? 'var(--primary-dim)' : 'var(--on-surface)' }}>
        {value}
      </div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0',
                  borderBottom: '1px solid var(--separator)' }}>
      <span className="text-muted">{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/DashboardPage.jsx
git commit -m "feat: global stats widget on dashboard"
```

---

## Task 13: Frontend — ReferralsPage (Transfer + link)

**Files:**
- Modify: `web/src/pages/ReferralsPage.jsx`

- [ ] **Step 1: Replace ReferralsPage.jsx**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function ReferralsPage() {
  const [user, setUser]       = useState(null)
  const [copied, setCopied]   = useState(false)
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)

  async function refresh() { api.me().then(setUser) }
  useEffect(() => { refresh() }, [])

  function copyLink() {
    navigator.clipboard.writeText(refLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function transfer() {
    setLoading(true)
    setMsg('')
    try {
      const res = await api.referralTransfer()
      setMsg(res.message)
      await refresh()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  const refLink = `https://totalhunter.vercel.app/ref/${user.ref_code}`

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24, fontSize: 22, fontWeight: 700 }}>Referrals</h2>

      <div className="card" style={{ maxWidth: 520, marginBottom: 16 }}>
        <div className="text-muted" style={{ marginBottom: 8 }}>Your referral link</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8,
                      flexWrap: 'wrap' }}>
          <code style={{ fontSize: 13, color: 'var(--primary-dim)', wordBreak: 'break-all',
                         flex: 1 }}>
            {refLink}
          </code>
          <button className="btn-secondary" onClick={copyLink}
                  style={{ padding: '10px 20px', flexShrink: 0 }}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <div className="text-muted" style={{ fontSize: 12 }}>
          Code: <strong>{user.ref_code}</strong>
        </div>

        <div className="separator" />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      flexWrap: 'wrap', gap: 12 }}>
          <span className="text-muted">
            Referral balance:{' '}
            <strong style={{ color: 'var(--on-surface)' }}>{user.ref_credits} credits</strong>
          </span>
          <button
            className="btn-green"
            onClick={transfer}
            disabled={loading || user.ref_credits === 0}
            style={{ padding: '12px 24px' }}
          >
            {loading ? 'Transferring...' : 'Transfer to Balance'}
          </button>
        </div>
        {msg && (
          <div className="text-muted" style={{ marginTop: 10 }}>{msg}</div>
        )}
      </div>

      <div className="card" style={{ maxWidth: 520 }}>
        <div className="text-muted" style={{ marginBottom: 12 }}>How it works</div>
        <p style={{ fontSize: 14, lineHeight: 1.8, color: 'var(--on-surface2)' }}>
          Share your link with other players. When they register using your link, you both
          get bonus credits. Referral earnings go to your referral balance — transfer them
          to your main balance anytime.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/ReferralsPage.jsx
git commit -m "feat: Transfer button and referral link on Referrals page"
```

---

## Task 14: Frontend — FeedbackPage.jsx (new)

**Files:**
- Create: `web/src/pages/FeedbackPage.jsx`

- [ ] **Step 1: Create FeedbackPage.jsx**

```jsx
import { useState } from 'react'
import { api } from '../api.js'

export default function FeedbackPage() {
  const [text, setText]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)

  async function send() {
    if (!text.trim()) return
    setLoading(true)
    setMsg('')
    try {
      const res = await api.sendFeedback(text.trim())
      setMsg(res.message)
      setText('')
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 8, fontSize: 22, fontWeight: 700 }}>Feedback</h2>
      <p className="text-muted" style={{ marginBottom: 24 }}>
        Got an idea or suggestion? We read every message.
      </p>
      <div className="card" style={{ maxWidth: 520 }}>
        <textarea
          value={text}
          onChange={e => setText(e.target.value.slice(0, 1000))}
          placeholder="Your idea or suggestion..."
          rows={5}
          style={{
            width: '100%', background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 8, color: 'var(--on-surface)', padding: '14px', fontSize: 15,
            resize: 'vertical', marginBottom: 16, fontFamily: 'inherit',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="text-muted" style={{ fontSize: 12 }}>
            {text.length} / 1000
          </span>
          <button
            className="btn-primary"
            onClick={send}
            disabled={loading || !text.trim()}
          >
            {loading ? 'Sending...' : 'Send Idea'}
          </button>
        </div>
        {msg && (
          <div className="text-muted" style={{ marginTop: 14 }}>{msg}</div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/FeedbackPage.jsx
git commit -m "feat: Feedback page — suggestions form"
```

---

## Task 15: Frontend — BalancePage (stubs)

**Files:**
- Modify: `web/src/pages/BalancePage.jsx`

- [ ] **Step 1: Replace BalancePage.jsx**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function BalancePage() {
  const [user, setUser] = useState(null)

  useEffect(() => { api.me().then(setUser) }, [])

  if (!user) return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24, fontSize: 22, fontWeight: 700 }}>Balance</h2>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard title="Credits"          value={user.credits} />
        <StatCard title="Referral balance" value={user.ref_credits} />
      </div>

      {/* Daily Bonus stub */}
      <div className="card" style={{ maxWidth: 480, marginBottom: 16 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>Daily Bonus</div>
        <div className="text-muted" style={{ marginBottom: 16 }}>
          Watch a short ad and get 3–7 free credits. Up to 3 times per day.
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button className="btn-primary" disabled title="Coming soon"
                  style={{ opacity: 0.5, cursor: 'not-allowed' }}>
            Watch Ad → Get Credits
          </button>
          <span className="text-muted">0 / 3 today</span>
        </div>
        <div className="text-muted" style={{ marginTop: 10, fontSize: 12 }}>
          Coming soon
        </div>
      </div>

      {/* Buy Credits stub */}
      <div className="card" style={{ maxWidth: 480 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>Buy Credits</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {[
            { label: '50 credits', price: '$2.99' },
            { label: '100 credits', price: '$4.99' },
            { label: '500 credits', price: '$19.99' },
          ].map(pkg => (
            <div key={pkg.label} className="card"
                 style={{ flex: 1, minWidth: 120, textAlign: 'center',
                          background: 'var(--elevated)' }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{pkg.label}</div>
              <div className="text-muted">{pkg.price}</div>
            </div>
          ))}
        </div>
        <button className="btn-primary" disabled title="Coming soon"
                style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          Buy via Free-Kassa
        </button>
        <div className="text-muted" style={{ marginTop: 10, fontSize: 12 }}>
          Coming soon
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value }) {
  return (
    <div className="card" style={{ minWidth: 160 }}>
      <div className="text-muted" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 700 }}>{value}</div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/BalancePage.jsx
git commit -m "feat: Balance page with Daily Bonus and Free-Kassa stubs"
```

---

## Task 16: Admin — unread feedback counter

**Files:**
- Modify: `server/web_routes.py` — add `GET /admin/feedback/unread` endpoint
- Modify: `server/admin/index.html` — badge в шапке

- [ ] **Step 1: Add admin endpoint for unread feedback count**

Add to `web_routes.py` (или в `main.py` если admin роуты там):

```python
@router.get("/admin/feedback/unread")
async def feedback_unread(db: AsyncSession = Depends(get_db)):
    row = await db.execute(select(func.count()).select_from(Feedback))
    return {"count": row.scalar() or 0}
```

- [ ] **Step 2: Add badge to admin panel**

In `server/admin/index.html`, find the Feedback section header and add a live badge. Add this script snippet before `</body>`:

```html
<script>
async function loadFeedbackBadge() {
  try {
    const r = await fetch('/admin/feedback/unread', {
      headers: { 'X-Admin-Key': localStorage.getItem('admin_key') || '' }
    });
    const d = await r.json();
    const badge = document.getElementById('feedback-badge');
    if (badge) {
      badge.textContent = d.count;
      badge.style.display = d.count > 0 ? 'inline-block' : 'none';
    }
  } catch {}
}
loadFeedbackBadge();
setInterval(loadFeedbackBadge, 30000);
</script>
```

Also add the badge element next to the "Feedback" nav item in the admin sidebar:
```html
<span id="feedback-badge" style="
  background: #e53935; color: #fff; border-radius: 10px;
  padding: 1px 7px; font-size: 11px; margin-left: 6px; display: none;
"></span>
```

- [ ] **Step 3: Commit**

```bash
git add server/web_routes.py server/admin/index.html
git commit -m "feat: unread feedback badge in admin panel"
```

---

## Task 17: Final push and Vercel deploy

- [ ] **Step 1: Push all frontend changes**

```bash
git push
```

Vercel автоматически пересоберёт frontend по push в master.

- [ ] **Step 2: Verify Vercel deployment**

Открой https://totalhunter.vercel.app — убедись что сайт собрался без ошибок (Vercel Dashboard → Deployments).

- [ ] **Step 3: Smoke test checklist**

- [ ] Открыть `/login` — кнопка Google должна быть крупной
- [ ] Войти → Dashboard: глобальная статистика показывается (или прочерки если 0)
- [ ] Перейти Referrals: показывает полную ссылку, кнопка Transfer отображается
- [ ] Перейти Balance: карточки Daily Bonus и Buy Credits с disabled кнопками
- [ ] Перейти Feedback: textarea + кнопка Send Idea
- [ ] Открыть `/ref/TESTCODE` → должно редиректить на `/login` + в DevTools/Cookies проверить `th_ref=TESTCODE`
- [ ] Проверить ad-slot сверху и снизу страницы

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -p   # only stage tested fixes
git commit -m "fix: post-deploy corrections Phase 2A"
git push
```
