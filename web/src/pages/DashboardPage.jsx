import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const STAT_KEYS = [
  { key: 'exchanges_today', icon: '⚔', color: 'var(--accent)'       },
  { key: 'crypts_today',    icon: '💀', color: '#B060FF'              },
  { key: 'active_hunters',  icon: '◈',  color: 'var(--credits-gold)' },
]

const HUNT_ICONS = {
  exchange: { color: '#B060FF' },
  crypt:    { color: '#4ADE80' },
}

function timeAgo(iso, T) {
  const diff = (Date.now() - new Date(iso)) / 1000
  if (diff < 60)   return T.justNow
  if (diff < 3600) return `${Math.floor(diff / 60)} ${T.minutesAgo}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${T.hoursAgo}`
  return `${Math.floor(diff / 86400)} ${T.daysAgo}`
}

function StatTile({ label, color, rawValue }) {
  const animated = useCounter(typeof rawValue === 'number' ? rawValue : null)
  return (
    <div style={{
      flex: '1 1 180px',
      background: 'var(--elevated)',
      border: '1px solid var(--outline)',
      borderRadius: 14, padding: '28px 20px',
      textAlign: 'center',
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
      <div style={{
        fontSize: 54, fontWeight: 900, color, lineHeight: 1, marginBottom: 10,
        textShadow: `0 0 28px ${color}88`,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {rawValue != null ? animated : '—'}
      </div>
      <div style={{ fontSize: 13, color: '#C8D8F0', fontWeight: 600, letterSpacing: '0.3px' }}>{label}</div>
    </div>
  )
}

export default function DashboardPage() {
  const [user,  setUser]  = useState(null)
  const [stats, setStats] = useState(null)
  const [hunts, setHunts] = useState(null)
  const [error, setError] = useState('')
  const { lang } = useLang()
  const D = lang === 'en' ? D_EN : D_RU

  useEffect(() => {
    api.me().then(setUser).catch(e => setError(e.message))
    api.globalStats().then(setStats).catch(() => {})
    api.hunts().then(setHunts).catch(() => {})
  }, [])

  if (error) return <div className="page-content" style={{ color: 'var(--error-text)' }}>{error}</div>
  if (!user)  return <div className="page-content text-muted">{D.loading}</div>

  const recentHunts = hunts?.items?.slice(0, 8) ?? []
  const statTileLabels = [D.statTiles.exchangesToday, D.statTiles.cryptsToday, D.statTiles.huntersOnline]

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 120% 40% at 50% 0%, rgba(61,127,255,0.07) 0%, transparent 55%)',
      padding: '32px 24px',
      maxWidth: 960, margin: '0 auto',
    }}>

      {/* ── Global stat tiles ─────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 36, flexWrap: 'wrap' }}>
        {STAT_KEYS.map(({ key, icon, color }, i) => (
          <StatTile key={key} label={statTileLabels[i]} color={color}
                    rawValue={stats ? stats[key] : null} />
        ))}
      </div>

      {/* ── Two-column layout ─────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Profile card */}
        <div>
          <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 20 }}>
            {D.profile.title}
          </h2>
          <div className="card" style={{ borderRadius: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
              <div style={{
                width: 48, height: 48, borderRadius: '50%',
                background: 'rgba(61,127,255,0.15)',
                border: '1px solid rgba(61,127,255,0.4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 20, color: 'var(--accent)',
              }}>◈</div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF' }}>
                  {user.username || 'Hunter'}
                </div>
                <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{user.email}</div>
              </div>
            </div>
            <div className="separator" />
            {[
              { label: D.profile.credits,    value: user.credits,     gold: true  },
              { label: D.profile.refCredits, value: user.ref_credits, gold: false },
              { label: D.profile.refCode,    value: user.ref_code,    gold: false },
              { label: D.profile.status,     value: user.trial_used ? D.profile.trialUsed : D.profile.trialAvailable, gold: false },
              { label: D.profile.memberSince,value: user.created_at?.slice(0, 10) ?? '—', gold: false },
            ].map(({ label, value, gold }) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0', borderBottom: '1px solid var(--separator)',
              }}>
                <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{label}</span>
                <span style={{ fontWeight: 600, fontSize: 14, color: gold ? 'var(--credits-gold)' : '#FFFFFF' }}>
                  {value}
                </span>
              </div>
            ))}
            <div style={{ marginTop: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Link to="/dashboard/balance" style={{
                display: 'inline-block', padding: '9px 20px',
                background: 'var(--accent)', color: '#FFFFFF',
                borderRadius: 8, fontSize: 13, fontWeight: 600,
                textDecoration: 'none', boxShadow: '0 0 14px var(--accent-glow)',
              }}>
                {D.profile.topUp}
              </Link>
              <a
                href="https://github.com/Yevgeniy204566/totalhunter/releases/latest/download/TotalHunter_Setup.exe"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '9px 20px',
                  background: 'rgba(74,222,128,0.12)',
                  border: '1px solid rgba(74,222,128,0.35)',
                  color: '#4ADE80', borderRadius: 8, fontSize: 13, fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                ↓ {D.profile.download}
              </a>
            </div>
          </div>
        </div>

        {/* Recent activity */}
        <div>
          <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 20 }}>
            {D.recentHunts.title}
          </h2>
          <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
            {recentHunts.length === 0 ? (
              <div style={{ padding: 24, color: 'var(--on-surface2)', fontSize: 14, textAlign: 'center' }}>
                {D.recentHunts.empty}
              </div>
            ) : (
              recentHunts.map((h, i) => {
                const hunti = HUNT_ICONS[h.hunt_type] ?? { color: 'var(--on-surface2)' }
                const label = D.huntTypes[h.hunt_type] ?? h.hunt_type
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '12px 20px',
                    borderBottom: i < recentHunts.length - 1 ? '1px solid var(--separator)' : 'none',
                    transition: 'background 0.12s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <div style={{
                      width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
                      background: hunti.color,
                      boxShadow: `0 0 6px ${hunti.color}`,
                    }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: hunti.color }}>
                        {label}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                        {timeAgo(h.created_at, D.timeAgo)}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
          <div style={{ marginTop: 10, textAlign: 'right' }}>
            <Link to="/dashboard/hunts" style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
              {D.recentHunts.allHistory}
            </Link>
          </div>
        </div>

      </div>
    </div>
  )
}
