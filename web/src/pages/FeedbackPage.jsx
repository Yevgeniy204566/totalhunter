import { useState } from 'react'
import { api } from '../api.js'

export default function FeedbackPage() {
  const [text, setText]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)

  async function send() {
    if (!text.trim()) return
    setLoading(true)
    setMsg('')
    try {
      const res = await api.sendFeedback(text.trim())
      setMsg(res.message)
      setText('')
    } catch (e) {
      setMsg(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 8, fontSize: 22, fontWeight: 700 }}>Feedback</h2>
      <p className="text-muted" style={{ marginBottom: 24 }}>
        Got an idea or suggestion? We read every message.
      </p>
      <div className="card" style={{ maxWidth: 520 }}>
        <textarea
          value={text}
          onChange={e => setText(e.target.value.slice(0, 1000))}
          placeholder="Your idea or suggestion..."
          rows={5}
          style={{
            width: '100%', background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 8, color: 'var(--on-surface)', padding: '14px', fontSize: 15,
            resize: 'vertical', marginBottom: 16, fontFamily: 'inherit',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="text-muted" style={{ fontSize: 12 }}>
            {text.length} / 1000
          </span>
          <button
            className="btn-primary"
            onClick={send}
            disabled={loading || !text.trim()}
          >
            {loading ? 'Sending...' : 'Send Idea'}
          </button>
        </div>
        {msg && (
          <div className="text-muted" style={{ marginTop: 14 }}>{msg}</div>
        )}
      </div>
    </div>
  )
}
