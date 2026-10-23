import { useState } from 'react'
import { normAt, epicRefAt } from '../lib/heroQuota.js'
import { computeRow, emcChimeraAt, emcTotalAt, round } from '../lib/emcQuota.js'
import { BERSERK_COLUMNS, BERSERK_ROWS } from '../lib/berserkActivity.js'

// Редактор пресетов T5–T9 в «Пульте» (владелец 2026-10-23): очки за сундук (общий пресет сервера + правки клана),
// квоты за 2 недели (очки, эпик-склепы, EMC), загрузка в пульт, справка по замеру активности Берсерков.
// Правки лежат в personal.tier_presets (points / removed / norm / epic / emc) и сохраняются кнопкой «Сохранить настройки».
// Вид — карточка в стиле пульта: вкладки ступеней, акцентная строка квот, сетка сундуков по группам;
// пояснения свёрнуты (не тултипы: на телефоне нет наведения, а основной текст держим крупным).

const TXT = {
  ru: {
    title: 'Редактор пресета', tier: 'Ступень',
    quotas: 'Квоты за 2 недели', norm: 'Очки', epic: 'Эпик-склепы (минимум)', emc: 'EMC, штук',
    groupCrypts: 'Склепы и цитадели', groupEmc: 'Эпические монстры (EMC)',
    points: 'Очки за сундук', less: 'Меньше', more: 'Больше', remove: 'Убрать сундук из пресета',
    add: '+ Добавить сундук', addPick: 'Выберите сундук', addNone: 'Все сундуки уже в пресете', addPoints: 'очки', addOk: 'Добавить', addCancel: 'Отмена',
    load: 'Загрузить пресет в ростер (для учёта)', reset: 'Сбросить к общему', edited: 'изменено',
    applyHint: 'Это не правка пресета: по загруженному пресету клан ведёт учёт очков игроков. После загрузки нажмите «Сохранить настройки».',
    loaded: 'Пресет {n} загружен в учёт ростера (изменено типов: {c}). По нему будет вестись учёт — нажмите «Сохранить настройки».',
    info: 'Как это работает',
    basis: 'Основа ступени',
    emcSum: 'EMC за 2 недели (сумма трёх колонок)',
    help: [
      'Очки за сундук и квоты — это ваш вариант пресета ступени. Кнопки − и + меняют очки на 1, «×» убирает сундук из пресета, «+ Добавить сундук» возвращает убранный или добавляет новый. Изменённое выделено жёлтой рамкой.',
      '«Загрузить в пульт» ставит очки за сундук из пресета для ступеней Героя, отмеченных в пульте выше («Все уровни» — на все): пульт сам подбирает множитель, чтобы при примерном Герое очки равнялись пресетным. Затрагиваются только типы из «Учёта» клана.',
      'Правки в редакторе сохраняются кнопкой «Сохранить настройки» выше.',
    ],
    statTitle: 'Замер активности клана Берсерки (T9): 2 недели, {n} игроков',
    col: 'Столбец', median: 'Медиана', mean: 'Среднее', max: 'Максимум',
    reach: 'Выполнили минимум эпик-склепов',
    statHint: 'Данные без имён. Минимум берётся из поля выбранной ступени (если пусто — из шкалы).',
  },
  en: {
    title: 'Preset editor', tier: 'Tier',
    quotas: '2-week quotas', norm: 'Points', epic: 'Epic crypts (minimum)', emc: 'EMC, pcs',
    groupCrypts: 'Crypts and citadels', groupEmc: 'Epic monsters (EMC)',
    points: 'Points per chest', less: 'Less', more: 'More', remove: 'Remove chest from preset',
    add: '+ Add chest', addPick: 'Pick a chest', addNone: 'All chests are already in the preset', addPoints: 'points', addOk: 'Add', addCancel: 'Cancel',
    load: 'Load preset into roster (for accounting)', reset: 'Reset to shared', edited: 'edited',
    applyHint: "This is not editing the preset: the clan keeps player accounting by the loaded preset. Press 'Save settings' after loading.",
    loaded: "Preset {n} loaded into the roster accounting (types changed: {c}). Accounting will follow it — press 'Save settings'.",
    info: 'How it works',
    basis: 'Tier basis',
    emcSum: 'EMC per 2 weeks (sum of three columns)',
    help: [
      "Points per chest and the quotas are your version of the tier preset. The − and + buttons change points by 1, '×' removes a chest from the preset, '+ Add chest' brings back a removed one or adds a new one. Edited items have a yellow frame.",
      "'Load into mixer' sets points per chest from the preset for the Hero steps ticked in the mixer above ('All levels' = every step): the mixer picks a multiplier so that at the sample Hero the points equal the preset's. Only types the clan keeps in accounting are affected.",
      "Press 'Save settings' above to keep the editor changes.",
    ],
    statTitle: 'Activity sample, clan Berserki (T9): 2 weeks, {n} players',
    col: 'Column', median: 'Median', mean: 'Mean', max: 'Max',
    reach: 'Players at or above the epic crypts minimum',
    statHint: 'No names. The minimum comes from the chosen tier field (scale value if empty).',
  },
}

const TIERS = ['T5', 'T6', 'T7', 'T8', 'T9']
const STEP = 1 // шаг кнопок ± (владелец 2026-10-23: по 1, а не по 5)

// Основа ступеней (владелец 2026-10-23): T9 — Берсерки (Герой 450 в среднем), T8 — ЭДО (387.5), T7 — Феникс (298),
// T6 — Старт (279). Очки за сундук лежат в общих пресетах сервера. Квоты по умолчанию: «стена» — записанное число
// клана, «расчёт» — шкала пульта (heroQuota/emcQuota), для T5 данных нет.
// hero — уровень, на котором стоит стена клана для нормы и эпик-склепов; emcHero — средний Герой клана в данных EMC.
const BASES = {
  T9: { hero: 450, emcHero: 450, norm: () => 25000, epic: () => 300,
        ru: 'Берсерки (Герой в среднем 450): очки, эпик-склепы и EMC — данные клана (EMC — сумма трёх колонок замера, среднее по клану).',
        en: 'Berserki (average Hero 450): points, epic crypts and EMC are clan data (EMC is the sum of three sample columns, clan average).' },
  T8: { hero: 387.5, emcHero: 383, norm: () => 14000, epic: () => 200,
        ru: 'ЭДО / ELDORADO (Герой 383–387.5): очки, норма и эпик-склепы — стена клана; EMC — столбец EMC из истории сезона (45,6 на игрока, все эпик-монстры).',
        en: 'ELDORADO (Hero 383–387.5): points, norm and epic crypts are the clan wall; EMC is the EMC column of the season history (45.6 per player, all epic monsters).' },
  T7: { hero: 298, emcHero: 298, norm: () => normAt(298), epic: () => epicRefAt(298),
        ru: 'Феникс (Герой 298): очки за сундук — стена клана; норма, эпик-склепы и EMC — расчёт шкалы.',
        en: 'Phoenix (Hero 298): points per chest are the clan wall; norm, epic crypts and EMC are scale calculations.' },
  T6: { hero: 279, emcHero: 279, emcFixed: 0, norm: () => 5000, epic: () => 50,
        ru: 'Старт (Герой 279): норма 5 000 и 50 эпик-склепов — стена клана; очки за сундук — расчёт шкалы. Старту не хватает мощи бить эпических монстров — EMC 0.',
        en: 'Start (Hero 279): norm 5,000 and 50 epic crypts are the clan wall; points per chest are a scale calculation. Start lacks the power to kill epic monsters — EMC 0.' },
}

const fmt = n => Number(n).toLocaleString('ru-RU')
const num = v => (v === '' || v == null ? null : Math.max(0, Number(String(v).replace(',', '.')) || 0))
const isCrypt = id => /Crypt|Citadel/i.test(id)

const median = arr => {
  const v = [...arr].sort((a, b) => a - b)
  const mid = v.length >> 1
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2
}

function stats(col) {
  const v = BERSERK_ROWS.map(r => r[col]).sort((a, b) => a - b)
  const mid = v.length >> 1
  const median = v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2
  return { median, mean: Math.round(v.reduce((a, b) => a + b, 0) / v.length), max: v[v.length - 1] }
}

export default function TierPresetEditor({ lang = 'ru', clanPresets, personal, onPersonal, onLoad, catalogItems = [], sets = null, setsTitle = '', setsHint = '', setsNote = '' }) {
  const t = TXT[lang] || TXT.ru
  const names = TIERS.filter(n => clanPresets?.[n])
  const [tier, setTier] = useState('')
  const [note, setNote] = useState('')
  const [adding, setAdding] = useState(null) // { id, points }
  if (!names.length) return null
  const cur = names.includes(tier) ? tier : names[names.length - 1]
  const base = clanPresets[cur]
  const own = personal.tier_presets?.[cur] || {}

  // Состав пресета: общий пресет минус убранные кланом + добавленные кланом (их очки лежат в own.points)
  const removed = new Set(own.removed || [])
  const baseIds = new Set(base.map(x => x.catalog_id))
  const added = Object.keys(own.points || {}).filter(id => !baseIds.has(id))
  const list = [
    ...base.filter(x => !removed.has(x.catalog_id)).map(x => ({ id: x.catalog_id, points: own.points?.[x.catalog_id] ?? x.points, custom: false })),
    ...added.map(id => ({ id, points: own.points[id], custom: true })),
  ]
  const items = list.map(x => ({ catalog_id: x.id, points: x.points, is_in_pattern: true }))

  const setOwn = patch => {
    onPersonal({ ...personal, tier_presets: { ...(personal.tier_presets || {}), [cur]: { ...own, ...patch } } })
  }
  const setPoints = (id, v) => {
    const points = { ...(own.points || {}) }
    const n = num(v)
    const def = base.find(x => x.catalog_id === id)?.points
    if (n == null && def === undefined) return // у добавленного сундука очки не стираются — его можно только убрать
    if (n == null || n === def) delete points[id]; else points[id] = n
    setOwn({ points })
  }
  const step = (x, d) => setPoints(x.id, Math.max(0, x.points + d))
  const removeChest = x => {
    const points = { ...(own.points || {}) }
    delete points[x.id]
    setOwn({ points, removed: x.custom ? (own.removed || []) : [...new Set([...(own.removed || []), x.id])] })
  }
  const addChest = () => {
    if (!adding?.id) return
    const points = { ...(own.points || {}) }
    const p = num(adding.points)
    const def = base.find(x => x.catalog_id === adding.id)?.points
    if (def === undefined) points[adding.id] = p ?? STEP; else if (p != null && p !== def) points[adding.id] = p
    setOwn({ points, removed: (own.removed || []).filter(id => id !== adding.id) })
    setAdding(null)
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

  const basis = BASES[cur]
  const defNorm = basis ? Math.round(basis.norm()) : null
  const defEpic = basis ? Math.round(basis.epic()) : null
  // EMC — все эпик-монстры вместе (модель lib/emcQuota.js), показываем и разбивку по монстрам
  const emcRow = basis && basis.emcFixed == null ? computeRow(basis.emcHero) : null
  const defEmc = basis ? (basis.emcFixed ?? round(emcTotalAt(basis.emcHero))) : null
  const epicWant = own.epic ?? defEpic
  const edited = Object.keys(own.points || {}).length > 0 || (own.removed || []).length > 0
    || own.norm != null || own.epic != null || own.emc != null

  const groups = [
    ['crypts', t.groupCrypts, list.filter(x => isCrypt(x.id))],
    ['emc', t.groupEmc, list.filter(x => !isCrypt(x.id))],
  ]
  // что можно добавить в группу: известные типы, которых сейчас нет в пресете
  const present = new Set(list.map(x => x.id))
  // все сундуки клана из вкладки «Общие нормы клана» + типы общих пресетов; уже стоящие в пресете не предлагаем
  const labels = new Map(catalogItems.map(x => [x.id, x.label || x.id]))
  for (const x of Object.values(clanPresets).flat()) if (!labels.has(x.catalog_id)) labels.set(x.catalog_id, x.catalog_id)
  const addable = [...labels].filter(([id]) => !present.has(id)).sort((a, b) => a[1].localeCompare(b[1]))

  return (
    <section className="pult-card">
      <div className="pult-card-head">
        <h3>{t.title}</h3>
        {edited && <span className="pult-badge">{t.edited}</span>}
      </div>

      <div className="chest-tabs chest-tabs--pill" role="tablist" aria-label={t.tier}>
        {names.map(n => (
          <button key={n} type="button" className={`chest-tab chest-tab--pill ${n === cur ? 'chest-tab--active' : ''}`}
            onClick={() => { setTier(n); setNote(''); setAdding(null) }}>{n}</button>
        ))}
      </div>
      {basis && <p className="pult-hint"><b>{t.basis}:</b> {basis[lang] || basis.ru}</p>}

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
        {emcRow && (
          <div className="pult-quotas-sub">EMC: Hydra {emcRow.finalH} · Undead {emcRow.finalU} · Arachna {emcRow.finalA} · Shadow City {emcRow.finalS} · Chimera {emcChimeraAt(basis.emcHero)}</div>
        )}
      </div>

      {groups.map(([gid, title, rows]) => (
        <div key={gid}>
          <h4 className="pult-group">{title}</h4>
          <div className="pult-chests">
            {rows.map(x => {
              const changed = x.custom || own.points?.[x.id] != null
              return (
                <div key={x.id} className={`pult-chest ${changed ? 'pult-chest--edited' : ''}`}>
                  <span className="pult-chest-name">{x.id}</span>
                  <span className="pult-stepper">
                    <button type="button" className="pult-step" aria-label={`${x.id}: ${t.less}`} title={t.less} onClick={() => step(x, -STEP)}>−</button>
                    <input className="input-dark pult-num" inputMode="decimal" aria-label={`${x.id}: ${t.points}`}
                      value={own.points?.[x.id] ?? ''} placeholder={x.points}
                      onChange={e => setPoints(x.id, e.target.value)} />
                    <button type="button" className="pult-step" aria-label={`${x.id}: ${t.more}`} title={t.more} onClick={() => step(x, STEP)}>+</button>
                    <button type="button" className="pult-step pult-step--del" aria-label={`${x.id}: ${t.remove}`} title={t.remove} onClick={() => removeChest(x)}>×</button>
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {adding ? (
        <div className="pult-add">
          <select className="input-dark" value={adding.id} onChange={e => setAdding({ ...adding, id: e.target.value })}>
            <option value="">{addable.length ? t.addPick : t.addNone}</option>
            {addable.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
          <input className="input-dark pult-num" inputMode="decimal" placeholder={t.addPoints} value={adding.points}
            onChange={e => setAdding({ ...adding, points: e.target.value })} />
          <button type="button" className="chest-pill-btn" disabled={!adding.id} onClick={addChest}>{t.addOk}</button>
          <button type="button" className="pult-link-btn" onClick={() => setAdding(null)}>{t.addCancel}</button>
        </div>
      ) : (
        <button type="button" className="chest-pill-btn pult-add-btn" onClick={() => setAdding({ id: '', points: '' })}>{t.add}</button>
      )}

      {/* Нижняя строка, как в классических окнах: выбор пресета, наборы «Сохранить / Загрузить», главная кнопка справа */}
      <div className="pult-footer">
        <label className="pult-footer-field"><span>{t.tier}</span>
          <select className="input-dark" value={cur} onChange={e => { setTier(e.target.value); setNote(''); setAdding(null) }}>
            {names.map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        {sets}
        <button type="button" className="pult-link-btn" disabled={!edited} onClick={reset}>{t.reset}</button>
        <button type="button" className="chest-pill-btn chest-pill-btn--primary pult-apply" onClick={load}>{t.load}</button>
      </div>
      <p className="pult-hint">{t.applyHint}</p>
      {setsHint && <p className="pult-hint"><b>{setsTitle}.</b> {setsHint}</p>}
      {(note || setsNote) && <p className="pult-flash">{note || setsNote}</p>}

      <details className="pult-note">
        <summary>{t.info}</summary>
        {t.help.map((line, i) => <p key={i}>{line}</p>)}
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
            {(() => {
              const sums = BERSERK_ROWS.map(r => r[1] + r[2] + r[3])
              return <tr><td>{t.emcSum}</td><td>{fmt(median(sums))}</td><td>{fmt(Math.round(sums.reduce((a, b) => a + b, 0) / sums.length))}</td><td>{fmt(Math.max(...sums))}</td></tr>
            })()}
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
