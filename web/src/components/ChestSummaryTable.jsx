import { useEffect, useRef, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TROOP_STEPS = [
  '', 'G5 S5 M5', 'G5 S5 M6', 'G5 S6 M6',
  'G6 S6 M6', 'G6 S6 M7', 'G6 S7 M7',
  'G7 S7 M7', 'G7 S7 M8', 'G7 S8 M8',
  'G8 S8 M8', 'G8 S8 M9', 'G8 S9 M9',
  'G9 S9 M9',
]

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
      init[p.name] = { rank: p.rank || '', troop_level: p.troop_level || '' }
    })
    setEditRows(init)
  }, [editMode, players])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    setSaving(playerName)
    try {
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, row.troop_level || null)
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
              const tier = pointTier(p, targets)
              return (
                <tr key={p.name} className={rowColorClass(p, targets)}>
                  <td>{i + 1}</td>
                  <td title={p.name}>
                    {tier
                      ? <span className={`public-tier-name public-tier-${tier}`}>{p.name}</span>
                      : p.name}
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
                      <select
                        value={editRows[p.name]?.troop_level || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.name]: { ...prev[p.name], troop_level: e.target.value },
                        }))}
                        style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {TROOP_STEPS.map(s => <option key={s} value={s}>{s || '—'}</option>)}
                      </select>
                    </td>
                  )}
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
