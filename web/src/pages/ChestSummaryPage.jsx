import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchChestSummary, fetchChestByKingdomSlug, fetchChestHistory, fetchChestHistorySeason } from '../api.js'
import ChestSummaryTable from '../components/ChestSummaryTable.jsx'

// Публичная таблица: RU/EN со своим переключателем (владелец 2026-09-26). Адрес /c/... не
// несёт язык, поэтому общий useLang тут всегда дал бы 'en'. Остальные языки — переводчик
// браузера; ники/клан/названия сундуков помечены translate="no", чтобы он их не портил.
const TXT = {
  ru: {
    ended: 'Сбор завершён',
    left: (d, h, m) => `Осталось: ${d} дн. ${h} ч. ${m} мин.`,
    stoppedTitle: '⏸ Учёт сундуков остановлен.',
    stoppedText: 'Лидер клана завершил сезон досрочно. Новый сезон пока не начат — данные не обновляются. Предыдущие сезоны доступны во вкладке «История».',
    targetTitle: 'Цели сезона',
    pointsWord: 'очков',
    tz: 'Часовой пояс',
    editOpen: '✏️ Ввести состав', editClose: '✕ Закрыть',
    updated: 'Последнее обновление',
    tabCurrent: 'Текущий сезон', tabHistory: 'История',
    historyEmpty: 'Архив пока пуст — сезоны появятся здесь после первого автозакрытия.',
    points: 'очков', back: '← Назад к списку сезонов',
  },
  en: {
    ended: 'Collection finished',
    left: (d, h, m) => `Time left: ${d}d ${h}h ${m}m`,
    stoppedTitle: '⏸ Chest tracking is stopped.',
    stoppedText: 'The clan leader ended the season early. A new season has not started yet — data is not updated. Previous seasons are in the "History" tab.',
    targetTitle: 'Season targets',
    pointsWord: 'points',
    tz: 'Time zone',
    editOpen: '✏️ Enter troops', editClose: '✕ Close',
    updated: 'Last update',
    tabCurrent: 'Current season', tabHistory: 'History',
    historyEmpty: 'The archive is empty — seasons will appear here after the first auto-close.',
    points: 'points', back: '← Back to seasons',
  },
}

function initialLang() {
  try {
    const saved = localStorage.getItem('th_lang')
    if (saved === 'ru' || saved === 'en') return saved
  } catch { /* приватный режим */ }
  return (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en'
}

function formatRemaining(periodEndIso, offsetMinutes, t) {
  const [datePart, timePart] = periodEndIso.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi, s] = (timePart || '00:00:00').split(':').map(Number)
  const periodEndMillis = Date.UTC(y, mo - 1, d, h, mi, s || 0)
  const clanNowMillis = Date.now() + offsetMinutes * 60000
  const remaining = periodEndMillis - clanNowMillis
  if (remaining <= 0) return t.ended
  const totalMinutes = Math.floor(remaining / 60000)
  const days = Math.floor(totalMinutes / (24 * 60))
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60)
  const minutes = totalMinutes % 60
  return t.left(days, hours, minutes)
}

function CountdownTimer({ periodEnd, offsetMinutes, t }) {
  const [label, setLabel] = useState(() => formatRemaining(periodEnd, offsetMinutes, t))

  useEffect(() => {
    setLabel(formatRemaining(periodEnd, offsetMinutes, t))
    const id = setInterval(() => {
      setLabel(formatRemaining(periodEnd, offsetMinutes, t))
    }, 60000)
    return () => clearInterval(id)
  }, [periodEnd, offsetMinutes, t])

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
  const [lang, setLang] = useState(initialLang)
  const navigate = useNavigate()
  // Открыли по «сырому» адресу (/c/229/Феникс → %D0%A4...) или старому /chests/{slug} —
  // показываем в адресной строке читаемую ссылку с сервера (/c/229/feniks).
  useEffect(() => {
    if (!data?.public_url) return
    try {
      const path = new URL(data.public_url).pathname
      if (decodeURIComponent(window.location.pathname) !== decodeURIComponent(path)) {
        navigate(path, { replace: true })
      }
    } catch { /* некорректный url — оставляем как есть */ }
  }, [data?.public_url])  // eslint-disable-line react-hooks/exhaustive-deps
  const t = TXT[lang]
  function toggleLang() {
    const next = lang === 'ru' ? 'en' : 'ru'
    try { localStorage.setItem('th_lang', next) } catch { /* приватный режим */ }
    setLang(next)
  }
  // Общий LangProvider ставит <html lang="en"> для любого адреса вне /ru — перебиваем после
  // него (его эффект выполняется позже нашего), чтобы переводчик браузера видел верный язык.
  useEffect(() => {
    const id = setTimeout(() => document.documentElement.setAttribute('lang', lang), 0)
    return () => clearTimeout(id)
  }, [lang])

  // kingdom param is present on /c/:kingdom/:slug route, absent on /chests/:slug route
  const internalSlug = data?.collector_slug || (!kingdom ? slug : null)

  const loadData = () => {
    const loader = kingdom
      ? fetchChestByKingdomSlug(kingdom, slug)
      : fetchChestSummary(slug)
    loader.then(setData).catch(e => setError(e.message || 'not found'))
  }

  useEffect(() => { loadData() }, [slug, kingdom])  // eslint-disable-line react-hooks/exhaustive-deps

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
  // Все цели сезона (владелец 2026-09-26): очки + каждая квота со своей целью; архив до
  // квот — прежняя одна цель по сундукам.
  const targetParts = [
    ...(targets.points != null ? [`${targets.points} ${t.pointsWord}`] : []),
    ...(Array.isArray(targets.quotas)
      ? targets.quotas.filter(q => q.target != null).map(q => `${q.name}: ${q.target}`)
      : (targets.chests != null ? [`Epic: ${targets.chests}`] : [])),
  ]
  const hasSeasonTargets = targetParts.length > 0

  return (
    <div className="page-content">
      {/* Переход на лендинг — тот же логотип, что в шапке кабинета (владелец 2026-09-26) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <Link to="/" translate="no" className="notranslate" style={{
          display: 'inline-flex', alignItems: 'center', gap: 10,
          textDecoration: 'none', fontWeight: 700, fontSize: 18, letterSpacing: '0.3px',
        }}>
          <span style={{ fontSize: 20, color: 'var(--accent)' }}>⚔</span>
          <span className="header-logo-text" style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span className="header-logo-text" style={{ color: 'var(--on-surface)' }}>Hunter</span>
        </Link>
        <button type="button" className="public-avg-toggle notranslate" translate="no" onClick={toggleLang}>
          {lang === 'ru' ? 'EN' : 'RU'}
        </button>
      </div>
      <h1 className="public-summary-title notranslate" translate="no">
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
          <strong>{t.stoppedTitle}</strong><br />
          {t.stoppedText}
        </div>
      )}

      <div className="public-season-info">
        {hasSeasonTargets && (
          <span className="public-season-badge">
            {t.targetTitle}: <span translate="no" className="notranslate">{targetParts.join(' · ')}</span>
          </span>
        )}
        {hasSeasonTargets && data.timezone_offset_minutes != null && (
          <span className="public-season-badge">
            {t.tz}: UTC{formatOffsetLabel(data.timezone_offset_minutes)}
          </span>
        )}
        {hasSeasonTargets && data.period_start && data.period_end && (
          <span className="public-season-badge">
            {formatPeriodPoint(data.period_start)} – {formatPeriodPoint(data.period_end)}
          </span>
        )}
        {hasSeasonTargets && data.period_end && (
          <CountdownTimer periodEnd={data.period_end} offsetMinutes={data.timezone_offset_minutes ?? 0} t={t} />
        )}
        {tab === 'current' && (
          <button
            className="chest-pill-btn chest-pill-btn--sm"
            style={{ marginLeft: 'auto' }}
            onClick={() => {
              if (editMode) { setEditMode(false); loadData() }
              else { setEditMode(true) }
            }}
          >
            {editMode ? t.editClose : t.editOpen}
          </button>
        )}
      </div>

      <div className="public-summary-updated">{t.updated}: {updatedLabel}</div>
      <div className="public-summary-divider" />

      <div className="chest-tabs chest-tabs--pill">
        <button
          className={`chest-tab chest-tab--pill ${tab === 'current' ? 'chest-tab--active' : ''}`}
          onClick={() => setTab('current')}
        >
          {t.tabCurrent}
        </button>
        <button
          className={`chest-tab chest-tab--pill ${tab === 'history' ? 'chest-tab--active' : ''}`}
          onClick={() => setTab('history')}
        >
          {t.tabHistory}
        </button>
      </div>

      {tab === 'current' && (
        <>
          <ChestSummaryTable
            chestTypes={data.chest_types}
            players={data.players}
            targets={targets}
            editMode={editMode}
            collectorSlug={internalSlug}
            lang={lang}
          />
        </>
      )}

      {tab === 'history' && !selectedSeasonId && (
        <div className="chest-history-list">
          {historyError && <div className="text-muted">{historyError}</div>}
          {!historyError && !history && <div className="text-muted">...</div>}
          {history && history.seasons.length === 0 && (
            <div className="text-muted">{t.historyEmpty}</div>
          )}
          {history && history.seasons.map(s => (
            <button
              key={s.id}
              className="public-season-badge"
              onClick={() => setSelectedSeasonId(s.id)}
              style={{ display: 'block', marginBottom: 8, cursor: 'pointer' }}
            >
              {formatPeriodPoint(s.period_start)} – {formatPeriodPoint(s.period_end)} · {s.total_points} {t.points}
            </button>
          ))}
        </div>
      )}

      {tab === 'history' && selectedSeasonId && (
        <div>
          <button className="public-season-badge" onClick={() => { setSelectedSeasonId(null); setSeasonDetail(null) }} style={{ marginBottom: 12, cursor: 'pointer' }}>
            {t.back}
          </button>
          {!seasonDetail && <div className="text-muted">...</div>}
          {seasonDetail && (
            <ChestSummaryTable
              chestTypes={seasonDetail.chest_types}
              players={seasonDetail.players}
              targets={seasonDetail.targets || { points: null, chests: null }}
              lang={lang}
            />
          )}
        </div>
      )}
    </div>
  )
}
