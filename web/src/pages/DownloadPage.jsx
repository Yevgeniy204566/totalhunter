import { Link } from 'react-router-dom'
import { useLang } from '../lang.js'
import { DOWNLOAD as DL_RU } from '../constants.js'
import { DOWNLOAD as DL_EN } from '../constants.en.js'
import { useMeta } from '../hooks/useMeta.js'

const RELEASE_URL =
  'https://github.com/Yevgeniy204566/totalhunter/releases/latest/download/TotalHunter_Setup.exe'

export default function DownloadPage() {
  const { lang, toggle } = useLang()
  const T = lang === 'en' ? DL_EN : DL_RU

  useMeta(lang === 'en'
    ? { title: 'Download Total Hunter — Free Bot for Total Battle (Windows)',
        description: 'Download Total Hunter installer for Windows 10/11. Free setup, 100 free diamonds included. Exchange and crypt automation for Total Battle.' }
    : { title: 'Скачать Total Hunter — бесплатный бот для Total Battle (Windows)',
        description: 'Скачай установщик Total Hunter для Windows 10/11. Бесплатная установка, 100 алмазов в подарок. Автоматизация бирж и склепов в Total Battle.' }
  )

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5,8,16,0.92)', backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 64,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>
        <Link to="/" style={{
          display: 'flex', alignItems: 'center', gap: 10,
          fontWeight: 700, fontSize: 18, textDecoration: 'none',
        }}>
          <span style={{ color: 'var(--accent)', fontSize: 20 }}>⚔</span>
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: '#FFFFFF' }}>Hunter</span>
        </Link>
        <button onClick={toggle} style={{
          padding: '8px 12px', borderRadius: 8, fontSize: 13,
          background: 'transparent', color: 'var(--on-surface2)',
          border: '1px solid var(--outline)', cursor: 'pointer',
          fontWeight: 600, fontFamily: 'inherit',
        }}>
          {lang.toUpperCase()}
        </button>
      </nav>

      {/* Hero */}
      <section style={{
        padding: '80px 24px 60px', textAlign: 'center',
        background: `
          radial-gradient(ellipse 70% 60% at 50% 30%, rgba(61,127,255,0.13) 0%, transparent 70%),
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

        <div style={{ position: 'relative', maxWidth: 680, margin: '0 auto' }}>
          <div style={{
            display: 'inline-block', padding: '5px 16px', borderRadius: 20, marginBottom: 24,
            background: 'rgba(61,127,255,0.12)', border: '1px solid rgba(61,127,255,0.35)',
            fontSize: 12, fontWeight: 700, letterSpacing: '1.2px',
            color: 'var(--accent)', textTransform: 'uppercase',
          }}>
            {T.badge}
          </div>

          <h1 style={{
            fontSize: 'clamp(36px, 6vw, 64px)', fontWeight: 800,
            color: '#FFFFFF', lineHeight: 1.1, marginBottom: 20, letterSpacing: '-1px',
          }}>
            {T.title}
          </h1>

          <p style={{
            fontSize: 'clamp(15px, 2.2vw, 18px)', color: '#C8D8F0',
            lineHeight: 1.7, maxWidth: 500, margin: '0 auto 48px',
          }}>
            {T.subtitle}
          </p>

          {/* Download button */}
          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a
              href={RELEASE_URL}
              className="btn-pulse"
              style={{
                padding: '18px 44px', borderRadius: 12, fontSize: 18,
                background: 'var(--accent)', color: '#FFFFFF',
                fontWeight: 700, textDecoration: 'none', display: 'inline-flex',
                alignItems: 'center', gap: 10,
              }}
            >
              <span style={{ fontSize: 22 }}>⬇</span>
              {T.btnDownload}
            </a>
            <Link to="/guide" style={{
              padding: '18px 32px', borderRadius: 12, fontSize: 17,
              background: 'transparent', color: '#FFFFFF',
              fontWeight: 600, textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.18)', display: 'inline-flex',
              alignItems: 'center',
            }}>
              {T.btnGuide}
            </Link>
          </div>
        </div>
      </section>

      {/* System Requirements + Steps */}
      <section style={{ padding: '72px 24px', background: 'var(--card)', borderTop: '1px solid var(--outline)' }}>
        <div style={{
          maxWidth: 860, margin: '0 auto',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 32,
        }}>

          {/* Sys req */}
          <div style={{
            background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 16, padding: 32,
          }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#FFFFFF', marginBottom: 24 }}>
              {T.sysTitle}
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {T.sysItems.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{
                    width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                    background: 'rgba(61,127,255,0.10)', border: '1px solid rgba(61,127,255,0.25)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
                  }}>
                    {item.icon}
                  </div>
                  <span style={{ fontSize: 15, color: '#C8D8F0', fontWeight: 500 }}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Steps */}
          <div style={{
            background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 16, padding: 32,
          }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#FFFFFF', marginBottom: 24 }}>
              {T.stepsTitle}
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {T.steps.map((step) => (
                <div key={step.n} style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                    background: 'var(--accent)', color: '#FFFFFF',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, fontWeight: 800,
                  }}>
                    {step.n}
                  </div>
                  <p style={{ fontSize: 14, color: '#C8D8F0', lineHeight: 1.65, margin: '4px 0 0' }}>
                    {step.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Free note */}
      <section style={{
        padding: '60px 24px', textAlign: 'center',
        background: `radial-gradient(ellipse 50% 70% at 50% 50%, rgba(61,127,255,0.09) 0%, transparent 70%), var(--bg)`,
        borderTop: '1px solid var(--outline)',
      }}>
        <div style={{
          maxWidth: 520, margin: '0 auto',
          background: 'rgba(61,127,255,0.08)', border: '1px solid rgba(61,127,255,0.25)',
          borderRadius: 16, padding: '32px 36px',
        }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>💎</div>
          <h3 style={{ fontSize: 20, fontWeight: 700, color: '#FFFFFF', marginBottom: 10 }}>
            {T.noteTitle}
          </h3>
          <p style={{ fontSize: 15, color: '#C8D8F0', lineHeight: 1.65 }}>
            {T.noteText}
          </p>
          <Link to="/login" className="btn-pulse" style={{
            display: 'inline-block', marginTop: 24,
            padding: '14px 36px', borderRadius: 10, fontSize: 16,
            background: 'var(--accent)', color: '#FFFFFF',
            fontWeight: 700, textDecoration: 'none',
          }}>
            {lang === 'en' ? 'Create Account →' : 'Создать аккаунт →'}
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        padding: '24px 32px', borderTop: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12,
      }}>
        <span style={{ color: 'var(--on-surface2)', fontSize: 13 }}>© 2026 Total Hunter</span>
        <Link to="/" style={{ color: 'var(--on-surface2)', fontSize: 13 }}>
          {T.backHome}
        </Link>
      </footer>
    </div>
  )
}
