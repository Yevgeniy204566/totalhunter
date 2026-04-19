import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function ReferralsPage() {
  const [user, setUser]     = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => { api.me().then(setUser) }, [])

  function copyCode() {
    navigator.clipboard.writeText(user.ref_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  const refLink = `https://total-hunter.vercel.app/login?ref=${user.ref_code}`

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>Referrals</h2>
      <div className="card" style={{ maxWidth: 480, marginBottom: 16 }}>
        <div className="text-muted" style={{ marginBottom: 8 }}>Your referral code</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <code style={{ fontSize: 22, fontWeight: 600, color: 'var(--primary-dim)' }}>{user.ref_code}</code>
          <button className="btn-secondary" onClick={copyCode} style={{ padding: '6px 14px' }}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <div className="separator" />
        <div className="text-muted" style={{ fontSize: 12, wordBreak: 'break-all' }}>{refLink}</div>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <div className="text-muted" style={{ marginBottom: 16 }}>How it works</div>
        <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--on-surface2)' }}>
          Share your code with other players. When they activate it in the bot, you both get bonus credits.
          Referral earnings go to your referral balance — transfer them to main balance anytime.
        </p>
        <div className="separator" />
        <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
          Referral balance: <strong style={{ color: 'var(--on-surface)' }}>{user.ref_credits} credits</strong>
        </div>
      </div>
    </div>
  )
}
