import { useState } from 'react'
import { Link } from 'react-router-dom'
import { isLoggedIn } from '../auth.js'
import { useLang } from '../lang.js'
import { GUIDE as GUIDE_RU } from '../guide_content.js'
import { GUIDE as GUIDE_EN } from '../guide_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

function Diamond({ size = 28, style = {} }) {
  return (
    <span style={{
      fontSize: size, lineHeight: 1,
      background: 'linear-gradient(135deg, #B060FF 0%, #3D7FFF 50%, #00CFFF 100%)',
      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
      filter: 'drop-shadow(0 0 8px rgba(61,127,255,0.7))',
      display: 'inline-block', ...style,
    }}>◆</span>
  )
}

function Section({ id, icon, title, children }) {
  return (
    <section id={id} style={{ marginBottom: 64 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(61,127,255,0.1)', border: '1px solid rgba(61,127,255,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0,
        }}>
          {icon}
        </div>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', margin: 0 }}>{title}</h2>
      </div>
      {children}
    </section>
  )
}

function Card({ children, style, glow }) {
  return (
    <div style={{
      background: 'var(--elevated)', border: '1px solid var(--outline)',
      borderRadius: 14, padding: '24px 28px',
      boxShadow: glow ? `0 0 32px ${glow}` : 'none',
      ...style,
    }}>
      {children}
    </div>
  )
}

function NeonCard({ children, color, style }) {
  return (
    <div style={{
      borderRadius: 14, padding: '20px',
      background: `${color}08`,
      border: `1px solid ${color}44`,
      boxShadow: `0 0 18px ${color}18`,
      ...style,
    }}>
      {children}
    </div>
  )
}

function Step({ n, title, desc, note }) {
  return (
    <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
        background: 'rgba(61,127,255,0.15)', border: '1px solid rgba(61,127,255,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 700, color: 'var(--accent)',
      }}>{n}</div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7 }}>{desc}</div>
        {note && (
          <div style={{
            marginTop: 8, padding: '7px 12px', borderRadius: 8, fontSize: 12,
            background: 'rgba(61,127,255,0.07)', border: '1px solid rgba(61,127,255,0.18)',
            color: '#A0B8D8',
          }}>{note}</div>
        )}
      </div>
    </div>
  )
}

function Note({ children }) {
  return (
    <div style={{
      padding: '12px 16px', borderRadius: 10, marginTop: 16,
      background: 'rgba(255,209,102,0.07)', border: '1px solid rgba(255,209,102,0.25)',
      fontSize: 13, color: '#FFD166', lineHeight: 1.6,
    }}>{children}</div>
  )
}

export default function GuidePage() {
  const { lang, toggle } = useLang()
  const G = lang === 'en' ? GUIDE_EN : GUIDE_RU
  const isEn = lang === 'en'
  const [tocOpen, setTocOpen] = useState(false)

  useMeta(isEn
    ? { title: 'Total Hunter Guide — How to Set Up and Use the Bot',
        description: 'Step-by-step guide to installing, calibrating and using Total Hunter bot for Total Battle. Exchange search and crypt farming explained.' }
    : { title: 'Гайд Total Hunter — установка, калибровка и запуск программы',
        description: 'Пошаговое руководство по установке, калибровке и использованию Total Hunter. Поиск бирж и фарм склепов в Total Battle.' }
  )

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5,8,16,0.92)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 64,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', fontWeight: 700, fontSize: 18 }}>
          <Diamond size={22} />
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: '#FFFFFF' }}>Hunter</span>
        </Link>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={toggle} style={{
            background: 'rgba(61,127,255,0.08)', border: '1px solid rgba(61,127,255,0.25)',
            borderRadius: 8, padding: '6px 14px', color: 'var(--accent)',
            fontSize: 13, fontWeight: 700, cursor: 'pointer',
          }}>
            {isEn ? 'RU' : 'EN'}
          </button>
          <Link to={isLoggedIn() ? '/dashboard' : '/login'} style={{
            padding: '9px 22px', borderRadius: 8, fontSize: 14,
            background: 'var(--accent)', color: '#FFFFFF', fontWeight: 700, textDecoration: 'none',
            boxShadow: '0 0 14px var(--accent-glow)',
          }}>
            {isLoggedIn() ? 'Dashboard →' : (isEn ? 'Login' : 'Войти')}
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div style={{
        padding: '64px 24px 48px',
        background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(61,127,255,0.1) 0%, transparent 60%)',
        borderBottom: '1px solid var(--outline)', textAlign: 'center',
      }}>
        <div style={{
          display: 'inline-block', padding: '5px 16px', borderRadius: 20,
          background: 'rgba(61,127,255,0.1)', border: '1px solid rgba(61,127,255,0.3)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1.5px', color: 'var(--accent)',
          textTransform: 'uppercase', marginBottom: 20,
        }}>{G.docsBadge}</div>
        <h1 style={{ fontSize: 'clamp(32px,5vw,54px)', fontWeight: 800, color: '#FFFFFF', marginBottom: 16, letterSpacing: '-1px' }}>
          {G.heroTitle}
        </h1>
        <p style={{ fontSize: 17, color: '#C8D8F0', maxWidth: 560, margin: '0 auto', lineHeight: 1.7 }}>
          {G.heroSub}
        </p>
      </div>

      {/* Layout: TOC + Content */}
      <div className="guide-layout" style={{
        maxWidth: 1060, margin: '0 auto', padding: '48px 24px',
        display: 'grid', gridTemplateColumns: '220px 1fr', gap: 48, alignItems: 'start',
      }}>

        {/* Sidebar TOC — desktop only */}
        <div className="guide-toc-sidebar" style={{ position: 'sticky', top: 80 }}>
          <div style={{ background: 'var(--elevated)', border: '1px solid var(--outline)', borderRadius: 14, padding: '20px' }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '1.5px', color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 16 }}>
              {isEn ? 'Contents' : 'Содержание'}
            </div>
            {G.toc.map(({ id, label }) => (
              <a key={id} href={`#${id}`} style={{
                display: 'block', padding: '7px 10px', borderRadius: 8,
                fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none', fontWeight: 500,
              }}
              onMouseEnter={e => { e.currentTarget.style.color='#FFFFFF'; e.currentTarget.style.background='rgba(61,127,255,0.08)' }}
              onMouseLeave={e => { e.currentTarget.style.color='var(--on-surface2)'; e.currentTarget.style.background='transparent' }}
              >{label}</a>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div>

          {/* ── Windows-only banner ── */}
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: 14,
            background: 'rgba(255,100,30,0.1)',
            border: '1px solid rgba(255,120,40,0.45)',
            borderLeft: '4px solid #FF6420',
            borderRadius: 12, padding: '16px 20px', marginBottom: 32,
          }}>
            <span style={{ fontSize: 30, flexShrink: 0 }}>🪟</span>
            <div>
              <div style={{ fontSize: 15, fontWeight: 900, color: '#FF8C50', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>
                {isEn ? 'WINDOWS ONLY — 10 / 11 (64-bit)' : 'ТОЛЬКО WINDOWS — 10 / 11 (64-bit)'}
              </div>
              <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
                {isEn
                  ? 'Total Hunter is a desktop program for Windows PC. It does not run on mobile devices, Mac or Linux.'
                  : 'Total Hunter — десктопная программа для Windows. Не работает на телефоне, Mac и Linux.'}
              </div>
            </div>
          </div>

          {/* ── Mobile TOC dropdown — hidden on desktop ── */}
          <div className="guide-toc-mobile" style={{ position: 'relative', marginBottom: 28 }}>
            <button
              onClick={() => setTocOpen(o => !o)}
              style={{
                width: '100%', padding: '11px 16px', borderRadius: 10,
                background: 'var(--elevated)', border: '1px solid rgba(61,127,255,0.35)',
                color: 'var(--on-surface)', fontSize: 14, fontWeight: 600,
                fontFamily: 'inherit', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}
            >
              <span>📋 {isEn ? 'Contents' : 'Оглавление'}</span>
              <span style={{ fontSize: 11, transition: 'transform 0.2s', transform: tocOpen ? 'rotate(180deg)' : 'none', color: 'var(--accent)' }}>▼</span>
            </button>
            {tocOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 200,
                background: 'var(--elevated)', border: '1px solid rgba(61,127,255,0.25)',
                borderRadius: 10, overflow: 'hidden',
                boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
              }}>
                {G.toc.map(({ id, label }, i) => (
                  <button
                    key={id}
                    onClick={() => {
                      const el = document.getElementById(id)
                      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                      setTocOpen(false)
                    }}
                    style={{
                      display: 'block', width: '100%', padding: '12px 16px', textAlign: 'left',
                      background: 'transparent', border: 'none',
                      borderBottom: i < G.toc.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                      color: 'var(--on-surface2)', fontSize: 14, fontWeight: 500,
                      fontFamily: 'inherit', cursor: 'pointer',
                    }}
                    onTouchStart={e => e.currentTarget.style.background = 'rgba(61,127,255,0.1)'}
                    onTouchEnd={e => e.currentTarget.style.background = 'transparent'}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 1. What is Total Hunter */}
          <Section id="what-is" icon={<Diamond size={18}/>} title={G.whatIs.title}>
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.85, marginBottom: 20 }}>
                <strong style={{ color: '#FFFFFF' }}>Total Hunter</strong> — {G.whatIs.intro}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <NeonCard color="#00CFFF">
                  <div style={{ fontSize: 22, marginBottom: 8 }}>🔍</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 6 }}>{G.whatIs.exchange.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{G.whatIs.exchange.desc}</div>
                </NeonCard>
                <NeonCard color="#B060FF">
                  <div style={{ fontSize: 22, marginBottom: 8 }}>🏆</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 6 }}>{G.whatIs.crypt.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{G.whatIs.crypt.desc}</div>
                </NeonCard>
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginTop: 20, marginBottom: 0 }}>
                {G.whatIs.outro}
              </p>
            </Card>
          </Section>

          {/* 2. Algorithm */}
          <Section id="algorithm" icon="🧠" title={G.algorithm.title}>
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                {G.algorithm.coastLabel}
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 16 }}>
                {G.algorithm.coastIntro}
              </p>
              {G.algorithm.coastSteps.map((s, i) => (
                <Step key={i} n={String(i + 1)} title={s.title} desc={s.desc} />
              ))}
              <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7, marginBottom: 0 }}>
                {G.algorithm.coastOutro}
              </p>
            </Card>

            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                {G.algorithm.yoloLabel}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <NeonCard color="#00CFFF">
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{G.algorithm.exchangeModel.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{G.algorithm.exchangeModel.desc}</div>
                </NeonCard>
                <NeonCard color="#B060FF">
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{G.algorithm.cryptModel.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{G.algorithm.cryptModel.desc}</div>
                </NeonCard>
              </div>
              <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7, marginBottom: 0 }}>
                {G.algorithm.yoloOutro}
              </p>
            </Card>

            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                {G.algorithm.cryptLabel}
              </div>
              {G.algorithm.cryptSteps.map((s, i) => (
                <Step key={i} n={String(i + 1)} title={s.title} desc={s.desc} />
              ))}
              <Note>{G.algorithm.cryptNote}</Note>
            </Card>
          </Section>

          {/* 3. Requirements */}
          <Section id="requirements" icon="💻" title={G.requirements.title}>
            <Card>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {G.requirements.rows.map(({ param, value }) => (
                  <div key={param} style={{
                    display: 'flex', gap: 16, padding: '10px 14px', borderRadius: 8,
                    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', minWidth: 100, flexShrink: 0 }}>{param}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{value}</div>
                  </div>
                ))}
              </div>
            </Card>
          </Section>

          {/* 4. Install */}
          <Section id="install" icon="⬇" title={G.install.title}>
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 24 }}>
                {G.install.intro}
              </p>
              {G.install.steps.map((s, i) => (
                <Step key={i} n={String(i + 1)} title={s.title} desc={s.desc} note={s.note} />
              ))}
            </Card>
          </Section>

          {/* 5. Calibration */}
          <Section id="calibration" icon="🎯" title={G.calibration.title}>
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                {G.calibration.intro}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
                {G.calibration.points.map(({ label, sublabel, color, desc }, i) => (
                  <NeonCard key={label} color={color}>
                    <div style={{ fontSize: 15, fontWeight: 700, color, marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--on-surface2)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>{sublabel}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.65, marginBottom: 10 }}>{desc}</div>
                    <img
                      src={i === 0 ? '/img/calib_point_a.png' : '/img/calib_point_b.png'}
                      alt={label}
                      style={{ width: '100%', borderRadius: 8, border: `1px solid ${color}33`, display: 'block' }}
                    />
                  </NeonCard>
                ))}
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                {G.calibration.stepsLabel}
              </div>
              {G.calibration.steps.map((s, i) => (
                <Step key={i} n={String(i + 1)} title={s.title} desc={s.desc} />
              ))}
              <div style={{
                padding: '12px 16px', borderRadius: 10, marginTop: 8,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.7,
              }}>
                {G.calibration.slotsNote}
              </div>
            </Card>
          </Section>

          {/* 6. Modes */}
          <Section id="modes" icon="⚡" title={G.modes.title}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <NeonCard color="#00CFFF">
                <div style={{ fontSize: 24, marginBottom: 10 }}>🔍</div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{G.modes.exchange.title}</div>
                <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, marginBottom: 14, background: 'rgba(0,207,255,0.15)', border: '1px solid rgba(0,207,255,0.3)', fontSize: 12, color: '#00CFFF', fontWeight: 600 }}>
                  {G.modes.exchange.cost}
                </div>
                {G.modes.exchange.rows.map(({ l, t }) => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#00CFFF' }}>{l}: </span>
                    <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{t}</span>
                  </div>
                ))}
              </NeonCard>
              <NeonCard color="#B060FF">
                <div style={{ fontSize: 24, marginBottom: 10 }}>🏆</div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{G.modes.crypt.title}</div>
                <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, marginBottom: 14, background: 'rgba(176,96,255,0.15)', border: '1px solid rgba(176,96,255,0.3)', fontSize: 12, color: '#B060FF', fontWeight: 600 }}>
                  {G.modes.crypt.cost}
                </div>
                {G.modes.crypt.rows.map(({ l, t }) => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#B060FF' }}>{l}: </span>
                    <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{t}</span>
                  </div>
                ))}
              </NeonCard>
            </div>
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7, margin: 0 }}>
                <strong style={{ color: '#FFFFFF' }}>{isEn ? 'Emergency Stop:' : 'Экстренная остановка:'}</strong>{' '}
                <kbd style={{ padding: '2px 8px', borderRadius: 5, background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', fontSize: 13, fontWeight: 700 }}>ESC</kbd>
                {' '}{G.modes.stopNote.replace(/^[^:：]+[:：]\s*/, '').replace(/ESC\s*[—–-]\s*/, '')}
              </p>
            </Card>
          </Section>

          {/* 7. Settings */}
          <Section id="settings" icon="⚙️" title={G.settings.title}>
            {[
              { label: G.settings.exchangeLabel, note: G.settings.exchangeNote, items: G.settings.exchange, color: '#00CFFF' },
              { label: G.settings.cryptLabel,    note: G.settings.cryptNote,    items: G.settings.crypt,    color: '#B060FF' },
            ].map(({ label, note, items, color }) => (
              <Card key={label} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color, marginBottom: note ? 10 : 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                  {label}
                </div>
                {note && (
                  <div style={{
                    fontSize: 12, color: 'var(--on-surface2)', lineHeight: 1.6,
                    background: `rgba(${color === '#00CFFF' ? '0,207,255' : '176,96,255'},0.06)`,
                    border: `1px solid rgba(${color === '#00CFFF' ? '0,207,255' : '176,96,255'},0.2)`,
                    borderRadius: 8, padding: '8px 12px', marginBottom: 14,
                  }}>
                    {note}
                  </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {items.map(({ name, range, optimal, desc }) => (
                    <div key={name} style={{
                      display: 'grid', gridTemplateColumns: '180px 90px 90px 1fr',
                      gap: 12, padding: '10px 14px', borderRadius: 8,
                      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                      alignItems: 'start',
                    }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#FFFFFF' }}>{name}</div>
                      <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                        <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', color: color, marginBottom: 2, letterSpacing: '0.5px' }}>{G.settings.rangeLabel}</div>
                        {range}
                      </div>
                      <div style={{ fontSize: 12, color }}>
                        <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', color: color, marginBottom: 2, letterSpacing: '0.5px' }}>{G.settings.optimalLabel}</div>
                        {optimal}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{desc}</div>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </Section>

          {/* 8. Credits */}
          <Section id="credits" icon={<Diamond size={18}/>} title={G.credits.title}>
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 0 }}>
                {G.credits.intro}
              </p>
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 16 }}>
              {G.packages.map(({ name, price, diamonds, bonus, color, popular }) => (
                <div key={name} style={{
                  position: 'relative', borderRadius: 16, padding: '28px 20px', textAlign: 'center',
                  background: popular
                    ? 'linear-gradient(160deg, rgba(0,207,255,0.08) 0%, rgba(61,127,255,0.12) 50%, rgba(176,96,255,0.08) 100%)'
                    : 'var(--elevated)',
                  border: `1px solid ${color}55`,
                  boxShadow: popular ? `0 0 40px ${color}30, 0 0 80px ${color}10` : `0 0 12px ${color}10`,
                }}>
                  {popular && (
                    <div style={{
                      position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)',
                      padding: '4px 16px', borderRadius: 20,
                      background: 'linear-gradient(90deg, #B060FF, #3D7FFF, #00CFFF)',
                      color: '#FFF', fontSize: 10, fontWeight: 800, whiteSpace: 'nowrap', letterSpacing: '1px',
                    }}>{G.credits.popularLabel}</div>
                  )}
                  <div style={{ fontSize: 32, fontWeight: 900, color, marginBottom: 2,
                    textShadow: popular ? `0 0 20px ${color}` : 'none' }}>{price}</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 8 }}>{name}</div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 4 }}>
                    <Diamond size={popular ? 22 : 18} />
                    <span style={{ fontSize: popular ? 28 : 22, fontWeight: 900, color,
                      textShadow: popular ? `0 0 16px ${color}` : 'none' }}>{diamonds}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: bonus ? 12 : 0 }}>
                    {isEn ? 'diamonds' : 'алмазов'}
                  </div>
                  {bonus && (
                    <div style={{
                      display: 'inline-block', padding: '4px 12px', borderRadius: 20,
                      background: `linear-gradient(90deg, ${color}22, ${color}44)`,
                      border: `1px solid ${color}55`, fontSize: 12, color, fontWeight: 800,
                    }}>{bonus}</div>
                  )}
                </div>
              ))}
            </div>

            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                {G.credits.spendLabel}
              </div>
              <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', marginBottom: 20 }}>
                {G.credits.spendRows.map(({ label, cost, color }) => (
                  <div key={label}>
                    <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color }}>{cost}</div>
                  </div>
                ))}
              </div>
              <Note>{G.credits.trialNote}</Note>
            </Card>
          </Section>

          {/* 8. Referrals */}
          <Section id="referrals" icon="◈" title={G.referrals.title}>
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 28 }}>
                {G.referrals.intro}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 24 }}>
                {G.referrals.levels.map(({ level, pct, desc, color }) => (
                  <div key={level} style={{
                    textAlign: 'center', padding: '24px 12px', borderRadius: 14,
                    background: `${color}0A`, border: `1px solid ${color}44`,
                    boxShadow: `0 0 20px ${color}14`,
                  }}>
                    <div style={{ fontSize: 13, color, fontWeight: 800, letterSpacing: '2px', textTransform: 'uppercase', marginBottom: 10 }}>{level}</div>
                    <div style={{ fontSize: 44, fontWeight: 900, color, lineHeight: 1, marginBottom: 10,
                      textShadow: `0 0 20px ${color}` }}>{pct}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{desc}</div>
                  </div>
                ))}
              </div>
              <div style={{
                padding: '14px 16px', borderRadius: 10,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.6,
              }}>
                {G.referrals.note}
              </div>
            </Card>
          </Section>

          {/* 9. Security */}
          <Section id="security" icon="🛡" title={G.security.title}>
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                {G.security.intro}
              </p>
              {G.security.rows.map(({ icon, title, desc }) => (
                <div key={title} style={{
                  display: 'flex', gap: 14, marginBottom: 14, padding: '14px',
                  borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                }}>
                  <div style={{ fontSize: 20, flexShrink: 0 }}>{icon}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{title}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.65 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </Card>
          </Section>

          {/* 10. FAQ */}
          <Section id="faq" icon="❓" title={G.faq.title}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {G.faq.rows.map(({ q, a }) => (
                <Card key={q}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 8 }}>{q}</div>
                  <div style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.75 }}>{a}</div>
                </Card>
              ))}
            </div>
          </Section>

          {/* CTA */}
          <div style={{
            textAlign: 'center', padding: '48px 32px',
            background: 'linear-gradient(160deg, rgba(0,207,255,0.06) 0%, rgba(61,127,255,0.08) 50%, rgba(176,96,255,0.06) 100%)',
            border: '1px solid rgba(61,127,255,0.25)', borderRadius: 20,
            boxShadow: '0 0 60px rgba(61,127,255,0.08)',
          }}>
            <Diamond size={48} style={{ marginBottom: 16 }} />
            <div style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', marginBottom: 12 }}>
              {G.cta.title}
            </div>
            <p style={{ fontSize: 14, color: 'var(--on-surface2)', marginBottom: 28, lineHeight: 1.7 }}>
              {G.cta.sub}
            </p>
            <Link to={isLoggedIn() ? '/dashboard' : '/login'} style={{
              display: 'inline-block', padding: '14px 40px', borderRadius: 10,
              background: 'linear-gradient(90deg, #3D7FFF, #00CFFF)',
              color: '#FFFFFF', fontSize: 16, fontWeight: 700, textDecoration: 'none',
              boxShadow: '0 0 30px rgba(0,207,255,0.35)',
            }}>
              {isLoggedIn() ? G.cta.btnDashboard : G.cta.btnStart}
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
