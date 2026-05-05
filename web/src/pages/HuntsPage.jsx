import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const HUNT_COLORS = {
  exchange: { color: '#B060FF', bg: 'rgba(176,96,255,0.12)' },
  crypt:    { color: '#4ADE80', bg: 'rgba(74,222,128,0.10)' },
}

function StatTile({ icon, label, color, value }) {
  const animated = useCounter(typeof value === 'number' ? value : null, 1000)
  return (
    <div style={{
      flex: '1 1 140px', background: 'var(--elevated)',
      border: '1px solid var(--outline)', borderRadius: 12,
      padding: '20px 16px', textAlign: 'center', transition: 'box-shadow 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 20px ${color}44`; e.currentTarget.style.borderColor = `${color}55` }}
    onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.borderColor = 'var(--outline)' }}>
      <div style={{ fontSize: 20, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 36, fontWeight: 800, color, lineHeight: 1, marginBottom: 6,
                    textShadow: `0 0 20px ${color}88`, fontVariantNumeric: 'tabular-nums' }}>
        {value != null ? animated : '—'}
      </div>
      <div style={{ fontSize: 12, color: '#C8D8F0', fontWeight: 500 }}>{label}</div>
    </div>
  )
}

export default function HuntsPage() {
  const [data, setData] = useState(null)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const h = D.hunts
  const ta = D.timeAgo

  function timeAgo(iso) {
    const diff = (Date.now() - new Date(iso)) / 1000
    if (diff < 60)    return ta.justNow
    if (diff < 3600)  return `${Math.floor(diff / 60)} ${ta.minutesAgo}`
    if (diff < 86400) return `${Math.floor(diff / 3600)} ${ta.hoursAgo}`
    return `${Math.floor(diff / 86400)} ${ta.daysAgo}`
  }

  useEffect(() => { api.hunts().then(setData) }, [])

  if (!data) return <div className="page-content text-muted">{D.loading}</div>

  const items    = data.items ?? []
  const exchanges = items.filter(i => i.hunt_type === 'exchange').length
  const crypts    = items.filter(i => i.hunt_type === 'crypt').length
  const visTotal  = exchanges + crypts
  const exRatio   = visTotal > 0 ? (exchanges / visTotal) * 100 : 50

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 100% 40% at 50% 0%, rgba(61,127,255,0.06) 0%, transparent 55%)',
      padding: '32px 24px', maxWidth: 960, margin: '0 auto',
    }}>
      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 24 }}>
        {h.title}
      </h2>

      <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
        <StatTile icon="⚔" label={h.statToday}  color="var(--accent)"        value={data.today} />
        <StatTile icon="📅" label={h.stat7days}  color="#B060FF"              value={data.week}  />
        <StatTile icon="◈"  label={h.statTotal}  color="var(--credits-gold)"  value={data.total} />
      </div>

      {visTotal > 0 && (
        <div className="card" style={{ borderRadius: 12, marginBottom: 24, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 13, color: '#B060FF', fontWeight: 600 }}>
              {h.exchangeLabel} — {exchanges}
            </span>
            <span style={{ fontSize: 13, color: '#4ADE80', fontWeight: 600 }}>
              {crypts} — {h.cryptLabel}
            </span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: 'var(--outline)', overflow: 'hidden' }}>
            <div style={{ height: '100%', borderRadius: 4, width: `${exRatio}%`,
                          background: 'linear-gradient(90deg, var(--accent), #B060FF)',
                          transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginTop: 6, textAlign: 'center' }}>
            {h.lastRecords} {visTotal} {h.lastRecordsSuffix}
          </div>
        </div>
      )}

      <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '40px 1fr 1fr', padding: '10px 20px',
          borderBottom: '1px solid var(--outline)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1px',
          color: 'var(--on-surface2)', textTransform: 'uppercase',
        }}>
          <div /><div>{h.colType}</div>
          <div style={{ textAlign: 'right' }}>{h.colTime}</div>
        </div>

        {items.length === 0 ? (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--on-surface2)' }}>
            {h.empty}
          </div>
        ) : items.map((item, i) => {
          const meta = HUNT_COLORS[item.hunt_type] ?? { icon: '◈', color: 'var(--on-surface2)', bg: 'transparent' }
          const label = D.huntTypes[item.hunt_type] ?? item.hunt_type
          return (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '40px 1fr 1fr', alignItems: 'center',
              padding: '12px 20px',
              borderBottom: i < items.length - 1 ? '1px solid var(--separator)' : 'none',
              transition: 'background 0.12s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ width: 10, height: 10, borderRadius: '50%',
                            background: meta.color, boxShadow: `0 0 6px ${meta.color}`,
                            margin: '0 10px' }} />
              <div style={{ fontSize: 14, fontWeight: 600, color: meta.color }}>{label}</div>
              <div style={{ fontSize: 12, color: 'var(--on-surface2)', textAlign: 'right' }}>
                {timeAgo(item.created_at)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
