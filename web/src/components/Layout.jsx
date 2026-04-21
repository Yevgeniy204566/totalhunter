import { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom'
import { clearToken } from '../auth.js'
import { api } from '../api.js'

const NAV = [
  { to: '/dashboard',              icon: '◈', label: 'Profile' },
  { to: '/dashboard/balance',      icon: '◆', label: 'Balance' },
  { to: '/dashboard/hunts',        icon: '⚔', label: 'Hunts' },
  { to: '/dashboard/referrals',    icon: '⬡', label: 'Referrals' },
  { to: '/dashboard/devices',      icon: '▣', label: 'Devices' },
  { to: '/dashboard/transactions', icon: '≡', label: 'Transactions' },
  { to: '/dashboard/feedback',     icon: '✦', label: 'Feedback' },
]

export default function Layout() {
  const navigate = useNavigate()
  const [credits, setCredits] = useState(null)

  useEffect(() => {
    api.me().then(d => setCredits(d.credits)).catch(() => {})
  }, [])

  function logout() {
    clearToken()
    navigate('/login')
  }

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>

      {/* ── Fixed Header ─────────────────────────────────────── */}
      <header style={{
        position: 'fixed', top: 0, left: 0, right: 0,
        height: 'var(--header-height)',
        background: 'var(--header-bg)',
        borderBottom: '1px solid var(--outline)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        zIndex: 100,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>

        {/* Logo */}
        <Link to="/" style={{
          display: 'flex', alignItems: 'center', gap: 10,
          textDecoration: 'none',
          fontWeight: 700, fontSize: 18, letterSpacing: '0.3px',
        }}>
          <span style={{ fontSize: 20, color: 'var(--accent)' }}>⚔</span>
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>
            Total
          </span>
          <span style={{ color: 'var(--on-surface)' }}>Hunter</span>
        </Link>

        {/* Right area */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>

          {credits !== null && (
            <div className="credits-badge">
              <span style={{ fontSize: 13 }}>◈</span>
              <span>{credits.toLocaleString()}</span>
            </div>
          )}

          <button className="header-btn" title="Language (coming soon)">RU</button>

          <button className="header-btn header-btn--logout" onClick={logout}>
            Выйти
          </button>

        </div>
      </header>

      {/* ── Fixed Sidebar ─────────────────────────────────────── */}
      <nav style={{
        position: 'fixed',
        top: 'var(--header-height)',
        left: 0,
        width: 'var(--sidebar-width)',
        height: 'calc(100vh - var(--header-height))',
        background: 'var(--card)',
        borderRight: '1px solid var(--outline)',
        display: 'flex', flexDirection: 'column',
        paddingTop: 12,
        overflowY: 'auto',
        zIndex: 50,
      }}>

        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}

        <div style={{ flex: 1 }} />

        <a href="/guide" className="nav-item" style={{
          borderTop: '1px solid var(--outline)',
          marginTop: 8,
        }}>
          <span className="nav-icon" style={{ fontSize: 14 }}>📖</span>
          Guide
        </a>

      </nav>

      {/* ── Main content ─────────────────────────────────────── */}
      <main style={{
        marginLeft: 'var(--sidebar-width)',
        marginTop: 'var(--header-height)',
        minHeight: 'calc(100vh - var(--header-height))',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ flex: 1 }}>
          <Outlet />
        </div>
        <div className="ad-slot-footer">AD</div>
      </main>

    </div>
  )
}
