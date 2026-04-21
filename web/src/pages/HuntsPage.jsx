import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'

const HUNT_META = {
  exchange: { icon: '⚔', label: 'Биржа',  color: 'var(--accent)',       bg: 'rgba(61,127,255,0.12)'  },
  crypt:    { icon: '💀', label: 'Склеп',  color: '#B060FF',             bg: 'rgba(176,96,255,0.12)'  },
}

function StatTile({ icon, label, color, value }) {
  const animated = useCounter(typeof value === 'number' ? value : null, 1000)
  return (
    <div style={{
      flex: '1 1 140px',
      background: 'var(--elevated)',
      border: '1px solid var(--outline)',
      borderRadius: 12, padding: '20px 16px', textAlign: 'center',
      transition: 'box-shadow 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.boxShadow = `0 0 20px ${color}44`
      e.currentTarget.style.borderColor = `${color}55`
    }}
    onMouseLeave={e => {
      e.currentTarget.style.boxShadow = ''
      e.currentTarget.style.borderColor = 'var(--outline)'
    }}>
      <div style={{ fontSize: 20, marginBottom: 8 }}>{icon}</div>
      <div style={{
        fontSize: 36, fontWeight: 800, color, lineHeight: 1, marginBottom: 6,
        textShadow: `0 0 20px ${color}88`,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {value != null ? animated : '—'}
      </div>
      <div style={{ fontSize: 12, color: '#C8D8F0', fontWeight: 500 }}>{label}</div>
    </div>
  )
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso)) / 1000
  if (diff < 60)    return 'только что'
  if (diff < 3600)  return `${Math.floor(diff / 60)} мин назад`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`
  return `${Math.floor(diff / 86400)} дн назад`
}

export default function HuntsPage() {
  const [data, setData] = useState(null)

  useEffect(() => { api.hunts().then(setData) }, [])

  if (!data) return <div className="page-content text-muted">Загрузка...</div>

  const items = data.items ?? []
  const exchanges = items.filter(h => h.hunt_type === 'exchange').length
  const crypts    = items.filter(h => h.hunt_type === 'crypt').length
  const visTotal  = exchanges + crypts
  const exRatio   = visTotal > 0 ? (exchanges / visTotal) * 100 : 50

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 100% 40% at 50% 0%, rgba(61,127,255,0.06) 0%, transparent 55%)',
      padding: '32px 24px', maxWidth: 960, margin: '0 auto',
    }}>
      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 24 }}>
        История охот
      </h2>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
        <StatTile icon="⚔" label="Сегодня"      color="var(--accent)" value={data.today} />
        <StatTile icon="📅" label="За 7 дней"    color="#B060FF"       value={data.week}  />
        <StatTile icon="◈"  label="Всего охот"   color="var(--credits-gold)" value={data.total} />
      </div>

      {/* Exchange vs Crypt ratio bar */}
      {visTotal > 0 && (
        <div className="card" style={{ borderRadius: 12, marginBottom: 24, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 600 }}>
              ⚔ Биржи — {exchanges}
            </span>
            <span style={{ fontSize: 13, color: '#B060FF', fontWeight: 600 }}>
              {crypts} — Склепы 💀
            </span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: 'var(--outline)', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 4,
              width: `${exRatio}%`,
              background: 'linear-gradient(90deg, var(--accent), #B060FF)',
              transition: 'width 0.8s ease',
            }} />
          </div>
          <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginTop: 6, textAlign: 'center' }}>
            последние {visTotal} записей
          </div>
        </div>
      )}

      {/* Hunt list */}
      <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
        {/* Header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '40px 1fr 1fr',
          padding: '10px 20px',
          borderBottom: '1px solid var(--outline)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1px',
          color: 'var(--on-surface2)', textTransform: 'uppercase',
        }}>
          <div />
          <div>Тип</div>
          <div style={{ textAlign: 'right' }}>Время</div>
        </div>

        {items.length === 0 ? (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--on-surface2)' }}>
            Охот пока нет. Запусти бота! ⚔
          </div>
        ) : (
          items.map((h, i) => {
            const meta = HUNT_META[h.hunt_type] ?? { icon: '◈', label: h.hunt_type, color: 'var(--on-surface2)', bg: 'transparent' }
            return (
              <div key={i} style={{
                display: 'grid', gridTemplateColumns: '40px 1fr 1fr',
                alignItems: 'center', padding: '12px 20px',
                borderBottom: i < items.length - 1 ? '1px solid var(--separator)' : 'none',
                transition: 'background 0.12s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <div style={{
                  width: 30, height: 30, borderRadius: 8,
                  background: meta.bg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14,
                }}>
                  {meta.icon}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: meta.color }}>
                  {meta.label}
                </div>
                <div style={{ fontSize: 12, color: 'var(--on-surface2)', textAlign: 'right' }}>
                  {timeAgo(h.created_at)}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
