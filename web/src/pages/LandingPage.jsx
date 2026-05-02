import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { isLoggedIn } from '../auth.js'
import { LANDING as LANDING_RU } from '../constants.js'
import { LANDING as LANDING_EN } from '../constants.en.js'
import { useLang } from '../lang.js'

function useCounter(target, duration = 1400) {
  const [value, setValue] = useState(0)
  const raf = useRef(null)

  useEffect(() => {
    if (target === null || target === undefined) return
    const start = performance.now()
    function tick(now) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(target * eased))
      if (progress < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])

  return value
}

function StatCard({ icon, label, color, rawValue }) {
  const animated = useCounter(typeof rawValue === 'number' ? rawValue : null)
  const display  = typeof rawValue === 'number' ? animated.toLocaleString() : '—'

  return (
    <div style={{
      background: 'var(--elevated)',
      border: '1px solid var(--outline)',
      borderRadius: 14, padding: '36px 24px',
      textAlign: 'center',
      transition: 'box-shadow 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.boxShadow = `0 0 24px ${color}44`
      e.currentTarget.style.borderColor = `${color}55`
    }}
    onMouseLeave={e => {
      e.currentTarget.style.boxShadow = ''
      e.currentTarget.style.borderColor = 'var(--outline)'
    }}>
      <div style={{ fontSize: 30, marginBottom: 14 }}>{icon}</div>
      <div style={{
        fontSize: 'clamp(40px, 5vw, 58px)', fontWeight: 800,
        color, lineHeight: 1, marginBottom: 10,
        textShadow: `0 0 28px ${color}88`,
        fontVariantNumeric: 'tabular-nums',
      }}>{display}</div>
      <div style={{ fontSize: 14, color: '#FFFFFF', fontWeight: 600 }}>{label}</div>
    </div>
  )
}

const FEATURE_IMAGES = ['/img/exchange.png', '/img/crypt.png', null]

export default function LandingPage() {
  const [stats, setStats] = useState(null)
  const { lang, toggle } = useLang()
  const LANDING = lang === 'en' ? LANDING_EN : LANDING_RU

  useEffect(() => {
    api.globalStats().then(d => setStats(d)).catch(() => {})
  }, [])

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Sticky nav ─────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5, 8, 16, 0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 64,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 700, fontSize: 18 }}>
          <span style={{ color: 'var(--accent)', fontSize: 20 }}>⚔</span>
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: '#FFFFFF' }}>Hunter</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link to="/guide" style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 14,
            color: 'var(--on-surface2)', border: '1px solid var(--outline)', fontWeight: 500,
          }}>
            {lang === 'en' ? 'Guide' : 'Гайд'}
          </Link>
          <button onClick={toggle} style={{
            padding: '8px 12px', borderRadius: 8, fontSize: 13,
            background: 'transparent', color: 'var(--on-surface2)',
            border: '1px solid var(--outline)', cursor: 'pointer',
            fontWeight: 600, fontFamily: 'inherit',
          }}>
            {lang.toUpperCase()}
          </button>
          <Link to={isLoggedIn() ? '/dashboard' : '/login'} className="btn-pulse" style={{
            padding: '9px 22px', borderRadius: 8, fontSize: 14,
            background: 'var(--accent)', color: '#FFFFFF',
            fontWeight: 700, textDecoration: 'none', display: 'inline-block',
          }}>
            {isLoggedIn() ? 'Dashboard →' : (lang === 'en' ? 'Sign In' : 'Войти')}
          </Link>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section style={{
        minHeight: '86vh',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        textAlign: 'center',
        padding: '80px 24px 60px',
        background: `
          radial-gradient(ellipse 80% 60% at 50% 40%, rgba(61,127,255,0.13) 0%, transparent 70%),
          radial-gradient(ellipse 40% 40% at 25% 75%, rgba(176,96,255,0.06) 0%, transparent 60%),
          var(--bg)
        `,
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.03,
          backgroundImage:
            'linear-gradient(var(--outline) 1px, transparent 1px), linear-gradient(90deg, var(--outline) 1px, transparent 1px)',
          backgroundSize: '48px 48px', pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', maxWidth: 800 }}>

          {/* ── Big Logo with glow ── */}
          <div style={{ marginBottom: 40, width: '100%' }}>
            <img
              src="/img/logo.png"
              alt="Total Hunter"
              style={{
                width: '100%',
                maxWidth: 720,
                height: 'auto',
                borderRadius: 32,
                objectFit: 'contain',
                filter: 'drop-shadow(0 0 48px rgba(61,127,255,0.8)) drop-shadow(0 0 96px rgba(61,127,255,0.4))',
                display: 'block',
                margin: '0 auto',
              }}
            />
          </div>

          <div style={{
            display: 'inline-block',
            padding: '5px 16px', borderRadius: 20, marginBottom: 28,
            background: 'rgba(61,127,255,0.12)',
            border: '1px solid rgba(61,127,255,0.35)',
            fontSize: 12, fontWeight: 700, letterSpacing: '1.2px',
            color: 'var(--accent)', textTransform: 'uppercase',
          }}>
            {LANDING.badge}
          </div>

          <h1 style={{
            fontSize: 'clamp(42px, 7.5vw, 80px)',
            fontWeight: 800, color: '#FFFFFF',
            lineHeight: 1.1, marginBottom: 24, letterSpacing: '-1.5px',
          }}>
            {LANDING.heroTitle}<br />
            <span style={{ color: 'var(--accent)', textShadow: '0 0 48px rgba(61,127,255,0.55)' }}>
              {LANDING.heroAccent}
            </span>
          </h1>

          <p style={{
            fontSize: 'clamp(16px, 2.4vw, 20px)',
            color: '#C8D8F0', lineHeight: 1.75,
            maxWidth: 620, margin: '0 auto 48px',
          }}>
            {LANDING.heroSub}
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to={isLoggedIn() ? '/dashboard' : '/login'} className="btn-pulse" style={{
              padding: '17px 40px', borderRadius: 10, fontSize: 17,
              background: 'var(--accent)', color: '#FFFFFF',
              fontWeight: 700, textDecoration: 'none', display: 'inline-block',
            }}>
              {isLoggedIn() ? (lang === 'en' ? 'Go to Dashboard →' : 'Перейти в Dashboard →') : LANDING.ctaPrimary}
            </Link>
            <a href="#features" style={{
              padding: '17px 32px', borderRadius: 10, fontSize: 17,
              background: 'transparent', color: '#FFFFFF',
              fontWeight: 600, textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.18)', display: 'inline-block',
            }}>
              {LANDING.ctaSecondary}
            </a>
          </div>
        </div>
      </section>

      {/* ── Live Stats ─────────────────────────────────────────── */}
      <section style={{
        padding: '72px 24px',
        background: 'linear-gradient(180deg, var(--bg) 0%, var(--card) 100%)',
        borderTop: '1px solid var(--outline)', borderBottom: '1px solid var(--outline)',
      }}>
        <div style={{ maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
          <p style={{
            fontSize: 11, fontWeight: 700, letterSpacing: '2.5px',
            color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 44,
          }}>
            {LANDING.statsLabel}
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
            {LANDING.stats.map(({ key, icon, label, color }) => (
              <StatCard key={key} icon={icon} label={label} color={color} rawValue={stats ? stats[key] : null} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────────── */}
      <section id="features" style={{ padding: '88px 24px', background: 'var(--card)' }}>
        <div style={{ maxWidth: 920, margin: '0 auto' }}>
          <h2 style={{
            textAlign: 'center', fontSize: 'clamp(28px, 4vw, 44px)',
            fontWeight: 800, color: '#FFFFFF', marginBottom: 12,
          }}>
            {LANDING.featuresTitle}
          </h2>
          <p style={{
            textAlign: 'center', color: '#C8D8F0', fontSize: 16,
            maxWidth: 520, margin: '0 auto 60px',
          }}>
            {LANDING.featuresSub}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
            {LANDING.features.map(({ icon, color, title, desc }, i) => (
              <div key={title} className="card" style={{ borderRadius: 14, padding: 28 }}>
                {FEATURE_IMAGES[i] ? (
                  <div style={{
                    width: '100%', height: 220, borderRadius: 12,
                    marginBottom: 22, overflow: 'hidden',
                    border: `1px solid ${color}44`,
                    background: `${color}08`,
                  }}>
                    <img
                      src={FEATURE_IMAGES[i]}
                      alt={title}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>
                ) : (
                  <div style={{
                    width: 52, height: 52, borderRadius: 12,
                    background: `${color}14`, border: `1px solid ${color}44`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 24, marginBottom: 22,
                  }}>
                    {icon}
                  </div>
                )}
                <h3 style={{ fontSize: 18, fontWeight: 700, color: '#FFFFFF', marginBottom: 10 }}>
                  {title}
                </h3>
                <p style={{ fontSize: 14, color: '#C8D8F0', lineHeight: 1.75 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────── */}
      <section style={{
        padding: '88px 24px', textAlign: 'center',
        background: `radial-gradient(ellipse 60% 80% at 50% 50%, rgba(61,127,255,0.10) 0%, transparent 70%), var(--bg)`,
        borderTop: '1px solid var(--outline)',
      }}>
        <div style={{ maxWidth: 560, margin: '0 auto' }}>
          <h2 style={{ fontSize: 'clamp(30px, 4vw, 46px)', fontWeight: 800, color: '#FFFFFF', marginBottom: 16 }}>
            {LANDING.ctaTitle}
          </h2>
          <p style={{ fontSize: 16, color: '#C8D8F0', marginBottom: 44, lineHeight: 1.65 }}>
            {LANDING.ctaSub}
          </p>
          <Link to={isLoggedIn() ? '/dashboard' : '/login'} className="btn-pulse" style={{
            padding: '18px 52px', borderRadius: 12, fontSize: 18,
            background: 'var(--accent)', color: '#FFFFFF',
            fontWeight: 700, textDecoration: 'none', display: 'inline-block',
          }}>
            {isLoggedIn() ? (lang === 'en' ? 'Go to Dashboard →' : 'Перейти в Dashboard →') : LANDING.ctaBtn}
          </Link>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer style={{
        padding: '24px 32px', borderTop: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12,
      }}>
        <span style={{ color: 'var(--on-surface2)', fontSize: 13 }}>© 2026 Total Hunter</span>
        <div style={{ display: 'flex', gap: 20 }}>
          <Link to="/guide" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>
            {lang === 'en' ? 'Guide' : 'Гайд'}
          </Link>
          <Link to="/legal" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>Legal</Link>
        </div>
      </footer>

    </div>
  )
}
