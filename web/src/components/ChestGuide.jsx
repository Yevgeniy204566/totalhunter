import { useLang } from '../lang.js'
import { GUIDE as GUIDE_RU } from '../guide_content.js'
import { GUIDE as GUIDE_EN } from '../guide_content.en.js'

// Свёрнутый гайд по сундукам прямо в кабинете (владелец 2026-09-26) — тот же текст, что в
// /guide#chests, один источник правды: guide_content(.en).js.
const LABEL = { fontSize: 15, fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.5px',
                textTransform: 'uppercase', margin: '20px 0 10px' }

function Steps({ items, bullet }) {
  return items.map((s, i) => (
    <div key={s.title} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
      <div style={{ minWidth: 28, height: 28, borderRadius: '50%', background: 'rgba(56,189,248,0.15)',
                    color: 'var(--accent)', fontWeight: 700, fontSize: 15, display: 'flex',
                    alignItems: 'center', justifyContent: 'center' }}>{bullet ? '•' : i + 1}</div>
      <div>
        <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 3 }}>{s.title}</div>
        <div style={{ fontSize: 16, color: 'var(--on-surface2)', lineHeight: 1.65 }}>{s.desc}</div>
      </div>
    </div>
  ))
}

export default function ChestGuide() {
  const { lang } = useLang()
  const C = (lang === 'en' ? GUIDE_EN : GUIDE_RU).chests
  return (
    <details className="chest-guide" style={{ marginBottom: 24, borderRadius: 12, padding: '14px 18px',
                                             background: 'var(--card)', border: '1px solid var(--outline)' }}>
      <summary style={{ fontSize: 18, fontWeight: 700, cursor: 'pointer', color: 'var(--on-surface)' }}>
        📖 {lang === 'en' ? 'How chest tracking works — guide' : 'Как вести учёт сундуков — гайд'}
      </summary>
      <p style={{ fontSize: 16, color: 'var(--on-surface2)', lineHeight: 1.7, marginTop: 14 }}>{C.intro}</p>
      <div style={LABEL}>{C.botHowLabel}</div>
      <Steps items={C.botHow} />
      <div style={LABEL}>{C.webLabel}</div>
      <Steps items={C.webSteps} />
      <div style={LABEL}>{C.nuancesLabel}</div>
      <Steps items={C.nuances} bullet />
    </details>
  )
}
