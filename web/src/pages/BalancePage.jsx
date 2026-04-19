import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function BalancePage() {
  const [user, setUser]       = useState(null)
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => { api.me().then(setUser) }, [])

  async function transfer() {
    setLoading(true)
    try {
      const res = await api.referralTransfer()
      setMsg(res.message)
      const updated = await api.me()
      setUser(updated)
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>Balance</h2>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard title="Credits"          value={user.credits} />
        <StatCard title="Referral balance" value={user.ref_credits} />
      </div>
      {user.ref_credits > 0 && (
        <button className="btn-primary" onClick={transfer} disabled={loading}>
          {loading ? 'Transferring...' : `Transfer ${user.ref_credits} ref credits → main balance`}
        </button>
      )}
      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
      <div className="separator" />
      <p className="text-muted">To top up your balance, use the referral system or contact support.</p>
    </div>
  )
}

function StatCard({ title, value }) {
  return (
    <div className="card" style={{ minWidth: 160 }}>
      <div className="text-muted" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 600 }}>{value}</div>
    </div>
  )
}
