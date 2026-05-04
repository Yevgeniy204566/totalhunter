import { useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

export default function FeedbackPage() {
  const [text, setText]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const f = D.feedback

  async function send() {
    if (!text.trim()) return
    setLoading(true); setMsg('')
    try {
      const res = await api.sendFeedback(text.trim())
      setMsg(res.message)
      setText('')
    } catch (e) { setMsg(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 8, fontSize: 22, fontWeight: 700 }}>{f.title}</h2>
      <p className="text-muted" style={{ marginBottom: 24 }}>{f.sub}</p>
      <div className="card" style={{ maxWidth: 520 }}>
        <textarea
          value={text}
          onChange={e => setText(e.target.value.slice(0, 1000))}
          placeholder={f.placeholder}
          rows={5}
          style={{
            width: '100%', background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 8, color: 'var(--on-surface)', padding: '14px', fontSize: 15,
            resize: 'vertical', marginBottom: 16, fontFamily: 'inherit',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="text-muted" style={{ fontSize: 12 }}>{text.length} / 1000</span>
          <button className="btn-primary" onClick={send} disabled={loading || !text.trim()}>
            {loading ? f.sending : f.send}
          </button>
        </div>
        {msg && <div className="text-muted" style={{ marginTop: 14 }}>{msg}</div>}
      </div>
    </div>
  )
}
