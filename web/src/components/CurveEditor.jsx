import { useMemo, useRef, useState } from 'react'
import { BANDS, HANDLE_BANDS, DECADE_PTS, levelPts, applyDrag, bandsFromTargets, bandsOutOfRange } from '../lib/curveEdit.js'

// Кривая по уровням Героя (владелец 2026-10-26): как EQ в цифровом пульте — тянешь ручку, соседние точки плавно идут
// следом. Режим «Очки» — очки за сундук, «Количество» — штуки на игрока. Правит одну линию за раз; линии готовит
// lib/curveLines.js, хранение прежнее (поправки ступеней), график показывает числа.

const TXT = {
  ru: {
    titlePoints: 'Очки за сундук по уровням Героя', titleCount: 'Количество сундуков по уровням Героя',
    hintPoints: 'Выберите сундук внизу и тяните квадратные ручки вверх-вниз — соседние уровни идут следом. «Захват» задаёт, сколько уровней ручка тянет за собой, а «Приближение» растягивает график до одного уровня Героя: там у каждого уровня своя ручка. Пунктир — шкала по умолчанию (рядом с ним ручка «прилипает»), закрашено — ваше отличие.',
    zoom: 'Захват', zoomIn: 'Ручка тянет за собой больше соседних уровней', zoomOut: 'Ручка тянет за собой меньше соседних уровней (в минимуме — одна ступень)',
    zoomView: 'Приближение', viewIn: 'Приблизить график по оси Героя', viewOut: 'Отдалить график по оси Героя', viewPan: 'Сдвинуть окно графика по уровням Героя', viewAll: 'Весь график 100–600', levels: 'Герои',
    reset: 'Сброс', resetTip: 'Вернуть выбранную линию на всех уровнях к шкале',
    resetAll: 'Сбросить все линии',
    outOfRange: 'Такое значение записать нельзя: оно выходит за границы хранения (множитель 0,01…1000). Ничего не изменено.',
    hero: 'Герой', points: 'очков', count: 'шт.', scale: 'по шкале', muted: 'Тип выключен кнопкой — включите его, чтобы править линию.',
    locked: 'В шкале на этом уровне 0 — поднять нельзя.', off: 'Включите «Персонализированный учёт», чтобы править линии.',
    axisX: 'Уровень Героя', axisYPoints: 'Очки за сундук', axisYCount: 'Штук на игрока',
    none: 'Для этого пульта на графике нечего показывать: у типов нет значений по уровням Героя.', pick: 'Выбранный сундук',
  },
  en: {
    titlePoints: 'Chest points by Hero level', titleCount: 'Chest count by Hero level',
    hintPoints: 'Pick a chest below and drag the square handles up and down — neighbouring levels follow. “Reach” sets how many levels a handle pulls along; “Zoom” stretches the chart down to a single Hero level, where every level has its own handle. Dashed — the default scale (a handle snaps onto it), filled — your difference.',
    zoom: 'Reach', zoomIn: 'A handle pulls more neighbouring levels along', zoomOut: 'A handle pulls fewer neighbouring levels along (at the minimum — one step)',
    zoomView: 'Zoom', viewIn: 'Zoom the chart in along the Hero axis', viewOut: 'Zoom the chart out along the Hero axis', viewPan: 'Move the chart window along Hero levels', viewAll: 'Whole chart 100–600', levels: 'Heroes',
    reset: 'Reset', resetTip: 'Return the selected line to the scale on all levels',
    resetAll: 'Reset all lines',
    outOfRange: 'This value cannot be stored: it is out of bounds (multiplier 0.01…1000). Nothing was changed.',
    hero: 'Hero', points: 'points', count: 'pcs', scale: 'by scale', muted: 'This type is switched off — turn it on to edit the line.',
    locked: 'The scale gives 0 at this level — it cannot be raised.', off: 'Turn on "Personalized accounting" to edit the lines.',
    axisX: 'Hero level', axisYPoints: 'Points per chest', axisYCount: 'Pieces per player',
    none: 'Nothing to draw for this console: the types have no values by Hero level.', pick: 'Selected chest',
  },
}

const COLORS = ['#a78bfa', '#f59e0b', '#38bdf8', '#4ade80', '#f472b6', '#fb923c', '#22d3ee', '#facc15', '#c084fc', '#34d399', '#f87171', '#94a3b8']

const W = 1000, H = 400, ML = 58, MR = 16, MT = 16, MB = 62
// окна приближения по оси Героя: весь график (по ступеням) и до одного уровня (500 → 100 → 50 → 25 → 10 уровней в окне)
const SPANS = [500, 100, 50, 25, 10]
// верх оси — ближайшее «круглое» число с запасом 30%; линий сетки всегда пять
const NICE = [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 125, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1500, 2000, 3000, 5000, 10000]
const niceMax = v => NICE.find(n => n >= v * 1.3) ?? Math.ceil(v * 1.3 / 1000) * 1000

export default function CurveEditor({ lang = 'ru', mode = 'points', lines = [], disabled = false, onBands, onResetAll, hasLines = false, footer = null, note = '', onReject = null }) {
  const t = TXT[lang] || TXT.ru
  const [selKey, setSelKey] = useState(null)
  const [softness, setSoftness] = useState(40)
  const [hover, setHover] = useState(null) // уровень Героя под курсором
  const [spanIdx, setSpanIdx] = useState(0)
  const [lo0, setLo] = useState(100)
  const drag = useRef(null)
  const svgRef = useRef(null)
  const unitWord = mode === 'count' ? t.count : t.points

  const span = SPANS[spanIdx]
  const lo = Math.min(600 - span, Math.max(100, lo0)), hi = lo + span
  const fine = span <= 50 // приближено до уровня: точка и ручка на каждый уровень Героя, поправки пишутся ключом «L405»
  const xOf = h => ML + (h - lo) / (hi - lo) * (W - ML - MR)

  const series = useMemo(() => lines.map((x, i) => ({ ...x, color: COLORS[i % COLORS.length] })), [lines])
  const sel0 = series.find(x => x.key === selKey) || series[0]
  const pts = useMemo(() => (fine ? levelPts(lo, hi) : DECADE_PTS), [fine, lo, hi])
  // одна линия на тех же функциях, что читают пульт и страница: в приближении — по уровню на точку
  const view = useMemo(() => (sel0 ? (fine ? { ...sel0, ...sel0.rebuild(pts) } : sel0) : null), [sel0, fine, pts])
  const levels = useMemo(() => Array.from({ length: hi - lo + 1 }, (_, i) => lo + i), [lo, hi])
  const curArr = useMemo(() => (view ? levels.map(h => view.curAt(h)) : []), [view, levels])
  const baseArr = useMemo(() => (view ? levels.map(h => view.baseAt(h)) : []), [view, levels])
  if (!series.length) return <p className="emc-text"><small>{t.none}</small></p>

  const sel = view
  // ось Y не прыгает во время перетаскивания
  const ymax = drag.current?.ymax ?? niceMax(Math.max(...sel0.cur, ...sel0.base, ...curArr, ...baseArr, 1))
  const yOf = v => MT + (1 - Math.min(v, ymax) / ymax) * (H - MT - MB)
  const canEdit = !disabled && !sel.muted

  const pathOf = vals => vals.map((v, i) => `${i ? 'L' : 'M'}${xOf(levels[i]).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')
  const areaOf = (a, b) => `${pathOf(a)} ${[...b].map((v, i) => [v, i]).reverse().map(([v, i]) => `L${xOf(levels[i]).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')} Z`

  const commit = (handlePos, start, delta, existing) => {
    const target = applyDrag(start, handlePos, delta, softness, sel.locked, pts)
    const changed = target.map((v, i) => Math.abs(v - start[i]) > 1e-9)
    // значение за границами множителя (0…1000) вписать нельзя: правка не применяется и сказано почему, ничего не обрезается молча
    if (bandsOutOfRange(target, sel.ref, changed, sel.zero)) { onReject?.(t.outOfRange); return }
    onBands(sel0, bandsFromTargets(target, sel.ref, existing, changed, sel.zero, pts))
  }

  const pointerValue = e => {
    const r = svgRef.current.getBoundingClientRect()
    const y = (e.clientY - r.top) / r.height * H
    return Math.max(0, (1 - (y - MT) / (H - MT - MB)) * drag.current.ymax)
  }

  const onDown = (pt, i) => e => {
    if (!canEdit || sel.locked.has(pt.pos)) return
    e.preventDefault()
    svgRef.current.setPointerCapture(e.pointerId)
    drag.current = { pos: pt.pos, start: [...sel.cont], existing: { ...sel.bands }, ymax, v0: sel.cont[i], scaleV: sel.scaleV?.[i] ?? sel.ref[i] }
  }
  const onMove = e => {
    const d = drag.current
    const r = svgRef.current.getBoundingClientRect()
    const hero = lo + ((e.clientX - r.left) / r.width * W - ML) / (W - ML - MR) * (hi - lo)
    setHover(Math.min(hi, Math.max(lo, Math.round(hero))))
    if (!d) return
    // магнит к шкале: когда ручка показывает то же число, что и шкала (значения целые), она встаёт ровно на значение шкалы —
    // так линию можно вернуть в исходное без следа в данных
    let v = pointerValue(e)
    if (Math.round(v) === Math.round(d.scaleV) || Math.abs(v - d.scaleV) < Math.max(0.5, d.ymax * 0.02)) v = d.scaleV
    commit(d.pos, d.start, v - d.v0, d.existing)
  }
  const onUp = () => { drag.current = null }
  const onKey = (pt, i) => e => {
    if (!canEdit || sel.locked.has(pt.pos)) return
    const step = e.shiftKey ? 5 : 1
    const delta = e.key === 'ArrowUp' ? step : e.key === 'ArrowDown' ? -step : 0
    if (!delta) return
    e.preventDefault()
    commit(pt.pos, [...sel.cont], delta, { ...sel.bands })
  }

  const hv = hover ?? Math.min(hi, Math.max(lo, 400))
  const readout = `${t.hero} ${hv}: ${sel.title} — ${sel.curAt(hv)} ${unitWord} (${t.scale} ${sel.baseAt(hv)})`
  const gridStep = ymax / 5
  const grid = [0, 1, 2, 3, 4, 5].map(k => k * gridStep)
  const dirty = Object.keys(sel.bands || {}).length > 0
  const tickStep = span >= 300 ? 50 : span >= 80 ? 10 : span > 25 ? 5 : 1
  const ticks = []
  for (let h = Math.ceil(lo / tickStep) * tickStep; h <= hi; h += tickStep) ticks.push(h)
  // ручки: обзор — через 50 уровней, окно в 100 — по ступени, приближение — на каждый уровень
  const handleIdx = pts.map((pt, i) => i).filter(i => pts[i].h >= lo && pts[i].h <= hi && (fine || span === 100 || HANDLE_BANDS.includes(pts[i].pos)))
  const zoomTo = idx => {
    const c = hover ?? lo + (hi - lo) / 2
    const sp = SPANS[idx]
    setSpanIdx(idx)
    setLo(Math.min(600 - sp, Math.max(100, Math.round(c - sp / 2))))
  }

  return (
    <div className={`curve${disabled ? ' curve--off' : ''}`}>
      <h4 className="curve-title">{mode === 'count' ? t.titleCount : t.titlePoints}</h4>
      <p className="curve-hint">{t.hintPoints}</p>
      {disabled && <p className="emc-text"><small>{t.off}</small></p>}

      <div className="curve-viewbar" role="group" aria-label={t.zoomView}>
        <span>{t.zoomView}</span>
        <button type="button" title={t.viewOut} aria-label={`${t.zoomView} −`} disabled={spanIdx <= 0} onClick={() => zoomTo(spanIdx - 1)}>−</button>
        <button type="button" title={t.viewIn} aria-label={`${t.zoomView} +`} disabled={spanIdx >= SPANS.length - 1} onClick={() => zoomTo(spanIdx + 1)}>+</button>
        <span className="curve-viewrange">{t.levels} {lo}–{hi}</span>
        {span < 500 && (
          <input type="range" className="curve-zoom-strip" min={100} max={600 - span} step={1} value={lo} aria-label={t.viewPan}
            title={t.viewPan} style={{ '--p': `${(lo - 100) / (500 - span) * 100}%` }} onChange={e => setLo(Number(e.target.value))} />
        )}
        {span < 500 && <button type="button" className="chest-pill-btn" onClick={() => { setSpanIdx(0); setLo(100) }}>{t.viewAll}</button>}
      </div>

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
        {ticks.map(h => (
          <g key={h}>
            <line x1={xOf(h)} x2={xOf(h)} y1={H - MB} y2={H - MB + 7} className="curve-tick" />
            <text x={xOf(h)} y={H - MB + 25} textAnchor="middle" className="curve-axis">{h}</text>
          </g>
        ))}
        <text x={(ML + W - MR) / 2} y={H - 8} textAnchor="middle" className="curve-axis-title">{t.axisX}</text>
        <text x={ML} y={MT - 3} className="curve-axis-title">{mode === 'count' ? t.axisYCount : t.axisYPoints}</text>

        <path d={areaOf(curArr, baseArr)} fill={sel.color} opacity="0.2" />
        <path d={pathOf(baseArr)} fill="none" stroke="#e5e7eb" strokeWidth="2" strokeDasharray="7 6" opacity="0.7" />
        <path d={pathOf(curArr)} fill="none" stroke={sel.color} strokeWidth="4.5" strokeLinejoin="round" opacity={sel.muted ? 0.35 : 1} />

        {hover != null && (
          <line x1={xOf(hover)} x2={xOf(hover)} y1={MT} y2={H - MB} className="curve-cross" />
        )}

        {handleIdx.map(i => {
          const pt = pts[i]
          const locked = sel.locked.has(pt.pos)
          const x = xOf(pt.h), y = yOf(sel.cur[i])
          const narrow = fine && span > 25 // на 50 уровнях ручки стоят часто — уже
          return (
            <g key={pt.key} className={`curve-handle${locked ? ' curve-handle--locked' : ''}`} style={{ touchAction: 'none' }}
              tabIndex={canEdit && !locked ? 0 : -1} role="slider" aria-label={`${t.hero} ${pt.h}`} aria-valuemin={0} aria-valuemax={Math.round(ymax)}
              aria-valuenow={sel.cur[i]} onPointerDown={onDown(pt, i)} onKeyDown={onKey(pt, i)}>
              <title>{locked ? t.locked : `${t.hero} ${pt.h}: ${sel.cur[i]}`}</title>
              <rect x={x - (narrow ? 9 : 24)} y={y - 30} width={narrow ? 18 : 48} height="60" className="curve-hit" />
              <rect x={x - (narrow ? 7 : 11)} y={y - 15} width={narrow ? 14 : 22} height="30" rx="4" className="curve-cap"
                style={{ fill: `color-mix(in srgb, ${sel.color} 42%, #0f1626)`, stroke: sel.color }} />
              <line x1={x - (narrow ? 4 : 7)} x2={x + (narrow ? 4 : 7)} y1={y} y2={y} stroke={`color-mix(in srgb, ${sel.color} 35%, #ffffff)`} strokeWidth="3" strokeLinecap="round" />
              {(!narrow || i % 5 === 0) && <text x={x} y={y > MT + 46 ? y - 21 : y + 36} textAnchor="middle" className="curve-val">{sel.cur[i]}</text>}
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
