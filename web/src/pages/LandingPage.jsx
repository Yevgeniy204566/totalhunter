import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function LandingPage() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.globalStats().catch(() => null).then(d => d && setStats(d))
  }, [])

  const exchanges = stats?.exchanges_today ?? '—'
  const crypts    = stats?.crypts_today    ?? '—'
  const hunters   = stats?.active_hunters  ?? '—'

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Nav bar ────────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5, 8, 16, 0.90)',
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
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/guide" style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 14,
            color: 'var(--on-surface2)', border: '1px solid var(--outline)',
            fontWeight: 500,
          }}>
            Гайд
          </Link>
          <Link to="/login" style={{
            padding: '8px 20px', borderRadius: 8, fontSize: 14,
            background: 'var(--accent)', color: '#FFFFFF',
            fontWeight: 600, boxShadow: '0 0 16px var(--accent-glow)',
          }}>
            Войти
          </Link>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section style={{
        minHeight: '88vh',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        textAlign: 'center',
        padding: '80px 24px 60px',
        background: `
          radial-gradient(ellipse 80% 60% at 50% 40%, rgba(61,127,255,0.12) 0%, transparent 70%),
          radial-gradient(ellipse 40% 40% at 30% 70%, rgba(61,127,255,0.06) 0%, transparent 60%),
          var(--bg)
        `,
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Subtle grid overlay */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.03,
          backgroundImage: 'linear-gradient(var(--outline) 1px, transparent 1px), linear-gradient(90deg, var(--outline) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', maxWidth: 780 }}>
          <div style={{
            display: 'inline-block',
            padding: '5px 14px', borderRadius: 20, marginBottom: 28,
            background: 'rgba(61,127,255,0.12)',
            border: '1px solid rgba(61,127,255,0.35)',
            fontSize: 13, fontWeight: 600, letterSpacing: '0.8px',
            color: 'var(--accent)',
            textTransform: 'uppercase',
          }}>
            Total Battle · Автоматизация
          </div>

          <h1 style={{
            fontSize: 'clamp(40px, 7vw, 76px)',
            fontWeight: 800,
            color: '#FFFFFF',
            lineHeight: 1.1,
            marginBottom: 24,
            letterSpacing: '-1px',
          }}>
            Total Hunter —<br />
            <span style={{
              color: 'var(--accent)',
              textShadow: '0 0 40px rgba(61,127,255,0.5)',
            }}>
              Эволюция охоты
            </span>
          </h1>

          <p style={{
            fontSize: 'clamp(16px, 2.5vw, 20px)',
            color: '#C8D8F0',
            lineHeight: 1.7,
            maxWidth: 600, margin: '0 auto 44px',
          }}>
            Автоматический фарм ресурсов на карте: биржи, склепы, маршруты —
            бот работает, пока ты отдыхаешь.
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/login" style={{
              padding: '16px 36px', borderRadius: 10, fontSize: 17,
              background: 'var(--accent)', color: '#FFFFFF',
              fontWeight: 700, textDecoration: 'none',
              boxShadow: '0 0 32px rgba(61,127,255,0.45)',
              transition: 'box-shadow 0.2s, transform 0.15s',
              display: 'inline-block',
            }}>
              Начать охоту ⚔
            </Link>
            <a href="#features" style={{
              padding: '16px 32px', borderRadius: 10, fontSize: 17,
              background: 'transparent', color: '#FFFFFF',
              fontWeight: 600, textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.2)',
              display: 'inline-block',
            }}>
              Как это работает
            </a>
          </div>
        </div>
      </section>

      {/* ── Live Stats ─────────────────────────────────────────── */}
      <section style={{
        padding: '64px 24px',
        background: 'linear-gradient(180deg, var(--bg) 0%, var(--card) 100%)',
        borderTop: '1px solid var(--outline)',
        borderBottom: '1px solid var(--outline)',
      }}>
        <div style={{ maxWidth: 860, margin: '0 auto', textAlign: 'center' }}>
          <p style={{
            fontSize: 12, fontWeight: 600, letterSpacing: '2px',
            color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 40,
          }}>
            ⬡ Live — данные обновляются в реальном времени
          </p>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 20,
          }}>
            {[
              { icon: '⚔', label: 'Бирж сегодня',   value: exchanges, color: 'var(--accent)' },
              { icon: '💀', label: 'Склепов сегодня', value: crypts,    color: '#B060FF' },
              { icon: '◈', label: 'Охотников онлайн', value: hunters,   color: 'var(--credits-gold)' },
            ].map(({ icon, label, value, color }) => (
              <div key={label} style={{
                background: 'var(--elevated)',
                border: '1px solid var(--outline)',
                borderRadius: 12, padding: '32px 24px',
              }}>
                <div style={{ fontSize: 28, marginBottom: 12 }}>{icon}</div>
                <div style={{
                  fontSize: 'clamp(36px, 5vw, 52px)', fontWeight: 800,
                  color, lineHeight: 1, marginBottom: 8,
                  textShadow: `0 0 24px ${color}55`,
                }}>
                  {value}
                </div>
                <div style={{ fontSize: 14, color: '#C8D8F0', fontWeight: 500 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────────── */}
      <section id="features" style={{ padding: '80px 24px', background: 'var(--card)' }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <h2 style={{
            textAlign: 'center', fontSize: 'clamp(28px, 4vw, 42px)',
            fontWeight: 800, color: '#FFFFFF', marginBottom: 12,
          }}>
            Что умеет бот
          </h2>
          <p style={{
            textAlign: 'center', color: '#C8D8F0', fontSize: 16,
            maxWidth: 500, margin: '0 auto 56px',
          }}>
            Полная автоматизация двух ключевых механик Total Battle
          </p>

          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 20,
          }}>
            {[
              {
                icon: '⚔', color: 'var(--accent)',
                title: 'Биржи ресурсов',
                desc: 'Бот сканирует карту по спирали, находит и атакует биржи. Умная CoastalSnake-навигация огибает берега.',
              },
              {
                icon: '💀', color: '#B060FF',
                title: 'Слепые склепы',
                desc: 'Детерминированный маршрут в склепы Даркнета без OCR. Рассчитывает время марша по формуле и возвращается точно в срок.',
              },
              {
                icon: '◈', color: 'var(--credits-gold)',
                title: 'Облачный кабинет',
                desc: 'Статистика охот, реферальная система, пополнение кредитов — всё доступно с любого устройства.',
              },
            ].map(({ icon, color, title, desc }) => (
              <div key={title} className="card" style={{ borderRadius: 12 }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 10,
                  background: `${color}18`,
                  border: `1px solid ${color}44`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 22, marginBottom: 20,
                }}>
                  {icon}
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: '#FFFFFF', marginBottom: 10 }}>
                  {title}
                </h3>
                <p style={{ fontSize: 14, color: '#C8D8F0', lineHeight: 1.7 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────── */}
      <section style={{
        padding: '80px 24px',
        textAlign: 'center',
        background: `
          radial-gradient(ellipse 60% 80% at 50% 50%, rgba(61,127,255,0.1) 0%, transparent 70%),
          var(--bg)
        `,
        borderTop: '1px solid var(--outline)',
      }}>
        <div style={{ maxWidth: 560, margin: '0 auto' }}>
          <h2 style={{
            fontSize: 'clamp(28px, 4vw, 44px)',
            fontWeight: 800, color: '#FFFFFF', marginBottom: 16,
          }}>
            Готов к охоте?
          </h2>
          <p style={{ fontSize: 16, color: '#C8D8F0', marginBottom: 40, lineHeight: 1.6 }}>
            100 кредитов бесплатно при первом подключении устройства.
            Никакой кредитной карты.
          </p>
          <Link to="/login" style={{
            padding: '18px 48px', borderRadius: 12, fontSize: 18,
            background: 'var(--accent)', color: '#FFFFFF',
            fontWeight: 700, textDecoration: 'none',
            boxShadow: '0 0 40px rgba(61,127,255,0.5)',
            display: 'inline-block',
          }}>
            Попробовать бесплатно
          </Link>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer style={{
        padding: '24px 32px',
        borderTop: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12,
      }}>
        <span style={{ color: 'var(--on-surface2)', fontSize: 13 }}>
          © 2026 Total Hunter
        </span>
        <div style={{ display: 'flex', gap: 20 }}>
          <Link to="/guide" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>Гайд</Link>
          <Link to="/legal" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>Legal</Link>
        </div>
      </footer>

    </div>
  )
}
