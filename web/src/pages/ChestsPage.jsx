import { useEffect, useState, Fragment } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'
import ChestSummaryTable from '../components/ChestSummaryTable.jsx'
import ChestGuide from '../components/ChestGuide.jsx'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['5', '6', '7', '8', '9']

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

function displayName(row, catalogOptions) {
  if (row.raw_type) return row.raw_type
  if (row.custom_name) return row.custom_name
  if (row.catalog_id) {
    const opt = catalogOptions.find(o => o.catalog_id === row.catalog_id)
    if (opt) return opt.label
  }
  return '—'
}

// Mirrors ChestSummaryPage.jsx's formatPeriodPoint — same data contract (ISO
// datetime from chest_history.py), duplicated here since there's no shared
// utils module for this small pure helper.
function formatPeriodPoint(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
}

// Цвет «Учёта» (владелец 2026-09-26): не в учёте — бледно-красный, квоты — от бледно- к
// насыщенно-зелёному; «В учёте» — без подсветки.
const ACCOUNTING_BG = {
  off: { background: 'rgba(248,113,113,0.16)', borderColor: 'rgba(248,113,113,0.45)' },
  on:  {},
  1:   { background: 'rgba(74,222,128,0.12)', borderColor: 'rgba(74,222,128,0.35)' },
  2:   { background: 'rgba(74,222,128,0.26)', borderColor: 'rgba(74,222,128,0.55)' },
  3:   { background: 'rgba(74,222,128,0.42)', borderColor: 'rgba(74,222,128,0.75)' },
}

/* Квоты сезона (владелец 2026-09-26): до 3 штук, у каждой название и цель. Номер (slot) у
   квоты постоянный — новые берут наименьший свободный, чтобы отметки сундуков не съезжали.
   Карточки в один ряд; цвет карточки = цвет этой квоты в списке «Учёт», чтобы было видно,
   какие сундуки в какую квоту идут. */
function QuotaEditor({ quotas, cx, onChange }) {
  const set = (i, field, value) => onChange(quotas.map((q, j) => (j === i ? { ...q, [field]: value } : q)))
  const add = () => {
    const used = new Set(quotas.map(q => q.slot))
    const slot = [1, 2, 3].find(n => !used.has(n))
    if (slot) onChange([...quotas, { slot, name: '', target: '', mode: 'fixed', hero_k: 0, hero_h0: 400 }]
      .sort((a, b) => a.slot - b.slot))
  }
  return (
    <div className="quota-block">
      <div className="season-subtitle">{cx.quotasLabel}</div>
      <div className="quota-grid">
        {quotas.map((q, i) => (
          <div key={q.slot} className={`quota-card quota-card--${q.slot}`}>
            <div className="quota-card-head">
              <span>{cx.accLegendQuotaShort} {q.slot}</span>
              <button type="button" className="quota-del" title={cx.quotaDelete}
                onClick={() => onChange(quotas.filter((_, j) => j !== i))}>🗑</button>
            </div>
            <label className="quota-row">
              <span>{cx.quotaName}</span>
              <input className="input-dark" placeholder={cx.quotaNameHint} maxLength={40}
                value={q.name} onChange={e => set(i, 'name', e.target.value)} />
            </label>
            <label className="quota-row">
              <span>{cx.quotaTarget}</span>
              <input className="input-dark" type="number" min={0} placeholder={cx.quotaTargetHint}
                value={q.target} onChange={e => set(i, 'target', e.target.value)} />
            </label>
            <label className="quota-check">
              <input type="checkbox" checked={q.mode === 'per_player'}
                onChange={e => set(i, 'mode', e.target.checked ? 'per_player' : 'fixed')} />
              {cx.perPlayer}
            </label>
            {q.mode === 'per_player' && (
              <div className="quota-hero">
                <label className="quota-row">
                  <span>{cx.heroK}</span>
                  <input className="input-dark" type="number" min={-100} max={100}
                    value={q.hero_k} onChange={e => set(i, 'hero_k', e.target.value)} />
                  <small>{cx.heroKHelp}</small>
                </label>
                <label className="quota-row">
                  <span>{cx.heroH0}</span>
                  <input className="input-dark" type="number" min={1} max={999}
                    value={q.hero_h0} onChange={e => set(i, 'hero_h0', e.target.value)} />
                  <small>{cx.heroH0Help}</small>
                </label>
              </div>
            )}
          </div>
        ))}
        {quotas.length < 3 && (
          <button type="button" className="quota-add" onClick={add}>{cx.addQuota}</button>
        )}
      </div>
    </div>
  )
}

export default function ChestsPage() {
  const [collectors, setCollectors] = useState(null)
  const [rowsByCollector, setRowsByCollector] = useState({})
  const [playerRowsByCollector, setPlayerRowsByCollector] = useState({})
  const [activeTabByCollector, setActiveTabByCollector] = useState({})
  const [seasonByCollector, setSeasonByCollector] = useState({})
  const [msg, setMsg] = useState('')
  const [loadError, setLoadError] = useState('')
  const [claimCode, setClaimCode] = useState('')
  const [presets, setPresets] = useState(null)
  const [presetChoiceByCollector, setPresetChoiceByCollector] = useState({})
  const [historyByCollector, setHistoryByCollector] = useState({})
  const [seasonDetailByCollector, setSeasonDetailByCollector] = useState({})
  const [confirmCloseByCollector, setConfirmCloseByCollector] = useState({})
  const [confirmDeleteByCollector, setConfirmDeleteByCollector] = useState({})
  const [leaderByCollector, setLeaderByCollector] = useState({})
  const [leaderExcludedByCollector, setLeaderExcludedByCollector] = useState({})
  const [sortByCollector, setSortByCollector] = useState({})
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.chests
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Сундуки' : 'Total Hunter — Chests',
    description: lang === 'ru' ? 'Настройка сундуков клана.' : 'Configure your clan chests.',
  })

  async function refresh() {
    try {
      const data = await api.dashboardChests()
      setCollectors(data.collectors)
      const nextRows = {}
      const nextPlayerRows = {}
      const nextSeason = {}
      const nextLeader = {}
      const nextLeaderExcluded = {}
      for (const c of data.collectors) {
        nextRows[c.slug] = c.rows
        nextPlayerRows[c.slug] = c.player_alias_rows.map(r => {
          const { g, s, m } = parseTroop(r.troop_level)
          return { ...r, troop_g: g, troop_s: s, troop_m: m, hero_level: r.hero_level ?? '' }
        })
        nextSeason[c.slug] = {
          timezone_offset_minutes: c.timezone_offset_minutes,
          period_start: c.period_start ? c.period_start.slice(0, 16) : '',
          period_end: c.period_end ? c.period_end.slice(0, 16) : '',
          target_points: c.target_points,
          quotas: (c.quotas || []).map(q => ({ slot: q.slot, name: q.name, target: q.target ?? '',
                                               mode: q.mode || 'fixed', hero_k: q.hero_k ?? 0, hero_h0: q.hero_h0 ?? 400 })),
        }
        nextLeader[c.slug] = c.leader_canonical_name || null
        nextLeaderExcluded[c.slug] = c.leader_excluded_catalog_ids || []
      }
      setRowsByCollector(nextRows)
      setPlayerRowsByCollector(nextPlayerRows)
      setSeasonByCollector(nextSeason)
      setLeaderByCollector(nextLeader)
      setLeaderExcludedByCollector(nextLeaderExcluded)
    } catch (e) {
      setLoadError(e.message || 'failed to load')
    }
  }
  useEffect(() => { refresh() }, [])
  useEffect(() => { api.dashboardChestsPresets().then(setPresets).catch(() => {}) }, [])

  function activeTab(slug) { return activeTabByCollector[slug] || 'chests' }
  function setTab(slug, tab) {
    setActiveTabByCollector(prev => ({ ...prev, [slug]: tab }))
  }

  function updateRow(slug, index, field, value) {
    setRowsByCollector(prev => {
      const rows = [...prev[slug]]
      rows[index] = { ...rows[index], [field]: value }
      return { ...prev, [slug]: rows }
    })
  }

  function addRow(slug) {
    setRowsByCollector(prev => ({
      ...prev,
      [slug]: [...prev[slug], { raw_type: null, catalog_id: null, custom_name: null,
                                points: 0, is_in_pattern: false, quota_slot: null }],
    }))
  }

  function loadPreset(slug, presetName) {
    const preset = presets?.[presetName]
    if (!preset) return
    setRowsByCollector(prev => {
      const rows = [...(prev[slug] || [])]
      for (const item of preset) {
        const idx = rows.findIndex(r => r.catalog_id === item.catalog_id)
        // Пресет — только шаблон (владелец 2026-09-26): у существующих строк меняет очки,
        // «Учёт» не трогает; новые строки ставит «В учёте».
        if (idx >= 0) {
          rows[idx] = { ...rows[idx], points: item.points }
        } else {
          rows.push({ raw_type: null, catalog_id: item.catalog_id, custom_name: null,
                     points: item.points, is_in_pattern: true, quota_slot: null })
        }
      }
      return { ...prev, [slug]: rows }
    })
    setMsg(cx.presetLoaded)
  }

  async function save(slug) {
    try {
      await api.dashboardChestsSave(slug, rowsByCollector[slug])
      setMsg(cx.saved)
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  function updatePlayerRow(slug, index, field, value) {
    setPlayerRowsByCollector(prev => {
      const rows = [...prev[slug]]
      rows[index] = { ...rows[index], [field]: value }
      return { ...prev, [slug]: rows }
    })
  }

  function toggleSort(slug, field) {
    setSortByCollector(prev => {
      const cur = prev[slug] || { field: 'name', dir: 'asc' }
      return { ...prev, [slug]: { field, dir: cur.field === field && cur.dir === 'asc' ? 'desc' : 'asc' } }
    })
  }

  function addPlayerRow(slug) {
    setPlayerRowsByCollector(prev => ({
      ...prev,
      [slug]: [...prev[slug], { raw_name: '', canonical_name: '' }],
    }))
  }

  async function savePlayerAliases(slug) {
    try {
      await api.dashboardChestsPlayerAliases(slug, playerRowsByCollector[slug])
      // Save rank + troop_level profiles in the same action
      const profileRows = (playerRowsByCollector[slug] || [])
        .filter(r => (r.canonical_name || r.raw_name || '').trim())
        .map(r => ({
          canonical_name: r.canonical_name || r.raw_name,
          rank: r.rank || null,
          troop_level: r.troop_g && r.troop_s && r.troop_m
              ? `G${r.troop_g} S${r.troop_s} M${r.troop_m}`
              : null,
          // сохранение профилей — полная замена: без поля уровень Героя затрётся
          hero_level: Number(r.hero_level) || null,
        }))
      await api.dashboardChestsPlayerProfiles(slug, profileRows)
      await api.dashboardChestsLeader(slug, {
        leader_canonical_name: leaderByCollector[slug] || null,
        leader_excluded_catalog_ids: leaderExcludedByCollector[slug] || [],
      })
      setMsg(cx.saved)
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  function updateSeasonField(slug, field, value) {
    setSeasonByCollector(prev => ({
      ...prev,
      [slug]: { ...prev[slug], [field]: value },
    }))
  }

  async function saveSeason(slug) {
    const s = seasonByCollector[slug]
    const payload = {
      timezone_offset_minutes: s.timezone_offset_minutes === '' || s.timezone_offset_minutes == null
        ? null : Number(s.timezone_offset_minutes),
      period_start: s.period_start ? s.period_start + ':00' : null,
      period_end: s.period_end ? s.period_end + ':00' : null,
      target_points: s.target_points === '' || s.target_points == null ? null : Number(s.target_points),
      // квота без названия = удалена; сундуки удалённой квоты остаются «в учёте» (сервер)
      quotas: (s.quotas || [])
        .filter(q => (q.name || '').trim())
        .map(q => ({ slot: q.slot, name: q.name.trim(),
                     target: q.target === '' || q.target == null ? null : Number(q.target),
                     mode: q.mode || 'fixed',
                     ...(q.mode === 'per_player'
                       ? { hero_k: Number(q.hero_k) || 0, hero_h0: Number(q.hero_h0) || 400 } : {}) })),
    }
    try {
      await api.dashboardChestsSeason(slug, payload)
      setMsg(cx.saved)
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  async function genToken(slug) {
    const res = await api.dashboardChestsToken(slug)
    setMsg(res.code)
  }

  async function claim() {
    try {
      await api.dashboardChestsClaim(claimCode)
      setClaimCode('')
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  async function changeLanguage(slug, language) {
    await api.dashboardChestsLang(slug, language)
    await refresh()
  }

  async function loadHistory(slug) {
    if (historyByCollector[slug]) return
    const data = await api.dashboardChestsHistory(slug)
    setHistoryByCollector(prev => ({ ...prev, [slug]: data.seasons }))
  }

  async function loadSeasonDetail(slug, seasonId) {
    const data = await api.dashboardChestsHistoryDetail(slug, seasonId)
    setSeasonDetailByCollector(prev => ({ ...prev, [slug]: { seasonId, data } }))
  }

  async function closeSeason(slug) {
    try {
      await api.dashboardChestsCloseSeason(slug)
      setConfirmCloseByCollector(prev => ({ ...prev, [slug]: false }))
      setMsg(cx.saved)
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  if (loadError) return <div className="page-content text-muted">{loadError}</div>
  if (!collectors) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content" style={{ maxWidth: 1600 }}>
<h2 style={{ marginBottom: 24 }}>{cx.title}</h2>
      <ChestGuide />
      {/* Мини-таблица значений «Учёта» — одна над всеми ростерами (владелец 2026-09-26) */}
      <div style={{ marginBottom: 24, padding: '12px 16px', borderRadius: 12, background: 'var(--card)',
                    border: '1px solid var(--outline)' }}>
        <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>{cx.accLegendTitle}</div>
        <table style={{ borderCollapse: 'collapse', fontSize: 15 }}>
          <tbody>
            {[['off', cx.accOff, cx.accLegendOff], ['on', cx.accOn, cx.accLegendOn],
              ['1', cx.accLegendQuotaName, cx.accLegendQuota]].map(([k, name, desc]) => (
              <tr key={k}>
                <td style={{ padding: '6px 12px 6px 0', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                  <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 6,
                                 border: '1px solid var(--outline)', fontWeight: 600, ...ACCOUNTING_BG[k] }}>{name}</span>
                </td>
                <td style={{ padding: '6px 0', color: 'var(--on-surface2)', lineHeight: 1.5 }}>{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: 24, maxWidth: 520, borderRadius: 16 }}>
        <div style={{ fontSize: 13, color: 'var(--on-surface2)', marginBottom: 10 }}>
          {cx.claimBtn} — {cx.claimPlaceholder.toLowerCase()}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            className="input-dark"
            value={claimCode}
            onChange={e => setClaimCode(e.target.value)}
            placeholder={cx.claimPlaceholder}
            style={{ flex: '1 1 180px' }}
          />
          <button className="chest-pill-btn chest-pill-btn--primary" onClick={claim}>{cx.claimBtn}</button>
        </div>
      </div>

      {collectors.length === 0 && <div className="text-muted" style={{ marginTop: 12 }}>{cx.noCollectors}</div>}

      {collectors.map(collector => (
        <div className="collector-card" key={collector.slug}>
          {/* Header: identity left | links + destructive/transfer actions right */}
          <div className="collector-header">
            <div className="collector-identity">
              <span className="collector-clan-name">{collector.clan}</span>
              <span className="collector-kingdom-tag">{collector.kingdom}</span>
            </div>

            <div className="collector-links">
              <a
                href={collector.public_url}
                target="_blank" rel="noreferrer"
                className="chest-pill-btn chest-pill-btn--primary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}
              >
                🔗 {cx.publicLink}
              </a>
              {/* Под кнопкой — та же читаемая ссылка (/c/229/feniks), а не служебная
                  /chests/{случайный id}: её владелец видел как «каракули» (2026-09-26). */}
              {collector.public_url && (
                <a href={collector.public_url} target="_blank" rel="noreferrer"
                  translate="no" className="notranslate"
                  style={{ fontSize: 13, color: '#60A5FA', marginTop: 6, display: 'block', wordBreak: 'break-all' }}>
                  {collector.public_url.replace('https://', '')}
                </a>
              )}

              <div className="collector-actions-row" style={{ marginTop: 8 }}>
                {cx.language}
                <select
                  className="input-dark"
                  style={{ width: 'auto' }}
                  value={collector.language || ''}
                  onChange={e => changeLanguage(collector.slug, e.target.value)}
                >
                  <option value="ru">ru</option>
                  <option value="en">en</option>
                </select>
                <button className="chest-pill-btn chest-pill-btn--sm" onClick={() => genToken(collector.slug)}>
                  {cx.generateToken}
                </button>
              </div>
            </div>
          </div>

          {/* Сезон: поля в одну строку, квоты рядом, одна кнопка «Сохранить сезон» (владелец 2026-09-26) */}
          <div className="chest-season-card">
            <div className="season-subtitle">{cx.seasonTitle}</div>
            <div className="season-fields">
              <label className="season-field">
                <span>{cx.timezoneLabel}</span>
                <select
                  className="input-dark"
                  value={seasonByCollector[collector.slug]?.timezone_offset_minutes ?? ''}
                  onChange={e => updateSeasonField(collector.slug, 'timezone_offset_minutes', e.target.value)}
                >
                  <option value="">—</option>
                  {[-720, -660, -600, -540, -480, -420, -360, -300, -240, -210, -180, -120, -60, 0,
                    60, 120, 180, 210, 240, 270, 300, 330, 345, 360, 390, 420, 480, 540, 570, 600,
                    630, 660, 720, 765, 780, 840].map(m => (
                    <option key={m} value={m}>
                      UTC{m >= 0 ? '+' : '-'}{String(Math.floor(Math.abs(m) / 60)).padStart(2, '0')}:{String(Math.abs(m) % 60).padStart(2, '0')}
                    </option>
                  ))}
                </select>
              </label>
              <label className="season-field">
                <span>{cx.periodStartLabel}</span>
                <input className="input-dark" type="datetime-local"
                  value={seasonByCollector[collector.slug]?.period_start || ''}
                  onChange={e => updateSeasonField(collector.slug, 'period_start', e.target.value)}
                />
              </label>
              <label className="season-field">
                <span>{cx.periodEndLabel}</span>
                <input className="input-dark" type="datetime-local"
                  value={seasonByCollector[collector.slug]?.period_end || ''}
                  onChange={e => updateSeasonField(collector.slug, 'period_end', e.target.value)}
                />
              </label>
              <label className="season-field">
                <span>{cx.targetPointsLabel}</span>
                <input className="input-dark" type="number"
                  value={seasonByCollector[collector.slug]?.target_points ?? ''}
                  onChange={e => updateSeasonField(collector.slug, 'target_points', e.target.value)}
                />
              </label>
            </div>
            <QuotaEditor
              quotas={seasonByCollector[collector.slug]?.quotas || []}
              cx={cx}
              onChange={q => updateSeasonField(collector.slug, 'quotas', q)}
            />
            <div className="season-actions">
              <button className="chest-pill-btn chest-pill-btn--green" onClick={() => saveSeason(collector.slug)}>
                {cx.saveSeason}
              </button>
              {collector.period_end && (
                confirmCloseByCollector[collector.slug] ? (
                  <>
                    <span style={{ fontSize: 14, color: '#F87171', marginLeft: 'auto' }}>{cx.closeSeasonConfirmText}</span>
                    <button className="chest-pill-btn chest-pill-btn--solid-danger"
                      onClick={() => closeSeason(collector.slug)}
                    >{cx.closeSeasonYes}</button>
                    <button className="chest-pill-btn"
                      onClick={() => setConfirmCloseByCollector(prev => ({ ...prev, [collector.slug]: false }))}
                    >{cx.closeSeasonNo}</button>
                  </>
                ) : (
                  <button
                    className="chest-pill-btn chest-pill-btn--danger"
                    style={{ marginLeft: 'auto' }}
                    onClick={() => setConfirmCloseByCollector(prev => ({ ...prev, [collector.slug]: true }))}
                  >{cx.closeSeasonBtn}</button>
                )
              )}
            </div>
          </div>

          <div className="chest-tabs chest-tabs--pill">
            <button className={`chest-tab chest-tab--pill ${activeTab(collector.slug) === 'chests' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'chests')}>{cx.chestsTab}</button>
            <button className={`chest-tab chest-tab--pill ${activeTab(collector.slug) === 'players' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'players')}>{cx.playersTab}</button>
            <button className={`chest-tab chest-tab--pill ${activeTab(collector.slug) === 'history' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'history')}>{cx.historyTab}</button>
          </div>

          {activeTab(collector.slug) === 'chests' && (
            <>
              {/* Presets + Save + Итого in one row */}
              <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                {presets && Object.keys(presets).length > 0 && (
                  <>
                    <select
                      className="input-dark"
                      style={{ width: 'auto' }}
                      value={presetChoiceByCollector[collector.slug] || Object.keys(presets)[0]}
                      onChange={e => setPresetChoiceByCollector(prev => ({ ...prev, [collector.slug]: e.target.value }))}
                    >
                      {Object.keys(presets).map(name => <option key={name} value={name}>{name}</option>)}
                    </select>
                    <button className="chest-pill-btn chest-pill-btn--sm"
                      onClick={() => loadPreset(collector.slug, presetChoiceByCollector[collector.slug] || Object.keys(presets)[0])}
                    >{cx.loadPresetBtn}</button>
                  </>
                )}
                <button className="chest-pill-btn chest-pill-btn--primary" onClick={() => save(collector.slug)}>{cx.save}</button>
                <span style={{ fontWeight: 600, marginLeft: 8, color: 'var(--on-surface2)' }}>
                  {cx.grandTotalLabel} {(rowsByCollector[collector.slug] || []).reduce((sum, row) => sum + (row.total_ever ?? 0), 0)}
                </span>
              </div>
              {/* Ростер сундуков сворачивается (владелец 2026-09-26); открыт по умолчанию */}
              <details open className="chest-roster">
              <summary style={{ fontSize: 17, fontWeight: 700, cursor: 'pointer', margin: '4px 0 10px' }}>
                {cx.rosterTitle} ({(rowsByCollector[collector.slug] || []).length})
              </summary>
              <div style={{ overflowX: 'auto' }}>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: 220 }}>{cx.rawCol}</th>
                    <th style={{ minWidth: 240 }}>{cx.catalogCol}</th>
                    <th className="chest-secondary-col" style={{ minWidth: 130 }}>{cx.customNameCol}</th>
                    <th style={{ minWidth: 70 }}>{cx.pointsCol}</th>
                    <th style={{ minWidth: 170 }}>
                      {cx.accountingCol}
                      <span className="chest-col-help" title={cx.accountingTooltip}>?</span>
                    </th>
                    <th style={{ minWidth: 60 }}>{cx.totalEverCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {rowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td style={{ whiteSpace: 'nowrap' }}>{row.raw_type || '—'}</td>
                      <td>
                        <select
                          className="input-dark"
                          value={row.catalog_id || ''}
                          onChange={e => updateRow(collector.slug, i, 'catalog_id', e.target.value || null)}
                        >
                          <option value="">{cx.noCatalog}</option>
                          {collector.catalog_options.map(o => (
                            <option key={o.catalog_id} value={o.catalog_id}>{o.label}</option>
                          ))}
                        </select>
                      </td>
                      <td className="chest-secondary-col">
                        <input
                          className="input-dark"
                          value={row.custom_name || ''}
                          onChange={e => updateRow(collector.slug, i, 'custom_name', e.target.value || null)}
                        />
                      </td>
                      <td>
                        <input
                          className="input-dark"
                          type="number"
                          value={row.points === 0 ? '' : row.points}
                          onChange={e => updateRow(collector.slug, i, 'points', parseInt(e.target.value, 10) || 0)}
                        />
                      </td>
                      <td>
                        <select
                          className="input-dark chest-acc-select"
                          style={ACCOUNTING_BG[row.quota_slot ? String(row.quota_slot) : (row.is_in_pattern ? 'on' : 'off')]}
                          value={row.quota_slot ? String(row.quota_slot) : (row.is_in_pattern ? 'on' : 'off')}
                          onChange={e => {
                            const v = e.target.value
                            updateRow(collector.slug, i, 'is_in_pattern', v !== 'off')
                            updateRow(collector.slug, i, 'quota_slot', v === 'off' || v === 'on' ? null : Number(v))
                          }}
                        >
                          <option value="off">{cx.accOff}</option>
                          <option value="on">{cx.accOn}</option>
                          {(collector.quotas || []).map(q => (
                            <option key={q.slot} value={String(q.slot)}>{q.name}</option>
                          ))}
                        </select>
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--on-surface2)' }}>
                        {row.total_ever ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              </details>
              <button className="chest-pill-btn" onClick={() => addRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addRow}
              </button>
              <button className="chest-pill-btn chest-pill-btn--primary" onClick={() => save(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.save}
              </button>
            </>
          )}

          {activeTab(collector.slug) === 'players' && (() => {
            const sort = sortByCollector[collector.slug] || { field: 'name', dir: 'asc' }
            const sortArrow = (field) => sort.field === field ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''
            const sortedRows = (playerRowsByCollector[collector.slug] || [])
              .map((row, origIdx) => ({ row, origIdx }))
              .sort(({ row: a }, { row: b }) => {
                if (sort.field === 'name') {
                  const na = (a.canonical_name || a.raw_name || '').toLowerCase()
                  const nb = (b.canonical_name || b.raw_name || '').toLowerCase()
                  return sort.dir === 'asc' ? na.localeCompare(nb, 'ru') : nb.localeCompare(na, 'ru')
                } else {
                  const ta = (parseInt(a.troop_g)||0) + (parseInt(a.troop_s)||0) + (parseInt(a.troop_m)||0)
                  const tb = (parseInt(b.troop_g)||0) + (parseInt(b.troop_s)||0) + (parseInt(b.troop_m)||0)
                  if (!ta && !tb) return 0
                  if (!ta) return 1
                  if (!tb) return -1
                  return sort.dir === 'asc' ? ta - tb : tb - ta
                }
              })
            return (
            <div style={{ overflowX: 'auto' }}>
              <div style={{ marginBottom: 8, textAlign: 'right' }}>
                <button className="chest-pill-btn chest-pill-btn--primary" onClick={() => savePlayerAliases(collector.slug)}>
                  {cx.savePlayerAliases}
                </button>
              </div>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>№</th>
                    <th>{cx.playerRawCol}</th>
                    <th style={{ cursor: 'pointer', userSelect: 'none' }}
                        onClick={() => toggleSort(collector.slug, 'name')}>
                      {cx.playerCanonicalCol}{sortArrow('name')}
                    </th>
                    <th>Звание</th>
                    <th style={{ cursor: 'pointer', userSelect: 'none' }}
                        onClick={() => toggleSort(collector.slug, 'troop')}>
                      Состав{sortArrow('troop')}
                    </th>
                    <th>Глава</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRows.map(({ row, origIdx }, idx) => (
                    <Fragment key={origIdx}>
                    <tr>
                      <td>{idx + 1}</td>
                      <td>{row.raw_name || '—'}</td>
                      <td>
                        <input
                          className="input-dark"
                          value={row.canonical_name || ''}
                          onChange={e => updatePlayerRow(collector.slug, origIdx, 'canonical_name', e.target.value)}
                        />
                      </td>
                      <td>
                        <select
                          className="input-dark"
                          value={row.rank || ''}
                          onChange={e => updatePlayerRow(collector.slug, origIdx, 'rank', e.target.value)}
                        >
                          {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                        </select>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 3, alignItems: 'center', flexWrap: 'nowrap' }}>
                          <select className="input-dark" value={row.troop_g || ''} style={{ width: 44 }}
                            onChange={e => updatePlayerRow(collector.slug, origIdx, 'troop_g', e.target.value)}>
                            <option value="">G</option>
                            {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                          <select className="input-dark" value={row.troop_s || ''} style={{ width: 44 }}
                            onChange={e => updatePlayerRow(collector.slug, origIdx, 'troop_s', e.target.value)}>
                            <option value="">S</option>
                            {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                          <select className="input-dark" value={row.troop_m || ''} style={{ width: 44 }}
                            onChange={e => updatePlayerRow(collector.slug, origIdx, 'troop_m', e.target.value)}>
                            <option value="">M</option>
                            {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                          {row.troop_g && row.troop_s && row.troop_m
                            ? <span style={{ fontSize: 13, fontWeight: 700, color: '#f9a825', marginLeft: 6, whiteSpace: 'nowrap' }}>
                                G{row.troop_g} S{row.troop_s} M{row.troop_m}
                              </span>
                            : <span style={{ fontSize: 12, color: '#6c7086', marginLeft: 6 }}>—</span>
                          }
                          <input className="input-dark" type="number" min={1} max={999}
                            placeholder={cx.heroPlaceholder} style={{ width: 70, marginLeft: 6 }}
                            value={row.hero_level ?? ''}
                            onChange={e => updatePlayerRow(collector.slug, origIdx, 'hero_level',
                              e.target.value.replace(/\D/g, '').slice(0, 3))} />
                        </div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="radio"
                          name={`leader-${collector.slug}`}
                          checked={leaderByCollector[collector.slug] === (row.canonical_name || row.raw_name)}
                          onClick={() => {
                            const name = row.canonical_name || row.raw_name
                            setLeaderByCollector(prev => ({
                              ...prev,
                              [collector.slug]: prev[collector.slug] === name ? null : name,
                            }))
                          }}
                          onChange={() => {}}
                        />
                      </td>
                    </tr>
                    {leaderByCollector[collector.slug] === (row.canonical_name || row.raw_name) && (
                      <tr key={`leader-excl-${origIdx}`}>
                        <td colSpan={6} style={{ paddingLeft: 24, paddingBottom: 10, background: '#1e1e2e' }}>
                          <div style={{ fontSize: 13, color: '#a6adc8', marginBottom: 6 }}>
                            Не считать в статистику:
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                            {(rowsByCollector[collector.slug] || [])
                              .filter(r => r.is_in_pattern)
                              .map(r => {
                                const label = r.custom_name || r.catalog_id
                                const isExcluded = (leaderExcludedByCollector[collector.slug] || [])
                                  .includes(r.catalog_id)
                                return (
                                  <label key={r.catalog_id}
                                    style={{ display: 'flex', alignItems: 'center', gap: 5,
                                             cursor: 'pointer', fontSize: 13, color: '#cdd6f4' }}>
                                    <input
                                      type="checkbox"
                                      checked={isExcluded}
                                      onChange={e => {
                                        setLeaderExcludedByCollector(prev => {
                                          const current = prev[collector.slug] || []
                                          const next = e.target.checked
                                            ? [...current, r.catalog_id]
                                            : current.filter(id => id !== r.catalog_id)
                                          return { ...prev, [collector.slug]: next }
                                        })
                                      }}
                                    />
                                    {label}
                                  </label>
                                )
                              })}
                          </div>
                        </td>
                      </tr>
                    )}
                    </Fragment>
                  ))}
                </tbody>
              </table>

              <button className="chest-pill-btn" onClick={() => addPlayerRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addPlayerRow}
              </button>
              <button className="chest-pill-btn chest-pill-btn--primary" onClick={() => savePlayerAliases(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.savePlayerAliases}
              </button>
            </div>
            )
          })()}

          {activeTab(collector.slug) === 'history' && (
            <div>
              {!historyByCollector[collector.slug] && (
                <button className="chest-pill-btn" onClick={() => loadHistory(collector.slug)}>
                  {cx.loadHistoryBtn}
                </button>
              )}
              {/* Статистика для подбора формулы квоты EM (спека 02): сезоны × игроки × Герой × квоты */}
              <button className="chest-pill-btn" style={{ marginLeft: 8 }} onClick={async () => {
                try {
                  const blob = await api.dashboardChestsStatsCsv(collector.slug)
                  const a = document.createElement('a')
                  a.href = URL.createObjectURL(blob)
                  a.download = `chests-stats-${collector.kingdom}-${collector.clan}.csv`
                  a.click()
                  URL.revokeObjectURL(a.href)
                } catch (e) { setMsg(e.message) }
              }}>{cx.statsBtn}</button>
              {historyByCollector[collector.slug]?.length === 0 && (
                <div className="text-muted">{cx.historyEmpty}</div>
              )}
              {historyByCollector[collector.slug]?.map(s => (
                <button
                  key={s.id}
                  className="chest-pill-btn"
                  style={{ display: 'block', marginBottom: 8 }}
                  onClick={() => loadSeasonDetail(collector.slug, s.id)}
                >
                  {formatPeriodPoint(s.period_start)} – {formatPeriodPoint(s.period_end)} · {s.total_points} очков
                </button>
              ))}
              {seasonDetailByCollector[collector.slug] && (
                <ChestSummaryTable
                  chestTypes={seasonDetailByCollector[collector.slug].data.chest_types}
                  players={seasonDetailByCollector[collector.slug].data.players}
                  targets={seasonDetailByCollector[collector.slug].data.targets || { points: null, chests: null }}
                  lang={lang}
                />
              )}
            </div>
          )}

          {/* Удалить коллектор — намеренно отдельно внизу карточки, подальше от ссылок
              наверху (владелец 2026-09-25: рядом с публичной ссылкой легко нажать случайно) */}
          <div style={{ marginTop: 20, paddingTop: 12, borderTop: '1px solid var(--outline)',
                       display: 'flex', justifyContent: 'flex-end', gap: 8, alignItems: 'center' }}>
            {confirmDeleteByCollector[collector.slug] ? (
              <>
                <span style={{ fontSize: 12, color: '#F87171' }}>{cx.deleteCollectorConfirm}</span>
                <button
                  className="chest-pill-btn chest-pill-btn--sm chest-pill-btn--solid-danger"
                  onClick={async () => {
                    try {
                      await api.dashboardChestsDelete(collector.slug)
                      setConfirmDeleteByCollector(prev => ({ ...prev, [collector.slug]: false }))
                      await refresh()
                    } catch (e) {
                      setMsg(e.message || cx.deleteCollectorBtn)
                    }
                  }}
                >{cx.deleteCollectorYes}</button>
                <button
                  className="chest-pill-btn chest-pill-btn--sm"
                  onClick={() => setConfirmDeleteByCollector(prev => ({ ...prev, [collector.slug]: false }))}
                >{cx.closeSeasonNo}</button>
              </>
            ) : (
              <button
                className="chest-pill-btn chest-pill-btn--sm chest-pill-btn--danger"
                onClick={() => setConfirmDeleteByCollector(prev => ({ ...prev, [collector.slug]: true }))}
              >{cx.deleteCollectorBtn}</button>
            )}
          </div>
        </div>
      ))}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
