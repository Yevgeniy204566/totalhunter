import { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom'
import { clearToken } from '../auth.js'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import AdSlot from './AdSlot.jsx'

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
      <header className="header-top-bar" style={{
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
          <span className="header-logo-text" style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span className="header-logo-text" style={{ color: 'var(--on-surface)' }}>Hunter</span>
        </Link>

        <div className="header-btn-group" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {credits !== null && (
            <div className="credits-badge">
              <span style={{ fontSize: 13 }}>◈</span>
              <span>{credits.toLocaleString()}</span>
            </div>
          )}

          <a
            href="https://github.com/Yevgeniy204566/totalhunter/releases/latest/download/TotalHunter.zip"
            className="header-btn"
            style={{
              background: 'rgba(74,222,128,0.12)',
              border: '1px solid rgba(74,222,128,0.35)',
              color: '#4ADE80', fontWeight: 700, textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 5,
            }}
          >
            ↓ {D.profile.download}
          </a>

          <Link
            className="header-earn-btn"
            to="/dashboard/earn"
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

          <a
            href="https://discord.gg/7dJQdF2pBG"
            target="_blank"
            rel="noopener noreferrer"
            className="header-btn"
            title="Discord"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 5, textDecoration: 'none', color: '#5865F2' }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
            </svg>
          </a>
          <button className="header-btn" onClick={toggle}>{lang.toUpperCase()}</button>
          <button className="header-btn header-btn--logout" onClick={logout}>{D.nav.logout}</button>
        </div>
      </header>

      {/* ── Fixed Sidebar (desktop only) ─────────────────────── */}
      <nav className="desktop-sidebar" style={{
        position: 'fixed',
        top: 'var(--header-height)', left: 0,
        width: 'var(--sidebar-width)',
        height: `calc(100vh - var(--header-height))`,
        background: 'var(--card)',
        borderRight: '1px solid var(--outline)',
        flexDirection: 'column',
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

      {/* ── Bottom Navigation (mobile only) ──────────────────── */}
      <nav className="mobile-bottom-nav">
        {NAV.slice(0, 6).map(({ to, icon, label }) => (
          <NavLink
            key={to} to={to} end
            className={({ isActive }) => `mobile-nav-item${isActive ? ' active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* ── Main content ─────────────────────────────────────── */}
      <main className="main-content" style={{
        marginLeft: 'var(--sidebar-width)',
        marginTop: 'var(--header-height)',
        minHeight: `calc(100vh - var(--header-height))`,
        overflowY: 'auto',
      }}>

        {/* ── Leaderboard banner — desktop only, under header ── */}
        <div className="ad-leaderboard-wrap" style={{
          display: 'flex', justifyContent: 'center',
          padding: '10px 0 0',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
        }}>
          <AdSlot size="leaderboard" />
        </div>

        {/* ── Content + right rectangle ad ─────────────────── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Outlet />
          </div>
          {/* 300×250 sidebar ad — visible only on very wide screens */}
          <div className="ad-sidebar-wrap" style={{ paddingTop: 24, flexShrink: 0 }}>
            <AdSlot size="rectangle" style={{ position: 'sticky', top: 20 }} />
          </div>
        </div>

      </main>

      {/* ── Mobile sticky bottom ad — above mobile nav ───────── */}
      <div className="ad-mobile-bottom" style={{
        position: 'fixed', bottom: 'var(--mobile-nav-height, 60px)',
        left: 0, right: 0, zIndex: 90,
        display: 'flex', justifyContent: 'center',
        background: 'rgba(0,0,0,0.85)',
        borderTop: '1px solid rgba(255,255,255,0.06)',
      }}>
        <AdSlot size="mobile" />
      </div>


    </div>
  )
}
