import { useState } from 'react'
import { normAt } from '../lib/heroQuota.js'
import { BERSERK_COLUMNS, BERSERK_ROWS } from '../lib/berserkActivity.js'

// Редактор пресетов T5–T9 в «Пульте» (владелец 2026-10-23): очки за сундук (общий пресет сервера + правки клана),
// норма очков за 2 недели и ожидаемое число эпик-склепов; загрузка в пульт; справка по замеру активности Берсерков.
// Правки лежат в personal.tier_presets и сохраняются кнопкой «Сохранить настройки» пульта.

const TXT = {
  ru: {
    title: 'Редактор пресетов T5–T9',
    hint: 'Правьте очки за сундук и квоты за 2 недели: очки, эпик-склепы, EMC. Пустое поле = значение общего пресета. После правок нажмите «Сохранить настройки» выше.',
    tier: 'Пресет', chest: 'Сундук', points: 'Очки', norm: 'Норма очков за 2 недели', epic: 'Эпик-склепов (минимум)', emc: 'EMC, штук',
    reset: 'Сбросить пресет к общему', load: 'Загрузить в пульт',
    loaded: 'Пресет {n} загружен в пульт. Проверьте значения и нажмите «Сохранить настройки».',
    defNorm: 'Справка: шкала для Героя 413 — норма {v} очков.', edited: 'изменено',
    statTitle: 'Замер активности клана Берсерки (T9), 2 недели, {n} игроков',
    col: 'Столбец', median: 'Медиана', mean: 'Среднее', max: 'Максимум', reach: 'Выполнили минимум эпик-склепов',
    statHint: 'Данные без имён. Минимум берётся из поля выбранного пресета (если пусто — из шкалы).',
  },
  en: {
    title: 'T5–T9 preset editor',
    hint: "Edit points per chest and the 2-week quotas: points, epic crypts, EMC. Empty = shared preset value. Press 'Save settings' above afterwards.",
    tier: 'Preset', chest: 'Chest', points: 'Points', norm: '2-week points norm', epic: 'Epic crypts (minimum)', emc: 'EMC, pcs',
    reset: 'Reset preset to shared', load: 'Load into mixer',
    loaded: "Preset {n} loaded into the mixer. Check the values and press 'Save settings'.",
    defNorm: 'Reference: the scale at Hero 413 gives a norm of {v} points.', edited: 'edited',
    statTitle: 'Activity sample, clan Berserki (T9), 2 weeks, {n} players',
    col: 'Column', median: 'Median', mean: 'Mean', max: 'Max', reach: 'Players at or above the epic crypts minimum',
    statHint: 'No names. The minimum comes from the chosen preset field (scale value if empty).',
  },
}

const TIERS = ['T5', 'T6', 'T7', 'T8', 'T9']
// Квоты по умолчанию (владелец 2026-10-23): Берсерки, T9 — не меньше 300 эпик-склепов 30/35 и 25 000 очков за 2 недели.
// Для T5–T8 и EMC данных нет — поля пустые.
const fmt = n => Number(n).toLocaleString('ru-RU')
const num = v => (v === '' || v == null ? null : Math.max(0, Number(String(v).replace(',', '.')) || 0))

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
  const load = () => { onLoad(cur, items); setNote(t.loaded.replace('{n}', cur)) }

  // справка по шкале есть только для T9 (Берсерки, Герой 413); для T5–T8 данных нет — поля пустые
  const scaleNorm = cur === 'T9' ? normAt(413) : null
  const defNorm = cur === 'T9' ? 25000 : null
  const defEpic = cur === 'T9' ? 300 : null
  const epicWant = own.epic ?? defEpic
  const edited = Object.keys(own.points || {}).length > 0 || own.norm != null || own.epic != null || own.emc != null

  return (
    <div className="tier-presets">
      <h3>{t.title}</h3>
      <p className="emc-text"><small>{t.hint}</small></p>
      <div className="mixer-presets">
        <b>{t.tier}</b>
        <select className="input-dark" value={cur} onChange={e => { setTier(e.target.value); setNote('') }}>
          {names.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        {edited && <b className="mixer-dirty">{t.edited}</b>}
        <button type="button" className="chest-pill-btn chest-pill-btn--sm chest-pill-btn--green" onClick={load}>{t.load}</button>
        <button type="button" className="chest-pill-btn chest-pill-btn--sm" disabled={!edited} onClick={reset}>{t.reset}</button>
      </div>
      {note && <p className="emc-text"><small>{note}</small></p>}

      <div className="mixer-presets">
        <label>{t.norm}{' '}
          <input className="input-dark" inputMode="decimal" value={own.norm ?? ''} placeholder={defNorm ?? '—'}
            onChange={e => setOwn({ norm: num(e.target.value) })} />
        </label>
        <label>{t.epic}{' '}
          <input className="input-dark" inputMode="decimal" value={own.epic ?? ''} placeholder={defEpic ?? '—'}
            onChange={e => setOwn({ epic: num(e.target.value) })} />
        </label>
        <label>{t.emc}{' '}
          <input className="input-dark" inputMode="decimal" value={own.emc ?? ''} placeholder="—"
            onChange={e => setOwn({ emc: num(e.target.value) })} />
        </label>
      </div>
      {scaleNorm != null && <p className="emc-text"><small>{t.defNorm.replace('{v}', fmt(scaleNorm))}</small></p>}

      <table className="tier-presets-table">
        <thead><tr><th>{t.chest}</th><th>{t.points}</th></tr></thead>
        <tbody>
          {base.map(x => (
            <tr key={x.catalog_id}>
              <td>{x.catalog_id}</td>
              <td><input className="input-dark" inputMode="decimal" value={own.points?.[x.catalog_id] ?? ''}
                placeholder={x.points} onChange={e => setPoints(x.catalog_id, e.target.value)} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>{t.statTitle.replace('{n}', BERSERK_ROWS.length)}</h3>
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
        <p className="emc-text">{t.reach} ({fmt(epicWant)}): {BERSERK_ROWS.filter(r => r[0] >= epicWant).length} / {BERSERK_ROWS.length}</p>
      )}
      <p className="emc-text"><small>{t.statHint}</small></p>
    </div>
  )
}
