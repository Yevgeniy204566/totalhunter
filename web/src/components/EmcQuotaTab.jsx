import { useMemo, useState } from 'react'
import {
  DEFAULT_SETTINGS, EXTRAPOLATION_NOTES, MULTIPLIER_MAX, MULTIPLIER_MIN,
  clampMultiplier, computeTable,
} from '../lib/emcQuota.js'
import { downloadQuotaCsv } from '../lib/downloadCsv.js'

const STORAGE_KEY = 'emc_quota_settings_v1'
const MONSTERS = [
  { key: 'hydra', name: 'Hydra' },
  { key: 'undead', name: 'Undead' },
  { key: 'arachna', name: 'Arachna' },
  { key: 'shadow', name: 'Shadow City' },
]

// Рычаги — только удобство просмотра (не настройки клана): помнятся в браузере, без браузерного
// хранилища страница работает так же.
function loadSettings() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (raw && raw.monsters && Array.isArray(raw.ranges)) return raw
  } catch { /* нет хранилища — берём умолчания */ }
  return structuredClone(DEFAULT_SETTINGS)
}

function saveSettings(s) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)) } catch { /* не критично */ }
}

const fmt = n => (Math.round(n * 100) / 100).toFixed(2)
const isReal = hero => hero >= 360 && hero <= 440

function MultiplierInput({ value, onChange, label }) {
  return (
    <input
      className="input-dark emc-k-input" type="number" step="0.05"
      min={MULTIPLIER_MIN} max={MULTIPLIER_MAX} aria-label={label}
      value={value} onChange={e => onChange(e.target.value)}
    />
  )
}

// Что реально уходит на сервер: числа в границах 0.1…3.0, только корректные диапазоны 100–600.
function sanitize(s) {
  const ranges = (s.ranges || [])
    .map(r => ({ from: Math.round(Number(r.from)), to: Math.round(Number(r.to)), k: clampMultiplier(r.k) }))
    .filter(r => r.from >= 100 && r.to <= 600 && r.from <= r.to)
    .slice(0, 10)
  return {
    global: clampMultiplier(s.global),
    monsters: Object.fromEntries(MONSTERS.map(m => [m.key, clampMultiplier(s.monsters?.[m.key])])),
    ranges,
  }
}

export default function EmcQuotaTab({ cx, lang, quotas = [], onApply }) {
  const t = cx.emc
  // Применённые к сезону рычаги важнее локальных черновиков браузера.
  const applied = quotas.find(q => q.mode === 'emc_table')
  const [settings, setSettings] = useState(() => (applied?.emc ? { ...structuredClone(DEFAULT_SETTINGS), ...applied.emc } : loadSettings()))
  const [slot, setSlot] = useState(() => (applied || quotas.find(q => /e\s?m\s?c/i.test(q.name || '')) || quotas[quotas.length - 1] || {}).slot)
  const [applying, setApplying] = useState(false)
  const update = next => { setSettings(next); saveSettings(next) }
  const apply = async () => {
    setApplying(true)
    try { await onApply(Number(slot), sanitize(settings)) } finally { setApplying(false) }
  }

  const table = useMemo(() => computeTable(settings), [settings])
  const defaults = useMemo(() => computeTable(DEFAULT_SETTINGS), [])

  const setRange = (i, field, value) => update({
    ...settings,
    ranges: settings.ranges.map((r, j) => (j === i ? { ...r, [field]: value } : r)),
  })
  const addRange = () => {
    const last = settings.ranges[settings.ranges.length - 1]
    const from = last ? Math.min(Number(last.to) + 1, 600) : 100
    update({ ...settings, ranges: [...settings.ranges, { from, to: 600, k: 1 }] })
  }

  const ranges = settings.ranges.map(r => [Number(r.from), Number(r.to)]).sort((a, b) => a[0] - b[0])
  const overlap = ranges.some((r, i) => i > 0 && r[0] <= ranges[i - 1][1])
  const gaps = (() => {
    let cover = 100
    for (const [from, to] of ranges) {
      if (from > cover) return true
      cover = Math.max(cover, to + 1)
    }
    return cover <= 600
  })()

  const modified = clampMultiplier(settings.global) !== 1
    || MONSTERS.some(m => clampMultiplier(settings.monsters[m.key]) !== 1)
    || settings.ranges.some(r => clampMultiplier(r.k) !== 1)

  return (
    <div className="emc-tab">
      <h3 className="emc-title">{t.title}</h3>
      <p className="emc-text">{t.intro}</p>
      <p className="emc-text emc-period"><b>{t.period}</b></p>
      <p className="emc-text emc-formula">{t.formula}</p>

      <div className="emc-levers">
        <div className="emc-lever-card">
          <div className="season-subtitle">{t.globalLabel}</div>
          <MultiplierInput label={t.globalLabel} value={settings.global}
            onChange={v => update({ ...settings, global: v })} />
        </div>

        <div className="emc-lever-card">
          <div className="season-subtitle">{t.monstersLabel}</div>
          <div className="emc-monster-grid">
            {MONSTERS.map(m => (
              <label key={m.key} className="quota-row">
                <span>{m.name}</span>
                <MultiplierInput label={m.name} value={settings.monsters[m.key]}
                  onChange={v => update({ ...settings, monsters: { ...settings.monsters, [m.key]: v } })} />
              </label>
            ))}
          </div>
        </div>

        <div className="emc-lever-card emc-lever-card--wide">
          <div className="season-subtitle">{t.rangesLabel}</div>
          {settings.ranges.map((r, i) => (
            <div key={i} className="emc-range-row">
              <span>{t.rangeFrom}</span>
              <input className="input-dark emc-level-input" type="number" min={100} max={600}
                value={r.from} onChange={e => setRange(i, 'from', e.target.value)} />
              <span>{t.rangeTo}</span>
              <input className="input-dark emc-level-input" type="number" min={100} max={600}
                value={r.to} onChange={e => setRange(i, 'to', e.target.value)} />
              <span>×</span>
              <MultiplierInput label={t.rangeK} value={r.k} onChange={v => setRange(i, 'k', v)} />
              <button type="button" className="quota-del" title={t.rangeDelete}
                onClick={() => update({ ...settings, ranges: settings.ranges.filter((_, j) => j !== i) })}>🗑</button>
            </div>
          ))}
          <div className="emc-range-actions">
            <button type="button" className="chest-pill-btn chest-pill-btn--sm" onClick={addRange}>{t.rangeAdd}</button>
          </div>
          {overlap && <small className="emc-warn">{t.rangeOverlap}</small>}
          {!overlap && gaps && <small>{t.rangeGap}</small>}
        </div>
      </div>

      <div className="emc-apply">
        {quotas.length > 0 ? (
          <>
            <label className="emc-apply-pick">
              <span>{t.applyTo}</span>
              <select className="input-dark" value={slot ?? ''} onChange={e => setSlot(e.target.value)}>
                {quotas.map(q => <option key={q.slot} value={q.slot}>{`${q.slot}. ${q.name}`}</option>)}
              </select>
            </label>
            <button type="button" className="chest-pill-btn chest-pill-btn--green" disabled={applying || !slot}
              onClick={apply}>{t.apply}</button>
            <small>{applied ? t.appliedNote.replace('{name}', applied.name) : t.applyNote}</small>
          </>
        ) : <small>{t.noQuotas}</small>}
      </div>

      <div className="emc-toolbar">
        <small>{t.limitHint}</small>
        <button type="button" className="chest-pill-btn chest-pill-btn--sm"
          onClick={() => downloadQuotaCsv(table, lang)}>{t.download}</button>
        <button type="button" className="chest-pill-btn chest-pill-btn--sm" disabled={!modified}
          onClick={() => update(structuredClone(DEFAULT_SETTINGS))}>{t.reset}</button>
      </div>

      <div className="emc-table-wrap">
        <table className="chest-table emc-table">
          <thead>
            <tr>
              <th rowSpan={2} className="emc-sticky">{t.hero}</th>
              <th colSpan={4}>{t.base}</th>
              <th rowSpan={2}>{t.levelK}</th>
              <th rowSpan={2}>{t.monsterK}<br /><small>H / U / A / S</small></th>
              <th rowSpan={2}>{t.globalK}</th>
              <th colSpan={4}>{t.final} <small>{lang === "ru" ? "/ 2 нед." : "/ 2 wk"}</small></th>
              <th rowSpan={2} className="emc-emc-col">{t.emcCol}</th>
            </tr>
            <tr>
              {['H', 'U', 'A', 'S'].map(c => <th key={`b${c}`}>{c}</th>)}
              {['H', 'U', 'A', 'S'].map(c => <th key={`f${c}`}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.map((r, i) => {
              const d = defaults[i]
              const fin = [r.finalH, r.finalU, r.finalA, r.finalS]
              const dfin = [d.finalH, d.finalU, d.finalA, d.finalS]
              return (
                <tr key={r.hero} className={isReal(r.hero) ? '' : 'emc-row--est'}>
                  <td className="emc-sticky"><b>{r.hero}</b></td>
                  {r.base.map((b, k) => <td key={k}>{fmt(b)}</td>)}
                  <td className={r.levelK !== 1 ? 'emc-changed' : ''}>{fmt(r.levelK)}</td>
                  <td className={r.monsterK.some(k => k !== 1) ? 'emc-changed' : ''}>
                    {r.monsterK.map(fmt).join(' / ')}
                  </td>
                  <td className={r.globalK !== 1 ? 'emc-changed' : ''}>{fmt(r.globalK)}</td>
                  {fin.map((v, k) => <td key={k} className={v !== dfin[k] ? 'emc-changed' : ''}><b>{v}</b></td>)}
                  <td className={`emc-emc-col ${r.emc !== d.emc ? 'emc-changed' : ''}`}><b>{r.emc}</b></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="emc-text"><small>{t.changedHint} {t.estimatedHint}</small></p>
      <details className="emc-notes">
        <summary>{t.notesTitle}</summary>
        <ul>
          {EXTRAPOLATION_NOTES[lang === 'ru' ? 'ru' : 'en'].map(n => <li key={n}>{n}</li>)}
        </ul>
      </details>
    </div>
  )
}
