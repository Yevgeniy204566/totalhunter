import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function DevicesPage() {
  const [user, setUser]       = useState(null)
  const [code, setCode]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)

  async function refresh() { const u = await api.me(); setUser(u) }
  useEffect(() => { refresh() }, [])

  async function linkHwid() {
    if (code.length !== 6) { setMsg('Code must be 6 digits'); return }
    setLoading(true)
    try {
      const res = await api.linkVerify(code)
      setMsg(res.message)
      setCode('')
      await refresh()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function resetHwid() {
    if (!confirm('Unlink your current device? You will need to re-link from the bot.')) return
    setLoading(true)
    try {
      const res = await api.hwidReset()
      setMsg(res.message)
      await refresh()
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  const nextReset = user.hwid_reset_at
    ? new Date(new Date(user.hwid_reset_at).getTime() + 7 * 86400 * 1000).toLocaleDateString()
    : null

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>Devices</h2>

      {user.hwid ? (
        <div className="card" style={{ maxWidth: 480, marginBottom: 16 }}>
          <div className="text-muted" style={{ marginBottom: 8 }}>Linked device</div>
          <code style={{ fontSize: 18, fontWeight: 600 }}>{user.hwid}</code>
          <div className="separator" />
          <button
            className="btn-secondary"
            onClick={resetHwid}
            disabled={loading}
            style={{ borderColor: 'var(--error)', color: 'var(--error-text)' }}
          >
            Unlink device (reset HWID)
          </button>
          {nextReset && (
            <div className="text-muted" style={{ marginTop: 8, fontSize: 12 }}>
              Next reset available: {nextReset}
            </div>
          )}
        </div>
      ) : (
        <div className="card" style={{ maxWidth: 480, marginBottom: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8 }}>Link your device</div>
            <ol style={{ paddingLeft: 20, color: 'var(--on-surface2)', fontSize: 14, lineHeight: 2 }}>
              <li>Open the bot on your computer</li>
              <li>Go to the <strong>Profile</strong> tab</li>
              <li>Click <strong>Generate link code</strong></li>
              <li>Enter the 6-digit code below</li>
            </ol>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <input
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              style={{
                flex: 1, background: 'var(--elevated)', border: '1px solid var(--outline)',
                color: 'var(--on-surface)', borderRadius: 6, padding: '10px 14px',
                fontSize: 20, letterSpacing: 8, textAlign: 'center',
              }}
            />
            <button className="btn-primary" onClick={linkHwid} disabled={loading || code.length !== 6}>
              {loading ? '...' : 'Link'}
            </button>
          </div>
        </div>
      )}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
