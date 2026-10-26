import { useMemo, useState } from 'react'
import { HERO_LEVELS, DEFAULT_HERO, weightTable, weightAt, normAt, cryptsNormAt, epicRefAt, scoreOf } from '../lib/heroQuota.js'

// Публичные нормы «Общего учёта» по уровню Героя — только чтение: игрок находит свой уровень,
// видит вес каждого типа сундука и сравнивает свой результат с личной нормой. Считаем по тем же
// рычагам клана, что и столбец «Общий учёт» в таблице игроков.
const TXT = {
  ru: {
    title: 'Нормы по уровню Героя',
    intro: 'Чем ниже уровень Героя, тем меньше очков нужно набрать, но каждый сундук даёт больше очков. Чем выше уровень, тем норма больше, а сундук весит меньше.',
    find: 'Ваш уровень Героя',
    player: 'или выберите игрока',
    none: '— не выбран —',
    norm: 'Норма за сезон (14 дней), очков',
    epicRef: 'Ориентир по эпик-склепам, шт.',
    cryptsPart: 'из них Crypts',
    yours: 'Ваш результат',
    type: 'Тип сундука',
    weight: 'Очков за сундук',
    zero: '0 — не считается',
    tableTitle: 'Таблица по уровням',
    hero: 'Герой',
    normShort: 'Норма',
    noteFact: 'Значения построены по данным реальных замеров в королевстве и интерполированы между ними на уровни Героя 100–600. Ориентировочный учёт ведётся за 2 недели (14 дней).',
    noteCalc: 'Нормы для самых слабых и самых сильных Героев — предварительный расчёт по тем же замерам, а не требование клана. Лидер клана может поправить значения.',
    fallback: 'Тип не входит в шкалу — считается по очкам клана:',
    feedback: 'Нашли неточность? Напишите лидеру клана — он поправит значения.',
  },
  en: {
    title: 'Hero level norms',
    intro: 'The lower the Hero level, the fewer points are needed, but each chest gives more. The higher the level, the bigger the norm and the less each chest is worth.',
    find: 'Your Hero level',
    player: 'or pick a player',
    none: '— none —',
    norm: 'Season norm (14 days), points',
    epicRef: 'Epic crypts guideline, pcs',
    cryptsPart: 'of which Crypts',
    yours: 'Your result',
    type: 'Chest type',
    weight: 'Points per chest',
    zero: '0 — not counted',
    tableTitle: 'Table by level',
    hero: 'Hero',
    normShort: 'Norm',
    noteFact: 'The values are built from real measurements in the kingdom and interpolated between them to Hero levels 100–600. The estimated accounting covers 2 weeks (14 days).',
    noteCalc: 'Norms for the weakest and strongest Heroes are a preliminary estimate from the same measurements, not a clan requirement. The clan leader can adjust the values.',
    fallback: 'Type is outside the scale — counted by clan points:',
    feedback: 'Found a mistake? Tell your clan leader — they can adjust the values.',
  },
}

// Колонки общей таблицы — основные типы; полный список весов виден в блоке «Ваш уровень».
const TABLE_TYPES = ['Epic Crypt 35', 'Epic Crypt 30', 'Epic Crypt 25', 'Epic Crypt 20', 'Rare Crypt 30', 'Rare Crypt 25', 'Common Crypt 25', 'Citadel 30', 'Citadel 25']

export default function HeroPointsPublic({ model = {}, emcModel, players = [], meta = null, lang = 'ru' }) {
  const t = TXT[lang] || TXT.en
  const [heroInput, setHeroInput] = useState('')
  const [playerName, setPlayerName] = useState('')
  const player = players.find(p => p.name === playerName)
  const hero = player?.hero_level || Number(heroInput) || null
  const level = hero || DEFAULT_HERO
  const rows = useMemo(() => weightTable(level, model), [level, model])
  const mine = player ? scoreOf(player.counts, meta, player.hero_level, model) : null
  const norm = normAt(level, model)
  const cryptsNorm = cryptsNormAt(level, emcModel, model)
  const table = useMemo(() => HERO_LEVELS.map(h => ({
    hero: h, norm: normAt(h, model), w: TABLE_TYPES.map(id => weightAt(id, h, model)),
  })), [model])

  return (
    <div className="emc-public">
      <h3 className="emc-title">{t.title}</h3>
      <p className="emc-text">{t.intro}</p>

      <div className="emc-toolbar">
        <label>{t.find}{' '}
          <input className="input-dark emc-level-input" type="number" min={1} max={999} value={heroInput}
            onChange={e => { setHeroInput(e.target.value.replace(/\D/g, '').slice(0, 3)); setPlayerName('') }} />
        </label>
        {players.length > 0 && (
          <label>{t.player}{' '}
            <select className="input-dark" value={playerName}
              onChange={e => { setPlayerName(e.target.value); setHeroInput('') }}>
              <option value="">{t.none}</option>
              {[...players].sort((a, b) => a.name.localeCompare(b.name)).map(p => (
                <option key={p.name} value={p.name}>{p.name}{p.hero_level ? ` (${p.hero_level})` : ''}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      <p className="emc-text">
        {t.hero} <b>{level}</b>{hero ? '' : ' *'} · {t.norm}: <b>{norm.toLocaleString('ru-RU')}</b> ({t.cryptsPart}: <b>{cryptsNorm.toLocaleString('ru-RU')}</b>) · {t.epicRef}: <b>{epicRefAt(level)}</b>
        {mine && <> · {t.yours}: <b>{mine.score.toLocaleString('ru-RU')}</b> ({norm ? Math.round(mine.score / norm * 100) : 0}%)</>}
      </p>
      {mine?.fallback.length > 0 && (
        <p className="emc-text"><small>{t.fallback} {mine.fallback.join(', ')}</small></p>
      )}

      <div className="emc-table-wrap emc-table-wrap--public">
        <table className="chest-table emc-table emc-table--public" style={{ minWidth: 0 }}>
          <thead><tr><th>{t.type}</th><th>{t.weight}</th></tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.points > 0 ? <b>{r.points}</b> : t.zero}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="emc-title" style={{ marginTop: 22 }}>{t.tableTitle}</h3>
      <div className="emc-table-wrap emc-table-wrap--public">
        <table className="chest-table emc-table emc-table--public">
          <thead>
            <tr>
              <th>{t.hero}</th><th className="emc-emc-col">{t.normShort}</th>
              {TABLE_TYPES.map(id => <th key={id}>{id}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.map(r => (
              <tr key={r.hero}>
                <td><b>{r.hero}</b></td>
                <td className="emc-emc-col"><b>{r.norm.toLocaleString('ru-RU')}</b></td>
                {r.w.map((v, i) => <td key={TABLE_TYPES[i]}>{v}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="emc-text"><small>{t.noteFact}</small></p>
      <p className="emc-text"><small>{t.noteCalc}</small></p>
      <p className="emc-text"><small>{t.feedback}</small></p>
    </div>
  )
}
