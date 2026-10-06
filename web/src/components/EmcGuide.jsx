import { EMC_GUIDE } from '../emc_guide_content.js'

// Подробное описание квоты EMC: разделы сворачиваются, чтобы страница не превращалась в простыню.
export default function EmcGuide({ lang }) {
  const g = EMC_GUIDE[lang === 'ru' ? 'ru' : 'en']
  return (
    <section className="emc-guide">
      <h3 className="emc-guide-title">{g.title}</h3>
      <p className="emc-text">{g.intro}</p>
      {g.sections.map(sec => (
        <details key={sec.title} className="emc-guide-item">
          <summary>{sec.title}</summary>
          {sec.paragraphs.map(p => <p key={p} className="emc-text">{p}</p>)}
          {sec.cases && (
            <ul className="emc-guide-cases">
              {sec.cases.map(c => (
                <li key={c.name}><b>{c.name}.</b> {c.text}</li>
              ))}
            </ul>
          )}
        </details>
      ))}
    </section>
  )
}
