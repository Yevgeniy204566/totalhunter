import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

export default function DevicesPage() {
  const [user, setUser]       = useState(null)
  const [code, setCode]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const dv = D.devices

  async function refresh() { const u = await api.me(); setUser(u) }
  useEffect(() => { refresh() }, [])

  async function linkHwid() {
    if (code.length !== 6) { setMsg(dv.codeError); return }
    setLoading(true)
    try {
      const res = await api.linkVerify(code)
      setMsg(res.message); setCode('')
      await refresh()
    } catch (e) { setMsg(e.message) }
    finally { setLoading(false) }
  }

  async function resetHwid() {
    if (!confirm(dv.unlink)) return
    setLoading(true)
    try {
      const res = await api.hwidReset()
      setMsg(res.message); await refresh()
    } catch (e) { setMsg(e.message) }
    finally { setLoading(false) }
  }

  if (!user) return <div className="page-content text-muted">{D.loading}</div>

  const nextReset = user.hwid_reset_at
    ? new Date(new Date(user.hwid_reset_at).getTime() + 7 * 86400 * 1000).toLocaleDateString()
    : null

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>{dv.title}</h2>

      {user.hwid ? (
        <div className="card" style={{ maxWidth: 480, marginBottom: 16 }}>
          <div className="text-muted" style={{ marginBottom: 8 }}>{dv.linked}</div>
          <code style={{ fontSize: 18, fontWeight: 600 }}>{user.hwid}</code>
          <div className="separator" />
          <button
            className="btn-secondary"
            onClick={resetHwid}
            disabled={loading}
            style={{ borderColor: 'var(--error)', color: 'var(--error-text)' }}
          >
            {dv.unlink}
          </button>
          {nextReset && (
            <div className="text-muted" style={{ marginTop: 8, fontSize: 12 }}>
              {dv.nextReset} {nextReset}
            </div>
          )}
        </div>
      ) : (
        <div className="card" style={{ maxWidth: 480, marginBottom: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8 }}>{dv.linkTitle}</div>
            <ol style={{ paddingLeft: 20, color: 'var(--on-surface2)', fontSize: 14, lineHeight: 2 }}>
              {dv.linkSteps.map((step, i) => <li key={i}>{step}</li>)}
            </ol>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <input
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder={dv.placeholder}
              style={{
                flex: 1, background: 'var(--elevated)', border: '1px solid var(--outline)',
                color: 'var(--on-surface)', borderRadius: 6, padding: '10px 14px',
                fontSize: 20, letterSpacing: 8, textAlign: 'center',
              }}
            />
            <button className="btn-primary" onClick={linkHwid} disabled={loading || code.length !== 6}>
              {loading ? '...' : dv.linkBtn}
            </button>
          </div>
        </div>
      )}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
