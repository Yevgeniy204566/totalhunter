import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fetchChestByKingdomSlug } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

/* ─── helpers ─────────────────────────────────────────────────── */
/* ─── sub-components ──────────────────────────────────────────── */

/* Ячейка «Собрано»: шрифт и подсветка бывших верхних плиток (владелец 2026-09-26) */
function CollectedCell({ value, color }) {
  const animated = useCounter(typeof value === 'number' ? value : null, 1000)
  return (
    <div className="collected-cell" style={{
      background: 'var(--elevated)', border: '1px solid var(--outline)', borderRadius: 14,
      padding: '18px 12px', textAlign: 'center', transition: 'box-shadow 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 20px ${color}44`; e.currentTarget.style.borderColor = `${color}55` }}
    onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.borderColor = 'var(--outline)' }}>
      <div className="collected-num" style={{ fontSize: 44, fontWeight: 900, color, lineHeight: 1,
                    textShadow: `0 0 28px ${color}88`, fontVariantNumeric: 'tabular-nums' }}>
        {value != null ? animated.toLocaleString('ru-RU') : '—'}
      </div>
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
function ProfileTab({ user, hunts, D, onRefresh }) {
  const [code, setCode]       = useState('')
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)
  const dv = D.devices

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
        <div className="card" style={{ borderRadius: 14, padding: 0 }}>
          {(() => {
            const CRYPT = '#B060FF', EXCH = '#3D7FFF'
            const head = { fontSize: 15, fontWeight: 800, textAlign: 'center', letterSpacing: '0.5px', textTransform: 'uppercase' }
            return (
              <div className="collected-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(90px, 0.7fr) 1fr 1fr', gap: 12, padding: 16, alignItems: 'center' }}>
                <div />
                <div className="collected-head" style={{ ...head, color: CRYPT }}>{D.collected.crypts}</div>
                <div className="collected-head" style={{ ...head, color: EXCH }}>{D.collected.exchanges}</div>
                {['today', 'week', 'total'].map(period => {
                  const row = hunts?.by_type?.[period]
                  return [
                    <div key={period + 'l'} className="collected-label" style={{ fontSize: 16, fontWeight: 700, color: '#C8D8F0' }}>{D.collected[period]}</div>,
                    <CollectedCell key={period + 'c'} value={row ? row.crypt : null} color={CRYPT} />,
                    <CollectedCell key={period + 'e'} value={row ? row.exchange : null} color={EXCH} />,
                  ]
                })}
              </div>
            )
          })()}
        </div>
      </div>
    </>
  )
}



/* ─── main page ───────────────────────────────────────────────── */
export default function DashboardPage() {
  const [user,   setUser]   = useState(null)
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
      <ProfileTab user={user} hunts={hunts} D={D} onRefresh={refreshUser} />
    </div>
  )
}
