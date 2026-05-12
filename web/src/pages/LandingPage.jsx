import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { isLoggedIn } from '../auth.js'
import { LANDING as LANDING_RU } from '../constants.js'
import { LANDING as LANDING_EN } from '../constants.en.js'
import { useLang } from '../lang.js'
import AdSlot from '../components/AdSlot.jsx'
import { useMeta, useFaqSchema } from '../hooks/useMeta.js'

const FAQ_ITEMS_RU = [
  { q: 'Что такое Total Hunter?',
    a: 'Total Hunter — десктопный бот для автоматизации Total Battle. Автоматически ищет биржи наёмников и собирает склепы, имитируя действия реального игрока.' },
  { q: 'Сколько стоит Total Hunter?',
    a: 'Первые 100 алмазов бесплатно при регистрации — без кредитной карты. Алмазы списываются только за успешные действия: −10 за найденную биржу, −1 за собранный склеп.' },
  { q: 'Работает ли бот с браузером и клиентом Total Battle?',
    a: 'Да. Total Hunter поддерживает браузерную версию (Chrome, Firefox) и официальный клиент Total Battle. Настройки сохраняются в профилях.' },
  { q: 'Могут ли меня забанить за использование бота?',
    a: 'Бот полностью имитирует действия человека: случайные паузы 0.4–0.9 сек, случайное отклонение кликов ±5–8 пикселей. Риск минимален.' },
  { q: 'Нужен ли боту мой игровой пароль?',
    a: 'Нет. Бот работает поверх уже запущенной игры через скриншоты экрана. Ваши учётные данные нам не нужны.' },
  { q: 'На каких системах работает Total Hunter?',
    a: 'Windows 10 и Windows 11 (64-bit). Установщик включает все необходимые компоненты (VC++ Runtime).' },
]

const FAQ_ITEMS_EN = [
  { q: 'What is Total Hunter?',
    a: 'Total Hunter is a desktop bot for Total Battle automation. It automatically searches for mercenary exchanges and collects crypts, imitating real player actions.' },
  { q: 'How much does Total Hunter cost?',
    a: 'First 100 diamonds are free upon registration — no credit card required. Diamonds are charged only for successful actions: −10 per exchange found, −1 per crypt collected.' },
  { q: 'Does it work with both browser and client versions of Total Battle?',
    a: 'Yes. Total Hunter supports both browser (Chrome, Firefox) and the official Total Battle client. Settings are saved in profiles.' },
  { q: 'Can I get banned for using the bot?',
    a: 'The bot fully imitates human actions: random pauses 0.4–0.9s, random click offsets ±5–8 pixels. Risk is minimal.' },
  { q: 'Does the bot need my game password?',
    a: 'No. The bot works on top of an already running game via screen screenshots. Your credentials are never required.' },
  { q: 'What systems does Total Hunter support?',
    a: 'Windows 10 and Windows 11 (64-bit). The installer includes all required components (VC++ Runtime).' },
]

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

function Screenshot3D({ src, alt, rotY, rotX, glowColor, extraStyle = {} }) {
  const [hov, setHov] = useState(false)
  return (
    <img
      src={src} alt={alt}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: 'clamp(140px, 26vw, 295px)',
        height: 'auto',
        borderRadius: 14,
        border: `1px solid ${glowColor}55`,
        boxShadow: hov
          ? `0 0 70px ${glowColor}80, 0 0 130px ${glowColor}38, 0 28px 70px rgba(0,0,0,0.55)`
          : `0 0 44px ${glowColor}55, 0 0 90px ${glowColor}26, 0 20px 55px rgba(0,0,0,0.5)`,
        transform: hov
          ? `perspective(900px) rotateY(${rotY * 0.22}deg) rotateX(${rotX * 0.22}deg) scale(1.07)`
          : `perspective(900px) rotateY(${rotY}deg) rotateX(${rotX}deg) scale(1)`,
        transition: 'transform 0.45s cubic-bezier(0.23,1,0.32,1), box-shadow 0.45s ease',
        cursor: 'pointer',
        display: 'block',
        position: 'relative',
        ...extraStyle,
        zIndex: hov ? 10 : (extraStyle.zIndex || 1),
      }}
    />
  )
}

function StatCard({ label, color, rawValue }) {
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

const RELEASE_URL = 'https://github.com/Yevgeniy204566/totalhunter/releases/latest/download/TotalHunter.zip'

const FEATURE_IMAGES = ['/img/exchange.png', '/img/crypt.png', null]

export default function LandingPage() {
  const [stats, setStats] = useState(null)
  const { lang, toggle } = useLang()
  const LANDING = lang === 'en' ? LANDING_EN : LANDING_RU

  useMeta(lang === 'en'
    ? { title: 'Total Hunter — Bot for Total Battle | Exchange & Crypt Automation',
        description: 'Automatic search for mercenary exchanges and crypt collection in Total Battle. Neural network + player imitation. 100 free diamonds on registration.' }
    : { title: 'Total Hunter — автоматизация Total Battle | Биржи и склепы',
        description: 'Автоматический поиск бирж наёмников и сбор склепов в Total Battle. Нейросеть + имитация игрока. 100 алмазов бесплатно при регистрации.' }
  )
  useFaqSchema(lang === 'en' ? FAQ_ITEMS_EN : FAQ_ITEMS_RU)

  useEffect(() => {
    api.globalStats().then(d => setStats(d)).catch(() => {})
  }, [])

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Sticky nav ─────────────────────────────────────────── */}
      <nav className="landing-nav">
        <div className="landing-nav-logo">
          <span style={{ color: 'var(--accent)', fontSize: 20 }}>⚔</span>
          <span className="landing-nav-logo-text" style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span className="landing-nav-logo-text" style={{ color: '#FFFFFF' }}>Hunter</span>
        </div>
        <div className="landing-nav-actions">
          <Link to="/guide" className="landing-nav-guide landing-nav-btn">
            {lang === 'en' ? 'Guide' : 'Гайд'}
          </Link>
          <Link to="/download" className="landing-nav-btn landing-nav-btn--accent landing-nav-download">
            <span className="landing-nav-dl-text">{lang === 'en' ? '⬇ Download' : '⬇ Скачать'}</span>
            <span className="landing-nav-dl-icon">⬇</span>
          </Link>
          <button onClick={toggle} className="landing-nav-btn landing-nav-btn--lang">
            {lang.toUpperCase()}
          </button>
          <Link to={isLoggedIn() ? '/dashboard' : '/login'} className="btn-pulse landing-nav-btn landing-nav-btn--cta">
            <span className="landing-nav-cta-text">{isLoggedIn() ? 'Dashboard →' : (lang === 'en' ? 'Sign In' : 'Войти')}</span>
            <span className="landing-nav-cta-icon">→</span>
          </Link>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="landing-hero" style={{
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
                maxWidth: 920,
                height: 'auto',
                borderRadius: 32,
                objectFit: 'contain',
                filter: 'drop-shadow(0 0 64px rgba(61,127,255,0.9)) drop-shadow(0 0 120px rgba(61,127,255,0.5))',
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

          <div className="landing-cta-row" style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap', alignItems: 'center' }}>
            {/* ── BIG GREEN DOWNLOAD ── */}
            <a href={RELEASE_URL} style={{
              padding: '20px 52px', borderRadius: 12, fontSize: 20,
              background: 'linear-gradient(135deg, #00C853, #00FF88)',
              color: '#000',
              fontWeight: 900, textDecoration: 'none', display: 'inline-flex',
              alignItems: 'center', gap: 12,
              boxShadow: '0 0 32px rgba(0,255,136,0.55), 0 0 64px rgba(0,255,136,0.28), 0 6px 24px rgba(0,0,0,0.4)',
              border: '1px solid rgba(0,255,136,0.6)',
              letterSpacing: '0.3px',
              animation: 'glow-pulse 2.4s ease-in-out infinite',
            }}>
              <span style={{ fontSize: 24 }}>⬇</span>
              {lang === 'en' ? 'Download Free' : 'Скачать бесплатно'}
            </a>
            <Link to={isLoggedIn() ? '/dashboard' : '/login'} style={{
              padding: '20px 36px', borderRadius: 12, fontSize: 17,
              background: 'transparent', color: '#FFFFFF',
              fontWeight: 600, textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.2)', display: 'inline-block',
            }}>
              {isLoggedIn() ? (lang === 'en' ? 'Dashboard →' : 'Dashboard →') : (lang === 'en' ? 'Sign In →' : 'Войти →')}
            </Link>
          </div>
          <p style={{ marginTop: 14, fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
            Windows 10/11 · 64-bit · {lang === 'en' ? 'Installer · VC++ included' : 'Установщик · VC++ встроен'}
          </p>
        </div>
      </section>

      {/* ── Screenshots 3D ─────────────────────────────────────── */}
      <section style={{
        padding: '64px 24px 56px',
        background: 'var(--bg)',
        overflow: 'hidden',
      }}>
        <div style={{ maxWidth: 960, margin: '0 auto', textAlign: 'center' }}>
          <p style={{
            fontSize: 11, fontWeight: 700, letterSpacing: '2.5px',
            color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 14,
          }}>
            {lang === 'en' ? 'Program Interface' : 'Интерфейс программы'}
          </p>
          <h2 style={{
            fontSize: 'clamp(24px, 3.5vw, 38px)',
            fontWeight: 800, color: '#FFFFFF', marginBottom: 52,
          }}>
            {lang === 'en' ? 'Exchanges & Crypts — in one window' : 'Биржи и Склепы — в одном окне'}
          </h2>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Screenshot3D
              src="/img/lending-exchange.png"
              alt={lang === 'en' ? 'Exchange hunter UI' : 'Интерфейс поиска бирж'}
              rotY={-17} rotX={5}
              glowColor="#00CFFF"
              extraStyle={{ marginRight: '-52px', zIndex: 2 }}
            />
            <Screenshot3D
              src="/img/lending-crypts.png"
              alt={lang === 'en' ? 'Crypt hunter UI' : 'Интерфейс поиска склепов'}
              rotY={-13} rotX={4}
              glowColor="#00FF88"
              extraStyle={{ zIndex: 1 }}
            />
          </div>
        </div>
      </section>

      {/* ── Download CTA under screenshots ─────────────────────── */}
      <div style={{ textAlign: 'center', paddingBottom: 64, background: 'var(--bg)' }}>
        <a href={RELEASE_URL} style={{
          padding: '18px 56px', borderRadius: 12, fontSize: 19,
          background: 'linear-gradient(135deg, #00C853, #00FF88)',
          color: '#000',
          fontWeight: 900, textDecoration: 'none', display: 'inline-flex',
          alignItems: 'center', gap: 12,
          boxShadow: '0 0 28px rgba(0,255,136,0.5), 0 0 56px rgba(0,255,136,0.22), 0 6px 20px rgba(0,0,0,0.4)',
          border: '1px solid rgba(0,255,136,0.5)',
        }}>
          <span style={{ fontSize: 22 }}>⬇</span>
          {lang === 'en' ? 'Download TotalHunter (.zip)' : 'Скачать TotalHunter (.zip)'}
        </a>
        <p style={{ marginTop: 10, fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
          v1.2.2 · Windows 10/11 · 64-bit
        </p>
      </div>

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
          <div className="landing-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
            {LANDING.stats.map(({ key, label, color }) => (
              <StatCard key={key} label={label} color={color} rawValue={stats ? stats[key] : null} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Ad Banner — between Live Stats and Features ────────── */}
      <div style={{
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        padding: '28px 16px',
        background: 'var(--card)',
      }}>
        <AdSlot size="leaderboard" />
      </div>

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
                    width: '100%', height: 280, borderRadius: 12,
                    marginBottom: 22, overflow: 'hidden',
                    border: `1px solid ${color}44`,
                    background: `${color}08`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <img
                      src={FEATURE_IMAGES[i]}
                      alt={title}
                      style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 8 }}
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

      {/* ── Pricing ────────────────────────────────────────────── */}
      <section id="pricing" style={{ padding: '88px 24px', background: 'var(--bg)', borderTop: '1px solid var(--outline)' }}>
        <div style={{ maxWidth: 920, margin: '0 auto' }}>
          <h2 style={{ textAlign: 'center', fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800, color: '#FFFFFF', marginBottom: 12 }}>
            {lang === 'en' ? 'Simple Pricing' : 'Простые цены'}
          </h2>
          <p style={{ textAlign: 'center', color: '#C8D8F0', fontSize: 16, maxWidth: 520, margin: '0 auto 16px' }}>
            {lang === 'en'
              ? 'Buy diamonds — the internal currency of Total Hunter. Charged only for successful bot actions.'
              : 'Покупайте алмазы — внутреннюю валюту Total Hunter. Списание только за успешные действия бота.'}
          </p>
          <p style={{ textAlign: 'center', color: 'var(--on-surface2)', fontSize: 13, marginBottom: 56 }}>
            {lang === 'en'
              ? '−10 ◆ per Exchange found · −1 ◆ per Crypt gathered · 0 ◆ if nothing found'
              : '−10 ◆ за биржу · −1 ◆ за склеп · 0 ◆ если ничего не найдено'}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20, maxWidth: 400, margin: '0 auto' }}>
            {[
              { name: 'TOTAL HUNTER', price: '$10', diamonds: '5,000', bonus: null, color: '#00CFFF', popular: true },
            ].map(pkg => (
              <div key={pkg.name} style={{
                background: pkg.popular ? 'rgba(0,207,255,0.06)' : 'var(--card)',
                border: `1px solid ${pkg.popular ? 'rgba(0,207,255,0.4)' : 'var(--outline)'}`,
                borderRadius: 18, padding: '36px 28px', textAlign: 'center',
                position: 'relative',
                boxShadow: pkg.popular ? '0 0 40px rgba(0,207,255,0.12)' : 'none',
              }}>
                {pkg.popular && (
                  <div style={{
                    position: 'absolute', top: -13, left: '50%', transform: 'translateX(-50%)',
                    background: 'var(--accent)', color: '#fff', borderRadius: 20,
                    padding: '3px 18px', fontSize: 11, fontWeight: 800, letterSpacing: '1px', textTransform: 'uppercase',
                  }}>
                    {lang === 'en' ? 'POPULAR' : 'ПОПУЛЯРНО'}
                  </div>
                )}
                <div style={{ fontSize: 17, fontWeight: 700, color: pkg.color, marginBottom: 20 }}>{pkg.name}</div>
                <div style={{ fontSize: 'clamp(44px, 6vw, 58px)', fontWeight: 800, color: '#fff', lineHeight: 1, marginBottom: 6 }}>
                  {pkg.price}
                </div>
                <div style={{ fontSize: 14, color: 'var(--on-surface2)', marginBottom: 24 }}>USD</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 28 }}>
                  <span style={{ fontSize: 22, fontWeight: 800, color: pkg.color }}>◆ {pkg.diamonds}</span>
                  {pkg.bonus && (
                    <span style={{ background: `${pkg.color}22`, color: pkg.color, borderRadius: 8, padding: '2px 10px', fontSize: 12, fontWeight: 700 }}>
                      {pkg.bonus}
                    </span>
                  )}
                </div>
                <Link to={isLoggedIn() ? '/dashboard/balance' : '/login'} style={{
                  display: 'block', padding: '13px 0', borderRadius: 10,
                  background: pkg.popular ? 'var(--accent)' : 'transparent',
                  border: `1px solid ${pkg.popular ? 'var(--accent)' : pkg.color + '66'}`,
                  color: pkg.popular ? '#fff' : pkg.color,
                  fontWeight: 700, fontSize: 15, textDecoration: 'none',
                }}>
                  {lang === 'en' ? 'Get Diamonds' : 'Купить'}
                </Link>
              </div>
            ))}
          </div>

          <p style={{ textAlign: 'center', color: 'var(--on-surface2)', fontSize: 13, marginTop: 32 }}>
            🔒 {lang === 'en'
              ? 'Payments via NOWPayments (crypto). Diamonds credited instantly. No subscription, no expiry.'
              : 'Оплата через NOWPayments (крипта). Алмазы зачисляются мгновенно. Без подписки, без срока действия.'}
          </p>
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
          <Link to="/download" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>
            {lang === 'en' ? 'Download' : 'Скачать'}
          </Link>
          <Link to="/guide" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>
            {lang === 'en' ? 'Guide' : 'Гайд'}
          </Link>
          <Link to="/contacts" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>
            {lang === 'en' ? 'Contacts' : 'Контакты'}
          </Link>
          <Link to="/legal" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>Legal</Link>
        </div>
      </footer>

    </div>
  )
}
