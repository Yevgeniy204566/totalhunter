import { useMemo } from 'react'
import { computeTable, heroRangeLabel, clampMultiplier } from '../lib/emcQuota.js'
import { downloadQuotaCsv } from '../lib/downloadCsv.js'

// Публичная таблица квоты EMC — только чтение: клан видит, сколько сундуков каких монстров
// ждут от игрока с его уровнем Героя, и может предложить правки лидеру. Показываем уже
// применённые лидером множители: страница считает по тем же рычагам, что и полосы прогресса.
const TXT = {
  ru: {
    title: 'Квота Epic Monster Chests (EMC)',
    intro: 'Сколько сундуков каждого монстра ждут от игрока за сезон (2 недели) в зависимости от уровня его Героя. Значения — штук на игрока. Если Герой в таблице игроков не указан, цель считается по Герою 400.',
    levers: 'Применённые множители',
    none: 'без поправок',
    global: 'общий',
    hero: 'Герой',
    download: '⬇ Скачать таблицу (CSV)',
    feedback: 'Нашли неточность? Напишите лидеру клана — он поправит значения.',
  },
  en: {
    title: 'Epic Monster Chests (EMC) quota',
    intro: 'How many chests of each monster are expected from a player over the season (2 weeks) by Hero level. Values are chests per player. If a player has no Hero level set, the target uses Hero 400.',
    levers: 'Applied multipliers',
    none: 'no adjustments',
    global: 'global',
    hero: 'Hero',
    download: '⬇ Download table (CSV)',
    feedback: 'Found a mistake? Tell your clan leader — they can adjust the values.',
  },
}
const MONSTER_LABEL = { hydra: 'Hydra', undead: 'Undead', arachna: 'Arachna', shadow: 'Shadow City' }

function leverSummary(model, t) {
  const parts = []
  const g = clampMultiplier(model.global)
  if (g !== 1) parts.push(`${t.global} ×${g}`)
  for (const [key, label] of Object.entries(MONSTER_LABEL)) {
    const k = clampMultiplier(model.monsters?.[key])
    if (k !== 1) parts.push(`${label} ×${k}`)
  }
  for (const r of model.ranges || []) {
    const k = clampMultiplier(r.k)
    if (k !== 1) parts.push(`${t.hero} ${r.from}–${r.to} ×${k}`)
  }
  return parts.length ? parts.join(', ') : t.none
}

export default function EmcQuotaPublic({ model, lang = 'ru' }) {
  const t = TXT[lang] || TXT.en
  const table = useMemo(() => computeTable(model), [model])
  return (
    <div className="emc-public">
      <h3 className="emc-title">{t.title}</h3>
      <p className="emc-text">{t.intro}</p>
      <p className="emc-text"><small>{t.levers}: {leverSummary(model, t)}</small></p>
      <div className="emc-toolbar">
        <button type="button" className="chest-pill-btn chest-pill-btn--sm"
          onClick={() => downloadQuotaCsv(table, lang)}>{t.download}</button>
      </div>
      <div className="emc-table-wrap emc-table-wrap--public">
        <table className="chest-table emc-table emc-table--public">
          <thead>
            <tr>
              <th>{t.hero}</th>
              <th>Hydra</th><th>Undead</th><th>Arachna</th><th>Shadow City</th>
              <th className="emc-emc-col">EMC</th>
            </tr>
          </thead>
          <tbody>
            {table.map(r => (
              <tr key={r.hero}>
                <td><b>{heroRangeLabel(r.hero)}</b></td>
                <td>{r.finalH}</td><td>{r.finalU}</td><td>{r.finalA}</td><td>{r.finalS}</td>
                <td className="emc-emc-col"><b>{r.emc}</b></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="emc-text"><small>{t.feedback}</small></p>
    </div>
  )
}
