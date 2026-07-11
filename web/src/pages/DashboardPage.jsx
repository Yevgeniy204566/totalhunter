import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

/* ─── helpers ─────────────────────────────────────────────────── */
const STAT_KEYS = [
  { key: 'exchanges_today', color: 'var(--accent)'       },
  { key: 'crypts_today',    color: '#B060FF'              },
  { key: 'active_hunters',  color: 'var(--credits-gold)' },
]

const HUNT_COLORS = {
  exchange: { color: '#B060FF' },
  crypt:    { color: '#4ADE80' },
}

const TX_ICONS = {
  purchase:               { icon: '◆', color: '#4ADE80' },
  credit_use:             { icon: '⚔', color: '#FFFFFF' },
  trial:                  { icon: '🎁', color: '#4ADE80' },
  ref_welcome:            { icon: '⬡', color: 'var(--credits-gold)' },
  ref_earning:            { icon: '⬡', color: 'var(--credits-gold)' },
  ref_transfer:           { icon: '→', color: '#4ADE80' },
  hwid_duplicate_blocked: { icon: '⚠', color: 'var(--on-surface2)' },
  manual_adjust:          { icon: '✎', color: 'var(--on-surface2)' },
}

function timeAgo(iso, T) {
  const diff = (Date.now() - new Date(iso)) / 1000
  if (diff < 60)    return T.justNow
  if (diff < 3600)  return `${Math.floor(diff / 60)} ${T.minutesAgo}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${T.hoursAgo}`
  return `${Math.floor(diff / 86400)} ${T.daysAgo}`
}

/* ─── sub-components ──────────────────────────────────────────── */
function GlobalStatTile({ label, color, rawValue }) {
  const animated = useCounter(typeof rawValue === 'number' ? rawValue : null)
  return (
    <div style={{
      flex: '1 1 160px', background: 'var(--elevated)',
      border: '1px solid var(--outline)', borderRadius: 14,
      padding: '24px 16px', textAlign: 'center',
      transition: 'box-shadow 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 20px ${color}44`; e.currentTarget.style.borderColor = `${color}55` }}
    onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.borderColor = 'var(--outline)' }}>
      <div style={{ fontSize: 48, fontWeight: 900, color, lineHeight: 1, marginBottom: 8,
                    textShadow: `0 0 28px ${color}88`, fontVariantNumeric: 'tabular-nums' }}>
        {rawValue != null ? animated : '—'}
      </div>
      <div style={{ fontSize: 12, color: '#C8D8F0', fontWeight: 600, letterSpacing: '0.3px' }}>{label}</div>
    </div>
  )
}

function HuntStatTile({ icon, label, color, value }) {
  const animated = useCounter(typeof value === 'number' ? value : null, 1000)
  return (
    <div style={{
      flex: '1 1 140px', background: 'var(--elevated)',
      border: '1px solid var(--outline)', borderRadius: 12,
      padding: '20px 16px', textAlign: 'center',
      transition: 'box-shadow 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 20px ${color}44`; e.currentTarget.style.borderColor = `${color}55` }}
    onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.borderColor = 'var(--outline)' }}>
      <div style={{ fontSize: 18, marginBottom: 6 }}>{icon}</div>
      <div style={{ fontSize: 34, fontWeight: 800, color, lineHeight: 1, marginBottom: 6,
                    textShadow: `0 0 20px ${color}88`, fontVariantNumeric: 'tabular-nums' }}>
        {value != null ? animated : '—'}
      </div>
      <div style={{ fontSize: 12, color: '#C8D8F0', fontWeight: 500 }}>{label}</div>
    </div>
  )
}

/* ─── tab bar ─────────────────────────────────────────────────── */
function TabBar({ tabs, active, setActive }) {
  return (
    <div style={{ display: 'flex', gap: 4, marginBottom: 28,
                  background: 'var(--elevated)', borderRadius: 10, padding: 4,
                  border: '1px solid var(--outline)', alignSelf: 'flex-start' }}>
      {tabs.map(({ key, label }) => {
        const isActive = active === key
        return (
          <button key={key} onClick={() => setActive(key)} style={{
            padding: '8px 20px', borderRadius: 7, border: 'none', cursor: 'pointer',
            fontSize: 14, fontWeight: isActive ? 700 : 500,
            background: isActive ? 'var(--accent)' : 'transparent',
            color: isActive ? '#fff' : 'var(--on-surface2)',
            boxShadow: isActive ? '0 0 12px var(--accent-glow)' : 'none',
            transition: 'all 0.15s',
          }}>
            {label}
          </button>
        )
      })}
    </div>
  )
}

/* ─── tab: Profile ────────────────────────────────────────────── */
function ProfileTab({ user, stats, hunts, D, onViewHunts, onRefresh }) {
  const [code, setCode]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)
  const dv = D.devices
  const ta = D.timeAgo
  const recentHunts = hunts?.items?.slice(0, 5) ?? []
  const statTileLabels = [D.statTiles.exchangesToday, D.statTiles.cryptsToday, D.statTiles.huntersOnline]

  async function linkHwid() {
    if (code.length !== 6) { setMsg(dv.codeError); return }
    setLoading(true)
    try {
      const res = await api.linkVerify(code)
      setMsg(res.message); setCode('')
      await onRefresh()
    } catch (e) { setMsg(e.message) }
    finally { setLoading(false) }
  }

  async function resetHwid() {
    if (!confirm(dv.unlink)) return
    setLoading(true)
    try {
      const res = await api.hwidReset()
      setMsg(res.message); await onRefresh()
    } catch (e) { setMsg(e.message) }
    finally { setLoading(false) }
  }

  const nextReset = user.hwid_reset_at
    ? new Date(new Date(user.hwid_reset_at).getTime() + 7 * 86400 * 1000).toLocaleDateString()
    : null

  return (
    <>
      {/* global stat tiles */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
        {STAT_KEYS.map(({ key, color }, i) => (
          <GlobalStatTile key={key} label={statTileLabels[i]} color={color}
                          rawValue={stats ? stats[key] : null} />
        ))}
      </div>

      {/* two-column: profile + devices */}
      <div className="dash-two-col" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>

        {/* profile card */}
        <div>
          <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 16 }}>
            {D.profile.title}
          </h2>
          <div className="card" style={{ borderRadius: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
              <div style={{
                width: 44, height: 44, borderRadius: '50%',
                background: 'rgba(61,127,255,0.15)', border: '1px solid rgba(61,127,255,0.4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, color: 'var(--accent)',
              }}>◈</div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#FFFFFF' }}>{user.username || 'Hunter'}</div>
                <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>{user.email}</div>
              </div>
            </div>
            <div className="separator" />
            {[
              { label: D.profile.credits,     value: user.credits,     gold: true  },
              { label: D.profile.refCredits,  value: user.ref_credits, gold: false },
              { label: D.profile.refCode,     value: user.ref_code,    gold: false },
              { label: D.profile.status,      value: user.trial_used ? D.profile.trialUsed : D.profile.trialAvailable, gold: false },
              { label: D.profile.memberSince, value: user.created_at?.slice(0, 10) ?? '—', gold: false },
            ].map(({ label, value, gold }) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '9px 0', borderBottom: '1px solid var(--separator)',
              }}>
                <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{label}</span>
                <span style={{ fontWeight: 600, fontSize: 14, color: gold ? 'var(--credits-gold)' : '#FFFFFF' }}>
                  {value}
                </span>
              </div>
            ))}
            <div style={{ marginTop: 14 }}>
              <Link to="/dashboard/balance" style={{
                display: 'inline-block', padding: '9px 20px',
                background: 'var(--accent)', color: '#FFFFFF',
                borderRadius: 8, fontSize: 13, fontWeight: 600,
                textDecoration: 'none', boxShadow: '0 0 14px var(--accent-glow)',
              }}>
                {D.profile.topUp}
              </Link>
            </div>
          </div>
        </div>

        {/* devices widget */}
        <div>
          <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 16 }}>
            {dv.title}
          </h2>
          <div className="card" style={{ borderRadius: 14 }}>
            {user.hwid ? (
              <>
                <div className="text-muted" style={{ marginBottom: 8, fontSize: 13 }}>{dv.linked}</div>
                <code style={{ fontSize: 16, fontWeight: 600, wordBreak: 'break-all' }}>{user.hwid}</code>
                <div className="separator" />
                <button className="btn-secondary" onClick={resetHwid} disabled={loading}
                  style={{ borderColor: 'var(--error)', color: 'var(--error-text)', fontSize: 13 }}>
                  {dv.unlink}
                </button>
                {nextReset && (
                  <div className="text-muted" style={{ marginTop: 8, fontSize: 12 }}>
                    {dv.nextReset} {nextReset}
                  </div>
                )}
              </>
            ) : (
              <>
                <div style={{ fontWeight: 500, marginBottom: 10, fontSize: 14 }}>{dv.linkTitle}</div>
                <ol style={{ paddingLeft: 18, color: 'var(--on-surface2)', fontSize: 13, lineHeight: 1.9, margin: '0 0 14px' }}>
                  {dv.linkSteps.map((step, i) => <li key={i}>{step}</li>)}
                </ol>
                <div style={{ display: 'flex', gap: 10 }}>
                  <input value={code}
                    onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder={dv.placeholder}
                    style={{
                      flex: 1, background: 'var(--elevated)', border: '1px solid var(--outline)',
                      color: 'var(--on-surface)', borderRadius: 6, padding: '9px 12px',
                      fontSize: 18, letterSpacing: 8, textAlign: 'center',
                    }}
                  />
                  <button className="btn-primary" onClick={linkHwid}
                    disabled={loading || code.length !== 6}>
                    {loading ? '...' : dv.linkBtn}
                  </button>
                </div>
              </>
            )}
            {msg && <div className="text-muted" style={{ marginTop: 10, fontSize: 13 }}>{msg}</div>}
          </div>
        </div>
      </div>

      {/* recent hunts */}
      <div>
        <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 16 }}>
          {D.recentHunts.title}
        </h2>
        <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
          {recentHunts.length === 0 ? (
            <div style={{ padding: 24, color: 'var(--on-surface2)', fontSize: 14, textAlign: 'center' }}>
              {D.recentHunts.empty}
            </div>
          ) : recentHunts.map((h, i) => {
            const hunti = HUNT_COLORS[h.hunt_type] ?? { color: 'var(--on-surface2)' }
            const label = D.huntTypes[h.hunt_type] ?? h.hunt_type
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '11px 20px',
                borderBottom: i < recentHunts.length - 1 ? '1px solid var(--separator)' : 'none',
                transition: 'background 0.12s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
                              background: hunti.color, boxShadow: `0 0 6px ${hunti.color}` }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: hunti.color }}>{label}</div>
                  <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>{timeAgo(h.created_at, ta)}</div>
                </div>
              </div>
            )
          })}
        </div>
        <div style={{ marginTop: 10, textAlign: 'right' }}>
          <button onClick={onViewHunts} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 13, color: 'var(--on-surface2)',
          }}>
            {D.recentHunts.allHistory}
          </button>
        </div>
      </div>
    </>
  )
}

/* ─── tab: Hunts ──────────────────────────────────────────────── */
function HuntsTab({ data, D }) {
  const h  = D.hunts
  const ta = D.timeAgo
  const items    = data?.items ?? []
  const exchanges = items.filter(i => i.hunt_type === 'exchange').length
  const crypts    = items.filter(i => i.hunt_type === 'crypt').length
  const visTotal  = exchanges + crypts
  const exRatio   = visTotal > 0 ? (exchanges / visTotal) * 100 : 50

  function timeAgoFn(iso) {
    const diff = (Date.now() - new Date(iso)) / 1000
    if (diff < 60)    return ta.justNow
    if (diff < 3600)  return `${Math.floor(diff / 60)} ${ta.minutesAgo}`
    if (diff < 86400) return `${Math.floor(diff / 3600)} ${ta.hoursAgo}`
    return `${Math.floor(diff / 86400)} ${ta.daysAgo}`
  }

  if (!data) return <div className="text-muted">{D.loading}</div>

  return (
    <>
      <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 20 }}>
        {h.title}
      </h2>

      <div style={{ display: 'flex', gap: 14, marginBottom: 24, flexWrap: 'wrap' }}>
        <HuntStatTile icon="⚔" label={h.statToday} color="var(--accent)"       value={data.today} />
        <HuntStatTile icon="📅" label={h.stat7days} color="#B060FF"             value={data.week}  />
        <HuntStatTile icon="◈"  label={h.statTotal} color="var(--credits-gold)" value={data.total} />
      </div>

      {visTotal > 0 && (
        <div className="card" style={{ borderRadius: 12, marginBottom: 20, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 13, color: '#B060FF', fontWeight: 600 }}>{h.exchangeLabel} — {exchanges}</span>
            <span style={{ fontSize: 13, color: '#4ADE80', fontWeight: 600 }}>{crypts} — {h.cryptLabel}</span>
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
        <div className="dash-row" style={{
          display: 'grid', gridTemplateColumns: '40px 1fr 1fr', padding: '10px 20px',
          borderBottom: '1px solid var(--outline)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1px',
          color: 'var(--on-surface2)', textTransform: 'uppercase',
        }}>
          <div /><div>{h.colType}</div>
          <div style={{ textAlign: 'right' }}>{h.colTime}</div>
        </div>
        {items.length === 0 ? (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--on-surface2)' }}>{h.empty}</div>
        ) : items.map((item, i) => {
          const meta  = HUNT_COLORS[item.hunt_type] ?? { color: 'var(--on-surface2)' }
          const label = D.huntTypes[item.hunt_type] ?? item.hunt_type
          return (
            <div key={i} className="dash-row" style={{
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
                {timeAgoFn(item.created_at)}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

/* ─── tab: Transactions ───────────────────────────────────────── */
function TransactionsTab({ data, D }) {
  const t = D.transactions

  function formatDate(iso) {
    const d = new Date(iso)
    return d.toLocaleString(D === D_EN ? 'en-GB' : 'ru-RU', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  }

  if (!data) return <div className="text-muted">{D.loading}</div>

  const items = data.items ?? []

  return (
    <>
      <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 20 }}>
        {t.title}
      </h2>

      <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
        <div className="dash-row dash-row--tx" style={{
          display: 'grid', gridTemplateColumns: '36px 1fr 100px 140px', padding: '10px 20px',
          borderBottom: '1px solid var(--outline)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1px',
          color: 'var(--on-surface2)', textTransform: 'uppercase',
        }}>
          <div />
          <div>{t.colOp}</div>
          <div style={{ textAlign: 'right' }}>{t.colAmount}</div>
          <div style={{ textAlign: 'right' }}>{t.colDate}</div>
        </div>

        {items.length === 0 ? (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--on-surface2)', fontSize: 14 }}>
            {t.empty}
          </div>
        ) : items.map((tx, i) => {
          const meta  = TX_ICONS[tx.type] ?? { icon: '◈', color: '#FFFFFF' }
          const label = t.types[tx.type] ?? tx.type
          const isPos = tx.amount > 0
          const prefix = tx.amount > 0 ? '+' : tx.amount < 0 ? '−' : ''
          return (
            <div key={i} className="dash-row dash-row--tx" style={{
              display: 'grid', gridTemplateColumns: '36px 1fr 100px 140px',
              alignItems: 'center', padding: '13px 20px',
              borderBottom: i < items.length - 1 ? '1px solid var(--separator)' : 'none',
              transition: 'background 0.12s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ width: 28, height: 28, borderRadius: 6,
                            background: `${meta.color}18`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13 }}>
                {meta.icon}
              </div>
              <div style={{ fontSize: 14, color: '#FFFFFF', fontWeight: 500 }}>{label}</div>
              <div style={{ fontSize: 15, fontWeight: 700, textAlign: 'right',
                            color: isPos ? '#4ADE80' : '#FFFFFF',
                            textShadow: isPos ? '0 0 10px rgba(74,222,128,0.5)' : 'none',
                            fontVariantNumeric: 'tabular-nums' }}>
                {tx.amount !== 0 ? `${prefix}${Math.abs(tx.amount)}` : '—'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--on-surface2)', textAlign: 'right',
                            fontVariantNumeric: 'tabular-nums' }}>
                {formatDate(tx.created_at)}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

/* ─── main page ───────────────────────────────────────────────── */
export default function DashboardPage() {
  const [user,   setUser]   = useState(null)
  const [stats,  setStats]  = useState(null)
  const [hunts,  setHunts]  = useState(null)
  const [txs,    setTxs]    = useState(null)
  const [error,  setError]  = useState('')
  const [tab,    setTab]    = useState('profile')
  const { lang } = useLang()
  const D = lang === 'en' ? D_EN : D_RU
  useMeta({
    title:       lang === 'ru' ? 'Total Hunter — Профиль' : 'Total Hunter — Profile',
    description: lang === 'ru' ? 'Обзор аккаунта Total Hunter: профиль, охоты, транзакции, устройства.' : 'Total Hunter account overview: profile, hunts, transactions, devices.',
  })

  async function refreshUser() {
    const u = await api.me()
    setUser(u)
    return u
  }

  useEffect(() => {
    refreshUser().catch(e => setError(e.message))
    api.globalStats().then(setStats).catch(() => {})
    api.hunts().then(setHunts).catch(() => {})
    api.transactions().then(setTxs).catch(() => {})
  }, [])

  const TABS = [
    { key: 'profile',      label: D.nav.profile      },
    { key: 'hunts',        label: D.nav.hunts        },
    { key: 'transactions', label: D.nav.transactions },
  ]

  if (error) return <div className="page-content" style={{ color: 'var(--error-text)' }}>{error}</div>
  if (!user) return <div className="page-content text-muted">{D.loading}</div>

  return (
    <div className="dash-page-wrap" style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 120% 40% at 50% 0%, rgba(61,127,255,0.07) 0%, transparent 55%)',
      padding: '32px 24px',
      maxWidth: 1000, margin: '0 auto',
    }}>
      <TabBar tabs={TABS} active={tab} setActive={setTab} />

      {tab === 'profile' && (
        <ProfileTab
          user={user} stats={stats} hunts={hunts} D={D}
          onViewHunts={() => setTab('hunts')}
          onRefresh={refreshUser}
        />
      )}
      {tab === 'hunts' && <HuntsTab data={hunts} D={D} />}
      {tab === 'transactions' && <TransactionsTab data={txs} D={D} />}
    </div>
  )
}
