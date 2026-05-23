import { useState, useEffect, useRef } from 'react'
import { useLang } from '../lang.js'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function plural(n, one, few, many) {
  if (n === 1) return one
  if (n >= 2 && n <= 4) return few
  return many
}

export default function RoyPage() {
  const [kingdoms, setKingdoms]   = useState([])
  const [connected, setConnected] = useState(false)
  const { lang } = useLang()
  const isRu = lang === 'ru'
  const esRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/roy/kingdoms`)
      .then(r => r.json())
      .then(d => setKingdoms(d.kingdoms || []))
      .catch(() => {})

    const es = new EventSource(`${API_BASE}/roy/status-stream`)
    esRef.current = es
    es.onopen    = () => setConnected(true)
    es.onerror   = () => setConnected(false)
    es.onmessage = (e) => {
      try {
        setKingdoms(JSON.parse(e.data))
        setConnected(true)
      } catch {}
    }
    return () => { es.close(); esRef.current = null }
  }, [])

  const sorted = [...kingdoms].sort((a, b) => b.active_count - a.active_count)

  return (
    <div style={{ padding: '24px 20px', maxWidth: 560, margin: '0 auto' }}>

      {/* ── Header card ── */}
      <div style={{
        background: 'var(--elevated)', borderRadius: 14,
        padding: '20px 24px', marginBottom: 20,
        border: '1px solid var(--outline)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 22, color: 'var(--accent)' }}>⬡</span>
          <h1 style={{ fontSize: 19, fontWeight: 800, color: 'var(--accent)', letterSpacing: '0.5px' }}>
            {isRu ? 'СИСТЕМА РОЙ' : 'SWARM SYSTEM'}
          </h1>
        </div>
        <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.55 }}>
          {isRu
            ? 'Королевства, в которых прямо сейчас идёт поиск бирж. Зелёная лампочка — в этом ГОСе есть активные искатели.'
            : 'Kingdoms where exchange hunting is running right now. Green dot means hunters are active.'}
        </p>
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: connected ? '#4ADE80' : '#3A4560',
            boxShadow: connected ? '0 0 8px rgba(74,222,128,0.7)' : 'none',
            transition: 'all 0.4s',
          }} />
          <span style={{ fontSize: 11, color: 'var(--on-surface2)' }}>
            {connected
              ? (isRu ? 'Live-обновление активно' : 'Live updates active')
              : (isRu ? 'Подключение...' : 'Connecting...')}
          </span>
        </div>
      </div>

      {/* ── Kingdom list ── */}
      <div style={{
        background: 'var(--card)', borderRadius: 14,
        border: '1px solid var(--outline)', overflow: 'hidden',
        marginBottom: 16,
      }}>
        {sorted.length === 0 ? (
          <div style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--on-surface2)', fontSize: 14 }}>
            {isRu
              ? 'Нет активных королевств. Запусти бота с номером своего Королевства — и он появится здесь.'
              : 'No kingdoms yet. Launch the bot with your kingdom number and it will appear here.'}
          </div>
        ) : sorted.map((k, i) => (
          <div key={k.kingdom} style={{
            display: 'flex', alignItems: 'center', gap: 14,
            padding: '14px 20px',
            borderBottom: i < sorted.length - 1 ? '1px solid var(--outline)' : 'none',
            background: k.active ? 'rgba(61,127,255,0.04)' : 'transparent',
            transition: 'background 0.4s',
          }}>
            {/* Status dot */}
            <span style={{
              width: 11, height: 11, borderRadius: '50%', flexShrink: 0,
              background: k.active ? '#4ADE80' : '#2A3550',
              boxShadow: k.active ? '0 0 10px rgba(74,222,128,0.65)' : 'none',
              transition: 'all 0.4s',
            }} />

            {/* Kingdom label */}
            <span style={{
              fontSize: 15, fontWeight: 700, flex: 1,
              color: k.active ? 'var(--on-surface)' : 'var(--on-surface2)',
            }}>
              {isRu ? 'Королевство' : 'Kingdom'} {k.kingdom}
            </span>

            {/* Count badge */}
            {k.active_count > 0 ? (
              <span style={{
                background: 'rgba(74,222,128,0.12)',
                border: '1px solid rgba(74,222,128,0.28)',
                color: '#4ADE80', borderRadius: 20,
                padding: '3px 12px', fontSize: 12, fontWeight: 600,
              }}>
                {k.active_count} {isRu
                  ? plural(k.active_count, 'искатель', 'искателя', 'искателей')
                  : (k.active_count === 1 ? 'hunter' : 'hunters')}
              </span>
            ) : (
              <span style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                {isRu ? 'нет активных' : 'offline'}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* ── Hint ── */}
      <div style={{
        padding: '12px 16px',
        background: 'rgba(61,127,255,0.05)',
        border: '1px solid rgba(61,127,255,0.14)',
        borderRadius: 10, fontSize: 12, color: 'var(--on-surface2)', lineHeight: 1.55,
      }}>
        💡 {isRu
          ? 'Оптимально — 5–7 искателей на одно Королевство. Если ГОС переполнен, выбери соседний.'
          : 'Optimal is 5–7 hunters per kingdom. If a kingdom is crowded, pick a nearby one.'}
      </div>
    </div>
  )
}
