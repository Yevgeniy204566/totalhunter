import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function ReferralsPage() {
  const [user, setUser]       = useState(null)
  const [copied, setCopied]   = useState(false)
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)

  async function refresh() { api.me().then(setUser) }
  useEffect(() => { refresh() }, [])

  function copyLink() {
    navigator.clipboard.writeText(refLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function transfer() {
    setLoading(true)
    setMsg('')
    try {
      const res = await api.referralTransfer()
      setMsg(res.message)
      await refresh()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  const refLink = `https://totalhunter.vercel.app/ref/${user.ref_code}`

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24, fontSize: 22, fontWeight: 700 }}>Referrals</h2>

      <div className="card" style={{ maxWidth: 520, marginBottom: 16 }}>
        <div className="text-muted" style={{ marginBottom: 8 }}>Your referral link</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8,
                      flexWrap: 'wrap' }}>
          <code style={{ fontSize: 13, color: 'var(--primary-dim)', wordBreak: 'break-all',
                         flex: 1 }}>
            {refLink}
          </code>
          <button className="btn-secondary" onClick={copyLink}
                  style={{ padding: '10px 20px', flexShrink: 0 }}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <div className="text-muted" style={{ fontSize: 12 }}>
          Code: <strong>{user.ref_code}</strong>
        </div>

        <div className="separator" />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      flexWrap: 'wrap', gap: 12 }}>
          <span className="text-muted">
            Referral balance:{' '}
            <strong style={{ color: 'var(--on-surface)' }}>{user.ref_credits} credits</strong>
          </span>
          <button
            className="btn-green"
            onClick={transfer}
            disabled={loading || user.ref_credits === 0}
            style={{ padding: '12px 24px' }}
          >
            {loading ? 'Transferring...' : 'Transfer to Balance'}
          </button>
        </div>
        {msg && (
          <div className="text-muted" style={{ marginTop: 10 }}>{msg}</div>
        )}
      </div>

      <div className="card" style={{ maxWidth: 520 }}>
        <div className="text-muted" style={{ marginBottom: 12 }}>How it works</div>
        <p style={{ fontSize: 14, lineHeight: 1.8, color: 'var(--on-surface2)' }}>
          Share your link with other players. When they register using your link, you both
          get bonus credits. Referral earnings go to your referral balance — transfer them
          to your main balance anytime.
        </p>
      </div>
    </div>
  )
}
