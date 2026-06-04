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
  { to: '/dashboard/roy',          icon: '⬡', key: 'roy' },
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
            className="header-btn header-download-btn"
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
            href="https://t.me/Total_Hunter"
            target="_blank"
            rel="noopener noreferrer"
            className="header-btn"
            title="Telegram"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 5, textDecoration: 'none', color: '#229ED9' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.96 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
            </svg>
          </a>
          <a
            href="https://discord.gg/7dJQdF2pBG"
            target="_blank"
            rel="noopener noreferrer"
            className="header-btn"
            title="Discord"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 5, textDecoration: 'none', color: '#5865F2' }}
          >
            <img src="/img/discord.png" alt="Discord" width="18" height="18" style={{ objectFit: 'contain' }} />
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
        <a href="/features" className="nav-item" style={{ borderTop: '1px solid var(--outline)', marginTop: 8 }}>
          <span className="nav-icon" style={{ fontSize: 14 }}>⚡</span>
          {lang === 'ru' ? 'Возможности' : 'Features'}
        </a>
        <a href="/guide" className="nav-item">
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
        {/* ── Content ─────────────────────────────────────── */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Outlet />
        </div>

      </main>


    </div>
  )
}
