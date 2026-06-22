import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

function displayName(row, catalogOptions) {
  if (row.raw_type) return row.raw_type
  if (row.custom_name) return row.custom_name
  if (row.catalog_id) {
    const opt = catalogOptions.find(o => o.catalog_id === row.catalog_id)
    if (opt) return opt.label
  }
  return '—'
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
        nextPlayerRows[c.slug] = c.player_alias_rows
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

  if (loadError) return <div className="page-content text-muted">{loadError}</div>
  if (!collectors) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>{cx.title}</h2>

      <div className="card" style={{ marginBottom: 16, maxWidth: 480 }}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>{collector.kingdom} / {collector.clan}</div>
            <a href={collector.public_url} target="_blank" rel="noreferrer">{cx.publicLink}</a>
          </div>

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

          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.seasonTitle}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              <select
                className="input-dark"
                style={{ width: 'auto' }}
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
              <input
                className="input-dark" style={{ width: 'auto' }} type="datetime-local"
                value={seasonByCollector[collector.slug]?.period_start || ''}
                onChange={e => updateSeasonField(collector.slug, 'period_start', e.target.value)}
              />
              <input
                className="input-dark" style={{ width: 'auto' }} type="datetime-local"
                value={seasonByCollector[collector.slug]?.period_end || ''}
                onChange={e => updateSeasonField(collector.slug, 'period_end', e.target.value)}
              />
              <input
                className="input-dark" style={{ width: 120 }} type="number"
                placeholder={cx.targetPointsLabel}
                value={seasonByCollector[collector.slug]?.target_points ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'target_points', e.target.value)}
              />
              <input
                className="input-dark" style={{ width: 120 }} type="number"
                placeholder={cx.targetChestsLabel}
                value={seasonByCollector[collector.slug]?.target_chests ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'target_chests', e.target.value)}
              />
            </div>
            <button className="btn-primary" onClick={() => saveSeason(collector.slug)}>
              {cx.saveSeason}
            </button>
          </div>

          <div className="chest-tabs">
            <button
              className={`chest-tab ${activeTab(collector.slug) === 'chests' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'chests')}
            >
              {cx.chestsTab}
            </button>
            <button
              className={`chest-tab ${activeTab(collector.slug) === 'players' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'players')}
            >
              {cx.playersTab}
            </button>
          </div>

          {activeTab(collector.slug) === 'chests' && (
            <>
              {presets && Object.keys(presets).length > 0 && (
                <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <select
                    className="input-dark"
                    style={{ width: 'auto' }}
                    value={presetChoiceByCollector[collector.slug] || Object.keys(presets)[0]}
                    onChange={e => setPresetChoiceByCollector(prev => ({ ...prev, [collector.slug]: e.target.value }))}
                  >
                    {Object.keys(presets).map(name => <option key={name} value={name}>{name}</option>)}
                  </select>
                  <button
                    className="btn-secondary"
                    onClick={() => loadPreset(collector.slug, presetChoiceByCollector[collector.slug] || Object.keys(presets)[0])}
                  >
                    {cx.loadPresetBtn}
                  </button>
                </div>
              )}
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>{cx.rawCol}</th>
                    <th>{cx.catalogCol}</th>
                    <th>{cx.customNameCol}</th>
                    <th>{cx.pointsCol}</th>
                    <th>{cx.inPatternCol}</th>
                    <th>{cx.quotaCol}</th>
                    <th>{cx.totalEverCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {rowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{displayName(row, collector.catalog_options)}</td>
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

              <button className="btn-secondary" onClick={() => addRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addRow}
              </button>
              <button className="btn-primary" onClick={() => save(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.save}
              </button>
            </>
          )}

          {activeTab(collector.slug) === 'players' && (
            <>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>{cx.playerRawCol}</th>
                    <th>{cx.playerCanonicalCol}</th>
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
            </>
          )}
        </div>
      ))}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
