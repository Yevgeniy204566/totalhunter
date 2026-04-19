import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { clearToken } from '../auth.js'

const NAV = [
  { to: '/dashboard',              label: 'Profile' },
  { to: '/dashboard/balance',      label: 'Balance' },
  { to: '/dashboard/hunts',        label: 'Hunts' },
  { to: '/dashboard/referrals',    label: 'Referrals' },
  { to: '/dashboard/devices',      label: 'Devices' },
  { to: '/dashboard/transactions', label: 'Transactions' },
]

export default function Layout() {
  const navigate = useNavigate()

  function logout() {
    clearToken()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <nav style={{
        width: 200, background: 'var(--card)', borderRight: '1px solid var(--outline)',
        padding: '24px 0', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '0 16px 24px', fontWeight: 600, fontSize: 16 }}>Total Hunter</div>
        {NAV.map(({ to, label }) => (
          <NavLink key={to} to={to} end style={({ isActive }) => ({
            padding: '10px 16px', fontSize: 14,
            color: isActive ? 'var(--on-surface)' : 'var(--on-surface2)',
            background: isActive ? 'var(--elevated)' : 'transparent',
            borderLeft: isActive ? '2px solid var(--primary-dim)' : '2px solid transparent',
            textDecoration: 'none',
          })}>
            {label}
          </NavLink>
        ))}
        <div style={{ flex: 1 }} />
        <button className="btn-secondary" onClick={logout} style={{ margin: '0 16px 16px' }}>
          Log out
        </button>
      </nav>
      <main style={{ flex: 1, overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
