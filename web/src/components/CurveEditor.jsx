import { useMemo, useRef, useState } from 'react'
import { BANDS, HANDLE_BANDS, centerOf, applyDrag, bandsFromTargets } from '../lib/curveEdit.js'

// Кривая по уровням Героя (владелец 2026-10-26): как EQ в цифровом пульте — тянешь ручку, соседние точки плавно идут
// следом. Режим «Очки» — очки за сундук, «Количество» — штуки на игрока. Правит одну линию за раз; линии готовит
// lib/curveLines.js, хранение прежнее (поправки ступеней), график показывает числа.

const TXT = {
  ru: {
    titlePoints: 'Очки за сундук по уровням Героя', titleCount: 'Количество сундуков по уровням Героя',
    hintPoints: 'Выберите сундук внизу и тяните квадратные ручки вверх-вниз — соседние уровни идут следом. Полоска Zoom задаёт, сколько уровней ручка тянет за собой. Пунктир — шкала по умолчанию (рядом с ним ручка «прилипает»), закрашено — ваше отличие.',
    zoom: 'Zoom', zoomIn: 'Ручка тянет за собой больше соседних уровней', zoomOut: 'Ручка тянет за собой меньше соседних уровней (в минимуме — одна ступень)',
    reset: 'Сбросить линию к шкале', resetTip: 'Вернуть выбранную линию на всех уровнях к шкале',
    resetAll: 'Сбросить все линии',
    hero: 'Герой', points: 'очков', count: 'шт.', scale: 'по шкале', muted: 'Тип выключен кнопкой — включите его, чтобы править линию.',
    locked: 'В шкале на этом уровне 0 — поднять нельзя.', off: 'Включите «Персонализированный учёт», чтобы править линии.',
    axisX: 'Уровень Героя', axisYPoints: 'Очки за сундук', axisYCount: 'Штук на игрока',
    none: 'Для этого пульта на графике нечего показывать: у типов нет значений по уровням Героя.', pick: 'Выбранный сундук',
  },
  en: {
    titlePoints: 'Chest points by Hero level', titleCount: 'Chest count by Hero level',
    hintPoints: 'Pick a chest below and drag the square handles up and down — neighbouring levels follow. The Zoom strip sets how many levels a handle pulls along. Dashed — the default scale (a handle snaps onto it), filled — your difference.',
    zoom: 'Zoom', zoomIn: 'A handle pulls more neighbouring levels along', zoomOut: 'A handle pulls fewer neighbouring levels along (at the minimum — one step)',
    reset: 'Reset line to scale', resetTip: 'Return the selected line to the scale on all levels',
    resetAll: 'Reset all lines',
    hero: 'Hero', points: 'points', count: 'pcs', scale: 'by scale', muted: 'This type is switched off — turn it on to edit the line.',
    locked: 'The scale gives 0 at this level — it cannot be raised.', off: 'Turn on "Personalized accounting" to edit the lines.',
    axisX: 'Hero level', axisYPoints: 'Points per chest', axisYCount: 'Pieces per player',
    none: 'Nothing to draw for this console: the types have no values by Hero level.', pick: 'Selected chest',
  },
}

const COLORS = ['#a78bfa', '#f59e0b', '#38bdf8', '#4ade80', '#f472b6', '#fb923c', '#22d3ee', '#facc15', '#c084fc', '#34d399', '#f87171', '#94a3b8']

const W = 1000, H = 400, ML = 58, MR = 16, MT = 16, MB = 62
const xOf = h => ML + (h - 100) / 500 * (W - ML - MR)
// верх оси — ближайшее «круглое» число с запасом 30%; линий сетки всегда пять
const NICE = [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 125, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1500, 2000, 3000, 5000, 10000]
const niceMax = v => NICE.find(n => n >= v * 1.3) ?? Math.ceil(v * 1.3 / 1000) * 1000

export default function CurveEditor({ lang = 'ru', mode = 'points', lines = [], disabled = false, onBands, onResetAll, hasLines = false, footer = null, note = '' }) {
  const t = TXT[lang] || TXT.ru
  const [selKey, setSelKey] = useState(null)
  const [softness, setSoftness] = useState(40)
  const [hover, setHover] = useState(null)
  const drag = useRef(null)
  const svgRef = useRef(null)
  const unitWord = mode === 'count' ? t.count : t.points

  const series = useMemo(() => lines.map((x, i) => ({ ...x, color: COLORS[i % COLORS.length] })), [lines])
  if (!series.length) return <p className="emc-text"><small>{t.none}</small></p>

  const sel = series.find(x => x.key === selKey) || series[0]
  // ось Y не прыгает во время перетаскивания
  const ymax = drag.current?.ymax ?? niceMax(Math.max(...sel.cur, ...sel.base, 1))
  const yOf = v => MT + (1 - Math.min(v, ymax) / ymax) * (H - MT - MB)
  const canEdit = !disabled && !sel.muted

  const pathOf = vals => vals.map((v, i) => `${i ? 'L' : 'M'}${xOf(centerOf(BANDS[i])).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')
  const areaOf = (a, b) => `${pathOf(a)} ${[...b].map((v, i) => [v, i]).reverse().map(([v, i]) => `L${xOf(centerOf(BANDS[i])).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')} Z`

  const commit = (handleBand, start, delta, existing) => {
    const target = applyDrag(start, handleBand, delta, softness, sel.locked)
    const changed = target.map((v, i) => Math.abs(v - start[i]) > 1e-9)
    onBands(sel, bandsFromTargets(target, sel.ref, existing, changed))
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
    drag.current = { band, start: [...sel.cont], existing: { ...sel.bands }, ymax, v0: sel.cont[i], scaleV: sel.ref[i] }
  }
  const onMove = e => {
    const d = drag.current
    const r = svgRef.current.getBoundingClientRect()
    const hero = 100 + ((e.clientX - r.left) / r.width * W - ML) / (W - ML - MR) * 500
    setHover(Math.min(BANDS.length - 1, Math.max(0, Math.floor((hero - 100) / 10))))
    if (!d) return
    // магнит к шкале: когда ручка показывает то же число, что и шкала (значения целые), она встаёт ровно на значение шкалы —
    // так линию можно вернуть в исходное без следа в данных
    let v = pointerValue(e)
    if (Math.round(v) === Math.round(d.scaleV) || Math.abs(v - d.scaleV) < Math.max(0.5, d.ymax * 0.02)) v = d.scaleV
    commit(d.band, d.start, v - d.v0, d.existing)
  }
  const onUp = () => { drag.current = null }
  const onKey = (band, i) => e => {
    if (!canEdit || sel.locked.has(band)) return
    const step = e.shiftKey ? 5 : 1
    const delta = e.key === 'ArrowUp' ? step : e.key === 'ArrowDown' ? -step : 0
    if (!delta) return
    e.preventDefault()
    commit(band, [...sel.cont], delta, { ...sel.bands })
  }

  const hi = hover ?? BANDS.indexOf(400)
  const readout = `${t.hero} ${BANDS[hi]}${BANDS[hi] >= 600 ? '' : '–' + (BANDS[hi] + 9)}: ${sel.title} — ${sel.cur[hi]} ${unitWord} (${t.scale} ${sel.base[hi]})`
  const gridStep = ymax / 5
  const grid = [0, 1, 2, 3, 4, 5].map(k => k * gridStep)
  const dirty = Object.keys(sel.bands || {}).length > 0

  return (
    <div className={`curve${disabled ? ' curve--off' : ''}`}>
      <h4 className="curve-title">{mode === 'count' ? t.titleCount : t.titlePoints}</h4>
      <p className="curve-hint">{t.hintPoints}</p>
      {disabled && <p className="emc-text"><small>{t.off}</small></p>}

      <div className="curve-wrap">
      <div className="curve-zoom" role="group" aria-label={t.zoom}>
        <span>{t.zoom}</span>
        <button type="button" title={t.zoomOut} aria-label={`${t.zoom} −`} disabled={softness <= 0} onClick={() => setSoftness(v => Math.max(0, v - 10))}>−</button>
        <input type="range" className="curve-zoom-strip" min={0} max={100} step={10} value={softness} aria-label={t.zoom}
          style={{ '--p': `${softness}%` }} onChange={e => setSoftness(Number(e.target.value))} />
        <button type="button" title={t.zoomIn} aria-label={`${t.zoom} +`} disabled={softness >= 100} onClick={() => setSoftness(v => Math.min(100, v + 10))}>+</button>
      </div>
      <div className="curve-scroll">
      <svg ref={svgRef} className="curve-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={mode === 'count' ? t.titleCount : t.titlePoints}
        onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} onPointerLeave={() => { if (!drag.current) setHover(null) }}>
        {grid.map(v => (
          <g key={v}>
            <line x1={ML} x2={W - MR} y1={yOf(v)} y2={yOf(v)} className="curve-grid" />
            <text x={ML - 8} y={yOf(v) + 5} textAnchor="end" className="curve-axis">{Math.round(v * 100) / 100}</text>
          </g>
        ))}
        {[100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600].map(h => (
          <g key={h}>
            <line x1={xOf(h)} x2={xOf(h)} y1={H - MB} y2={H - MB + 7} className="curve-tick" />
            <text x={xOf(h)} y={H - MB + 25} textAnchor="middle" className="curve-axis">{h}</text>
          </g>
        ))}
        <text x={(ML + W - MR) / 2} y={H - 8} textAnchor="middle" className="curve-axis-title">{t.axisX}</text>
        <text x={ML} y={MT - 3} className="curve-axis-title">{mode === 'count' ? t.axisYCount : t.axisYPoints}</text>

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
              <rect x={x - 24} y={y - 30} width="48" height="60" className="curve-hit" />
              <rect x={x - 11} y={y - 15} width="22" height="30" rx="4" className="curve-cap"
                style={{ fill: `color-mix(in srgb, ${sel.color} 42%, #0f1626)`, stroke: sel.color }} />
              <line x1={x - 7} x2={x + 7} y1={y} y2={y} stroke={`color-mix(in srgb, ${sel.color} 35%, #ffffff)`} strokeWidth="3" strokeLinecap="round" />
              <text x={x} y={y > MT + 46 ? y - 21 : y + 36} textAnchor="middle" className="curve-val">{sel.cur[i]}</text>
            </g>
          )
        })}
      </svg>
      </div>
      </div>

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
        <button type="button" className="chest-pill-btn" title={t.resetTip} disabled={!canEdit || !dirty} onClick={() => onBands(sel, {})}>{t.reset}</button>
      </div>
      {footer && (
        <div className="curve-footer">
          {footer}
          <button type="button" className="chest-pill-btn" disabled={disabled || !hasLines} onClick={onResetAll}>{t.resetAll}</button>
        </div>
      )}
      {note && <p className="pult-flash">{note}</p>}
    </div>
  )
}
