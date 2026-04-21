import { useEffect, useState } from 'react'
import { api } from '../api.js'

const TYPE_META = {
  purchase:              { label: 'Покупка кредитов',   icon: '◆', sign: '+', color: '#4ADE80' },
  credit_use:            { label: 'Охота',               icon: '⚔', sign: '−', color: '#FFFFFF' },
  trial:                 { label: 'Триал-бонус',         icon: '🎁', sign: '+', color: '#4ADE80' },
  ref_welcome:           { label: 'Реф. приветствие',   icon: '⬡', sign: '+', color: 'var(--credits-gold)' },
  ref_earning:           { label: 'Реф. начисление',    icon: '⬡', sign: '+', color: 'var(--credits-gold)' },
  ref_transfer:          { label: 'Рефералы → баланс',  icon: '→',  sign: '+', color: '#4ADE80' },
  hwid_duplicate_blocked:{ label: 'HWID дубликат',      icon: '⚠', sign: '',  color: 'var(--on-surface2)' },
  manual_adjust:         { label: 'Корректировка',      icon: '✎', sign: '',  color: 'var(--on-surface2)' },
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function TransactionsPage() {
  const [data, setData] = useState(null)

  useEffect(() => { api.transactions().then(setData) }, [])

  if (!data) return <div className="page-content text-muted">Загрузка...</div>

  const items = data.items ?? []

  return (
    <div style={{
      minHeight: '100%',
      background: 'radial-gradient(ellipse 100% 40% at 50% 0%, rgba(74,222,128,0.04) 0%, transparent 55%)',
      padding: '32px 24px', maxWidth: 860, margin: '0 auto',
    }}>
      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 24 }}>
        Транзакции
      </h2>

      <div className="card" style={{ borderRadius: 14, padding: 0, overflow: 'hidden' }}>

        {/* Table header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '36px 1fr 100px 140px',
          padding: '10px 20px',
          borderBottom: '1px solid var(--outline)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1px',
          color: 'var(--on-surface2)', textTransform: 'uppercase',
        }}>
          <div />
          <div>Операция</div>
          <div style={{ textAlign: 'right' }}>Сумма</div>
          <div style={{ textAlign: 'right' }}>Дата</div>
        </div>

        {items.length === 0 ? (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--on-surface2)', fontSize: 14 }}>
            Транзакций пока нет
          </div>
        ) : (
          items.map((t, i) => {
            const meta = TYPE_META[t.type] ?? { label: t.type, icon: '◈', sign: '', color: '#FFFFFF' }
            const isPositive = t.amount > 0
            const amountColor = isPositive ? '#4ADE80' : '#FFFFFF'
            const amountGlow  = isPositive ? 'rgba(74,222,128,0.5)' : 'none'
            const prefix = t.amount > 0 ? '+' : t.amount < 0 ? '−' : ''

            return (
              <div key={i} style={{
                display: 'grid', gridTemplateColumns: '36px 1fr 100px 140px',
                alignItems: 'center', padding: '13px 20px',
                borderBottom: i < items.length - 1 ? '1px solid var(--separator)' : 'none',
                transition: 'background 0.12s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--elevated)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>

                {/* Icon */}
                <div style={{
                  width: 28, height: 28, borderRadius: 6,
                  background: `${meta.color}18`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13,
                }}>
                  {meta.icon}
                </div>

                {/* Label */}
                <div style={{ fontSize: 14, color: '#FFFFFF', fontWeight: 500 }}>
                  {meta.label}
                </div>

                {/* Amount */}
                <div style={{
                  fontSize: 15, fontWeight: 700, textAlign: 'right',
                  color: amountColor,
                  textShadow: isPositive ? `0 0 10px ${amountGlow}` : 'none',
                  fontVariantNumeric: 'tabular-nums',
                }}>
                  {t.amount !== 0 ? `${prefix}${Math.abs(t.amount)}` : '—'}
                </div>

                {/* Date */}
                <div style={{
                  fontSize: 12, color: 'var(--on-surface2)',
                  textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                }}>
                  {formatDate(t.created_at)}
                </div>

              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
