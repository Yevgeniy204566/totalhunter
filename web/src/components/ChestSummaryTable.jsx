import { useEffect, useRef, useState } from 'react'
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

// 0 → квота: рубин → бронза → сапфир → изумруд (насыщенные, "ювелирные" тона)
const BELOW_QUOTA_STOPS = ['#C81E3A', '#C9862E', '#1E6FE0', '#0FA968']
// квота → квота+100к: ярко-зелёный (салатовый) → жёлтый
const ABOVE_QUOTA_STOPS = ['#39FF6A', '#FFD700']
const LEGENDARY_OVERAGE = 100000

function nameGradientStyle(player, targets) {
  const quota = targets?.points
  if (!quota) return null
  const ratio = player.points / quota
  if (ratio < 1) {
    const color = multiLerp(BELOW_QUOTA_STOPS, ratio)
    return { mode: 'plain', color, stroke: darkenHex(color, 0.45), fontSize: 13 + ratio * 1.5 }
  }
  const overage = player.points - quota
  if (overage < LEGENDARY_OVERAGE) {
    const t = overage / LEGENDARY_OVERAGE
    const color = multiLerp(ABOVE_QUOTA_STOPS, t)
    return { mode: 'shimmer', color, stroke: darkenHex(color, 0.55), fontSize: 14.5 + t * 3 }
  }
  return { mode: 'legendary' }
}

function renderPlayerName(p, targets) {
  const s = nameGradientStyle(p, targets)
  if (!s) return p.name
  if (s.mode === 'legendary') return <span className="public-name-legendary">{p.name}</span>
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
function questHitTarget(player, targets) {
  return targets.chests != null && player.quota_chests >= targets.chests
}
function isEpicColumn(typeName) {
  return typeName.includes('Epic')
}

export default function ChestSummaryTable({ chestTypes, players, targets, editMode = false, collectorSlug }) {
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
      init[p.name] = { rank: p.rank || '', g, s, m }
    })
    setEditRows(init)
  }, [editMode, players])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    const troop = row.g && row.s && row.m ? `G${row.g} S${row.s} M${row.m}` : null
    setSaving(playerName)
    try {
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, troop)
      setSavedRows(prev => ({ ...prev, [playerName]: true }))
      setTimeout(() => setSavedRows(prev => { const n = { ...prev }; delete n[playerName]; return n }), 3000)
    } catch (e) {
      alert('Ошибка сохранения: ' + e.message)
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
            <tr>
              <th>#</th>
              <th>Player</th>
              {editMode && <th>Звание</th>}
              {editMode && <th>Состав</th>}
              {editMode && <th></th>}
              <th>Points</th>
              <th className="public-epic-cell">Epic Crypts</th>
              {chestTypes.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {players.map((p, i) => {
              return (
                <tr key={p.name}>
                  <td>{i + 1}</td>
                  <td title={p.name}>
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
                  <td className={[
                    'public-epic-cell',
                    questHitTarget(p, targets) && 'public-cell-hit-target',
                    p.quota_chests === 0 && 'public-cell-zero',
                  ].filter(Boolean).join(' ')}>
                    {p.quota_chests}
                  </td>
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
