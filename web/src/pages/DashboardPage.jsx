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
