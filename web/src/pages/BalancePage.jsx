import { useEffect, useState } from 'react'
import { api } from '../api.js'

const PACKAGES = [
  { id: 'lite',  label: '300 credits',  price: '$1.00', bonus: null },
  { id: 'pro',   label: '2000 credits', price: '$5.00', bonus: '+500 bonus' },
  { id: 'ultra', label: '5000 credits', price: '$10.00', bonus: '+1000 bonus' },
]

export default function BalancePage() {
  const [user, setUser]     = useState(null)
  const [buying, setBuying] = useState(null)
  const [error, setError]   = useState('')

  useEffect(() => { api.me().then(setUser) }, [])

  async function handleBuy(pkg) {
    setBuying(pkg)
    setError('')
    try {
      const data = await api.paymentCreate(pkg)
      window.location.href = data.redirect_url
    } catch (e) {
      setError(e.message || 'Payment error')
      setBuying(null)
    }
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24, fontSize: 22, fontWeight: 700 }}>Balance</h2>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard title="Credits"          value={user.credits} />
        <StatCard title="Referral balance" value={user.ref_credits} />
      </div>

      {/* Buy Credits */}
      <div className="card" style={{ maxWidth: 520, marginBottom: 16 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>Buy Credits</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {PACKAGES.map(pkg => (
            <div key={pkg.id} className="card"
                 style={{ flex: 1, minWidth: 140, textAlign: 'center',
                          background: 'var(--elevated)', position: 'relative' }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{pkg.label}</div>
              {pkg.bonus && (
                <div style={{ fontSize: 11, color: 'var(--primary-dim)',
                              marginBottom: 6 }}>{pkg.bonus}</div>
              )}
              <div className="text-muted" style={{ marginBottom: 12 }}>{pkg.price}</div>
              <button
                className="btn-primary"
                style={{ width: '100%', padding: '8px 0' }}
                disabled={buying === pkg.id}
                onClick={() => handleBuy(pkg.id)}
              >
                {buying === pkg.id ? '...' : 'Buy'}
              </button>
            </div>
          ))}
        </div>
        {error && (
          <div style={{ color: 'var(--error-text)', fontSize: 13 }}>{error}</div>
        )}
        <div className="text-muted" style={{ fontSize: 12, marginTop: 8 }}>
          Secure payment via Free-Kassa. Credits appear instantly after payment.
        </div>
      </div>

      {/* Daily Bonus stub */}
      <div className="card" style={{ maxWidth: 520 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>Daily Bonus</div>
        <div className="text-muted" style={{ marginBottom: 16 }}>
          Watch a short ad and get 3–7 free credits. Up to 3 times per day.
        </div>
        <button className="btn-primary" disabled
                style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          Watch Ad → Get Credits
        </button>
        <div className="text-muted" style={{ marginTop: 10, fontSize: 12 }}>Coming soon</div>
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
