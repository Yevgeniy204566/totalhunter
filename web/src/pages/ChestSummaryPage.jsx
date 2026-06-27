import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary, fetchChestByKingdomSlug, fetchChestHistory, fetchChestHistorySeason } from '../api.js'
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
  const { slug, kingdom } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('current')
  const [history, setHistory] = useState(null)
  const [historyError, setHistoryError] = useState('')
  const [selectedSeasonId, setSelectedSeasonId] = useState(null)
  const [seasonDetail, setSeasonDetail] = useState(null)
  const [editMode, setEditMode] = useState(false)

  // kingdom param is present on /c/:kingdom/:slug route, absent on /chests/:slug route
  const internalSlug = data?.collector_slug || (!kingdom ? slug : null)

  useEffect(() => {
    const loader = kingdom
      ? fetchChestByKingdomSlug(kingdom, slug)
      : fetchChestSummary(slug)
    loader.then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug, kingdom])

  useEffect(() => {
    if (tab !== 'history' || history || !internalSlug) return
    fetchChestHistory(internalSlug).then(setHistory).catch(e => setHistoryError(e.message || 'error'))
  }, [tab, internalSlug, history])

  useEffect(() => {
    if (selectedSeasonId == null || !internalSlug) return
    setSeasonDetail(null)
    fetchChestHistorySeason(internalSlug, selectedSeasonId).then(setSeasonDetail)
  }, [selectedSeasonId, internalSlug])

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

      {data.stopped_at && (
        <div style={{
          background: 'rgba(248,113,113,0.1)',
          border: '1px solid rgba(248,113,113,0.35)',
          borderRadius: 10,
          padding: '12px 18px',
          marginBottom: 16,
          color: '#FCA5A5',
          fontSize: 14,
          lineHeight: 1.5,
        }}>
          <strong>⏸ Учёт сундуков остановлен.</strong><br />
          Лидер клана завершил сезон досрочно. Новый сезон пока не начат — данные не обновляются.
          Предыдущие сезоны доступны во вкладке «История».
        </div>
      )}

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

      <div className="chest-tabs">
        <button
          className={`chest-tab ${tab === 'current' ? 'chest-tab--active' : ''}`}
          onClick={() => setTab('current')}
        >
          Текущий сезон
        </button>
        <button
          className={`chest-tab ${tab === 'history' ? 'chest-tab--active' : ''}`}
          onClick={() => setTab('history')}
        >
          История
        </button>
      </div>

      {tab === 'current' && (
        <>
          <div style={{ marginBottom: 12 }}>
            <button
              className="btn-secondary"
              style={{ fontSize: 13, padding: '4px 12px' }}
              onClick={() => setEditMode(m => !m)}
            >
              {editMode ? '✕ Закрыть' : '✏️ Ввести состав'}
            </button>
          </div>
          <ChestSummaryTable
            chestTypes={data.chest_types}
            players={data.players}
            targets={targets}
            editMode={editMode}
            collectorSlug={internalSlug}
            onSaveDone={() => setEditMode(false)}
          />
        </>
      )}

      {tab === 'history' && !selectedSeasonId && (
        <div className="chest-history-list">
          {historyError && <div className="text-muted">{historyError}</div>}
          {!historyError && !history && <div className="text-muted">...</div>}
          {history && history.seasons.length === 0 && (
            <div className="text-muted">Архив пока пуст — сезоны появятся здесь после первого автозакрытия.</div>
          )}
          {history && history.seasons.map(s => (
            <button
              key={s.id}
              className="public-season-badge"
              onClick={() => setSelectedSeasonId(s.id)}
              style={{ display: 'block', marginBottom: 8, cursor: 'pointer' }}
            >
              {formatPeriodPoint(s.period_start)} – {formatPeriodPoint(s.period_end)} · {s.total_points} очков
            </button>
          ))}
        </div>
      )}

      {tab === 'history' && selectedSeasonId && (
        <div>
          <button className="public-season-badge" onClick={() => { setSelectedSeasonId(null); setSeasonDetail(null) }} style={{ marginBottom: 12, cursor: 'pointer' }}>
            ← Назад к списку сезонов
          </button>
          {!seasonDetail && <div className="text-muted">...</div>}
          {seasonDetail && (
            <ChestSummaryTable
              chestTypes={seasonDetail.chest_types}
              players={seasonDetail.players}
              targets={seasonDetail.targets || { points: null, chests: null }}
            />
          )}
        </div>
      )}
    </div>
  )
}
