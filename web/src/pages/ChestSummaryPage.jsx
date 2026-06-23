import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'

function formatRemaining(periodEndIso, offsetMinutes) {
  const [datePart, timePart] = periodEndIso.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi, s] = (timePart || '00:00:00').split(':').map(Number)
  const periodEndMillis = Date.UTC(y, mo - 1, d, h, mi, s || 0)
  const clanNowMillis = Date.now() + offsetMinutes * 60000
  const remaining = periodEndMillis - clanNowMillis
  if (remaining <= 0) return 'Сбор завершён'
  const totalMinutes = Math.floor(remaining / 60000)
  const days = Math.floor(totalMinutes / (24 * 60))
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60)
  const minutes = totalMinutes % 60
  return `Осталось: ${days} дн. ${hours} ч. ${minutes} мин.`
}

function CountdownTimer({ periodEnd, offsetMinutes }) {
  const [label, setLabel] = useState(() => formatRemaining(periodEnd, offsetMinutes))

  useEffect(() => {
    setLabel(formatRemaining(periodEnd, offsetMinutes))
    const id = setInterval(() => {
      setLabel(formatRemaining(periodEnd, offsetMinutes))
    }, 60000)
    return () => clearInterval(id)
  }, [periodEnd, offsetMinutes])

  return <span className="public-season-badge public-season-timer">{label}</span>
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

function formatOffsetLabel(offsetMinutes) {
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMinutes)
  const h = String(Math.floor(abs / 60)).padStart(2, '0')
  const m = String(abs % 60).padStart(2, '0')
  return `${sign}${h}:${m}`
}

function formatPeriodPoint(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
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

export default function ChestSummaryPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [data])

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

  useEffect(() => {
    fetchChestSummary(slug).then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug])

  if (error) return <div className="page-content">{error}</div>
  if (!data) return <div className="page-content text-muted">...</div>

  const updatedLabel = data.updated_at
    ? new Date(data.updated_at).toLocaleString()
    : '—'

  const targets = data.targets || { points: null, chests: null }
  const hasSeasonTargets = targets.points != null || targets.chests != null

  return (
    <div className="page-content">
      <h1 className="public-summary-title">
        <span className="public-kingdom-label">{data.kingdom}/</span>
        <span className="public-clan-label">{data.clan}</span>
      </h1>

      {hasSeasonTargets && (
        <div className="public-season-info">
          <span className="public-season-badge">
            Цель сезона: {targets.points ?? '—'} очков / {targets.chests ?? '—'} Epic-склепов
          </span>
          {data.timezone_offset_minutes != null && (
            <span className="public-season-badge">
              Часовой пояс: UTC{formatOffsetLabel(data.timezone_offset_minutes)}
            </span>
          )}
          {data.period_start && data.period_end && (
            <span className="public-season-badge">
              {formatPeriodPoint(data.period_start)} – {formatPeriodPoint(data.period_end)}
            </span>
          )}
          {data.period_end && (
            <CountdownTimer periodEnd={data.period_end} offsetMinutes={data.timezone_offset_minutes ?? 0} />
          )}
        </div>
      )}

      <div className="public-summary-updated">Последнее обновление: {updatedLabel}</div>
      <div className="public-summary-divider" />

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
              {data.chest_types.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.players.map((p, i) => {
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
                {data.chest_types.map(t => {
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
    </div>
  )
}
