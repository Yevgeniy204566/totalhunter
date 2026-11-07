import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

// Серверный предел (server/schemas.py: FeedbackRequest.text max_length=1000).
const LIMIT = 1000

export default function FeedbackPage() {
  const [text, setText]       = useState('')
  const [status, setStatus]   = useState(null)   // null | 'ok' | 'error'
  const [loading, setLoading] = useState(false)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const f = D.feedback
  useMeta({
    title:       lang === 'ru' ? 'Total Hunter — Обратная связь' : 'Total Hunter — Feedback',
    description: lang === 'ru' ? 'Отправьте отзыв или сообщение о проблеме команде Total Hunter.' : 'Send feedback or report an issue to the Total Hunter team.',
  })

  async function send() {
    if (!text.trim()) return
    setLoading(true); setStatus(null)
    try {
      await api.sendFeedback(text.trim())
      setStatus('ok')
      setText('')
    } catch (e) {
      // Текст остаётся в поле — пользователь может отправить ещё раз, ничего не теряется.
      setStatus('error')
    } finally { setLoading(false) }
  }

  const nearLimit = text.length >= LIMIT - 50
  const atLimit   = text.length >= LIMIT

  // «Входящие»: переписка с администратором (ответ появляется здесь, игрок может ответить).
  const [tab, setTab]           = useState('write')   // 'write' | 'inbox'
  const [messages, setMessages] = useState(null)      // null = ещё не загружено
  function loadThread() {
    api.feedbackThread().then(d => setMessages(d.messages || [])).catch(() => setMessages([]))
  }
  useEffect(() => { loadThread() }, [])
  // Если есть непрочитанный ответ — при первой загрузке сразу показываем «Входящие».
  useEffect(() => {
    if (messages && messages.some(m => m.is_new)) setTab('inbox')
  }, [messages === null])
  async function sendReply() {
    if (!text.trim()) return
    setLoading(true); setStatus(null)
    try {
      await api.sendFeedback(text.trim())
      setText('')
      loadThread()
    } catch (e) { setStatus('error') } finally { setLoading(false) }
  }
  const tabBtn = (id, label) => (
    <button
      key={id} onClick={() => { setTab(id); setStatus(null); if (id === 'inbox') loadThread() }}
      className={tab === id ? 'btn-primary' : 'btn-ghost'}
      style={{ fontSize: 16, marginRight: 8 }}
    >{label}</button>
  )
  const fmt = iso => iso ? new Date(iso).toLocaleString(lang === 'ru' ? 'ru-RU' : 'en-GB') : ''

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 8, fontSize: 22, fontWeight: 700 }}>{f.title}</h2>
      <p className="text-muted" style={{ marginBottom: 16, fontSize: 16 }}>{f.sub}</p>
      <div style={{ marginBottom: 16 }}>
        {tabBtn('write', f.tabWrite)}
        {tabBtn('inbox', f.tabInbox)}
      </div>
      {tab === 'inbox' && (
        <div className="card" style={{ maxWidth: 680 }}>
          {messages && messages.length === 0 && (
            <p className="text-muted" style={{ fontSize: 16 }}>{f.inboxEmpty}</p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
            {(messages || []).map(m => (
              <div key={m.id} style={{
                alignSelf: m.sender === 'admin' ? 'flex-start' : 'flex-end', maxWidth: '88%',
                padding: '10px 14px', borderRadius: 10, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                background: m.sender === 'admin' ? 'var(--elevated)' : 'rgba(99,102,241,.22)',
                border: m.is_new ? '1px solid #fbbf24' : '1px solid transparent',
              }}>
                <div className="text-muted" style={{ fontSize: 14, marginBottom: 4 }}>
                  {m.sender === 'admin' ? f.fromAdmin : f.fromYou} · {fmt(m.created_at)}
                  {m.is_new && <span style={{ color: '#fbbf24' }}> · {f.isNew}</span>}
                </div>
                <div style={{ fontSize: 16, lineHeight: 1.5 }}>{m.text}</div>
              </div>
            ))}
          </div>
          {messages && messages.length > 0 && (
            <>
              <label htmlFor="reply-text" style={{ display: 'block', fontSize: 16, fontWeight: 600, marginBottom: 6 }}>{f.replyLabel}</label>
              <p className="text-muted" style={{ fontSize: 14, marginBottom: 8 }}>{f.replyHint}</p>
              <textarea
                id="reply-text" value={text} rows={4} maxLength={LIMIT}
                onChange={e => { setText(e.target.value.slice(0, LIMIT)); if (status) setStatus(null) }}
                style={{
                  width: '100%', boxSizing: 'border-box', background: 'var(--elevated)', border: '1px solid var(--outline)',
                  borderRadius: 8, color: 'var(--on-surface)', padding: 12, fontSize: 16, lineHeight: 1.55,
                  resize: 'vertical', marginBottom: 10, fontFamily: 'inherit',
                }}
              />
              <button className="btn-primary" onClick={sendReply} disabled={loading || !text.trim()} style={{ fontSize: 16 }}>
                {loading ? f.sending : f.send}
              </button>
              {status === 'error' && (
                <div role="alert" style={{ marginTop: 12, fontSize: 16, color: 'var(--error-text)' }}>{f.error}</div>
              )}
            </>
          )}
        </div>
      )}
      {tab === 'write' && (
      <div className="card" style={{ maxWidth: 680 }}>
        <label htmlFor="feedback-text" style={{ display: 'block', fontSize: 16, fontWeight: 600, marginBottom: 10 }}>
          {f.label}
        </label>
        <textarea
          id="feedback-text"
          value={text}
          onChange={e => { setText(e.target.value.slice(0, LIMIT)); if (status) setStatus(null) }}
          placeholder={f.placeholder}
          rows={9}
          maxLength={LIMIT}
          spellCheck
          style={{
            width: '100%', boxSizing: 'border-box', minHeight: 200,
            background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 8, color: 'var(--on-surface)', padding: 16, fontSize: 16, lineHeight: 1.55,
            resize: 'vertical', marginBottom: 10, fontFamily: 'inherit',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span
            className="text-muted"
            style={{ fontSize: 14, color: nearLimit ? 'var(--error-text)' : undefined }}
          >
            {text.length} / {LIMIT}{atLimit ? ` — ${f.limitHint}` : ''}
          </span>
          <button className="btn-primary" onClick={send} disabled={loading || !text.trim()} style={{ fontSize: 16 }}>
            {loading ? f.sending : f.send}
          </button>
        </div>
        {status === 'ok' && (
          <div role="status" style={{ marginTop: 16, fontSize: 16, color: '#4ADE80' }}>✓ {f.thanks}</div>
        )}
        {status === 'error' && (
          <div role="alert" style={{ marginTop: 16, fontSize: 16, color: 'var(--error-text)' }}>{f.error}</div>
        )}
      </div>
      )}
    </div>
  )
}
