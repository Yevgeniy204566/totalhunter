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
            ? 'Королевства, где охотники настроили поиск бирж. Зелёный — активное сканирование прямо сейчас (ивент идёт). Серый — охотник зарегистрирован в этом ГОСе.'
            : 'Kingdoms where hunters are configured. Green = actively scanning right now (event live). Grey = hunter registered in this kingdom.'}
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
        {kingdoms.length === 0 ? (
          <div style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--on-surface2)', fontSize: 14 }}>
            {isRu
              ? 'Нет зарегистрированных королевств. Укажи номер своего Королевства в боте — и оно появится здесь.'
              : 'No kingdoms yet. Set your kingdom number in the bot and it will appear here.'}
          </div>
        ) : kingdoms.map((k, i) => (
          <div key={k.kingdom} style={{
            display: 'flex', alignItems: 'center', gap: 14,
            padding: '14px 20px',
            borderBottom: i < kingdoms.length - 1 ? '1px solid var(--outline)' : 'none',
            background: k.active ? 'rgba(61,127,255,0.04)' : 'transparent',
            transition: 'background 0.4s',
          }}>
            {/* Status dot */}
            <span style={{
              width: 11, height: 11, borderRadius: '50%', flexShrink: 0,
              background: k.active ? '#4ADE80' : '#3A4560',
              boxShadow: k.active ? '0 0 10px rgba(74,222,128,0.65)' : 'none',
              border: k.active ? 'none' : '1.5px solid #5A6580',
              transition: 'all 0.4s',
            }} />

            {/* Kingdom label */}
            <span style={{
              fontSize: 15, fontWeight: 700, flex: 1,
              color: k.active ? 'var(--on-surface)' : 'var(--on-surface2)',
            }}>
              {isRu ? 'Королевство' : 'Kingdom'} {k.kingdom}
            </span>

            {/* Badges */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {/* Registered (grey) */}
              {k.registered_count > 0 && (
                <span style={{
                  background: 'rgba(90,101,128,0.18)',
                  border: '1px solid rgba(90,101,128,0.35)',
                  color: '#8A9AB5', borderRadius: 20,
                  padding: '3px 10px', fontSize: 11, fontWeight: 600,
                }}>
                  {k.registered_count} {isRu
                    ? plural(k.registered_count, 'охотник', 'охотника', 'охотников')
                    : (k.registered_count === 1 ? 'member' : 'members')}
                </span>
              )}
              {/* Active (green) */}
              {k.active_count > 0 ? (
                <span style={{
                  background: 'rgba(74,222,128,0.12)',
                  border: '1px solid rgba(74,222,128,0.28)',
                  color: '#4ADE80', borderRadius: 20,
                  padding: '3px 10px', fontSize: 11, fontWeight: 600,
                }}>
                  {k.active_count} {isRu
                    ? plural(k.active_count, 'онлайн', 'онлайн', 'онлайн')
                    : (k.active_count === 1 ? 'online' : 'online')}
                </span>
              ) : (
                <span style={{ fontSize: 11, color: 'var(--on-surface2)' }}>
                  {isRu ? 'ивент не идёт' : 'event offline'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ── Legend ── */}
      <div style={{
        display: 'flex', gap: 20, marginBottom: 12,
        padding: '10px 16px',
        background: 'rgba(61,127,255,0.04)',
        border: '1px solid rgba(61,127,255,0.10)',
        borderRadius: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--on-surface2)' }}>
          <span style={{
            width: 9, height: 9, borderRadius: '50%', flexShrink: 0,
            background: '#3A4560', border: '1.5px solid #5A6580',
          }} />
          {isRu ? 'Зарегистрирован в ГОСе' : 'Registered in kingdom'}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--on-surface2)' }}>
          <span style={{
            width: 9, height: 9, borderRadius: '50%', flexShrink: 0,
            background: '#4ADE80', boxShadow: '0 0 6px rgba(74,222,128,0.5)',
          }} />
          {isRu ? 'Сканирует во время ивента' : 'Scanning during event'}
        </div>
      </div>

      {/* ── Hint ── */}
      <div style={{
        padding: '12px 16px',
        background: 'rgba(61,127,255,0.05)',
        border: '1px solid rgba(61,127,255,0.14)',
        borderRadius: 10, fontSize: 12, color: 'var(--on-surface2)', lineHeight: 1.55,
      }}>
        💡 {isRu
          ? 'Оптимально — 5–7 охотников на одно Королевство. Если ГОС переполнен, выбери соседний.'
          : 'Optimal is 5–7 hunters per kingdom. If a kingdom is crowded, pick a nearby one.'}
      </div>
    </div>
  )
}
