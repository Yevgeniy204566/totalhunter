import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function DashboardPage() {
  const [user, setUser] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.me().then(setUser).catch(e => setError(e.message))
  }, [])

  if (error) return <div className="page-content text-error">{error}</div>
  if (!user)  return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>Profile</h2>
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

function Row({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0',
                  borderBottom: '1px solid var(--separator)' }}>
      <span className="text-muted">{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  )
}
