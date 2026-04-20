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
