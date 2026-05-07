import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCounter } from '../hooks/useCounter.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const PACKAGES = [
  {
    id:       'ultra',
    name:     'TOTAL HUNTER',
    subtitle: '5000 Diamonds',
    credits:  5000,
    bonus:    null,
    total:    5000,
    price:    '$10.00',
    grad:     ['#0066CC', '#00CFFF'],
    border:   '#00CFFF',
    glow:     'rgba(0,207,255,0.45)',
    featured: true,
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
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: 280, maxWidth: 320, flexShrink: 0,
        position: 'relative', textAlign: 'center',
        borderRadius: 24,
        background: 'linear-gradient(160deg, #0a0a1a 0%, #0d0f2a 50%, #080818 100%)',
        border: `2px solid ${hovered ? '#00EFFF' : '#0066AA'}`,
        padding: '32px 24px 28px',
        boxShadow: hovered
          ? '0 0 60px rgba(0,180,255,0.5), 0 0 120px rgba(0,100,255,0.25), inset 0 0 40px rgba(0,100,255,0.08)'
          : '0 0 30px rgba(0,100,255,0.2), inset 0 0 20px rgba(0,80,200,0.05)',
        transform: hovered ? 'scale(1.04) translateY(-4px)' : 'scale(1)',
        transition: 'all 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        cursor: 'pointer',
        overflow: 'hidden',
      }}
    >
      {/* Animated corner glow */}
      <div style={{
        position: 'absolute', top: -40, right: -40, width: 120, height: 120,
        background: 'radial-gradient(circle, rgba(0,207,255,0.25) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: -40, left: -40, width: 100, height: 100,
        background: 'radial-gradient(circle, rgba(80,0,255,0.2) 0%, transparent 70%)',
        borderRadius: '50%', pointerEvents: 'none',
      }} />

      {/* TOP BADGE */}
      <div style={{
        position: 'absolute', top: -1, left: '50%', transform: 'translateX(-50%)',
        background: 'linear-gradient(90deg, #0055BB, #00AAFF, #0055BB)',
        borderRadius: '0 0 14px 14px',
        padding: '4px 22px', fontSize: 9, fontWeight: 900,
        color: '#fff', letterSpacing: '2px', textTransform: 'uppercase',
        boxShadow: '0 4px 16px rgba(0,150,255,0.5)',
        whiteSpace: 'nowrap',
      }}>
        ★ BEST VALUE ★
      </div>

      {/* Big Diamond */}
      <div style={{
        fontSize: 52, lineHeight: 1, marginBottom: 4, marginTop: 14,
        filter: 'drop-shadow(0 0 20px rgba(0,207,255,0.9)) drop-shadow(0 0 40px rgba(0,100,255,0.5))',
        animation: 'none',
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
        $10
      </div>
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', letterSpacing: '2px', marginBottom: 16 }}>
        USD · ONE TIME
      </div>

      {/* Divider */}
      <div style={{
        width: '80%', height: 1, margin: '0 auto 16px',
        background: 'linear-gradient(90deg, transparent, #00AAFF66, transparent)',
      }} />

      {/* Diamonds count */}
      <div style={{
        fontSize: 42, fontWeight: 900, lineHeight: 1,
        background: 'linear-gradient(135deg, #00CFFF, #00EFFF)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        filter: 'drop-shadow(0 0 16px rgba(0,207,255,0.8))',
        fontVariantNumeric: 'tabular-nums', marginBottom: 4,
      }}>
        5 000
      </div>
      <div style={{
        fontSize: 11, fontWeight: 700, letterSpacing: '3px',
        color: '#00CFFF', textTransform: 'uppercase', marginBottom: 6,
        opacity: 0.85,
      }}>
        ◆ DIAMONDS
      </div>

      {/* Usage hint */}
      <div style={{
        fontSize: 11, color: 'rgba(255,255,255,0.35)',
        marginBottom: 22, lineHeight: 1.5,
      }}>
        500 Exchange hunts · 5000 Crypt hunts
      </div>

      {/* BUY BUTTON */}
      <button
        disabled={!!buying}
        onClick={() => onBuy(pkg.id)}
        style={{
          width: '100%', padding: '14px 0',
          background: isBuying
            ? 'rgba(0,100,200,0.3)'
            : 'linear-gradient(135deg, #0066FF, #00AAFF, #0066FF)',
          backgroundSize: '200% 100%',
          color: '#fff',
          border: '1px solid rgba(0,200,255,0.4)',
          borderRadius: 12, fontSize: 14, fontWeight: 900,
          cursor: buying ? 'not-allowed' : 'pointer',
          opacity: buying && !isBuying ? 0.4 : 1,
          transition: 'all 0.2s',
          boxShadow: isBuying ? 'none' : '0 0 24px rgba(0,150,255,0.6), inset 0 1px 0 rgba(255,255,255,0.2)',
          fontFamily: 'inherit', letterSpacing: '2px', textTransform: 'uppercase',
        }}
      >
        {isBuying ? '⏳ Redirecting...' : '💎 BUY NOW'}
      </button>

      {/* Crypto note */}
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 12 }}>
        Crypto · Instant · Secure
      </div>
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
          <PackageCard key={pkg.name} pkg={pkg} buying={buying} onBuy={handleBuy} />
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
