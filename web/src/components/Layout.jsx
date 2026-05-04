import { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom'
import { clearToken } from '../auth.js'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const NAV_KEYS = [
  { to: '/dashboard',              icon: '◈', key: 'profile' },
  { to: '/dashboard/balance',      icon: '◆', key: 'balance' },
  { to: '/dashboard/hunts',        icon: '⚔', key: 'hunts' },
  { to: '/dashboard/referrals',    icon: '⬡', key: 'referrals' },
  { to: '/dashboard/devices',      icon: '▣', key: 'devices' },
  { to: '/dashboard/transactions', icon: '≡', key: 'transactions' },
  { to: '/dashboard/feedback',     icon: '✦', key: 'feedback' },
]


export default function Layout() {
  const navigate = useNavigate()
  const [credits, setCredits] = useState(null)
  const { lang, toggle } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const NAV = NAV_KEYS.map(n => ({ ...n, label: D.nav[n.key] }))

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
        <Link to="/" style={{
          display: 'flex', alignItems: 'center', gap: 10,
          textDecoration: 'none', fontWeight: 700, fontSize: 18, letterSpacing: '0.3px',
        }}>
          <span style={{ fontSize: 20, color: 'var(--accent)' }}>⚔</span>
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: 'var(--on-surface)' }}>Hunter</span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {credits !== null && (
            <div className="credits-badge">
              <span style={{ fontSize: 13 }}>◈</span>
              <span>{credits.toLocaleString()}</span>
            </div>
          )}

          <Link
            to="/dashboard/balance"
            title="Посмотри короткий ролик и получи кредиты для охоты"
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '8px 14px', borderRadius: 8, fontSize: 14,
              background: 'rgba(74,222,128,0.10)',
              border: '1px solid rgba(74,222,128,0.35)',
              color: '#4ADE80', fontWeight: 800, textDecoration: 'none',
              letterSpacing: '0.2px',
              transition: 'background 0.15s, box-shadow 0.15s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(74,222,128,0.20)'
              e.currentTarget.style.boxShadow  = '0 0 16px rgba(74,222,128,0.35)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(74,222,128,0.10)'
              e.currentTarget.style.boxShadow  = 'none'
            }}
          >
            {/* Faucet / water-drop icon */}
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
              <path d="M12 2C12 2 4 10 4 15a8 8 0 0 0 16 0C20 10 12 2 12 2z"/>
            </svg>
            +5 КР
          </Link>

          <button className="header-btn" onClick={toggle}>{lang.toUpperCase()}</button>
          <button className="header-btn header-btn--logout" onClick={logout}>{D.nav.logout}</button>
        </div>
      </header>

      {/* ── Fixed Sidebar ─────────────────────────────────────── */}
      <nav style={{
        position: 'fixed',
        top: 'var(--header-height)', left: 0,
        width: 'var(--sidebar-width)',
        height: `calc(100vh - var(--header-height))`,
        background: 'var(--card)',
        borderRight: '1px solid var(--outline)',
        display: 'flex', flexDirection: 'column',
        paddingTop: 12,
        zIndex: 50,
      }}>
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to} to={to} end
            className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
        <div style={{ flex: 1 }} />
        <a href="/guide" className="nav-item" style={{ borderTop: '1px solid var(--outline)', marginTop: 8 }}>
          <span className="nav-icon" style={{ fontSize: 14 }}>📖</span>
          {D.nav.guide}
        </a>
      </nav>

      {/* ── Main content ─────────────────────────────────────── */}
      <main style={{
        marginLeft: 'var(--sidebar-width)',
        marginTop: 'var(--header-height)',
        minHeight: `calc(100vh - var(--header-height))`,
        overflowY: 'auto',
      }}>
        <Outlet />
      </main>


    </div>
  )
}
