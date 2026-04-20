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
