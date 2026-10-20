import { useMemo, useState } from 'react'
import { posToK, kToPos, MIXER_MIN, MIXER_MAX } from '../lib/mixer.js'
import { DEFAULT_SETTINGS as EMC_DEFAULTS, computeRow, bandKey, clampMultiplier } from '../lib/emcQuota.js'
import {
  DEFAULT_SETTINGS as SCALE_DEFAULTS, CRYPT_TYPES, EMC_TYPES, weightAt, normAt, cryptsNormAt, epicRefAt,
} from '../lib/heroQuota.js'

// «Пульт» (владелец 2026-10-20): единый центр персональных настроек. Вкладки Crypts / EMC, колонка на
// тип сундука, фейдер: середина = рассчитанное значение (×1), вверх — больше, вниз — меньше; зелёная
// точка — вкл/выкл тип. Меню над фейдерами выбирает, чьи ступени Героя правим: «все уровни» — множитель
// пропорционально на каждую ступень, конкретная ступень — поправка поверх. Переключатель «Очки/Количество»
// меняет, что именно двигают фейдеры. Фейдер логарифмический: ×0.1 … ×1 … ×3, вверх и вниз ход одинаков.

const TXT = {
  ru: {
    tabCrypts: 'Crypts', tabEmc: 'EMC',
    points: 'Очки', count: 'Количество',
    levels: 'Уровни Героя', allLevels: 'Все уровни Героя', hero: 'Герой',
    master: 'Общий', masterCryptsPoints: 'Норма', masterEmcCount: 'Все монстры',
    enable: 'Персонализированный учёт по уровню Героя',
    off: 'Сейчас выключен: цели фиксированные, из настроек сезона. Включите, чтобы пользоваться пультом.',
    sample: 'Пример для Героя',
    base: 'расчёт', now: 'сейчас',
    reset: 'Двойной щелчок по фейдеру — вернуть ×1',
    mute: 'Вкл/выкл: выключенный тип не считается',
    epicOnly: 'Эпик-склепы, шт.',
    countNote: 'Для склепов в режиме «Количество» есть только ориентир по эпик-склепам; остальные типы считаются в очках.',
    save: '💾 Сохранить', saved: 'Нажмите «Сохранить», чтобы применить к сезону.',
    summary: 'Герой {h}: норма «Всего» {total} · Crypts {crypts} · EMC {emc} шт.',
    allNote: '«Все уровни» меняет значение на каждой ступени пропорционально её расчёту.',
    bandNote: 'Поправка только для этой ступени — поверх «Всех уровней».',
    mult: 'множитель',
  },
  en: {
    tabCrypts: 'Crypts', tabEmc: 'EMC',
    points: 'Points', count: 'Count',
    levels: 'Hero levels', allLevels: 'All Hero levels', hero: 'Hero',
    master: 'Master', masterCryptsPoints: 'Norm', masterEmcCount: 'All monsters',
    enable: 'Personalized accounting by Hero level',
    off: 'Currently off: targets are fixed from the season settings. Turn it on to use the mixer.',
    sample: 'Example for Hero',
    base: 'calculated', now: 'now',
    reset: 'Double-click a fader to reset to ×1',
    mute: 'On/off: a muted type is not counted',
    epicOnly: 'Epic crypts, pcs',
    countNote: "For crypts in 'Count' mode there is only the epic crypts guideline; other types are counted in points.",
    save: '💾 Save', saved: "Press 'Save' to apply to the season.",
    summary: 'Hero {h}: Total norm {total} · Crypts {crypts} · EMC {emc} pcs',
    allNote: "'All levels' changes the value on every step in proportion to its calculation.",
    bandNote: "A correction for this step only, on top of 'All levels'.",
    mult: 'multiplier',
  },
}

const MONSTERS = [['hydra', 'Hydra'], ['undead', 'Undead'], ['arachna', 'Arachna'], ['shadow', 'Shadow City']]
const BANDS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)
const MIN = MIXER_MIN
const MAX = MIXER_MAX
const fmt = n => Number(n).toLocaleString('ru-RU')

function Fader({ k, onK, on, onToggle, title, sub, disabled, tt }) {
  return (
    <div className={`mixer-col${disabled ? ' mixer-col--disabled' : ''}${on === false ? ' mixer-col--muted' : ''}`}>
      <div className="mixer-name" title={title}>{title}</div>
      {onToggle
        ? <button type="button" className={`mixer-dot${on === false ? ' mixer-dot--off' : ''}`} title={tt.mute}
            onClick={onToggle} disabled={disabled} />
        : <span className="mixer-dot-gap" />}
      <div className="mixer-rail" title={tt.reset}>
        <input type="range" className="mixer-range" min={0} max={1000} value={kToPos(k)} disabled={disabled}
          onChange={e => onK(posToK(Number(e.target.value)))} onDoubleClick={() => onK(1)} />
      </div>
      <input className="input-dark mixer-k" type="number" min={MIN} max={MAX} step={0.01} value={k}
        disabled={disabled} title={tt.mult}
        onChange={e => onK(e.target.value === '' ? 1 : clampMultiplier(e.target.value))} />
      <div className="mixer-sub">{sub}</div>
    </div>
  )
}

export default function MixerTab({ lang = 'ru', personal, onPersonal, quotas, onQuotas, onSave }) {
  const t = TXT[lang] || TXT.ru
  const [tab, setTab] = useState('crypts')
  const [mode, setMode] = useState('points')
  const [band, setBand] = useState('all')
  const [sample, setSample] = useState(400)

  const emcQ = quotas.find(q => q.slot === 2)
  const emc = useMemo(() => ({ ...structuredClone(EMC_DEFAULTS), ...(emcQ?.emc || {}) }), [emcQ])
  const mix = personal.mix || {}
  const flag = tab === 'crypts' ? 'crypts' : 'emc'
  const enabled = !!personal[flag]
  const exHero = band === 'all' ? Number(sample) || 400 : Number(band) + 5
  const scale = { ...SCALE_DEFAULTS, norm: personal.norm, weights: personal.weights, ranges: personal.ranges, mix }

  const setPersonal = patch => onPersonal({ ...personal, ...patch })
  const setEmc = next => onQuotas(quotas.map(q => (q.slot === 2 ? { ...q, emc: next } : q)))
  const setMixEntry = (path, id, patch) => {
    const cur = path === 'epic' ? (mix.epic || {}) : (mix.w?.[id] || {})
    const next = { ...cur, ...patch }
    setPersonal({ mix: { ...mix, ...(path === 'epic' ? { epic: next } : { w: { ...(mix.w || {}), [id]: next } }) } })
  }

  // значение фейдера «этой» ступени: all или поправка конкретной ступени
  const entryK = entry => (band === 'all' ? entry?.all ?? 1 : entry?.bands?.[band] ?? 1)
  const withK = (entry, k) => (band === 'all' ? { ...(entry || {}), all: k }
    : { ...(entry || {}), bands: { ...(entry?.bands || {}), [band]: k } })

  const cols = []
  if (tab === 'crypts' && mode === 'points') {
    for (const id of CRYPT_TYPES) {
      const e = mix.w?.[id]
      cols.push({
        key: id, title: id, on: e?.on !== false, k: entryK(e),
        onK: k => setMixEntry('w', id, withK(e, k)),
        onToggle: () => setMixEntry('w', id, { on: e?.on === false }),
        sub: `${weightAt(id, exHero, SCALE_DEFAULTS)} → ${weightAt(id, exHero, scale)}`,
      })
    }
  } else if (tab === 'crypts') {
    const e = mix.epic
    cols.push({
      key: 'epic', title: t.epicOnly, on: e?.on !== false, k: entryK(e),
      onK: k => setMixEntry('epic', null, withK(e, k)),
      onToggle: () => setMixEntry('epic', null, { on: e?.on === false }),
      sub: `${epicRefAt(exHero)} → ${epicRefAt(exHero, scale)}`,
    })
  } else if (mode === 'points') {
    for (const id of EMC_TYPES) {
      const e = mix.w?.[id]
      cols.push({
        key: id, title: id.replace(/^Epic /, ''), on: e?.on !== false, k: entryK(e),
        onK: k => setMixEntry('w', id, withK(e, k)),
        onToggle: () => setMixEntry('w', id, { on: e?.on === false }),
        sub: `${weightAt(id, exHero, SCALE_DEFAULTS)} → ${weightAt(id, exHero, scale)}`,
      })
    }
  } else {
    const keys = ['finalH', 'finalU', 'finalA', 'finalS']
    const baseRow = computeRow(exHero)
    const nowRow = computeRow(exHero, emc)
    MONSTERS.forEach(([key, label], i) => {
      const isOff = (emc.off || []).includes(key)
      const curK = band === 'all' ? emc.monsters?.[key] ?? 1 : emc.cells?.[key]?.[band] ?? 1
      cols.push({
        key, title: label, on: !isOff, k: curK,
        onK: k => setEmc(band === 'all'
          ? { ...emc, monsters: { ...emc.monsters, [key]: k } }
          : { ...emc, cells: { ...(emc.cells || {}), [key]: { ...(emc.cells?.[key] || {}), [band]: k } } }),
        onToggle: () => setEmc({ ...emc, off: isOff ? emc.off.filter(x => x !== key) : [...(emc.off || []), key] }),
        sub: `${baseRow[keys[i]]} → ${nowRow[keys[i]]}`,
      })
    })
  }

  // общий фейдер: Crypts/«Очки» — норма; EMC/«Количество» — общий множитель; остальное недоступно
  const master = tab === 'crypts' && mode === 'points'
    ? { title: t.masterCryptsPoints, k: personal.norm ?? 1, onK: k => setPersonal({ norm: k }),
        sub: `${fmt(normAt(exHero, SCALE_DEFAULTS))} → ${fmt(normAt(exHero, scale))}` }
    : tab === 'emc' && mode === 'count'
      ? { title: t.masterEmcCount, k: emc.global ?? 1, onK: k => setEmc({ ...emc, global: k }),
          sub: `${computeRow(exHero).emc} → ${computeRow(exHero, emc).emc}` }
      : null

  const emcRow = computeRow(exHero, emc)
  const summary = t.summary.replace('{h}', exHero).replace('{total}', fmt(normAt(exHero, scale)))
    .replace('{crypts}', fmt(cryptsNormAt(exHero, emc, scale))).replace('{emc}', emcRow.emc)

  return (
    <div className="mixer">
      <div className="chest-tabs chest-tabs--pill">
        {[['crypts', t.tabCrypts], ['emc', t.tabEmc]].map(([id, label]) => (
          <button key={id} type="button" className={`chest-tab chest-tab--pill ${tab === id ? 'chest-tab--active' : ''}`}
            onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      <div className="mixer-bar">
        <label className="quota-check">
          <input type="checkbox" checked={enabled} onChange={e => setPersonal({ [flag]: e.target.checked })} />
          {t.enable}
        </label>
        <div className="mixer-switch">
          {[['points', t.points], ['count', t.count]].map(([id, label]) => (
            <button key={id} type="button" className={`chest-pill-btn chest-pill-btn--sm${mode === id ? ' chest-pill-btn--green' : ''}`}
              onClick={() => setMode(id)}>{label}</button>
          ))}
        </div>
        <label className="mixer-pick">
          <span>{t.levels}</span>
          <select className="input-dark" value={band} onChange={e => setBand(e.target.value)}>
            <option value="all">{t.allLevels}</option>
            {BANDS.map(h => <option key={h} value={String(h)}>{h >= 600 ? `${t.hero} 600` : `${t.hero} ${h}–${h + 9}`}</option>)}
          </select>
        </label>
        {band === 'all' && (
          <label className="mixer-pick">
            <span>{t.sample}</span>
            <input className="input-dark emc-level-input" type="number" min={100} max={600} value={sample}
              onChange={e => setSample(e.target.value)} />
          </label>
        )}
      </div>

      {!enabled && <p className="emc-text"><small>{t.off}</small></p>}
      <p className="emc-text"><small>{band === 'all' ? t.allNote : t.bandNote}</small></p>
      {tab === 'crypts' && mode === 'count' && <p className="emc-text"><small>{t.countNote}</small></p>}

      <div className={`mixer-board${enabled ? '' : ' mixer-board--off'}`}>
        <div className="mixer-cols">
          {cols.map(c => (
            <Fader key={c.key} tt={t} title={c.title} k={c.k} onK={c.onK} on={c.on} onToggle={c.onToggle}
              sub={c.sub} disabled={!enabled} />
          ))}
        </div>
        <div className="mixer-master">
          {master
            ? <Fader tt={t} title={master.title} k={master.k} onK={master.onK} sub={master.sub} disabled={!enabled} />
            : <div className="mixer-name">{t.master}</div>}
        </div>
      </div>

      <p className="emc-text">{summary}</p>
      <div className="season-actions">
        <button type="button" className="chest-pill-btn chest-pill-btn--green" onClick={onSave}>{t.save}</button>
        <small>{t.saved}</small>
      </div>
    </div>
  )
}
