import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function RosterPage() {
  const [collectors, setCollectors] = useState(null)
  const [selectedSlug, setSelectedSlug] = useState('')
  const [rows, setRows] = useState([])
  const [msg, setMsg] = useState('')
  const [loadError, setLoadError] = useState('')
  const [importText, setImportText] = useState('')
  const [showImport, setShowImport] = useState(false)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.roster

  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Участники' : 'Total Hunter — Roster',
    description: lang === 'ru' ? 'Список участников клана.' : 'Clan member roster.',
  })

  async function refresh() {
    try {
      const data = await api.dashboardRoster()
      setCollectors(data.collectors)
      if (data.collectors.length > 0) {
        const slug = selectedSlug || data.collectors[0].slug
        setSelectedSlug(slug)
        const c = data.collectors.find(c => c.slug === slug) || data.collectors[0]
        setRows(c.roster_rows.map(r => ({ ...r })))
      }
    } catch (e) {
      setLoadError(String(e))
    }
  }

  useEffect(() => { refresh() }, [])

  function handleSelectCollector(slug) {
    setSelectedSlug(slug)
    const c = collectors.find(c => c.slug === slug)
    setRows(c ? c.roster_rows.map(r => ({ ...r })) : [])
    setMsg('')
  }

  function addRow() {
    setRows(prev => [...prev, { raw_name: '', canonical_name: '' }])
  }

  function updateRow(idx, field, val) {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: val } : r))
  }

  function deleteRow(idx) {
    setRows(prev => prev.filter((_, i) => i !== idx))
  }

  async function save() {
    try {
      await api.dashboardRosterSave(selectedSlug, rows)
      setMsg(cx.saved)
      await refresh()
      setTimeout(() => setMsg(''), 3000)
    } catch (e) {
      setMsg(String(e))
    }
  }

  function handleImport() {
    try {
      const parsed = JSON.parse(importText)
      const names = parsed.names || parsed
      if (!Array.isArray(names)) throw new Error('Expected array or {names:[...]}')
      const imported = names
        .filter(n => typeof n === 'string' && n.trim())
        .map(n => ({ raw_name: n.trim(), canonical_name: n.trim() }))
      setRows(imported)
      setShowImport(false)
      setImportText('')
      setMsg(`Импортировано ${imported.length} записей — проверь и сохрани`)
    } catch (e) {
      setMsg('Ошибка парсинга JSON: ' + String(e))
    }
  }

  if (loadError) return <div style={{ padding: 32, color: '#f87171' }}>{loadError}</div>
  if (!collectors) return <div style={{ padding: 32, color: 'var(--on-surface-dim)' }}>{D.loading}</div>
  if (collectors.length === 0) return <div style={{ padding: 32, color: 'var(--on-surface-dim)' }}>{cx.noClan}</div>

  const selectedCollector = collectors.find(c => c.slug === selectedSlug)

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <h2 style={{ color: 'var(--accent)', marginBottom: 20 }}>{cx.title}</h2>

      {/* Clan selector */}
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
        <label style={{ color: 'var(--on-surface-dim)', fontSize: 14 }}>{cx.selectClan}:</label>
        <select
          value={selectedSlug}
          onChange={e => handleSelectCollector(e.target.value)}
          style={{
            background: 'var(--card)', color: 'var(--on-surface)',
            border: '1px solid var(--outline)', borderRadius: 6,
            padding: '6px 12px', fontSize: 14, cursor: 'pointer',
          }}
        >
          {collectors.map(c => (
            <option key={c.slug} value={c.slug}>
              {c.clan} ({c.kingdom})
            </option>
          ))}
        </select>
        <span style={{ color: 'var(--on-surface-dim)', fontSize: 13 }}>
          {rows.length} записей
        </span>
      </div>

      {/* Import button */}
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <button className="btn-primary" onClick={save} disabled={!selectedSlug}>
          {cx.save}
        </button>
        <button className="btn-secondary" onClick={() => setShowImport(v => !v)}>
          {cx.importBtn}
        </button>
        {msg && (
          <span style={{ color: msg.includes('рор') || msg.includes('rror') ? '#f87171' : '#4ade80', fontSize: 13 }}>
            {msg}
          </span>
        )}
      </div>

      {/* JSON import panel */}
      {showImport && (
        <div style={{
          marginBottom: 16, padding: 16,
          background: 'var(--card)', border: '1px solid var(--outline)', borderRadius: 8,
        }}>
          <div style={{ fontSize: 13, color: 'var(--on-surface-dim)', marginBottom: 8 }}>
            {cx.importHint}
          </div>
          <textarea
            value={importText}
            onChange={e => setImportText(e.target.value)}
            rows={6}
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'var(--bg)', color: 'var(--on-surface)',
              border: '1px solid var(--outline)', borderRadius: 6,
              padding: 8, fontSize: 12, fontFamily: 'monospace',
              resize: 'vertical',
            }}
            placeholder='{"names": ["AEGON", "AJAX The Ant", ...]}'
          />
          <button className="btn-primary" onClick={handleImport} style={{ marginTop: 8 }}>
            OK
          </button>
        </div>
      )}

      {/* Table */}
      {rows.length === 0 ? (
        <div style={{ color: 'var(--on-surface-dim)', fontSize: 14, padding: '20px 0' }}>
          {cx.empty}
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="chest-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ width: 40 }}>#</th>
                <th>{cx.rawName}</th>
                <th>{cx.canonName}</th>
                <th style={{ width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx}>
                  <td style={{ color: 'var(--on-surface-dim)', fontSize: 12, textAlign: 'center' }}>
                    {idx + 1}
                  </td>
                  <td>
                    <input
                      value={row.raw_name}
                      onChange={e => updateRow(idx, 'raw_name', e.target.value)}
                      style={{
                        background: 'transparent', color: 'var(--on-surface)',
                        border: '1px solid var(--outline)', borderRadius: 4,
                        padding: '4px 8px', width: '100%', fontSize: 13,
                      }}
                    />
                  </td>
                  <td>
                    <input
                      value={row.canonical_name}
                      onChange={e => updateRow(idx, 'canonical_name', e.target.value)}
                      style={{
                        background: 'transparent', color: 'var(--on-surface)',
                        border: '1px solid var(--outline)', borderRadius: 4,
                        padding: '4px 8px', width: '100%', fontSize: 13,
                      }}
                    />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      onClick={() => deleteRow(idx)}
                      style={{
                        background: 'none', border: 'none', color: '#f87171',
                        cursor: 'pointer', fontSize: 16, lineHeight: 1,
                      }}
                      title="Удалить"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        <button className="btn-secondary" onClick={addRow}>{cx.addRow}</button>
        <button className="btn-primary" onClick={save} disabled={!selectedSlug}>{cx.save}</button>
      </div>
    </div>
  )
}
