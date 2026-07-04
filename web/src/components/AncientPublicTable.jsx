import { useEffect, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'
import { rowShortfallClass } from '../lib/ancientQuota.js'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['', '5', '6', '7', '8', '9']

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

function fmtNum(n, fractionDigits = 0) {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

export default function AncientPublicTable({ roster, quotaThresholds, editMode, collectorSlug }) {
  const [editRows, setEditRows] = useState({})
  const [saving, setSaving] = useState(null)
  const [savedRows, setSavedRows] = useState({})

  useEffect(() => {
    if (!editMode) return
    const init = {}
    roster.forEach(p => {
      const { g, s, m } = parseTroop(p.troop_level)
      init[p.player_name] = { rank: p.rank || '', g, s, m }
    })
    setEditRows(init)
  }, [editMode, roster])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    const troop = row.g && row.s && row.m ? `G${row.g} S${row.s} M${row.m}` : null
    setSaving(playerName)
    try {
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, troop)
      setSavedRows(prev => ({ ...prev, [playerName]: true }))
      setTimeout(() => setSavedRows(prev => { const n = { ...prev }; delete n[playerName]; return n }), 3000)
    } catch (e) {
      alert('Ошибка сохранения: ' + e.message)
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="public-table-wrap">
      <table className="public-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Имя</th>
            <th>Звание</th>
            <th>Войска</th>
            {editMode && <th></th>}
            <th>Очки</th>
            <th>Квота</th>
            <th>Недобор</th>
          </tr>
        </thead>
        <tbody>
          {roster.map((p, i) => (
            <tr key={p.player_name} className={rowShortfallClass(p.shortfall_pct, quotaThresholds)}>
              <td>{i + 1}</td>
              <td title={p.player_name}>{p.player_name}</td>
              <td>
                {editMode ? (
                  <select
                    value={editRows[p.player_name]?.rank || ''}
                    onChange={e => setEditRows(prev => ({
                      ...prev,
                      [p.player_name]: { ...prev[p.player_name], rank: e.target.value },
                    }))}
                    style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                  >
                    {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                  </select>
                ) : (p.rank || '—')}
              </td>
              <td>
                {editMode ? (
                  <div style={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'nowrap' }}>
                    {['g', 's', 'm'].map((k, idx) => (
                      <select
                        key={k}
                        value={editRows[p.player_name]?.[k] || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.player_name]: { ...prev[p.player_name], [k]: e.target.value },
                        }))}
                        style={{ fontSize: 11, padding: '2px 2px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4, width: 36 }}
                      >
                        <option value="">{'GSM'[idx]}</option>
                        {TIERS.slice(1).map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    ))}
                  </div>
                ) : (p.troop_level || '—')}
              </td>
              {editMode && (
                <td>
                  <button
                    onClick={() => handleSave(p.player_name)}
                    disabled={saving === p.player_name}
                    style={{ fontSize: 12, padding: '2px 8px', cursor: 'pointer',
                      background: savedRows[p.player_name] ? '#1e3a1e' : '#313244',
                      color: savedRows[p.player_name] ? '#a6e3a1' : '#cdd6f4',
                      border: `1px solid ${savedRows[p.player_name] ? '#a6e3a1' : '#45475a'}`, borderRadius: 4 }}
                  >
                    {saving === p.player_name ? '...' : savedRows[p.player_name] ? '✓' : '💾'}
                  </button>
                </td>
              )}
              <td>{fmtNum(p.points)}</td>
              <td>{fmtNum(p.quota, 2)}</td>
              <td>{p.shortfall_pct != null ? `${p.shortfall_pct.toFixed(1)}%` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
