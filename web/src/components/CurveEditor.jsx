import { useMemo, useRef, useState } from 'react'
import { BANDS, HANDLE_BANDS, centerOf, applyDrag, seriesOf, bandsFromTargets } from '../lib/curveEdit.js'
import { weightAt, DEFAULT_SETTINGS } from '../lib/heroQuota.js'

// Кривая очков за сундук по уровням Героя (владелец 2026-10-26): как EQ в цифровом пульте — тянешь ручку, соседние точки
// плавно идут следом. Правит одну линию за раз; хранение прежнее (поправки ступеней mix.w[тип].bands), график показывает очки.

const TXT = {
  ru: {
    title: 'Очки за сундук по уровням Героя',
    hint: 'Выберите сундук внизу и тяните квадратные ручки вверх и вниз: соседние уровни следуют плавно. «Мягкость» — как далеко достаёт влияние ручки. Пунктир — очки по шкале, закрашено — ваше отличие от неё. Клавиши ↑ ↓ на выбранной ручке — шаг 5 очков.',
    soft: 'Мягкость', softOnly: 'одна точка', softWide: 'широкая волна',
    reset: 'Сбросить линию к шкале', resetTip: 'Вернуть очки выбранного сундука на всех уровнях к шкале',
    hero: 'Герой', points: 'очков', scale: 'по шкале', muted: 'Тип выключен кнопкой — включите его, чтобы править линию.',
    locked: 'В шкале на этом уровне 0 очков — поднять нельзя.', off: 'Включите «Персонализированный учёт», чтобы править линии.',
    anchor: 'опора', none: 'В шкале нет типов этого пульта.', pick: 'Выбранный сундук',
  },
  en: {
    title: 'Chest points by Hero level',
    hint: 'Pick a chest below and drag the square handles up and down: neighbouring levels follow smoothly. "Softness" is how far a handle reaches. Dashed — points by the scale, filled — your difference from it. Arrow keys ↑ ↓ on a focused handle step 5 points.',
    soft: 'Softness', softOnly: 'single point', softWide: 'wide wave',
    reset: 'Reset line to scale', resetTip: 'Return the selected chest to the scale on all levels',
    hero: 'Hero', points: 'points', scale: 'by scale', muted: 'This type is switched off — turn it on to edit the line.',
    locked: 'The scale gives 0 points at this level — it cannot be raised.', off: 'Turn on "Personalized accounting" to edit the lines.',
    anchor: 'anchor', none: 'No types of this console are in the scale.', pick: 'Selected chest',
  },
}

const COLORS = ['#a78bfa', '#f59e0b', '#38bdf8', '#4ade80', '#f472b6', '#fb923c', '#22d3ee', '#facc15', '#c084fc', '#34d399', '#f87171', '#94a3b8']
// опорные Герои шкалы: на них стоят реальные данные кланов, между ними кривая интерполирована
const ANCHORS = [298, 387.5, 450]

const W = 1000, H = 380, ML = 54, MR = 16, MT = 16, MB = 36
const xOf = h => ML + (h - 100) / 500 * (W - ML - MR)
const niceMax = v => Math.max(50, Math.ceil(v * 1.3 / 50) * 50)

export default function CurveEditor({ lang = 'ru', items = [], scale, disabled = false, onBands }) {
  const t = TXT[lang] || TXT.ru
  const [selKey, setSelKey] = useState(null)
  const [softness, setSoftness] = useState(40)
  const [hover, setHover] = useState(null)
  const drag = useRef(null)
  const svgRef = useRef(null)

  const series = useMemo(() => {
    const out = items.map(x => ({ ...x, ...seriesOf(x.key, scale) })).filter(x => x.ref.some(r => r > 0) || x.base.some(b => b > 0))
    return out.map((x, i) => ({ ...x, color: COLORS[i % COLORS.length], muted: scale.mix?.w?.[x.key]?.on === false }))
  }, [items, scale])
  if (!series.length) return <p className="emc-text"><small>{t.none}</small></p>

  const sel = series.find(x => x.key === selKey) || series[0]
  const selBands = scale.mix?.w?.[sel.key]?.bands || {}
  // ось Y не прыгает во время перетаскивания
  const ymax = drag.current?.ymax ?? niceMax(Math.max(...sel.cur, ...sel.base))
  const yOf = v => MT + (1 - Math.min(v, ymax) / ymax) * (H - MT - MB)
  const canEdit = !disabled && !sel.muted

  const pathOf = vals => vals.map((v, i) => `${i ? 'L' : 'M'}${xOf(centerOf(BANDS[i])).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')
  const areaOf = (a, b) => `${pathOf(a)} ${[...b].map((v, i) => [v, i]).reverse().map(([v, i]) => `L${xOf(centerOf(BANDS[i])).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')} Z`

  const commit = (handleBand, start, delta, existing) => {
    const target = applyDrag(start, handleBand, delta, softness, sel.locked)
    const changed = target.map((v, i) => Math.abs(v - start[i]) > 1e-9)
    onBands(sel.key, bandsFromTargets(target, sel.ref, existing, changed))
  }

  const pointerValue = e => {
    const r = svgRef.current.getBoundingClientRect()
    const y = (e.clientY - r.top) / r.height * H
    return Math.max(0, (1 - (y - MT) / (H - MT - MB)) * drag.current.ymax)
  }

  const onDown = (band, i) => e => {
    if (!canEdit || sel.locked.has(band)) return
    e.preventDefault()
    svgRef.current.setPointerCapture(e.pointerId)
    drag.current = { band, start: [...sel.cur], existing: { ...selBands }, ymax, v0: sel.cur[i] }
  }
  const onMove = e => {
    const d = drag.current
    const r = svgRef.current.getBoundingClientRect()
    const hero = 100 + ((e.clientX - r.left) / r.width * W - ML) / (W - ML - MR) * 500
    setHover(Math.min(BANDS.length - 1, Math.max(0, Math.floor((hero - 100) / 10))))
    if (!d) return
    commit(d.band, d.start, pointerValue(e) - d.v0, d.existing)
  }
  const onUp = () => { drag.current = null }
  const onKey = (band, i) => e => {
    if (!canEdit || sel.locked.has(band)) return
    const step = e.shiftKey ? 25 : 5
    const delta = e.key === 'ArrowUp' ? step : e.key === 'ArrowDown' ? -step : 0
    if (!delta) return
    e.preventDefault()
    commit(band, [...sel.cur], delta, { ...selBands })
  }

  const hi = hover ?? BANDS.indexOf(400)
  const readout = `${t.hero} ${BANDS[hi]}${BANDS[hi] >= 600 ? '' : '–' + (BANDS[hi] + 9)}: ${sel.title} — ${sel.cur[hi]} ${t.points} (${t.scale} ${sel.base[hi]})`
  const gridStep = ymax <= 250 ? 50 : 100
  const grid = Array.from({ length: Math.floor(ymax / gridStep) + 1 }, (_, k) => k * gridStep)
  const dirty = Object.keys(selBands).length > 0

  return (
    <div className={`curve${disabled ? ' curve--off' : ''}`}>
      <h4 className="curve-title">{t.title}</h4>
      <p className="curve-hint">{t.hint}</p>
      {disabled && <p className="emc-text"><small>{t.off}</small></p>}

      <svg ref={svgRef} className="curve-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.title}
        onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} onPointerLeave={() => { if (!drag.current) setHover(null) }}>
        {grid.map(v => (
          <g key={v}>
            <line x1={ML} x2={W - MR} y1={yOf(v)} y2={yOf(v)} className="curve-grid" />
            <text x={ML - 8} y={yOf(v) + 5} textAnchor="end" className="curve-axis">{Math.round(v)}</text>
          </g>
        ))}
        {[100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600].map(h => (
          <text key={h} x={xOf(h)} y={H - 10} textAnchor="middle" className="curve-axis">{h}</text>
        ))}
        {ANCHORS.map((h, n) => {
          const v = weightAt(sel.key, h, scale) ?? 0
          const b0 = weightAt(sel.key, h, DEFAULT_SETTINGS) ?? 0
          return (
            <g key={h}>
              <line x1={xOf(h)} x2={xOf(h)} y1={MT} y2={H - MB} className="curve-anchor" />
              <text x={xOf(h) + 6} y={MT + 15 + n * 19} className="curve-anchor-text">{t.anchor} {h}: <tspan className="curve-anchor-val">{v}</tspan>{v !== b0 ? ` (${t.scale} ${b0})` : ''}</text>
              <circle cx={xOf(h)} cy={yOf(v)} r="5.5" className="curve-anchor-dot" />
            </g>
          )
        })}

        <path d={areaOf(sel.cur, sel.base)} fill={sel.color} opacity="0.2" />
        <path d={pathOf(sel.base)} fill="none" stroke="#e5e7eb" strokeWidth="2" strokeDasharray="7 6" opacity="0.7" />
        <path d={pathOf(sel.cur)} fill="none" stroke={sel.color} strokeWidth="4.5" strokeLinejoin="round" opacity={sel.muted ? 0.35 : 1} />

        {hover != null && (
          <line x1={xOf(centerOf(BANDS[hover]))} x2={xOf(centerOf(BANDS[hover]))} y1={MT} y2={H - MB} className="curve-cross" />
        )}

        {HANDLE_BANDS.map(b => {
          const i = BANDS.indexOf(b)
          const locked = sel.locked.has(b)
          const x = xOf(centerOf(b)), y = yOf(sel.cur[i])
          return (
            <g key={b} className={`curve-handle${locked ? ' curve-handle--locked' : ''}`} style={{ touchAction: 'none' }}
              tabIndex={canEdit && !locked ? 0 : -1} role="slider" aria-label={`${t.hero} ${b}`} aria-valuemin={0} aria-valuemax={Math.round(ymax)}
              aria-valuenow={sel.cur[i]} onPointerDown={onDown(b, i)} onKeyDown={onKey(b, i)}>
              <title>{locked ? t.locked : `${t.hero} ${b}: ${sel.cur[i]}`}</title>
              <rect x={x - 11} y={y - 15} width="22" height="30" rx="4" className="curve-cap" />
              <line x1={x - 11} x2={x + 11} y1={y} y2={y} stroke={sel.color} strokeWidth="3" />
              <text x={x} y={y > MT + 46 ? y - 21 : y + 36} textAnchor="middle" className="curve-val">{sel.cur[i]}</text>
            </g>
          )
        })}
      </svg>

      <p className="curve-readout" role="status" aria-live="polite">{readout}</p>
      {sel.muted && <p className="emc-text"><small>{t.muted}</small></p>}

      <div className="curve-chips" role="group" aria-label={t.pick}>
        {series.map(x => (
          <button key={x.key} type="button" className={`curve-chip${x.key === sel.key ? ' curve-chip--on' : ''}`}
            style={{ '--cc': x.color }} onClick={() => setSelKey(x.key)}>
            <i /> {x.title}
          </button>
        ))}
      </div>

      <div className="curve-tools">
        <label className="curve-soft">
          <span>{t.soft}</span>
          <small>{t.softOnly}</small>
          <input type="range" min={0} max={100} value={softness} onChange={e => setSoftness(Number(e.target.value))} aria-label={t.soft} />
          <small>{t.softWide}</small>
        </label>
        <button type="button" className="chest-pill-btn" title={t.resetTip} disabled={!canEdit || !dirty} onClick={() => onBands(sel.key, {})}>{t.reset}</button>
      </div>
    </div>
  )
}
