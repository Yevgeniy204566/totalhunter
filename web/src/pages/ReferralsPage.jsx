import { useEffect, useState, useRef } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

export default function ReferralsPage() {
  const [user,       setUser]       = useState(null)
  const [copied,     setCopied]     = useState(false)
  const [msg,        setMsg]        = useState('')
  const [loading,    setLoading]    = useState(false)
  const [codeInput,  setCodeInput]  = useState('')
  const [codeMsg,    setCodeMsg]    = useState('')
  const [codeLoading,setCodeLoading]= useState(false)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const r = D.referrals

  const refCredits = useCounter(user ? user.ref_credits : null, 900)

  async function refresh() { api.me().then(setUser) }
  useEffect(() => { refresh() }, [])

  function copyLink() {
    navigator.clipboard.writeText(`https://total-hunter.com/ref/${user.ref_code}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function activateCode() {
    if (!codeInput.trim()) return
    setCodeLoading(true); setCodeMsg('')
    try {
      const res = await api.activateReferral(codeInput.trim().toUpperCase())
      setCodeMsg(res.message)
      if (res.success) { setCodeInput(''); await refresh() }
    } catch (e) { setCodeMsg(e.message) }
    finally { setCodeLoading(false) }
  }

  async function transfer() {
    setLoading(true); setMsg('')
    try {
      const res = await api.referralTransfer()
      setMsg(res.message)
      await refresh()
    } catch (e) { setMsg(e.message) }
    finally { setLoading(false) }
  }

  if (!user) return <div className="page-content text-muted">{D.loading}</div>

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 100% 40% at 50% 0%, rgba(176,96,255,0.06) 0%, transparent 55%)',
      padding: '32px 24px', maxWidth: 800, margin: '0 auto',
    }}>
      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>
        {r.title}
      </h2>
      <p style={{ fontSize: 14, color: 'var(--on-surface2)', marginBottom: 32 }}>{r.sub}</p>

      {/* Referral link */}
      <div style={{
        background: 'rgba(10,15,30,0.65)', backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)', border: '1px solid rgba(61,127,255,0.35)',
        borderRadius: 16, padding: '28px 24px', marginBottom: 20,
        boxShadow: '0 4px 32px rgba(61,127,255,0.12)',
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '1.5px',
                      color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 12 }}>
          {r.linkLabel}
        </div>
        <div style={{
          display: 'flex', gap: 10, alignItems: 'center',
          background: 'rgba(5,8,16,0.6)', borderRadius: 10,
          border: '1px solid var(--outline)', padding: '10px 14px', marginBottom: 16, flexWrap: 'wrap',
        }}>
          <code style={{ flex: 1, fontSize: 13, color: 'var(--accent)', wordBreak: 'break-all', fontFamily: 'monospace' }}>
            https://total-hunter.com/ref/{user.ref_code}
          </code>
          <button onClick={copyLink} style={{
            padding: '9px 20px', borderRadius: 8, fontSize: 13, fontWeight: 700,
            background: copied ? 'rgba(61,127,255,0.2)' : 'var(--accent)',
            color: copied ? 'var(--accent)' : '#000',
            border: copied ? '1px solid var(--accent)' : 'none',
            cursor: 'pointer', flexShrink: 0, fontFamily: 'inherit',
            transition: 'all 0.2s', boxShadow: copied ? 'none' : '0 0 14px var(--accent-glow)',
          }}>
            {copied ? r.copied : r.copy}
          </button>
        </div>
        <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
          {r.codeLabel} <span style={{ color: '#FFFFFF', fontWeight: 600 }}>{user.ref_code}</span>
        </div>
      </div>

      {/* Network L1/L2/L3 */}
      {user.referrals && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '1.5px',
                        color: 'var(--on-surface2)', textTransform: 'uppercase',
                        width: '100%', marginBottom: 4 }}>
            {r.networkTitle}
          </div>
          {[
            { key: 'l1', label: 'L1', color: 'var(--accent)' },
            { key: 'l2', label: 'L2', color: '#B060FF' },
            { key: 'l3', label: 'L3', color: 'var(--credits-gold)' },
          ].map(({ key, label, color }) => (
            <div key={key} style={{
              flex: '1 1 80px', background: 'var(--elevated)',
              border: `1px solid ${color}33`, borderRadius: 12,
              padding: '16px 12px', textAlign: 'center',
            }}>
              <div style={{ fontSize: 11, color: 'var(--on-surface2)', marginBottom: 6, fontWeight: 600 }}>{label}</div>
              <div style={{ fontSize: 32, fontWeight: 800, color,
                            textShadow: `0 0 16px ${color}88`, lineHeight: 1 }}>
                {user.referrals[key] || 0}
              </div>
              <div style={{ fontSize: 11, color: 'var(--on-surface2)', marginTop: 4 }}>{r.networkPeople}</div>
            </div>
          ))}
        </div>
      )}

      {/* Referral balance */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{
          flex: '1 1 180px', background: 'var(--elevated)',
          border: '1px solid rgba(255,209,102,0.3)', borderRadius: 14,
          padding: '24px 20px', textAlign: 'center',
          boxShadow: '0 0 16px rgba(255,209,102,0.1)',
        }}>
          <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 10, fontWeight: 500 }}>
            {r.balanceLabel}
          </div>
          <div style={{ fontSize: 46, fontWeight: 800, color: 'var(--credits-gold)',
                        textShadow: '0 0 24px rgba(255,209,102,0.6)',
                        fontVariantNumeric: 'tabular-nums', lineHeight: 1, marginBottom: 16 }}>
            {refCredits}
          </div>
          <button onClick={transfer} disabled={loading || user.ref_credits === 0} style={{
            width: '100%', padding: '13px 0', borderRadius: 10,
            fontSize: 14, fontWeight: 900, fontFamily: 'inherit',
            background: user.ref_credits > 0
              ? 'linear-gradient(135deg, #00CC66, #00FF88)'
              : 'rgba(255,255,255,0.05)',
            color: user.ref_credits > 0 ? '#000' : 'rgba(255,255,255,0.25)',
            border: 'none',
            cursor: user.ref_credits > 0 ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s',
            boxShadow: user.ref_credits > 0 ? '0 0 24px rgba(0,255,136,0.4)' : 'none',
            letterSpacing: '0.5px',
          }}>
            {loading ? '⏳ ' + r.transferring : '💸 ' + r.transfer}
          </button>
          {msg && <div style={{ marginTop: 10, fontSize: 13, color: 'var(--on-surface2)' }}>{msg}</div>}
        </div>
      </div>

      {/* Inviter code — shown only if not yet referred */}
      {!user.invited_by_id && (
        <div className="card" style={{ borderRadius: 14, marginBottom: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 8 }}>
            {r.inviterTitle}
          </div>
          <p style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 8 }}>
            {r.inviterSub}
          </p>
          <p style={{ fontSize: 12, color: 'rgba(255,209,102,0.75)', marginBottom: 16 }}>
            {lang === 'en'
              ? '⚡ Bonus (+50 ◆) is credited after your first device link in the bot.'
              : '⚡ Бонус (+50 ◆) начисляется после первой привязки устройства в боте.'}
          </p>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              value={codeInput}
              onChange={e => setCodeInput(e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 8))}
              placeholder="XXXXXXXX"
              maxLength={8}
              style={{
                flex: 1, background: 'var(--elevated)', border: '1px solid var(--outline)',
                color: 'var(--on-surface)', borderRadius: 8, padding: '10px 14px',
                fontSize: 18, letterSpacing: 6, textAlign: 'center', fontFamily: 'monospace',
              }}
            />
            <button
              onClick={activateCode}
              disabled={codeLoading || codeInput.length < 6}
              style={{
                padding: '10px 22px', borderRadius: 8, fontSize: 14, fontWeight: 700,
                background: codeInput.length >= 6 ? 'var(--accent)' : 'var(--elevated)',
                color: codeInput.length >= 6 ? '#000' : 'var(--on-surface2)',
                border: 'none', cursor: codeInput.length >= 6 ? 'pointer' : 'not-allowed',
                fontFamily: 'inherit',
              }}
            >
              {codeLoading ? '...' : r.inviterBtn}
            </button>
          </div>
          {codeMsg && (
            <div style={{ marginTop: 10, fontSize: 13,
              color: codeMsg.includes('ctivat') || codeMsg.includes('ктивир') ? '#4ADE80' : 'var(--on-surface2)' }}>
              {codeMsg}
            </div>
          )}
        </div>
      )}

      {/* If already referred — show success */}
      {user.invited_by_id && (
        <div style={{
          background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.25)',
          borderRadius: 12, padding: '14px 18px', marginBottom: 20,
          fontSize: 13, color: '#4ADE80', fontWeight: 600,
        }}>
          ✅ {r.inviterActive}
        </div>
      )}

      {/* Cascade info */}
      <div className="card" style={{ borderRadius: 14 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 16 }}>
          {r.howTitle}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {r.levels.map(({ level, pct, desc, color }) => (
            <div key={level} style={{
              display: 'flex', alignItems: 'center', gap: 14,
              padding: '12px 16px', borderRadius: 10,
              background: 'var(--elevated)', border: '1px solid var(--outline)',
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: 8, flexShrink: 0,
                background: `${color}18`, border: `1px solid ${color}44`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 800, color,
              }}>
                {level}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, color: '#FFFFFF', fontWeight: 600 }}>{desc}</div>
                <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>{r.perPurchase}</div>
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, color, textShadow: `0 0 12px ${color}88` }}>
                {pct}
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 14, fontSize: 12, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
          {r.note}
        </div>
      </div>
    </div>
  )
}
