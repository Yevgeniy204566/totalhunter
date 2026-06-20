import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function ChestsPage() {
  const [collectors, setCollectors] = useState(null)
  const [rowsByCollector, setRowsByCollector] = useState({})
  const [msg, setMsg] = useState('')
  const [claimCode, setClaimCode] = useState('')
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.chests
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Сундуки' : 'Total Hunter — Chests',
    description: lang === 'ru' ? 'Настройка сундуков клана.' : 'Configure your clan chests.',
  })

  async function refresh() {
    const data = await api.dashboardChests()
    setCollectors(data.collectors)
    const next = {}
    for (const c of data.collectors) next[c.slug] = c.rows
    setRowsByCollector(next)
  }
  useEffect(() => { refresh() }, [])

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

  if (!collectors) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>{cx.title}</h2>

      <div className="card" style={{ marginBottom: 16, maxWidth: 480 }}>
        <input
          value={claimCode}
          onChange={e => setClaimCode(e.target.value)}
          placeholder={cx.claimPlaceholder}
          style={{ marginRight: 8 }}
        />
        <button className="btn-secondary" onClick={claim}>{cx.claimBtn}</button>
      </div>

      {collectors.map(collector => (
        <div className="card" key={collector.slug} style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>{collector.kingdom} / {collector.clan}</div>
            <a href={collector.public_url} target="_blank" rel="noreferrer">{cx.publicLink}</a>
          </div>

          <div style={{ marginBottom: 12 }}>
            {cx.language}:
            <select
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

          <table style={{ width: '100%' }}>
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
                      value={row.custom_name || ''}
                      onChange={e => updateRow(collector.slug, i, 'custom_name', e.target.value || null)}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.points}
                      onChange={e => updateRow(collector.slug, i, 'points', parseInt(e.target.value, 10) || 0)}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={row.is_in_pattern}
                      onChange={e => updateRow(collector.slug, i, 'is_in_pattern', e.target.checked)}
                    />
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
        </div>
      ))}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
