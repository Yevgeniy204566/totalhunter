import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function ChestsPage() {
  const [collectors, setCollectors] = useState(null)
  const [rowsByCollector, setRowsByCollector] = useState({})
  const [playerRowsByCollector, setPlayerRowsByCollector] = useState({})
  const [activeTabByCollector, setActiveTabByCollector] = useState({})
  const [msg, setMsg] = useState('')
  const [loadError, setLoadError] = useState('')
  const [claimCode, setClaimCode] = useState('')
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
      for (const c of data.collectors) {
        nextRows[c.slug] = c.rows
        nextPlayerRows[c.slug] = c.player_alias_rows
      }
      setRowsByCollector(nextRows)
      setPlayerRowsByCollector(nextPlayerRows)
    } catch (e) {
      setLoadError(e.message || 'failed to load')
    }
  }
  useEffect(() => { refresh() }, [])

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
                                points: 0, is_in_pattern: false }],
    }))
  }

  async function save(slug) {
    await api.dashboardChestsSave(slug, rowsByCollector[slug])
    setMsg(cx.saved)
    await refresh()
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
    await api.dashboardChestsPlayerAliases(slug, playerRowsByCollector[slug])
    setMsg(cx.saved)
    await refresh()
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
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>{cx.rawCol}</th>
                    <th>{cx.catalogCol}</th>
                    <th>{cx.customNameCol}</th>
                    <th>{cx.pointsCol}</th>
                    <th>{cx.inPatternCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {rowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.raw_type || '—'}</td>
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
