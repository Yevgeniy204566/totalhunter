import { useEffect, useRef, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['', '1', '2', '3', '4', '5', '6', '7', '8', '9']
const FULL_TROOP = 'G8 S8 M8'

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

function rowColorClass(player, targets) {
  const ratios = []
  if (targets.points) ratios.push(player.points / targets.points)
  if (targets.chests) ratios.push(player.quota_chests / targets.chests)
  if (ratios.length === 0) return ''
  const ratio = Math.min(...ratios)
  if (ratio >= 1) return 'row-success'
  if (ratio >= 0.5) return ''
  if (ratio > 0) return 'row-lagging'
  return 'row-danger'
}

const POINT_TIERS = [
  { key: '500k', threshold: 500000 },
  { key: '400k', threshold: 400000 },
  { key: '300k', threshold: 300000 },
  { key: '200k', threshold: 200000 },
  { key: '100k', threshold: 100000 },
  { key: '50k', threshold: 50000 },
]

function pointTier(player, targets) {
  if (rowColorClass(player, targets) !== 'row-success') return null
  const tier = POINT_TIERS.find(t => player.points >= t.threshold)
  return tier ? tier.key : null
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

export default function ChestSummaryTable({ chestTypes, players, targets, editMode = false, collectorSlug, onSaveDone }) {
  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [chestTypes, players])

  const [editRows, setEditRows] = useState({})
  const [saving, setSaving] = useState(null)

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
      if (onSaveDone) onSaveDone()
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
              <th>Звание</th>
              <th>Состав</th>
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
              const tier = pointTier(p, targets)
              return (
                <tr key={p.name} className={rowColorClass(p, targets)}>
                  <td>{i + 1}</td>
                  <td title={p.name}>
                    {tier
                      ? <span className={`public-tier-name public-tier-${tier}`}>{p.name}</span>
                      : p.name}
                  </td>
                  <td>
                    {editMode ? (
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
                    ) : (
                      <span style={{ fontSize: 12, color: '#a6adc8' }}>{p.rank || ''}</span>
                    )}
                  </td>
                  <td>
                    {editMode ? (
                      <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
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
                      </div>
                    ) : p.troop_level ? (
                      <span style={p.troop_level === FULL_TROOP
                        ? { color: '#f9a825', fontWeight: 700, fontSize: 14 }
                        : { fontSize: 12, color: '#cdd6f4' }}>
                        {p.troop_level}
                      </span>
                    ) : null}
                  </td>
                  {editMode && (
                    <td>
                      <button
                        onClick={() => handleSave(p.name)}
                        disabled={saving === p.name}
                        style={{ fontSize: 12, padding: '2px 8px', cursor: 'pointer', background: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {saving === p.name ? '...' : '💾'}
                      </button>
                    </td>
                  )}
                  <td className={`public-points-cell ${pointsHitTarget(p, targets) ? 'public-cell-hit-target' : ''}`}>
                    {p.points}
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
