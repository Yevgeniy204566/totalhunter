import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'

const PACKAGES = [
  {
    id:       'lite',
    name:     'SCOUT',
    credits:  300,
    bonus:    null,
    total:    300,
    price:    '$1.00',
    color:    '#3D7FFF',
    glow:     'rgba(61,127,255,0.30)',
    bg:       'rgba(61,127,255,0.06)',
    featured: false,
  },
  {
    id:       'pro',
    name:     'STALKER',
    credits:  1500,
    bonus:    500,
    total:    2000,
    price:    '$5.00',
    color:    '#4ADE80',
    glow:     'rgba(74,222,128,0.30)',
    bg:       'rgba(74,222,128,0.07)',
    featured: true,
  },
  {
    id:       'ultra',
    name:     'RAIDER',
    credits:  4000,
    bonus:    1000,
    total:    5000,
    price:    '$10.00',
    color:    '#FFD166',
    glow:     'rgba(255,209,102,0.30)',
    bg:       'rgba(255,209,102,0.06)',
    featured: false,
  },
]

function BalanceCard({ title, value, color }) {
  const animated = useCounter(typeof value === 'number' ? value : null)
  return (
    <div className="card" style={{
      flex: '1 1 160px', borderRadius: 14, textAlign: 'center', padding: '22px 20px',
    }}>
      <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 8,
                    fontWeight: 600, letterSpacing: '0.5px' }}>
        {title}
      </div>
      <div style={{
        fontSize: 44, fontWeight: 900, color,
        textShadow: `0 0 22px ${color}99`,
        fontVariantNumeric: 'tabular-nums',
        lineHeight: 1,
      }}>
        {value != null ? animated.toLocaleString() : '—'}
      </div>
    </div>
  )
}

function PackageCard({ pkg, buying, onBuy }) {
  const [hovered, setHovered] = useState(false)
  const isActive = hovered || pkg.featured

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: '1 1 210px',
        position: 'relative',
        background: `linear-gradient(160deg, ${pkg.bg} 0%, rgba(5,8,16,0.95) 100%)`,
        border: `1px solid ${isActive ? pkg.color : 'var(--outline)'}`,
        borderRadius: 18,
        padding: pkg.featured ? '36px 24px 24px' : '28px 20px 20px',
        textAlign: 'center',
        transition: 'box-shadow 0.25s, border-color 0.25s, transform 0.2s',
        boxShadow: isActive
          ? `0 0 36px ${pkg.glow}, inset 0 1px 0 ${pkg.color}33`
          : 'none',
        transform: pkg.featured ? 'scale(1.04)' : hovered ? 'scale(1.01)' : 'scale(1)',
      }}
    >
      {/* Featured badge */}
      {pkg.featured && (
        <div style={{
          position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)',
          background: `linear-gradient(90deg, #4ADE80, #3D7FFF)`,
          color: '#000', fontSize: 11, fontWeight: 900,
          padding: '5px 18px', borderRadius: 20, letterSpacing: '0.8px',
          whiteSpace: 'nowrap', textTransform: 'uppercase',
        }}>
          ⭐ Выбор охотника
        </div>
      )}

      {/* Pack name */}
      <div style={{
        fontSize: 22, fontWeight: 900, color: pkg.color,
        letterSpacing: '2px', textTransform: 'uppercase',
        textShadow: `0 0 20px ${pkg.glow}`,
        marginBottom: 20,
      }}>
        {pkg.name}
      </div>

      {/* BONUS — the hook */}
      {pkg.bonus ? (
        <>
          <div style={{
            fontSize: 62, fontWeight: 900, lineHeight: 1,
            color: '#FFD166',
            textShadow: '0 0 30px rgba(255,209,102,0.85), 0 0 60px rgba(255,209,102,0.35)',
            fontVariantNumeric: 'tabular-nums',
            marginBottom: 4,
          }}>
            +{pkg.bonus.toLocaleString()}
          </div>
          <div style={{
            fontSize: 11, fontWeight: 900, letterSpacing: '2px',
            color: '#FFD166', opacity: 0.9,
            textTransform: 'uppercase', marginBottom: 18,
          }}>
            🎁 бонус кредитов
          </div>
        </>
      ) : (
        <div style={{ height: 88 }} />
      )}

      {/* Total — secondary hero */}
      <div style={{
        fontSize: 34, fontWeight: 900, color: '#FFFFFF', lineHeight: 1,
        textShadow: '0 0 14px rgba(255,255,255,0.55)',
        fontVariantNumeric: 'tabular-nums',
        marginBottom: 6,
      }}>
        = {pkg.total.toLocaleString()} КР
      </div>

      {/* Base credits strikethrough */}
      {pkg.bonus ? (
        <div style={{
          fontSize: 13, color: 'var(--on-surface2)', marginBottom: 22,
        }}>
          <span style={{ textDecoration: 'line-through', opacity: 0.55 }}>
            {pkg.credits.toLocaleString()}
          </span>
          {' '}базовых
        </div>
      ) : (
        <div style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 22 }}>
          кредитов на охоту
        </div>
      )}

      {/* Buy button */}
      <button
        disabled={!!buying}
        onClick={() => onBuy(pkg.id)}
        style={{
          width: '100%', padding: '14px 0',
          background: buying === pkg.id
            ? 'var(--elevated)'
            : `linear-gradient(135deg, ${pkg.color}, ${pkg.color}cc)`,
          color: buying === pkg.id ? 'var(--on-surface2)' : '#000',
          border: 'none', borderRadius: 10,
          fontSize: 15, fontWeight: 900,
          cursor: buying ? 'not-allowed' : 'pointer',
          opacity: buying && buying !== pkg.id ? 0.4 : 1,
          transition: 'opacity 0.15s, box-shadow 0.2s',
          boxShadow: buying === pkg.id ? 'none' : `0 0 20px ${pkg.glow}`,
          fontFamily: 'inherit', letterSpacing: '0.3px',
        }}
      >
        {buying === pkg.id ? 'Переход...' : `Купить — ${pkg.price}`}
      </button>
    </div>
  )
}

export default function BalancePage() {
  const [user,   setUser]   = useState(null)
  const [buying, setBuying] = useState(null)
  const [error,  setError]  = useState('')

  useEffect(() => { api.me().then(setUser) }, [])

  async function handleBuy(pkg) {
    setBuying(pkg)
    setError('')
    try {
      const data = await api.paymentCreate(pkg)
      window.location.href = data.redirect_url
    } catch (e) {
      setError(e.message || 'Ошибка оплаты')
      setBuying(null)
    }
  }

  if (!user) return <div className="page-content text-muted">Загрузка...</div>

  return (
    <div style={{
      minHeight: '100%',
      background: `
        radial-gradient(ellipse 80% 40% at 20% 0%, rgba(74,222,128,0.05) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 0%, rgba(61,127,255,0.05) 0%, transparent 60%),
        var(--bg)
      `,
      padding: '32px 24px', maxWidth: 980, margin: '0 auto',
    }}>

      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 900, marginBottom: 24 }}>
        Баланс
      </h2>

      {/* Balance overview */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 44, flexWrap: 'wrap' }}>
        <BalanceCard title="Кредиты"           value={user.credits}     color="var(--accent)" />
        <BalanceCard title="Реферальный баланс" value={user.ref_credits} color="var(--credits-gold)" />
      </div>

      {/* Section title */}
      <div style={{ textAlign: 'center', marginBottom: 36 }}>
        <div style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '3px',
          color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 10,
        }}>
          ⬡ Выбери свой арсенал
        </div>
        <h3 style={{ fontSize: 26, fontWeight: 900, color: '#FFFFFF', marginBottom: 6 }}>
          Пополнение кредитов
        </h3>
        <p style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
          Оплата через Free-Kassa · Зачисление мгновенно
        </p>
      </div>

      {/* Package cards */}
      <div style={{
        display: 'flex', gap: 20, flexWrap: 'wrap',
        alignItems: 'flex-start',
        paddingTop: 20,   /* space for featured badge */
        marginBottom: 36,
      }}>
        {PACKAGES.map(pkg => (
          <PackageCard key={pkg.id} pkg={pkg} buying={buying} onBuy={handleBuy} />
        ))}
      </div>

      {error && (
        <div style={{
          color: 'var(--error-text)', fontSize: 14, marginBottom: 24,
          padding: '12px 16px', background: 'rgba(122,32,32,0.2)',
          borderRadius: 10, border: '1px solid var(--error)',
        }}>
          {error}
        </div>
      )}

      {/* Daily Bonus */}
      <div className="card" style={{ maxWidth: 480, borderRadius: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 10, flexShrink: 0,
            background: 'rgba(255,209,102,0.12)',
            border: '1px solid rgba(255,209,102,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
          }}>
            🎁
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#FFFFFF' }}>Daily Bonus</div>
            <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>До 3 раз в день</div>
          </div>
        </div>
        <div style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 16, lineHeight: 1.65 }}>
          Посмотри короткую рекламу и получи 3–7 бесплатных кредитов.
        </div>
        <button disabled style={{
          padding: '10px 20px', borderRadius: 8, fontSize: 14, fontWeight: 700,
          background: 'var(--elevated)', color: 'var(--on-surface2)',
          border: '1px solid var(--outline)', cursor: 'not-allowed', fontFamily: 'inherit',
        }}>
          Скоро...
        </button>
      </div>

    </div>
  )
}
