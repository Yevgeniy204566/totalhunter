import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const TYPE_ICONS = {
  purchase:               { icon: '◆', color: '#4ADE80' },
  credit_use:             { icon: '⚔', color: '#FFFFFF' },
  trial:                  { icon: '🎁', color: '#4ADE80' },
  ref_welcome:            { icon: '⬡', color: 'var(--credits-gold)' },
  ref_earning:            { icon: '⬡', color: 'var(--credits-gold)' },
  ref_transfer:           { icon: '→', color: '#4ADE80' },
  hwid_duplicate_blocked: { icon: '⚠', color: 'var(--on-surface2)' },
  manual_adjust:          { icon: '✎', color: 'var(--on-surface2)' },
}

export default function TransactionsPage() {
  const [data, setData] = useState(null)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const t = D.transactions

  function formatDate(iso) {
    const d = new Date(iso)
    return d.toLocaleString(lang === 'ru' ? 'ru-RU' : 'en-GB', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  }

  useEffect(() => { api.transactions().then(setData) }, [])

  if (!data) return <div className="page-content text-muted">{D.loading}</div>

  const items = data.items ?? []

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 100% 40% at 50% 0%, rgba(74,222,128,0.04) 0%, transparent 55%)',
      padding: '32px 24px', maxWidth: 860, margin: '0 auto',
    }}>
      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 24 }}>
        {t.title}
      </h2>

      <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>
        <div style={{
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
          const meta  = TYPE_ICONS[tx.type] ?? { icon: '◈', color: '#FFFFFF' }
          const label = t.types[tx.type] ?? tx.type
          const isPos = tx.amount > 0
          const prefix = tx.amount > 0 ? '+' : tx.amount < 0 ? '−' : ''
          return (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '36px 1fr 100px 140px',
              alignItems: 'center', padding: '13px 20px',
              borderBottom: i < items.length - 1 ? '1px solid var(--separator)' : 'none',
              transition: 'background 0.12s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: `${meta.color}18`,
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
    </div>
  )
}
