import { useEffect, useRef, useState } from 'react'

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

export default function ChestSummaryTable({ chestTypes, players, targets }) {
  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [chestTypes, players])

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
