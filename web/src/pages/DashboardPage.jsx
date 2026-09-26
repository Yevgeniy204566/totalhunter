import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fetchChestByKingdomSlug } from '../api.js'
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


/* ─── Сохранённые таблицы сундуков кланов (Профиль, владелец 2026-09-26) ───
   Список хранится в аккаунте (/web/chest-links): выпадающий список кланов, ссылка на
   публичную таблицу выбранного, Сохранить / Удалить. Ссылку (читаемую, /c/229/feniks)
   строит сервер — сайт её не собирает, иначе кириллица превращается в %D0%A4... */

function ChestFinder({ D }) {
  const T = D.chestFinder
  const [links, setLinks]     = useState([])
  const [sel, setSel]         = useState(-1)   // -1 — новый клан
  const [kingdom, setKingdom] = useState('')
  const [clan, setClan]       = useState('')
  const [msg, setMsg]         = useState({ text: '', ok: false })
  const [busy, setBusy]       = useState(false)

  useEffect(() => {
    api.chestLinks().then(r => {
      const list = r?.links || []
      setLinks(list)
      if (list.length) pick(0, list)
    }).catch(() => {})
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  function pick(i, list = links) {
    setSel(i); setMsg({ text: '', ok: false })
    if (i >= 0) { setKingdom(list[i].kingdom); setClan(list[i].clan) }
    else { setKingdom(''); setClan('') }
  }

  async function persist(next, selectIndex) {
    const r = await api.saveChestLinks(next.map(({ kingdom, clan }) => ({ kingdom, clan })))
    const list = r?.links || next
    setLinks(list)
    pick(Math.min(selectIndex, list.length - 1), list)
  }

  async function save() {
    const k = kingdom.trim(), c = clan.trim()
    if (!k || !c) { setMsg({ text: T.empty, ok: false }); return }
    setBusy(true)
    try {
      // Сервер сам приводит название к слагу — сохраняем только существующий клан.
      await fetchChestByKingdomSlug(k, c)
    } catch {
      setMsg({ text: T.notFound, ok: false }); setBusy(false); return
    }
    try {
      const same = links.findIndex(l => l.kingdom === k && l.clan.toLowerCase() === c.toLowerCase())
      const next = [...links]
      let idx
      if (same >= 0) { next[same] = { kingdom: k, clan: c }; idx = same }
      else if (sel >= 0) { next[sel] = { kingdom: k, clan: c }; idx = sel }
      else { next.push({ kingdom: k, clan: c }); idx = next.length - 1 }
      await persist(next, idx)
      setMsg({ text: T.saved, ok: true })
    } catch (e) {
      setMsg({ text: e.message, ok: false })
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (sel < 0) return
    setBusy(true)
    try {
      await persist(links.filter((_, i) => i !== sel), 0)
    } catch (e) {
      setMsg({ text: e.message, ok: false })
    } finally {
      setBusy(false)
    }
  }

  const field = {
    background: 'var(--elevated)', border: '1px solid var(--outline)', color: 'var(--on-surface)',
    borderRadius: 6, padding: '9px 12px', fontSize: 16,
  }
  const current = sel >= 0 ? links[sel] : null
  return (
    <div style={{ marginBottom: 20 }}>
      <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 16 }}>{T.title}</h2>
      <div className="card" style={{ borderRadius: 14 }}>
        <div className="text-muted" style={{ fontSize: 14, marginBottom: 12 }}>{T.sub}</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
          <select value={sel} onChange={e => pick(Number(e.target.value))}
            style={{ ...field, flex: '0 1 260px', minWidth: 0 }} translate="no" className="notranslate">
            {links.map((l, i) => <option key={`${l.kingdom}/${l.clan}`} value={i}>{l.kingdom} / {l.clan}</option>)}
            <option value={-1}>{T.newItem}</option>
          </select>
          {current?.url && (
            <a href={current.url} target="_blank" rel="noreferrer"
              style={{ color: 'var(--accent)', fontSize: 15, wordBreak: 'break-all' }}
              translate="no" className="notranslate">
              {current.url}
            </a>
          )}
        </div>
        <form onSubmit={e => { e.preventDefault(); save() }}
          style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <input value={kingdom} placeholder={T.kingdom} inputMode="numeric"
            onChange={e => setKingdom(e.target.value.replace(/\D/g, '').slice(0, 4))}
            style={{ ...field, width: 140 }} />
          <input value={clan} placeholder={T.clan} onChange={e => setClan(e.target.value)}
            style={{ ...field, flex: '1 1 200px', minWidth: 0 }} />
          <button type="submit" className="btn-primary" disabled={busy}>{busy ? '...' : T.save}</button>
          <button type="button" className="btn-secondary" onClick={remove} disabled={busy || sel < 0}
            style={{ borderColor: 'var(--error)', color: 'var(--error-text)' }}>
            {T.remove}
          </button>
        </form>
        {msg.text && (
          <div style={{ marginTop: 10, fontSize: 14, color: msg.ok ? 'var(--secondary, #4ADE80)' : 'var(--error-text)' }}>
            {msg.text}
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── tab: Profile ────────────────────────────────────────────── */
function ProfileTab({ user, stats, hunts, D, onRefresh }) {
  const [code, setCode]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)
  const dv = D.devices
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

      <ChestFinder D={D} />

      {/* «Собрано» (владелец 2026-09-26): вместо вкладок «Охоты»/«Транзакции» и списка
          последних находок — три строки: сегодня / неделя / всё время × склепы / биржи. */}
      <div>
        <h2 className="gradient-text" style={{ fontSize: 20, fontWeight: 800, marginBottom: 16 }}>
          {D.collected.title}
        </h2>
        <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 16 }}>
            <thead>
              <tr style={{ color: 'var(--on-surface2)', fontSize: 14 }}>
                <th style={{ textAlign: 'left', padding: '12px 20px', fontWeight: 600 }}></th>
                <th style={{ textAlign: 'right', padding: '12px 20px', fontWeight: 700, color: '#B060FF' }}>{D.collected.crypts}</th>
                <th style={{ textAlign: 'right', padding: '12px 20px', fontWeight: 700, color: 'var(--accent)' }}>{D.collected.exchanges}</th>
              </tr>
            </thead>
            <tbody>
              {['today', 'week', 'total'].map(period => {
                const row = hunts?.by_type?.[period] || { crypt: 0, exchange: 0 }
                return (
                  <tr key={period} style={{ borderTop: '1px solid var(--separator)' }}>
                    <td style={{ padding: '12px 20px', fontWeight: 600 }}>{D.collected[period]}</td>
                    <td style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 700 }}>{row.crypt.toLocaleString('ru-RU')}</td>
                    <td style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 700 }}>{row.exchange.toLocaleString('ru-RU')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}



/* ─── main page ───────────────────────────────────────────────── */
export default function DashboardPage() {
  const [user,   setUser]   = useState(null)
  const [stats,  setStats]  = useState(null)
  const [hunts,  setHunts]  = useState(null)
  const [error,  setError]  = useState('')
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
  }, [])


  if (error) return <div className="page-content" style={{ color: 'var(--error-text)' }}>{error}</div>
  if (!user) return <div className="page-content text-muted">{D.loading}</div>

  return (
    <div className="dash-page-wrap" style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 120% 40% at 50% 0%, rgba(61,127,255,0.07) 0%, transparent 55%)',
      padding: '32px 24px',
      maxWidth: 1000, margin: '0 auto',
    }}>
      <ProfileTab user={user} stats={stats} hunts={hunts} D={D} onRefresh={refreshUser} />
    </div>
  )
}
