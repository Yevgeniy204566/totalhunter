import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

const BLACKSEA_URLS = {
  scout:  'https://totalhunter.blacksea.in.ua/l/pso',
  hunter: 'https://totalhunter.blacksea.in.ua/l/hvy',
  ultra:  'https://totalhunter.blacksea.in.ua/l/dbb',
}

// Ultra — визуал не менять (владелец зафиксировал). Scout/Hunter — та же
// структура карточки, другая цветовая гамма (accent/border/glow/buttonGrad),
// плюс bonusLine — выгода в % относительно базового тарифа Scout ($3/1000 —
// 1 алмаз = $0.003; Hunter 2000 за $5 = +20%; Ultra 5000 за $10 = +50%).
const PACKAGES = [
  {
    id: 'scout', name: 'SCOUT', price: '$3', usd: 3, credits: 1000, creditsDisplay: '1 000',
    topBadge: null, bonusLine: null,
    usageHint: '1,000 Crypt hunts (1 ◆ = 1 Crypt)',
    countColor: '#00FFA3', countGrad: 'linear-gradient(135deg, #00CC7A, #00FFA3)',
    countGlow: 'rgba(0,255,163,0.8)',
    diamondGlow: 'drop-shadow(0 0 20px rgba(0,255,163,0.9)) drop-shadow(0 0 40px rgba(0,180,110,0.5))',
    borderBase: '#00663D', borderHover: '#00FFA3',
    shadowBase: '0 0 30px rgba(0,180,110,0.2), inset 0 0 20px rgba(0,150,90,0.05)',
    shadowHover: '0 0 60px rgba(0,255,163,0.5), 0 0 120px rgba(0,180,110,0.25), inset 0 0 40px rgba(0,150,90,0.08)',
    buttonGrad: 'linear-gradient(135deg, #009955, #00CC7A, #009955)',
    buttonBorder: 'rgba(0,255,163,0.4)', buttonShadow: '0 0 24px rgba(0,200,130,0.6)',
    hasCrypto: false,
  },
  {
    id: 'hunter', name: 'HUNTER', price: '$5', usd: 5, credits: 2000, creditsDisplay: '2 000',
    topBadge: '🔥 POPULAR', bonusLine: '+20% MORE DIAMONDS',
    usageHint: '2,000 Crypt hunts (1 ◆ = 1 Crypt)',
    countColor: '#B060FF', countGrad: 'linear-gradient(135deg, #9933FF, #C080FF)',
    countGlow: 'rgba(176,96,255,0.8)',
    diamondGlow: 'drop-shadow(0 0 20px rgba(176,96,255,0.9)) drop-shadow(0 0 40px rgba(120,50,220,0.5))',
    borderBase: '#5A2299', borderHover: '#C080FF',
    shadowBase: '0 0 30px rgba(120,50,220,0.2), inset 0 0 20px rgba(100,40,200,0.05)',
    shadowHover: '0 0 60px rgba(176,96,255,0.5), 0 0 120px rgba(120,50,220,0.25), inset 0 0 40px rgba(100,40,200,0.08)',
    buttonGrad: 'linear-gradient(135deg, #7A2FCC, #B060FF, #7A2FCC)',
    buttonBorder: 'rgba(176,96,255,0.4)', buttonShadow: '0 0 24px rgba(150,80,255,0.6)',
    hasCrypto: false,
  },
  {
    id: 'ultra', name: 'TOTAL HUNTER', price: '$10', usd: 10, credits: 5000, creditsDisplay: '5 000',
    topBadge: '★ BEST VALUE ★', bonusLine: '+50% MORE DIAMONDS',
    usageHint: '5,000 Crypt hunts (1 ◆ = 1 Crypt)',
    countColor: '#00CFFF', countGrad: 'linear-gradient(135deg, #00CFFF, #00EFFF)',
    countGlow: 'rgba(0,207,255,0.8)',
    diamondGlow: 'drop-shadow(0 0 20px rgba(0,207,255,0.9)) drop-shadow(0 0 40px rgba(0,100,255,0.5))',
    borderBase: '#0066AA', borderHover: '#00EFFF',
    shadowBase: '0 0 30px rgba(0,100,255,0.2), inset 0 0 20px rgba(0,80,200,0.05)',
    shadowHover: '0 0 60px rgba(0,180,255,0.5), 0 0 120px rgba(0,100,255,0.25), inset 0 0 40px rgba(0,100,255,0.08)',
    buttonGrad: 'linear-gradient(135deg, #0066FF, #00AAFF, #0066FF)',
    buttonBorder: 'rgba(0,200,255,0.4)', buttonShadow: '0 0 24px rgba(0,150,255,0.6)',
    hasCrypto: true, featured: true,
  },
]

function Diamond({ size = 22 }) {
  return (
    <span style={{
      fontSize: size, lineHeight: 1,
      background: 'linear-gradient(135deg, #B060FF 0%, #3D7FFF 50%, #00CFFF 100%)',
      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
      filter: 'drop-shadow(0 0 6px rgba(61,127,255,0.7))',
      display: 'inline-block',
    }}>◆</span>
  )
}

function BalanceCard({ title, value, color }) {
  const animated = useCounter(typeof value === 'number' ? value : null)
  return (
    <div style={{
      flex: '1 1 160px', borderRadius: 16, textAlign: 'center', padding: '22px 20px',
      background: 'rgba(255,255,255,0.04)',
      backdropFilter: 'blur(12px)',
      border: `1px solid ${color}44`,
      boxShadow: `0 0 32px ${color}22`,
    }}>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: 8,
                    fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase' }}>
        {title}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        <Diamond size={26} />
        <div style={{
          fontSize: 42, fontWeight: 900, color,
          textShadow: `0 0 32px ${color}cc`,
          fontVariantNumeric: 'tabular-nums', lineHeight: 1,
        }}>
          {value != null ? animated.toLocaleString() : '—'}
        </div>
      </div>
    </div>
  )
}

function Sparkles({ color }) {
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden', borderRadius: 20 }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} style={{
          position: 'absolute',
          width: 3, height: 3, borderRadius: '50%',
          background: color,
          boxShadow: `0 0 6px ${color}`,
          left: `${15 + i * 14}%`,
          top: `${10 + (i % 3) * 25}%`,
          animation: `sparkle ${1.2 + i * 0.3}s ease-in-out infinite alternate`,
          opacity: 0.7,
        }} />
      ))}
    </div>
  )
}

function PackageCard({ pkg, buying, onBuy }) {
  const [hovered, setHovered] = useState(false)
  const isBuying = buying === pkg.id

  return (
    <div
      className="package-card"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: 280, maxWidth: 320, flexShrink: 0,
        position: 'relative', textAlign: 'center',
        borderRadius: 24,
        background: 'linear-gradient(160deg, #0a0a1a 0%, #0d0f2a 50%, #080818 100%)',
        border: `2px solid ${hovered ? pkg.borderHover : pkg.borderBase}`,
        padding: '32px 24px 28px',
        boxShadow: hovered ? pkg.shadowHover : pkg.shadowBase,
        transform: hovered ? 'scale(1.04) translateY(-4px)' : 'scale(1)',
        transition: 'all 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        overflow: 'hidden',
      }}
    >
      {/* Animated corner glow */}
      <div style={{
        position: 'absolute', top: -40, right: -40, width: 120, height: 120,
        background: `radial-gradient(circle, ${pkg.countGlow.replace('0.8', '0.25')} 0%, transparent 70%)`,
        borderRadius: '50%', pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: -40, left: -40, width: 100, height: 100,
        background: 'radial-gradient(circle, rgba(80,0,255,0.2) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none',
      }} />

      {/* TOP BADGE */}
      {pkg.topBadge && (
        <div style={{
          position: 'absolute', top: -1, left: '50%', transform: 'translateX(-50%)',
          background: pkg.buttonGrad,
          borderRadius: '0 0 14px 14px',
          padding: '4px 22px', fontSize: 9, fontWeight: 900,
          color: '#fff', letterSpacing: '2px', textTransform: 'uppercase',
          boxShadow: `0 4px 16px ${pkg.countGlow.replace('0.8', '0.5')}`,
          whiteSpace: 'nowrap',
        }}>
          {pkg.topBadge}
        </div>
      )}

      {/* Big Diamond */}
      <div style={{
        fontSize: 52, lineHeight: 1, marginBottom: 4, marginTop: 14,
        filter: pkg.diamondGlow,
      }}>◆</div>

      {/* Price */}
      <div style={{
        fontSize: 58, fontWeight: 900, lineHeight: 1,
        background: 'linear-gradient(135deg, #FFD700, #FFA500, #FFD700)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        filter: 'drop-shadow(0 0 16px rgba(255,200,0,0.8))',
        fontVariantNumeric: 'tabular-nums', marginBottom: 2,
      }}>
        {pkg.price}
      </div>
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', letterSpacing: '2px', marginBottom: pkg.bonusLine ? 4 : 16 }}>
        USD · ONE TIME
      </div>
      {pkg.bonusLine && (
        <div style={{
          fontSize: 11, fontWeight: 800, letterSpacing: '1px',
          color: pkg.countColor, marginBottom: 16,
        }}>
          {pkg.bonusLine}
        </div>
      )}

      {/* Divider */}
      <div style={{
        width: '80%', height: 1, margin: '0 auto 16px',
        background: `linear-gradient(90deg, transparent, ${pkg.countColor}66, transparent)`,
      }} />

      {/* Diamonds count */}
      <div style={{
        fontSize: 42, fontWeight: 900, lineHeight: 1,
        background: pkg.countGrad,
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        filter: `drop-shadow(0 0 16px ${pkg.countGlow})`,
        fontVariantNumeric: 'tabular-nums', marginBottom: 4,
      }}>
        {pkg.creditsDisplay}
      </div>
      <div style={{
        fontSize: 11, fontWeight: 700, letterSpacing: '3px',
        color: pkg.countColor, textTransform: 'uppercase', marginBottom: 6,
        opacity: 0.85,
      }}>
        ◆ DIAMONDS
      </div>

      {/* Usage hint */}
      <div style={{
        fontSize: 11, color: 'rgba(255,255,255,0.35)',
        marginBottom: 22, lineHeight: 1.5,
      }}>
        {pkg.usageHint}
      </div>

      {/* BUY WITH CARD (BlackSea) — static product link, no backend call */}
      <a
        href={BLACKSEA_URLS[pkg.id]}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'block', width: '100%', padding: '14px 0',
          background: pkg.buttonGrad,
          backgroundSize: '200% 100%',
          color: '#fff',
          border: `1px solid ${pkg.buttonBorder}`,
          borderRadius: 12, fontSize: 14, fontWeight: 900,
          cursor: 'pointer',
          transition: 'all 0.2s',
          boxShadow: `${pkg.buttonShadow}, inset 0 1px 0 rgba(255,255,255,0.2)`,
          fontFamily: 'inherit', letterSpacing: '2px', textTransform: 'uppercase',
          textDecoration: 'none', boxSizing: 'border-box',
        }}
      >
        💳 PAY BY CARD
      </a>

      {/* BUY WITH CRYPTO (NOWPayments) — only the $10 package: NOWPayments has a
          $10 minimum invoice, unusable for Scout/Hunter */}
      {pkg.hasCrypto && (
        <button
          disabled={!!buying}
          onClick={() => onBuy(pkg.id)}
          style={{
            display: 'block', width: '100%', padding: '12px 0', marginTop: 10,
            background: isBuying ? 'rgba(0,100,200,0.3)' : 'transparent',
            color: 'rgba(255,255,255,0.7)',
            border: `1px solid ${pkg.buttonBorder}`,
            borderRadius: 12, fontSize: 12, fontWeight: 800,
            cursor: buying ? 'not-allowed' : 'pointer',
            opacity: buying && !isBuying ? 0.4 : 1,
            transition: 'all 0.2s',
            fontFamily: 'inherit', letterSpacing: '1.5px', textTransform: 'uppercase',
            boxSizing: 'border-box',
          }}
        >
          {isBuying ? '⏳ Redirecting...' : '◇ Pay with Crypto'}
        </button>
      )}
    </div>
  )
}

export default function BalancePage() {
  const [user,   setUser]   = useState(null)
  const [buying, setBuying] = useState(null)
  const [error,  setError]  = useState('')
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const b = D.balance
  useMeta({
    title:       lang === 'ru' ? 'Total Hunter — Пополнение баланса' : 'Total Hunter — Buy Diamonds',
    description: lang === 'ru' ? 'Пополните баланс алмазов для использования бота Total Hunter.' : 'Buy diamonds to use the Total Hunter bot.',
  })

  useEffect(() => { api.me().then(setUser) }, [])

  async function handleBuy(pkg) {
    if (!pkg) return
    setBuying(pkg)
    setError('')
    try {
      const data = await api.paymentCreate(pkg)
      window.location.href = data.redirect_url
    } catch (e) {
      setError(e.message || 'Payment error')
      setBuying(null)
    }
  }

  if (!user) return <div className="page-content text-muted">{D.loading}</div>

  return (
    <div style={{
      minHeight: '100%',
      background: 'linear-gradient(160deg, #000033 0%, #000510 50%, #000020 100%)',
      padding: '32px 20px', maxWidth: 1060, margin: '0 auto',
    }}>
      <style>{`
        @keyframes sparkle {
          from { opacity: 0.3; transform: scale(0.8); }
          to   { opacity: 1.0; transform: scale(1.3); }
        }
      `}</style>

      <h2 style={{
        fontSize: 22, fontWeight: 900, marginBottom: 24,
        background: 'linear-gradient(90deg, #00CFFF, #B060FF)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }}>
        {b.title}
      </h2>

      {/* Balance overview */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 48, flexWrap: 'wrap' }}>
        <BalanceCard title={b.diamonds}   value={user.credits}     color="#00CFFF" />
        <BalanceCard title={b.refBalance} value={user.ref_credits} color="#FFD166" />
      </div>

      {/* Section title */}
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <div style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '4px',
          color: 'rgba(0,191,255,0.8)', textTransform: 'uppercase', marginBottom: 12,
        }}>
          {b.sectionBadge}
        </div>
        <h3 style={{ fontSize: 28, fontWeight: 900, color: '#FFFFFF', marginBottom: 8,
                     letterSpacing: '-0.5px' }}>
          {b.sectionTitle}
        </h3>
        <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)' }}>
          {b.sectionSub}
        </p>
      </div>

      {/* Package cards */}
      <div style={{
        display: 'flex', gap: 16, flexWrap: 'wrap',
        justifyContent: 'center',
        alignItems: 'flex-start', paddingTop: 20, marginBottom: 36,
      }}>
        {PACKAGES.map(pkg => (
          <PackageCard key={pkg.id} pkg={pkg} buying={buying} onBuy={handleBuy} />
        ))}
      </div>

      {error && (
        <div style={{
          color: '#ff6b6b', fontSize: 14, marginBottom: 24,
          padding: '12px 16px', background: 'rgba(122,32,32,0.2)',
          borderRadius: 10, border: '1px solid rgba(255,107,107,0.3)',
        }}>
          {error}
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.5px' }}>
          {b.secureNote}
        </span>
      </div>
    </div>
  )
}
