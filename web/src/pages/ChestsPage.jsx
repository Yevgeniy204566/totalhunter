import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'
import ChestSummaryTable from '../components/ChestSummaryTable.jsx'

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
      for (const c of data.collectors) {
        nextRows[c.slug] = c.rows
        nextPlayerRows[c.slug] = c.player_alias_rows.map(r => {
          const { g, s, m } = parseTroop(r.troop_level)
          return { ...r, troop_g: g, troop_s: s, troop_m: m }
        })
        nextSeason[c.slug] = {
          timezone_offset_minutes: c.timezone_offset_minutes,
          period_start: c.period_start ? c.period_start.slice(0, 16) : '',
          period_end: c.period_end ? c.period_end.slice(0, 16) : '',
          target_points: c.target_points,
          target_chests: c.target_chests,
        }
      }
      setRowsByCollector(nextRows)
      setPlayerRowsByCollector(nextPlayerRows)
      setSeasonByCollector(nextSeason)
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
                                points: 0, is_in_pattern: false, counts_toward_quota: false }],
    }))
  }

  function loadPreset(slug, presetName) {
    const preset = presets?.[presetName]
    if (!preset) return
    setRowsByCollector(prev => {
      const rows = [...(prev[slug] || [])]
      for (const item of preset) {
        const idx = rows.findIndex(r => r.catalog_id === item.catalog_id)
        if (idx >= 0) {
          rows[idx] = { ...rows[idx], points: item.points, is_in_pattern: item.is_in_pattern }
        } else {
          rows.push({ raw_type: null, catalog_id: item.catalog_id, custom_name: null,
                     points: item.points, is_in_pattern: item.is_in_pattern,
                     counts_toward_quota: false })
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
        }))
      await api.dashboardChestsPlayerProfiles(slug, profileRows)
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
      target_chests: s.target_chests === '' || s.target_chests == null ? null : Number(s.target_chests),
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

      <div className="card" style={{ marginBottom: 16, maxWidth: 600 }}>
        <input
          className="input-dark"
          value={claimCode}
          onChange={e => setClaimCode(e.target.value)}
          placeholder={cx.claimPlaceholder}
          style={{ marginBottom: 8 }}
        />
        <button className="btn-secondary" onClick={claim}>{cx.claimBtn}</button>
      </div>

      {collectors.length === 0 && <div className="text-muted" style={{ marginTop: 12 }}>{cx.noCollectors}</div>}

      {collectors.map(collector => (
        <div className="card" key={collector.slug} style={{ marginBottom: 24 }}>
          {/* Header: kingdom/clan left | links stacked right */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{collector.kingdom} / {collector.clan}</div>
            <div style={{ textAlign: 'right' }}>
              {collector.short_url && (
                <div>
                  <a href={collector.short_url} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: '#60A5FA' }}>
                    {collector.short_url.replace('https://', '')}
                  </a>
                </div>
              )}
              <div>
                <a href={collector.public_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                  {cx.publicLink}
                </a>
              </div>
            </div>
          </div>

          {/* Language + token */}
          <div style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
            {cx.language}:
            <select
              className="input-dark"
              style={{ width: 'auto' }}
              value={collector.language || ''}
              onChange={e => changeLanguage(collector.slug, e.target.value)}
            >
              <option value="ru">ru</option>
              <option value="en">en</option>
            </select>
            <button className="btn-secondary" onClick={() => genToken(collector.slug)}>
              {cx.generateToken}
            </button>
          </div>

          {/* Season settings */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.seasonTitle}</div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8, overflowX: 'auto', paddingBottom: 2 }}>
              <select
                className="input-dark"
                style={{ width: 120, flexShrink: 0 }}
                value={seasonByCollector[collector.slug]?.timezone_offset_minutes ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'timezone_offset_minutes', e.target.value)}
              >
                <option value="">{cx.timezoneLabel}</option>
                {[-720, -660, -600, -540, -480, -420, -360, -300, -240, -210, -180, -120, -60, 0,
                  60, 120, 180, 210, 240, 270, 300, 330, 345, 360, 390, 420, 480, 540, 570, 600,
                  630, 660, 720, 765, 780, 840].map(m => (
                  <option key={m} value={m}>
                    UTC{m >= 0 ? '+' : '-'}{String(Math.floor(Math.abs(m) / 60)).padStart(2, '0')}:{String(Math.abs(m) % 60).padStart(2, '0')}
                  </option>
                ))}
              </select>
              <input className="input-dark" style={{ width: 170, flexShrink: 0 }} type="datetime-local"
                value={seasonByCollector[collector.slug]?.period_start || ''}
                onChange={e => updateSeasonField(collector.slug, 'period_start', e.target.value)}
              />
              <input className="input-dark" style={{ width: 170, flexShrink: 0 }} type="datetime-local"
                value={seasonByCollector[collector.slug]?.period_end || ''}
                onChange={e => updateSeasonField(collector.slug, 'period_end', e.target.value)}
              />
              <input className="input-dark" style={{ width: 100, flexShrink: 0 }} type="number"
                placeholder={cx.targetPointsLabel}
                value={seasonByCollector[collector.slug]?.target_points ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'target_points', e.target.value)}
              />
              <input className="input-dark" style={{ width: 100, flexShrink: 0 }} type="number"
                placeholder={cx.targetChestsLabel}
                value={seasonByCollector[collector.slug]?.target_chests ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'target_chests', e.target.value)}
              />
            </div>
            {/* Buttons: Save left, Close season far right */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button className="btn-green" onClick={() => saveSeason(collector.slug)}>
                {cx.saveSeason}
              </button>
              {collector.period_end && (
                confirmCloseByCollector[collector.slug] ? (
                  <>
                    <span style={{ fontSize: 13, color: '#F87171', marginLeft: 'auto' }}>{cx.closeSeasonConfirmText}</span>
                    <button className="btn-primary" style={{ background: '#DC2626', boxShadow: 'none' }}
                      onClick={() => closeSeason(collector.slug)}
                    >{cx.closeSeasonYes}</button>
                    <button className="btn-secondary"
                      onClick={() => setConfirmCloseByCollector(prev => ({ ...prev, [collector.slug]: false }))}
                    >{cx.closeSeasonNo}</button>
                  </>
                ) : (
                  <button
                    className="btn-secondary"
                    style={{ marginLeft: 'auto', color: '#F87171', borderColor: '#F8717144' }}
                    onClick={() => setConfirmCloseByCollector(prev => ({ ...prev, [collector.slug]: true }))}
                  >{cx.closeSeasonBtn}</button>
                )
              )}
            </div>
          </div>

          <div className="chest-tabs">
            <button className={`chest-tab ${activeTab(collector.slug) === 'chests' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'chests')}>{cx.chestsTab}</button>
            <button className={`chest-tab ${activeTab(collector.slug) === 'players' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'players')}>{cx.playersTab}</button>
            <button className={`chest-tab ${activeTab(collector.slug) === 'history' ? 'chest-tab--active' : ''}`}
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
                    <button className="btn-secondary"
                      onClick={() => loadPreset(collector.slug, presetChoiceByCollector[collector.slug] || Object.keys(presets)[0])}
                    >{cx.loadPresetBtn}</button>
                  </>
                )}
                <button className="btn-primary" onClick={() => save(collector.slug)}>{cx.save}</button>
                <span style={{ fontWeight: 600, marginLeft: 8, color: 'var(--on-surface2)' }}>
                  {cx.grandTotalLabel} {(rowsByCollector[collector.slug] || []).reduce((sum, row) => sum + (row.total_ever ?? 0), 0)}
                </span>
              </div>
              <div style={{ overflowX: 'auto' }}>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: 220 }}>{cx.rawCol}</th>
                    <th style={{ minWidth: 240 }}>{cx.catalogCol}</th>
                    <th style={{ minWidth: 150 }}>{cx.customNameCol}</th>
                    <th style={{ minWidth: 70 }}>{cx.pointsCol}</th>
                    <th style={{ minWidth: 90 }}>{cx.inPatternCol}</th>
                    <th style={{ minWidth: 90 }}>{cx.quotaCol}</th>
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
                      <td>
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
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={row.is_in_pattern}
                            onChange={e => updateRow(collector.slug, i, 'is_in_pattern', e.target.checked)}
                          />
                          <span className="slider"></span>
                        </label>
                      </td>
                      <td>
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={row.counts_toward_quota}
                            onChange={e => updateRow(collector.slug, i, 'counts_toward_quota', e.target.checked)}
                          />
                          <span className="slider"></span>
                        </label>
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--on-surface2)' }}>
                        {row.total_ever ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <button className="btn-secondary" onClick={() => addRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addRow}
              </button>
              <button className="btn-primary" onClick={() => save(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.save}
              </button>
            </>
          )}

          {activeTab(collector.slug) === 'players' && (
            <div style={{ overflowX: 'auto' }}>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>{cx.playerRawCol}</th>
                    <th>{cx.playerCanonicalCol}</th>
                    <th>Звание</th>
                    <th>Состав</th>
                  </tr>
                </thead>
                <tbody>
                  {playerRowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.raw_name || '—'}</td>
                      <td>
                        <input
                          className="input-dark"
                          value={row.canonical_name || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'canonical_name', e.target.value)}
                        />
                      </td>
                      <td>
                        <select
                          className="input-dark"
                          value={row.rank || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'rank', e.target.value)}
                        >
                          {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                        </select>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 3, alignItems: 'center' }}>
                          <select className="input-dark" value={row.troop_g || ''} style={{ width: 44 }}
                            onChange={e => updatePlayerRow(collector.slug, i, 'troop_g', e.target.value)}>
                            <option value="">G</option>
                            {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                          <select className="input-dark" value={row.troop_s || ''} style={{ width: 44 }}
                            onChange={e => updatePlayerRow(collector.slug, i, 'troop_s', e.target.value)}>
                            <option value="">S</option>
                            {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                          <select className="input-dark" value={row.troop_m || ''} style={{ width: 44 }}
                            onChange={e => updatePlayerRow(collector.slug, i, 'troop_m', e.target.value)}>
                            <option value="">M</option>
                            {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <button className="btn-secondary" onClick={() => addPlayerRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addPlayerRow}
              </button>
              <button className="btn-primary" onClick={() => savePlayerAliases(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.savePlayerAliases}
              </button>
            </div>
          )}

          {activeTab(collector.slug) === 'history' && (
            <div>
              {!historyByCollector[collector.slug] && (
                <button className="btn-secondary" onClick={() => loadHistory(collector.slug)}>
                  {cx.loadHistoryBtn}
                </button>
              )}
              {historyByCollector[collector.slug]?.length === 0 && (
                <div className="text-muted">{cx.historyEmpty}</div>
              )}
              {historyByCollector[collector.slug]?.map(s => (
                <button
                  key={s.id}
                  className="btn-secondary"
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
                />
              )}
            </div>
          )}
        </div>
      ))}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
