import { useState } from 'react'
import { normAt } from '../lib/heroQuota.js'
import { computeRow } from '../lib/emcQuota.js'
import { BERSERK_COLUMNS, BERSERK_ROWS } from '../lib/berserkActivity.js'

// Редактор пресетов T5–T9 в «Пульте» (владелец 2026-10-23): очки за сундук (общий пресет сервера + правки клана),
// квоты за 2 недели (очки, эпик-склепы, EMC), загрузка в пульт, справка по замеру активности Берсерков.
// Правки лежат в personal.tier_presets и сохраняются кнопкой «Сохранить настройки» пульта.
// Вид — карточка в стиле пульта: вкладки ступеней, акцентная строка квот, сетка сундуков по группам;
// пояснения свёрнуты (не тултипы: на телефоне нет наведения, а основной текст держим крупным).

const TXT = {
  ru: {
    title: 'Редактор пресета', tier: 'Ступень',
    quotas: 'Квоты за 2 недели', norm: 'Очки', epic: 'Эпик-склепы (минимум)', emc: 'EMC, штук',
    groupCrypts: 'Склепы и цитадели', groupEmc: 'Эпические монстры (EMC)',
    points: 'Очки за сундук',
    load: 'Загрузить в пульт', reset: 'Сбросить к общему', edited: 'изменено',
    loaded: 'Пресет {n} загружен в пульт, изменено типов: {c}. Проверьте значения и нажмите «Сохранить настройки».',
    info: 'Как это работает',
    help: [
      'Очки за сундук и квоты — это ваш вариант пресета ступени. Пустое поле означает значение общего пресета, изменённое выделено рамкой.',
      '«Загрузить в пульт» ставит очки за сундук из пресета для ступеней Героя, отмеченных в пульте выше («Все уровни» — на все): пульт сам подбирает множитель, чтобы при примерном Герое очки равнялись пресетным. Затрагиваются только типы из «Учёта» клана.',
      'Правки в редакторе сохраняются кнопкой «Сохранить настройки» выше.',
    ],
    defNorm: 'Справка: шкала для Героя 413 даёт норму {v} очков.',
    defEmc: 'EMC по умолчанию — для Героя 450 (средний у Берсерков): {v}.',
    statTitle: 'Замер активности клана Берсерки (T9): 2 недели, {n} игроков',
    col: 'Столбец', median: 'Медиана', mean: 'Среднее', max: 'Максимум',
    reach: 'Выполнили минимум эпик-склепов',
    statHint: 'Данные без имён. Минимум берётся из поля выбранной ступени (если пусто — из шкалы).',
  },
  en: {
    title: 'Preset editor', tier: 'Tier',
    quotas: '2-week quotas', norm: 'Points', epic: 'Epic crypts (minimum)', emc: 'EMC, pcs',
    groupCrypts: 'Crypts and citadels', groupEmc: 'Epic monsters (EMC)',
    points: 'Points per chest',
    load: 'Load into mixer', reset: 'Reset to shared', edited: 'edited',
    loaded: "Preset {n} loaded into the mixer, types changed: {c}. Check the values and press 'Save settings'.",
    info: 'How it works',
    help: [
      'Points per chest and the quotas are your version of the tier preset. An empty field means the shared preset value; edited fields have a frame.',
      "'Load into mixer' sets points per chest from the preset for the Hero steps ticked in the mixer above ('All levels' = every step): the mixer picks a multiplier so that at the sample Hero the points equal the preset's. Only types the clan keeps in accounting are affected.",
      "Press 'Save settings' above to keep the editor changes.",
    ],
    defNorm: 'Reference: the scale at Hero 413 gives a norm of {v} points.',
    defEmc: 'Default EMC for Hero 450 (Berserki average): {v}.',
    statTitle: 'Activity sample, clan Berserki (T9): 2 weeks, {n} players',
    col: 'Column', median: 'Median', mean: 'Mean', max: 'Max',
    reach: 'Players at or above the epic crypts minimum',
    statHint: 'No names. The minimum comes from the chosen tier field (scale value if empty).',
  },
}

const TIERS = ['T5', 'T6', 'T7', 'T8', 'T9']
// Квоты по умолчанию (владелец 2026-10-23): Берсерки, T9 — не меньше 300 эпик-склепов 30/35 и 25 000 очков за 2 недели.
// EMC — по таблице монстров для среднего Героя Берсерков 450. Для T5–T8 данных по кланам нет — поля пустые.
const fmt = n => Number(n).toLocaleString('ru-RU')
const num = v => (v === '' || v == null ? null : Math.max(0, Number(String(v).replace(',', '.')) || 0))
const isCrypt = id => /Crypt|Citadel/i.test(id)

function stats(col) {
  const v = BERSERK_ROWS.map(r => r[col]).sort((a, b) => a - b)
  const mid = v.length >> 1
  const median = v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2
  return { median, mean: Math.round(v.reduce((a, b) => a + b, 0) / v.length), max: v[v.length - 1] }
}

export default function TierPresetEditor({ lang = 'ru', clanPresets, personal, onPersonal, onLoad }) {
  const t = TXT[lang] || TXT.ru
  const names = TIERS.filter(n => clanPresets?.[n])
  const [tier, setTier] = useState('')
  const [note, setNote] = useState('')
  if (!names.length) return null
  const cur = names.includes(tier) ? tier : names[names.length - 1]
  const base = clanPresets[cur]
  const own = personal.tier_presets?.[cur] || {}
  const items = base.map(x => ({ ...x, points: own.points?.[x.catalog_id] ?? x.points }))

  const setOwn = patch => {
    onPersonal({ ...personal, tier_presets: { ...(personal.tier_presets || {}), [cur]: { ...own, ...patch } } })
  }
  const setPoints = (id, v) => {
    const points = { ...(own.points || {}) }
    const n = num(v)
    if (n == null || n === base.find(x => x.catalog_id === id)?.points) delete points[id]; else points[id] = n
    setOwn({ points })
  }
  const reset = () => {
    const rest = { ...(personal.tier_presets || {}) }
    delete rest[cur]
    onPersonal({ ...personal, tier_presets: rest })
  }
  const load = () => {
    const changed = onLoad(items)
    setNote(t.loaded.replace('{n}', cur).replace('{c}', changed ?? 0))
  }

  // справка по шкале есть только для T9 (Берсерки, Герой 413/450); для T5–T8 данных нет — поля пустые
  const scaleNorm = cur === 'T9' ? normAt(413) : null
  const defNorm = cur === 'T9' ? 25000 : null
  const defEpic = cur === 'T9' ? 300 : null
  const emcRow = cur === 'T9' ? computeRow(450) : null
  const defEmc = emcRow ? emcRow.emc : null
  const epicWant = own.epic ?? defEpic
  const edited = Object.keys(own.points || {}).length > 0 || own.norm != null || own.epic != null || own.emc != null

  const groups = [
    [t.groupCrypts, base.filter(x => isCrypt(x.catalog_id))],
    [t.groupEmc, base.filter(x => !isCrypt(x.catalog_id))],
  ].filter(([, list]) => list.length)

  return (
    <section className="pult-card">
      <div className="pult-card-head">
        <h3>{t.title}</h3>
        {edited && <span className="pult-badge">{t.edited}</span>}
      </div>

      <div className="chest-tabs chest-tabs--pill" role="tablist" aria-label={t.tier}>
        {names.map(n => (
          <button key={n} type="button" className={`chest-tab chest-tab--pill ${n === cur ? 'chest-tab--active' : ''}`}
            onClick={() => { setTier(n); setNote('') }}>{n}</button>
        ))}
      </div>

      <div className="pult-quotas">
        <div className="pult-quotas-title">{t.quotas}</div>
        <label>{t.norm}
          <input className="input-dark" inputMode="decimal" value={own.norm ?? ''} placeholder={defNorm ?? '—'}
            onChange={e => setOwn({ norm: num(e.target.value) })} />
        </label>
        <label>{t.epic}
          <input className="input-dark" inputMode="decimal" value={own.epic ?? ''} placeholder={defEpic ?? '—'}
            onChange={e => setOwn({ epic: num(e.target.value) })} />
        </label>
        <label>{t.emc}
          <input className="input-dark" inputMode="decimal" value={own.emc ?? ''} placeholder={defEmc ?? '—'}
            onChange={e => setOwn({ emc: num(e.target.value) })} />
        </label>
      </div>

      <div className="pult-actions">
        <button type="button" className="chest-pill-btn" onClick={load}>{t.load}</button>
        <button type="button" className="pult-link-btn" disabled={!edited} onClick={reset}>{t.reset}</button>
      </div>
      {note && <p className="pult-flash">{note}</p>}

      {groups.map(([title, list]) => (
        <div key={title}>
          <h4 className="pult-group">{title}</h4>
          <div className="pult-chests">
            {list.map(x => {
              const changed = own.points?.[x.catalog_id] != null
              return (
                <label key={x.catalog_id} className={`pult-chest ${changed ? 'pult-chest--edited' : ''}`}>
                  <span>{x.catalog_id}</span>
                  <input className="input-dark" inputMode="decimal" aria-label={`${x.catalog_id}: ${t.points}`}
                    value={own.points?.[x.catalog_id] ?? ''} placeholder={x.points}
                    onChange={e => setPoints(x.catalog_id, e.target.value)} />
                </label>
              )
            })}
          </div>
        </div>
      ))}

      <details className="pult-note">
        <summary>{t.info}</summary>
        {t.help.map((line, i) => <p key={i}>{line}</p>)}
        {scaleNorm != null && <p>{t.defNorm.replace('{v}', fmt(scaleNorm))}</p>}
        {emcRow && <p>{t.defEmc.replace('{v}', `Hydra ${emcRow.finalH}, Undead ${emcRow.finalU}, Arachna ${emcRow.finalA}, Shadow City ${emcRow.finalS}`)}</p>}
      </details>

      <details className="pult-note">
        <summary>{t.statTitle.replace('{n}', BERSERK_ROWS.length)}</summary>
        <table className="tier-presets-table">
          <thead><tr><th>{t.col}</th><th>{t.median}</th><th>{t.mean}</th><th>{t.max}</th></tr></thead>
          <tbody>
            {BERSERK_COLUMNS.map((name, i) => {
              const s = stats(i)
              return <tr key={name}><td>{name}</td><td>{fmt(s.median)}</td><td>{fmt(s.mean)}</td><td>{fmt(s.max)}</td></tr>
            })}
          </tbody>
        </table>
        {epicWant > 0 && (
          <p>{t.reach} ({fmt(epicWant)}): {BERSERK_ROWS.filter(r => r[0] >= epicWant).length} / {BERSERK_ROWS.length}</p>
        )}
        <p>{t.statHint}</p>
      </details>
    </section>
  )
}
