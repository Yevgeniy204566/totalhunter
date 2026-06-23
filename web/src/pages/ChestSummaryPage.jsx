import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'
import ChestSummaryTable from '../components/ChestSummaryTable.jsx'

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

function formatOffsetLabel(offsetMinutes) {
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMinutes)
  const h = String(Math.floor(abs / 60)).padStart(2, '0')
  const m = String(abs % 60).padStart(2, '0')
  return `${sign}${h}:${m}`
}

function formatUpdatedAt(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')}.${y} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
}

function formatPeriodPoint(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
}

export default function ChestSummaryPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchChestSummary(slug).then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug])

  if (error) return <div className="page-content">{error}</div>
  if (!data) return <div className="page-content text-muted">...</div>

  const updatedLabel = data.updated_at
    ? formatUpdatedAt(data.updated_at)
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

      <ChestSummaryTable chestTypes={data.chest_types} players={data.players} targets={targets} />
    </div>
  )
}
