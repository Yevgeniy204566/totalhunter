import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'

const STAT_TILES = [
  { key: 'exchanges_today', icon: '⚔', label: 'Бирж сегодня',    color: 'var(--accent)'       },
  { key: 'crypts_today',    icon: '💀', label: 'Склепов сегодня', color: '#B060FF'              },
  { key: 'active_hunters',  icon: '◈',  label: 'Охотников онлайн', color: 'var(--credits-gold)' },
]

const HUNT_META = {
  exchange: { icon: '⚔', label: 'Биржа',  color: 'var(--accent)'  },
  crypt:    { icon: '💀', label: 'Склеп',  color: '#B060FF'        },
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso)) / 1000
  if (diff < 60)   return 'только что'
  if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`
  return `${Math.floor(diff / 86400)} дн назад`
}

function StatTile({ icon, label, color, rawValue }) {
  const animated = useCounter(typeof rawValue === 'number' ? rawValue : null)
  return (
    <div style={{
      flex: '1 1 160px',
      background: 'var(--elevated)',
      border: '1px solid var(--outline)',
      borderRadius: 12, padding: '24px 20px',
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
      <div style={{ fontSize: 24, marginBottom: 10 }}>{icon}</div>
      <div style={{
        fontSize: 40, fontWeight: 800, color, lineHeight: 1, marginBottom: 8,
        textShadow: `0 0 24px ${color}88`,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {rawValue != null ? animated : '—'}
      </div>
      <div style={{ fontSize: 13, color: '#C8D8F0', fontWeight: 500 }}>{label}</div>
    </div>
  )
}

export default function DashboardPage() {
  const [user,  setUser]  = useState(null)
  const [stats, setStats] = useState(null)
  const [hunts, setHunts] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.me().then(setUser).catch(e => setError(e.message))
    api.globalStats().then(setStats).catch(() => {})
    api.hunts().then(setHunts).catch(() => {})
  }, [])

  if (error) return <div className="page-content" style={{ color: 'var(--error-text)' }}>{error}</div>
  if (!user)  return <div className="page-content text-muted">Загрузка...</div>

  const recentHunts = hunts?.items?.slice(0, 8) ?? []

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 120% 40% at 50% 0%, rgba(61,127,255,0.07) 0%, transparent 55%)',
      padding: '32px 24px',
      maxWidth: 960, margin: '0 auto',
    }}>

      {/* ── Global stat tiles ─────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 36, flexWrap: 'wrap' }}>
        {STAT_TILES.map(({ key, icon, label, color }) => (
          <StatTile key={key} icon={icon} label={label} color={color}
                    rawValue={stats ? stats[key] : null} />
        ))}
      </div>

      {/* ── Two-column layout ─────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Profile card */}
        <div>
          <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 20 }}>
            Профиль
          </h2>
          <div className="card" style={{ borderRadius: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
              <div style={{
                width: 48, height: 48, borderRadius: '50%',
                background: 'rgba(61,127,255,0.15)',
                border: '1px solid rgba(61,127,255,0.4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 20, color: 'var(--accent)',
              }}>
                ◈
              </div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF' }}>
                  {user.username || 'Hunter'}
                </div>
                <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{user.email}</div>
              </div>
            </div>
            <div className="separator" />
            {[
              { label: 'Кредиты',       value: user.credits,     gold: true },
              { label: 'Рефералы',       value: user.ref_credits, gold: false },
              { label: 'Реф. код',       value: user.ref_code,    gold: false },
              { label: 'Статус',         value: user.trial_used ? 'Триал использован' : '✓ Триал доступен', gold: false },
              { label: 'С нами с',       value: user.created_at?.slice(0, 10) ?? '—', gold: false },
            ].map(({ label, value, gold }) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0', borderBottom: '1px solid var(--separator)',
              }}>
                <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{label}</span>
                <span style={{
                  fontWeight: 600, fontSize: 14,
                  color: gold ? 'var(--credits-gold)' : '#FFFFFF',
                }}>
                  {value}
                </span>
              </div>
            ))}
            <div style={{ marginTop: 16 }}>
              <Link to="/dashboard/balance" style={{
                display: 'inline-block', padding: '9px 20px',
                background: 'var(--accent)', color: '#FFFFFF',
                borderRadius: 8, fontSize: 13, fontWeight: 600,
                textDecoration: 'none',
                boxShadow: '0 0 14px var(--accent-glow)',
              }}>
                Пополнить кредиты →
              </Link>
            </div>
          </div>
        </div>

        {/* Recent activity */}
        <div>
          <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 20 }}>
            Последние находки
          </h2>
          <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
            {recentHunts.length === 0 ? (
              <div style={{ padding: 24, color: 'var(--on-surface2)', fontSize: 14, textAlign: 'center' }}>
                Ещё нет охот. Запусти бота! ⚔
              </div>
            ) : (
              recentHunts.map((h, i) => {
                const meta = HUNT_META[h.hunt_type] ?? { icon: '◈', label: h.hunt_type, color: 'var(--on-surface2)' }
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
                      width: 34, height: 34, borderRadius: 8,
                      background: `${meta.color}18`,
                      border: `1px solid ${meta.color}44`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 16, flexShrink: 0,
                    }}>
                      {meta.icon}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#FFFFFF' }}>
                        {meta.label} — найден
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                        {timeAgo(h.created_at)}
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: meta.color, fontWeight: 700, letterSpacing: '0.5px' }}>
                      +ЛУТНУТО
                    </div>
                  </div>
                )
              })
            )}
          </div>
          <div style={{ marginTop: 10, textAlign: 'right' }}>
            <Link to="/dashboard/hunts" style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
              Вся история →
            </Link>
          </div>
        </div>

      </div>
    </div>
  )
}
