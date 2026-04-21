import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'

const PACKAGES = [
  {
    id: 'lite',
    name: 'Lite',
    credits: 300,
    price: '$1.00',
    bonus: null,
    color: 'var(--accent)',
    glow: 'rgba(61,127,255,0.25)',
    featured: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    credits: 1500,
    bonus: 500,
    price: '$5.00',
    color: '#B060FF',
    glow: 'rgba(176,96,255,0.25)',
    featured: true,
  },
  {
    id: 'ultra',
    name: 'Ultra',
    credits: 4000,
    bonus: 1000,
    price: '$10.00',
    color: 'var(--credits-gold)',
    glow: 'rgba(255,209,102,0.25)',
    featured: false,
  },
]

function BalanceCard({ title, value, color }) {
  const animated = useCounter(typeof value === 'number' ? value : null)
  return (
    <div className="card" style={{ flex: '1 1 160px', borderRadius: 12, textAlign: 'center', padding: '24px 20px' }}>
      <div style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 10 }}>{title}</div>
      <div style={{
        fontSize: 42, fontWeight: 800,
        color: color ?? 'var(--accent)',
        textShadow: `0 0 20px ${color ?? 'var(--accent)'}88`,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {value != null ? animated.toLocaleString() : '—'}
      </div>
    </div>
  )
}

function PackageCard({ pkg, buying, onBuy }) {
  const [hovered, setHovered] = useState(false)
  const total = (pkg.credits + (pkg.bonus ?? 0)).toLocaleString()

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: '1 1 200px',
        background: pkg.featured ? 'linear-gradient(160deg, rgba(176,96,255,0.08) 0%, rgba(61,127,255,0.08) 100%)' : 'var(--elevated)',
        border: `1px solid ${hovered || pkg.featured ? pkg.color : 'var(--outline)'}`,
        borderRadius: 14, padding: pkg.featured ? '28px 20px' : '24px 20px',
        position: 'relative',
        transition: 'box-shadow 0.2s, border-color 0.2s, transform 0.15s',
        boxShadow: hovered ? `0 0 28px ${pkg.glow}` : pkg.featured ? `0 0 16px ${pkg.glow}` : 'none',
        transform: pkg.featured ? 'scale(1.03)' : 'scale(1)',
        textAlign: 'center',
      }}
    >
      {/* Featured badge */}
      {pkg.featured && (
        <div style={{
          position: 'absolute', top: -13, left: '50%', transform: 'translateX(-50%)',
          background: 'linear-gradient(90deg, var(--accent), #B060FF)',
          color: '#FFFFFF', fontSize: 11, fontWeight: 700,
          padding: '4px 14px', borderRadius: 20, letterSpacing: '0.5px',
          whiteSpace: 'nowrap',
        }}>
          ⭐ Выбор охотника
        </div>
      )}

      <div style={{
        fontSize: 20, fontWeight: 800, color: pkg.color, marginBottom: 6,
        textShadow: `0 0 16px ${pkg.glow}`,
      }}>
        {pkg.name}
      </div>

      <div style={{ fontSize: 36, fontWeight: 800, color: '#FFFFFF', lineHeight: 1, marginBottom: 4 }}>
        {total}
      </div>
      <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 4 }}>кредитов</div>

      {pkg.bonus && (
        <div style={{
          fontSize: 12, fontWeight: 600, color: pkg.color,
          marginBottom: 16, letterSpacing: '0.3px',
        }}>
          +{pkg.bonus.toLocaleString()} бонусных кредитов
        </div>
      )}
      {!pkg.bonus && <div style={{ marginBottom: 16 }} />}

      <div style={{
        fontSize: 28, fontWeight: 700, color: '#FFFFFF', marginBottom: 20,
      }}>
        {pkg.price}
      </div>

      <button
        disabled={!!buying}
        onClick={() => onBuy(pkg.id)}
        style={{
          width: '100%', padding: '12px 0',
          background: buying === pkg.id ? 'var(--elevated)' : pkg.color,
          color: buying === pkg.id ? 'var(--on-surface2)' : '#000',
          border: 'none', borderRadius: 8,
          fontSize: 14, fontWeight: 700,
          cursor: buying ? 'not-allowed' : 'pointer',
          opacity: buying && buying !== pkg.id ? 0.5 : 1,
          transition: 'opacity 0.15s, box-shadow 0.15s',
          boxShadow: buying === pkg.id ? 'none' : `0 0 14px ${pkg.glow}`,
          fontFamily: 'inherit',
        }}
      >
        {buying === pkg.id ? 'Переход к оплате...' : 'Купить →'}
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
      background: 'radial-gradient(ellipse 100% 50% at 50% 0%, rgba(176,96,255,0.06) 0%, transparent 55%)',
      padding: '32px 24px', maxWidth: 960, margin: '0 auto',
    }}>

      <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 24 }}>
        Баланс
      </h2>

      {/* Balance overview */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 40, flexWrap: 'wrap' }}>
        <BalanceCard title="Кредиты"           value={user.credits}     color="var(--accent)" />
        <BalanceCard title="Реферальный баланс" value={user.ref_credits} color="var(--credits-gold)" />
      </div>

      {/* Packages */}
      <h3 style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 8 }}>
        Купить кредиты
      </h3>
      <p style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 28 }}>
        Оплата через Free-Kassa. Кредиты зачисляются мгновенно после оплаты.
      </p>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start', marginBottom: 32 }}>
        {PACKAGES.map(pkg => (
          <PackageCard key={pkg.id} pkg={pkg} buying={buying} onBuy={handleBuy} />
        ))}
      </div>

      {error && (
        <div style={{ color: 'var(--error-text)', fontSize: 14, marginBottom: 20,
                      padding: '10px 16px', background: 'rgba(122,32,32,0.2)',
                      borderRadius: 8, border: '1px solid var(--error)' }}>
          {error}
        </div>
      )}

      {/* Daily Bonus stub */}
      <div className="card" style={{ maxWidth: 480, borderRadius: 14 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12,
        }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: 'rgba(255,209,102,0.12)',
            border: '1px solid rgba(255,209,102,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
          }}>
            🎁
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF' }}>Daily Bonus</div>
        </div>
        <div style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 16, lineHeight: 1.6 }}>
          Посмотри короткую рекламу и получи 3–7 бесплатных кредитов. До 3 раз в день.
        </div>
        <button disabled style={{
          padding: '10px 20px', borderRadius: 8, fontSize: 14, fontWeight: 600,
          background: 'var(--elevated)', color: 'var(--on-surface2)',
          border: '1px solid var(--outline)', cursor: 'not-allowed', fontFamily: 'inherit',
        }}>
          Скоро...
        </button>
      </div>

    </div>
  )
}
