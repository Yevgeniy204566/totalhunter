import { useEffect, useMemo, useRef, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['', '5', '6', '7', '8', '9']
const FULL_TROOP = 'G8 S8 M8'

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

function fmtNum(n) {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('ru-RU')
}

function hexToRgb(hex) {
  const s = hex.replace('#', '')
  const full = s.length === 3 ? s.split('').map(c => c + c).join('') : s
  const n = parseInt(full, 16)
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}
function rgbToHex({ r, g, b }) {
  return '#' + [r, g, b].map(v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('')
}
function lerpColor(hexA, hexB, t) {
  const a = hexToRgb(hexA), b = hexToRgb(hexB)
  return rgbToHex({ r: a.r + (b.r - a.r) * t, g: a.g + (b.g - a.g) * t, b: a.b + (b.b - a.b) * t })
}
function multiLerp(stops, t) {
  const n = stops.length - 1
  const clamped = Math.max(0, Math.min(1, t))
  const scaled = clamped * n
  const idx = Math.min(Math.floor(scaled), n - 1)
  return lerpColor(stops[idx], stops[idx + 1], scaled - idx)
}
function darkenHex(hex, factor) {
  const { r, g, b } = hexToRgb(hex)
  return rgbToHex({ r: r * factor, g: g * factor, b: b * factor })
}
function hslToHex(h, s, l) {
  s /= 100; l /= 100
  const k = n => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  return rgbToHex({ r: 255 * f(0), g: 255 * f(8), b: 255 * f(4) })
}

// 0 → квота: красный → оранжевый (зелёный убран — сливался с зоной после квоты)
const BELOW_QUOTA_STOPS = ['#C81E3A', '#C9862E']
// квота → квота+100к: ярко-зелёный (салатовый) → жёлтый
const ABOVE_QUOTA_STOPS = ['#39FF6A', '#FFD700']
const LEGENDARY_OVERAGE = 100000
// легендарный: число цветов растёт каждые 100к превышения (макс. 6), оттенки едут непрерывно
const LEGENDARY_BAND_SIZE = 100000
const LEGENDARY_MAX_COLORS = 6

function legendaryPalette(overageBeyond) {
  const band = Math.floor(overageBeyond / LEGENDARY_BAND_SIZE)
  const numColors = Math.min(band + 1, LEGENDARY_MAX_COLORS)
  const baseHue = (overageBeyond / 1000) % 360
  const colors = []
  for (let i = 0; i < numColors; i++) {
    const hue = (baseHue + i * (360 / numColors)) % 360
    colors.push(hslToHex(hue, 88, 56))
  }
  return colors
}
function legendaryGradient(colors) {
  if (colors.length === 1) {
    const c = colors[0]
    return `linear-gradient(100deg, ${c} 0%, ${c} 38%, #FFFFFF 50%, ${c} 62%, ${c} 100%)`
  }
  const stops = colors.map((c, i) => `${c} ${(i / colors.length * 100).toFixed(1)}%`)
  stops.push(`${colors[0]} 100%`)
  return `linear-gradient(100deg, ${stops.join(', ')})`
}

function nameGradientStyle(player, targets) {
  const quota = targets?.points
  if (!quota) return null
  const ratio = player.points / quota
  if (ratio < 1) {
    const color = multiLerp(BELOW_QUOTA_STOPS, ratio)
    return { mode: 'plain', color, stroke: darkenHex(color, 0.45), fontSize: 14.5 }
  }
  const overage = player.points - quota
  if (overage < LEGENDARY_OVERAGE) {
    const t = overage / LEGENDARY_OVERAGE
    const color = multiLerp(ABOVE_QUOTA_STOPS, t)
    return { mode: 'shimmer', color, stroke: darkenHex(color, 0.55), fontSize: 14.5 + t * 3 }
  }
  const extra = overage - LEGENDARY_OVERAGE
  const band = Math.floor(extra / LEGENDARY_BAND_SIZE)
  const colors = legendaryPalette(extra)
  const fontSize = 19 + Math.min(band, 5) * 0.4
  return { mode: 'legendary', backgroundImage: legendaryGradient(colors), fontSize }
}

function renderPlayerName(p, targets) {
  const s = nameGradientStyle(p, targets)
  if (!s) return p.name
  if (s.mode === 'legendary') {
    return (
      <span
        className="public-name-legendary"
        style={{ backgroundImage: s.backgroundImage, fontSize: s.fontSize }}
      >
        {p.name}
      </span>
    )
  }
  if (s.mode === 'shimmer') {
    return (
      <span
        className="public-name-shimmer"
        style={{
          backgroundImage: `linear-gradient(100deg, ${s.color} 0%, ${s.color} 38%, #FFFFFF 50%, ${s.color} 62%, ${s.color} 100%)`,
          WebkitTextStroke: `0.3px ${s.stroke}`,
          fontSize: s.fontSize,
        }}
      >
        {p.name}
      </span>
    )
  }
  return (
    <span style={{ color: s.color, WebkitTextStroke: `0.35px ${s.stroke}`, fontWeight: 700, fontSize: s.fontSize }}>
      {p.name}
    </span>
  )
}

function pointsHitTarget(player, targets) {
  return targets.points != null && player.points >= targets.points
}
// Столбцы квот (владелец 2026-09-26): по одному на квоту из targets.quotas; архив, закрытый
// до квот (нет targets.quotas), — прежний один столбец «Epic-склепы» из quota_chests.
export function quotaColumns(targets, epicLabel) {
  if (Array.isArray(targets?.quotas)) {
    return targets.quotas.map(q => ({
      key: `quota:${q.slot}`, name: q.name, target: q.target,
      personal: q.mode === 'per_player',
      get: p => p.quotas?.[String(q.slot)] ?? 0,
      // личная цель игрока (per_player): считает сервер по уровню Героя
      targetOf: p => (q.mode === 'per_player' ? p.quota_targets?.[String(q.slot)] : q.target),
      partialOf: p => !!p.quota_targets_partial?.[String(q.slot)],
    }))
  }
  return [{ key: 'quota:legacy', name: epicLabel, target: targets?.chests ?? null,
            get: p => p.quota_chests ?? 0 }]
}
function isEpicColumn(typeName) {
  return typeName.includes('Epic')
}

// Среднее по участникам таблицы (входящие п.5): сумма столбца / число игроков в таблице,
// нули входят в расчёт; от сортировки не зависит.
export function columnAverage(players, getValue) {
  if (!players.length) return 0
  return players.reduce((sum, p) => sum + (getValue(p) || 0), 0) / players.length
}

export function sortPlayers(players, sort, chestTypes, quotaCols = []) {
  const qcol = quotaCols.find(c => c.key === sort.key)
  const value = p => sort.key === 'name' ? p.name.toLowerCase()
    : sort.key === 'points' ? p.points
    : qcol ? qcol.get(p)
    : (p.counts[sort.key] || 0)
  const dir = sort.dir === 'asc' ? 1 : -1
  return [...players].sort((a, b) => {
    const va = value(a), vb = value(b)
    if (va < vb) return -dir
    if (va > vb) return dir
    return b.points - a.points || a.name.localeCompare(b.name)
  })
}

const TABLE_TXT = {
  ru: { player: 'Игрок', points: 'Очки', epic: 'Epic-склепы', avg: 'Среднее', rank: 'Звание', troops: 'Состав', hero: 'Герой',
        hideAvg: 'Скрыть средние', showAvg: 'Показать средние', saveError: 'Ошибка сохранения: ' },
  en: { player: 'Player', points: 'Points', epic: 'Epic Crypts', avg: 'Average', rank: 'Rank', troops: 'Troops', hero: 'Hero',
        hideAvg: 'Hide averages', showAvg: 'Show averages', saveError: 'Save error: ' },
}

export default function ChestSummaryTable({ chestTypes, players, targets, editMode = false, collectorSlug, lang = 'en' }) {
  const tt = TABLE_TXT[lang] || TABLE_TXT.en
  const quotaCols = useMemo(() => quotaColumns(targets, tt.epic), [targets, tt.epic])
  // По умолчанию — порядок сервера (по очкам). «#» всегда место по очкам, не по текущей сортировке.
  const [sort, setSort] = useState(null)
  const pointsRank = useMemo(() => {
    const m = {}
    players.forEach((p, i) => { m[p.name] = i + 1 })
    return m
  }, [players])
  const shownPlayers = useMemo(
    () => (sort ? sortPlayers(players, sort, chestTypes, quotaCols) : players),
    [players, sort, chestTypes, quotaCols],
  )
  function toggleSort(key) {
    setSort(prev => {
      const firstDir = key === 'name' ? 'asc' : 'desc'
      if (!prev || prev.key !== key) return { key, dir: firstDir }
      return { key, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
    })
  }
  function sortMark(key) {
    if (!sort || sort.key !== key) return <span className="public-sort-mark"> ⇅</span>
    return <span className="public-sort-mark public-sort-mark--on">{sort.dir === 'desc' ? ' ▼' : ' ▲'}</span>
  }
  const fmtAvg = v => v.toFixed(1)
  // Строку средних можно скрыть (владелец 2026-09-26); выбор помнится в этом браузере.
  const [showAvg, setShowAvg] = useState(() => {
    try { return localStorage.getItem('chestShowAvg') !== '0' } catch { return true }
  })
  function toggleAvg() {
    setShowAvg(v => {
      try { localStorage.setItem('chestShowAvg', v ? '0' : '1') } catch { /* приватный режим */ }
      return !v
    })
  }

  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [chestTypes, players])

  const [editRows, setEditRows] = useState({})
  const [saving, setSaving] = useState(null)
  const [savedRows, setSavedRows] = useState({})

  useEffect(() => {
    if (!editMode) return
    const init = {}
    players.forEach(p => {
      const { g, s, m } = parseTroop(p.troop_level)
      init[p.name] = { rank: p.rank || '', g, s, m, hero: p.hero_level ?? '' }
    })
    setEditRows(init)
  }, [editMode, players])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    const troop = row.g && row.s && row.m ? `G${row.g} S${row.s} M${row.m}` : null
    setSaving(playerName)
    try {
      const hero = Number(row.hero) || null   // пусто/0 → не задан
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, troop, hero)
      setSavedRows(prev => ({ ...prev, [playerName]: true }))
      setTimeout(() => setSavedRows(prev => { const n = { ...prev }; delete n[playerName]; return n }), 3000)
    } catch (e) {
      alert(tt.saveError + e.message)
    } finally {
      setSaving(null)
    }
  }

  function syncTableFromTopScroll() {
    if (tableWrapRef.current && topScrollRef.current) {
      tableWrapRef.current.scrollLeft = topScrollRef.current.scrollLeft
    }
  }
  function syncTopScrollFromTable() {
    if (tableWrapRef.current && topScrollRef.current) {
      topScrollRef.current.scrollLeft = tableWrapRef.current.scrollLeft
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '0 0 6px' }}>
        <button type="button" className="public-avg-toggle" onClick={toggleAvg}>
          {showAvg ? tt.hideAvg : tt.showAvg}
        </button>
      </div>
      <div
        className="public-table-top-scroll"
        ref={topScrollRef}
        onScroll={syncTableFromTopScroll}
      >
        <div style={{ width: tableScrollWidth, height: 1 }} />
      </div>

      <div className="public-table-wrap" ref={tableWrapRef} onScroll={syncTopScrollFromTable}>
        <table className="public-table">
          <thead>
            {showAvg && <tr className="public-avg-row">
              <th></th>
              <th>{tt.avg}</th>
              {editMode && <th></th>}
              {editMode && <th></th>}
              {editMode && <th></th>}
              <th></th>
              {quotaCols.map(c => (
                <th key={c.key} className="public-epic-cell">{fmtAvg(columnAverage(players, c.get))}</th>
              ))}
              {chestTypes.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>
                  {fmtAvg(columnAverage(players, p => p.counts[t]))}
                </th>
              ))}
            </tr>}
            <tr className={showAvg ? 'public-head-row' : ''}>
              <th>#</th>
              <th className="public-sortable" onClick={() => toggleSort('name')}>{tt.player}{sortMark('name')}</th>
              {editMode && <th>{tt.rank}</th>}
              {editMode && <th>{tt.troops}</th>}
              {editMode && <th></th>}
              <th className="public-sortable" onClick={() => toggleSort('points')}>{tt.points}{sortMark('points')}</th>
              {quotaCols.map(c => (
                <th key={c.key} className="public-epic-cell public-sortable" onClick={() => toggleSort(c.key)}>
                  <span translate="no" className="notranslate">{c.name}</span>
                  {c.target != null && !c.personal && <span style={{ opacity: 0.6 }}> /{c.target}</span>}
                  {sortMark(c.key)}
                </th>
              ))}
              {chestTypes.map(t => (
                <th key={t} className={`${isEpicColumn(t) ? 'public-epic-cell ' : ''}public-sortable`}
                    onClick={() => toggleSort(t)}>
                  <span translate="no" className="notranslate">{t}</span>{sortMark(t)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shownPlayers.map(p => {
              return (
                <tr key={p.name}>
                  <td>{pointsRank[p.name]}</td>
                  <td title={p.name} translate="no" className="notranslate">
                    {renderPlayerName(p, targets)}
                  </td>
                  {editMode && (
                    <td>
                      <select
                        value={editRows[p.name]?.rank || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.name]: { ...prev[p.name], rank: e.target.value },
                        }))}
                        style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                      </select>
                    </td>
                  )}
                  {editMode && (
                    <td>
                      <div style={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'nowrap' }}>
                        {['g', 's', 'm'].map((k, idx) => (
                          <select
                            key={k}
                            value={editRows[p.name]?.[k] || ''}
                            onChange={e => setEditRows(prev => ({
                              ...prev,
                              [p.name]: { ...prev[p.name], [k]: e.target.value },
                            }))}
                            style={{ fontSize: 11, padding: '2px 2px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4, width: 36 }}
                          >
                            <option value="">{'GSM'[idx]}</option>
                            {TIERS.slice(1).map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                        ))}
                        {(() => {
                          const { g, s, m } = editRows[p.name] || {}
                          if (!g || !s || !m) return null
                          const val = `G${g} S${s} M${m}`
                          return (
                            <span style={val === FULL_TROOP
                              ? { fontSize: 11, color: '#f9a825', fontWeight: 700, marginLeft: 2 }
                              : { fontSize: 11, color: '#6c7086', marginLeft: 2 }}>
                              {val}
                            </span>
                          )
                        })()}
                        {/* уровень Героя — задел для квоты EM */}
                        <input type="number" min={1} max={999} placeholder={tt.hero}
                          value={editRows[p.name]?.hero ?? ''}
                          onChange={e => setEditRows(prev => ({
                            ...prev,
                            [p.name]: { ...prev[p.name], hero: e.target.value.replace(/\D/g, '').slice(0, 3) },
                          }))}
                          style={{ width: 62, fontSize: 11, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4, marginLeft: 4 }} />
                      </div>
                    </td>
                  )}
                  {editMode && (
                    <td>
                      <button
                        onClick={() => handleSave(p.name)}
                        disabled={saving === p.name}
                        style={{ fontSize: 12, padding: '2px 8px', cursor: 'pointer',
                          background: savedRows[p.name] ? '#1e3a1e' : '#313244',
                          color: savedRows[p.name] ? '#a6e3a1' : '#cdd6f4',
                          border: `1px solid ${savedRows[p.name] ? '#a6e3a1' : '#45475a'}`, borderRadius: 4 }}
                      >
                        {saving === p.name ? '...' : savedRows[p.name] ? '✓' : '💾'}
                      </button>
                    </td>
                  )}
                  <td className={`public-points-cell ${pointsHitTarget(p, targets) ? 'public-cell-hit-target' : ''}`}>
                    {fmtNum(p.points)}
                  </td>
                  {quotaCols.map(c => {
                    const v = c.get(p)
                    if (c.personal) {
                      // Личная цель EM (владелец 2026-09-26): прогресс-бар, % выполнения,
                      // цвет от красного (0%) к зелёному (100%+).
                      const tgt = c.targetOf(p)
                      const pct = tgt ? Math.round((v / tgt) * 100) : (v > 0 ? 100 : 0)
                      const fill = Math.min(pct, 100)
                      return (
                        <td key={c.key} className="public-epic-cell" style={{ minWidth: 120 }}
                            title={c.partialOf(p) ? '?' : ''}>
                          <div style={{ fontSize: 12, marginBottom: 3, whiteSpace: 'nowrap' }}>
                            {v}/{tgt ?? '—'}{c.partialOf(p) ? ' ?' : ''} · <b>{pct}%</b>
                          </div>
                          <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                            {/* градиент на всю шкалу: видна его часть до текущего процента */}
                            <div style={{ width: `${fill}%`, height: '100%', borderRadius: 3, transition: 'width 0.4s',
                                          background: 'linear-gradient(90deg, #ef4444, #f59e0b, #22c55e)',
                                          backgroundSize: `${fill ? 10000 / fill : 100}% 100%` }} />
                          </div>
                        </td>
                      )
                    }
                    return (
                      <td key={c.key} className={[
                        'public-epic-cell',
                        c.target != null && v >= c.target && 'public-cell-hit-target',
                        v === 0 && 'public-cell-zero',
                      ].filter(Boolean).join(' ')}>
                        {v}
                      </td>
                    )
                  })}
                  {chestTypes.map(t => {
                    const value = p.counts[t] || 0
                    return (
                      <td key={t} className={[
                        isEpicColumn(t) && 'public-epic-cell',
                        value === 0 && 'public-cell-zero',
                      ].filter(Boolean).join(' ')}>
                        {value}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
