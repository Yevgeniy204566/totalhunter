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
  const gradStr = `linear-gradient(135deg, ${pkg.grad[0]}, ${pkg.grad[1]})`

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: '1 1 200px',
        position: 'relative',
        background: hovered || pkg.featured
          ? `linear-gradient(160deg, ${pkg.grad[0]}18 0%, rgba(0,0,5,0.92) 100%)`
          : 'rgba(255,255,255,0.03)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: `1px solid ${hovered || pkg.featured ? pkg.border : 'rgba(255,255,255,0.10)'}`,
        borderRadius: 20,
        padding: pkg.featured ? '40px 22px 26px' : '30px 20px 22px',
        textAlign: 'center',
        transition: 'all 0.28s ease',
        boxShadow: hovered || pkg.featured
          ? `0 0 48px ${pkg.glow}, 0 0 96px ${pkg.glow}55, inset 0 1px 0 ${pkg.border}33`
          : 'none',
        transform: pkg.featured ? 'scale(1.05)' : hovered ? 'scale(1.02)' : 'scale(1)',
        cursor: pkg.soon ? 'default' : 'pointer',
        minWidth: 180,
      }}
    >
      {pkg.soon && <Sparkles color={pkg.grad[1]} />}

      {pkg.featured && (
        <div style={{
          position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)',
          background: gradStr,
          color: '#000', fontSize: 10, fontWeight: 900,
          padding: '5px 18px', borderRadius: 20, letterSpacing: '1px',
          whiteSpace: 'nowrap', textTransform: 'uppercase',
          boxShadow: `0 0 16px ${pkg.glow}`,
        }}>
          ⭐ {pkg.subtitle}
        </div>
      )}

      {/* Name with gradient */}
      <div style={{
        fontSize: 20, fontWeight: 900, letterSpacing: '3px', textTransform: 'uppercase',
        background: gradStr,
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        filter: `drop-shadow(0 0 12px ${pkg.grad[0]}88)`,
        marginBottom: 4,
      }}>
        {pkg.name}
      </div>

      {!pkg.featured && (
        <div style={{ fontSize: 10, color: pkg.grad[1], opacity: 0.7,
                      letterSpacing: '1.5px', marginBottom: 18, textTransform: 'uppercase' }}>
          {pkg.subtitle}
        </div>
      )}
      {pkg.featured && <div style={{ height: 22 }} />}

      {/* Bonus */}
      {pkg.bonus ? (
        <>
          <div style={{
            fontSize: 56, fontWeight: 900, lineHeight: 1,
            background: 'linear-gradient(135deg, #FFD166, #FFAA00)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            filter: 'drop-shadow(0 0 20px rgba(255,209,102,0.8))',
            fontVariantNumeric: 'tabular-nums', marginBottom: 4,
          }}>
            +{pkg.bonus.toLocaleString()}
          </div>
          <div style={{
            fontSize: 10, fontWeight: 900, letterSpacing: '2px',
            color: '#FFD166', textTransform: 'uppercase', marginBottom: 16,
          }}>
            🎁 Bonus Diamonds
          </div>
        </>
      ) : (
        <div style={{ height: 80 }} />
      )}

      {/* Total */}
      <div style={{
        fontSize: 30, fontWeight: 900,
        background: gradStr,
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        fontVariantNumeric: 'tabular-nums', lineHeight: 1, marginBottom: 6,
      }}>
        = {pkg.total.toLocaleString()} ◆
      </div>

      {pkg.bonus ? (
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginBottom: 20 }}>
          <span style={{ textDecoration: 'line-through' }}>{pkg.credits.toLocaleString()}</span> base ◆
        </div>
      ) : (
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginBottom: 20 }}>
          diamonds for hunts
        </div>
      )}

      {/* Button */}
      <button
        disabled={!!buying || pkg.soon}
        onClick={() => !pkg.soon && onBuy(pkg.id)}
        style={{
          width: '100%', padding: '13px 0',
          background: pkg.soon
            ? 'rgba(255,255,255,0.06)'
            : buying === pkg.id ? 'rgba(255,255,255,0.08)' : gradStr,
          color: pkg.soon ? 'rgba(255,255,255,0.4)'
            : buying === pkg.id ? 'rgba(255,255,255,0.5)' : '#000',
          border: `1px solid ${pkg.soon ? 'rgba(255,255,255,0.1)' : pkg.border}`,
          borderRadius: 10, fontSize: 13, fontWeight: 900,
          cursor: pkg.soon || buying ? 'not-allowed' : 'pointer',
          opacity: buying && buying !== pkg.id ? 0.4 : 1,
          transition: 'all 0.2s',
          boxShadow: pkg.soon || buying ? 'none' : `0 0 20px ${pkg.glow}`,
          fontFamily: 'inherit', letterSpacing: '1px', textTransform: 'uppercase',
        }}
      >
        {pkg.soon ? '🔒 Coming Soon'
          : buying === pkg.id ? 'Redirecting...'
          : `Buy — ${pkg.price}`}
      </button>
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
