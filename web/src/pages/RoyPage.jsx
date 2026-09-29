import { useState, useEffect, useRef } from 'react'
import { useLang } from '../lang.js'
import { useMeta } from '../hooks/useMeta.js'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

// Сколько находка висит на сайте — как SCOUT_FIND_TTL_MIN на сервере (roy.py)
const FIND_TTL_MS = 30 * 60 * 1000

// Формат координат как в игре (владелец 2026-09-29): вставленная в чат строка становится ссылкой
function coordText(f) { return `K:${f.kingdom} X:${f.x} Y:${f.y}` }

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // старые браузеры / нет разрешения — через скрытое поле
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    let ok = false
    try { ok = document.execCommand('copy') } catch { ok = false }
    document.body.removeChild(ta)
    return ok
  }
}

function fmtLeft(ms) {
  const total = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(total / 60)
  const sec = total % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

function plural(n, one, few, many) {
  if (n === 1) return one
  if (n >= 2 && n <= 4) return few
  return many
}

export default function RoyPage() {
  const [kingdoms, setKingdoms]   = useState([])
  const [connected, setConnected] = useState(false)
  const [finds, setFinds]         = useState(null)
  const [pool, setPool]           = useState([])
  const [findsError, setFindsError] = useState(false)
  const [now, setNow]             = useState(() => Date.now())
  const [copiedKey, setCopiedKey] = useState(null)
  const { lang } = useLang()
  useMeta({
    title:       lang === 'ru' ? 'Total Hunter — Система РОЙ' : 'Total Hunter — SWARM System',
    description: lang === 'ru' ? 'Коллективный пул координат бирж. Живые данные от охотников королевства.' : 'Collective exchange coordinate pool. Live data from kingdom hunters.',
  })
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

  const loadFinds = () => {
    fetch(`${API_BASE}/roy/scout-finds`)
      .then(r => { if (!r.ok) throw new Error('http'); return r.json() })
      .then(d => { setFinds(d.finds || []); setFindsError(false) })
      .catch(() => setFindsError(true))
    // биржи 1.0 из пула РОЙ — пока открыта дверь (ROY_OPEN_DOOR на сервере), иначе пустой список
    fetch(`${API_BASE}/roy/public-pool`)
      .then(r => { if (!r.ok) throw new Error('http'); return r.json() })
      .then(d => setPool(d.pool || []))
      .catch(() => setPool([]))
  }
  // находки подтягиваются сами раз в 30 с; таймер тикает каждую секунду
  useEffect(() => {
    loadFinds()
    const poll = setInterval(loadFinds, 30000)
    const tick = setInterval(() => setNow(Date.now()), 1000)
    return () => { clearInterval(poll); clearInterval(tick) }
  }, [])

  async function onCopy(f, key) {
    if (await copyText(coordText(f))) {
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(k => (k === key ? null : k)), 1500)
    }
  }

  // Биржа 1.0 — точные координаты и заполнение, живёт до expires_at сервера;
  // Биржа 2.0 — примерные, 30 минут с публикации. Один список, свежие сверху.
  const liveFinds = [
    ...pool.map(e => ({ ...e, exact: true, shownAt: e.updated_at || e.expires_at,
                        left: new Date(e.expires_at).getTime() - now })),
    ...(finds || []).map(f => ({ ...f, exact: false, shownAt: f.found_at,
                                 left: new Date(f.found_at).getTime() + FIND_TTL_MS - now })),
  ]
    .filter(f => f.left > 0)
    .sort((a, b) => new Date(b.shownAt) - new Date(a.shownAt))

  // Найденные биржи — наверху страницы (владелец 2026-09-29), список королевств — ниже
  const findsCard = (
    <div style={{
      background: 'var(--card)', borderRadius: 14, border: '1px solid var(--outline)',
      padding: '18px 20px', marginBottom: 20,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <h1 style={{ fontSize: 21, fontWeight: 800, color: 'var(--accent)', margin: 0 }}>
          {isRu ? 'Найденные биржи' : 'Found exchanges'}
        </h1>
        <button onClick={loadFinds} style={{
          background: 'transparent', border: '1px solid var(--outline)', color: 'var(--on-surface2)',
          borderRadius: 8, padding: '6px 14px', fontSize: 15, cursor: 'pointer',
        }}>{isRu ? 'Обновить' : 'Refresh'}</button>
      </div>
      <p style={{ fontSize: 15, color: 'var(--on-surface2)', lineHeight: 1.55, margin: '10px 0 12px' }}>
        {isRu
          ? 'Нажмите на координаты — они скопируются, вставьте в чат игры, получится ссылка. «Точные» — координаты самой биржи и её заполнение. «Примерные» — позиция экрана бота в момент кадра, биржа где-то рядом.'
          : 'Tap the coordinates to copy them, paste into the game chat and it becomes a link. "Exact" — the exchange itself and how full it is. "Approximate" — the bot screen position at the moment of the frame, the exchange is nearby.'}
      </p>
      {findsError ? (
        <div style={{ fontSize: 16, color: 'var(--on-surface2)' }}>
          {isRu ? 'Не удалось загрузить находки.' : 'Failed to load finds.'}
        </div>
      ) : finds === null ? null : liveFinds.length === 0 ? (
        <div style={{ fontSize: 16, color: 'var(--on-surface2)' }}>
          {isRu ? 'Сейчас находок нет.' : 'No finds right now.'}
        </div>
      ) : liveFinds.map((f, i) => {
        const key = `${f.exact ? 'p' : 's'}-${f.kingdom}-${f.x}-${f.y}-${f.shownAt}`
        const copied = copiedKey === key
        return (
          <div key={key} style={{
            display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px 14px', padding: '12px 0',
            borderTop: i === 0 ? 'none' : '1px solid var(--outline)',
          }}>
            <button onClick={() => onCopy(f, key)} title={isRu ? 'Скопировать' : 'Copy'} style={{
              background: copied ? 'rgba(74,222,128,0.14)' : 'rgba(61,127,255,0.10)',
              border: `1px solid ${copied ? 'rgba(74,222,128,0.5)' : 'rgba(61,127,255,0.35)'}`,
              color: copied ? '#4ADE80' : 'var(--on-surface)', borderRadius: 8,
              padding: '8px 14px', fontSize: 19, fontWeight: 700, cursor: 'pointer',
              fontVariantNumeric: 'tabular-nums', transition: 'all 0.2s',
            }}>
              {coordText(f)} <span style={{ fontSize: 15, fontWeight: 600, marginLeft: 6 }}>
                {copied ? (isRu ? '✓ скопировано' : '✓ copied') : '⧉'}
              </span>
            </button>
            <span style={{ marginLeft: 'auto', textAlign: 'right', fontSize: 16, lineHeight: 1.35 }}>
              <span style={{ color: f.left < 5 * 60 * 1000 ? '#F87171' : 'var(--credits-gold)', fontWeight: 700,
                             fontVariantNumeric: 'tabular-nums' }}>
                {isRu ? 'осталось' : 'left'} {fmtLeft(f.left)}
              </span>
              <br />
              <span style={{ color: 'var(--on-surface2)', fontSize: 14 }}>
                {isRu ? 'найдена' : 'found'} {new Date(f.shownAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <br />
              <span style={{ fontSize: 14, fontWeight: 600, color: f.exact ? '#4ADE80' : 'var(--on-surface2)' }}>
                {f.exact
                  ? (isRu ? `точные · заполнена ${f.percent}%` : `exact · ${f.percent}% full`)
                  : (isRu ? 'примерные' : 'approximate')}
              </span>
            </span>
          </div>
        )
      })}
    </div>
  )

  return (
    <div style={{ padding: '24px 20px', maxWidth: 560, margin: '0 auto' }}>
      {findsCard}

      {/* ── Header card ── */}
      <div style={{
        background: 'var(--elevated)', borderRadius: 14,
        padding: '20px 24px', marginBottom: 20,
        border: '1px solid var(--outline)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 22, color: 'var(--accent)' }}>⬡</span>
          <h2 style={{ fontSize: 19, fontWeight: 800, color: 'var(--accent)', letterSpacing: '0.5px', margin: 0 }}>
            {isRu ? 'СИСТЕМА РОЙ' : 'SWARM SYSTEM'}
          </h2>
        </div>
        <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.55 }}>
          {isRu
            ? 'Королевства, где охотники настроили поиск бирж. Зелёный — активное сканирование прямо сейчас (ивент идёт). Серый — охотник зарегистрирован в этом Королевстве.'
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
          {isRu ? 'Зарегистрирован в Королевстве' : 'Registered in kingdom'}
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
          ? 'Оптимально — 5–7 охотников на одно Королевство. Если Королевство переполнено, выбери соседнее.'
          : 'Optimal is 5–7 hunters per kingdom. If a kingdom is crowded, pick a nearby one.'}
      </div>
    </div>
  )
}
