import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchAncientsPublic, postPublicAddSelf } from '../api.js'
import AncientPublicTable from '../components/AncientPublicTable.jsx'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['5', '6', '7', '8', '9']

export default function PublicAncientsPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [addSelfForm, setAddSelfForm] = useState({ name: '', rank: '', g: '', s: '', m: '' })
  const [addSelfSimilar, setAddSelfSimilar] = useState('')
  const [addSelfError, setAddSelfError] = useState('')
  const [addSelfSaving, setAddSelfSaving] = useState(false)

  async function handleAddSelf(useNameOverride) {
    const name = useNameOverride || addSelfForm.name.trim()
    if (!name) return
    const { g, s, m } = addSelfForm
    const troop_level = g && s && m ? `G${g} S${s} M${m}` : null
    setAddSelfSaving(true)
    setAddSelfError('')
    try {
      await postPublicAddSelf(slug, name, addSelfForm.rank || null, troop_level)
      setAddSelfForm({ name: '', rank: '', g: '', s: '', m: '' })
      setAddSelfSimilar('')
      fetchAncientsPublic(slug).then(setData).catch(e => setError(e.message || 'not found'))
    } catch (e) {
      if (e.similarName) setAddSelfSimilar(e.similarName)
      else setAddSelfError(e.message || 'Ошибка сохранения')
    } finally {
      setAddSelfSaving(false)
    }
  }

  useEffect(() => {
    fetchAncientsPublic(slug).then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug])

  if (error) return <div className="page-content">{error}</div>
  if (!data) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h1 className="public-summary-title">
        <span className="public-kingdom-label">{data.kingdom}/</span>
        <span className="public-clan-label">{data.clan}</span>
      </h1>

      <div className="public-season-info">
        <button
          className="btn-secondary"
          style={{ fontSize: 13, padding: '4px 12px', marginLeft: 'auto' }}
          onClick={() => {
            if (editMode) { setEditMode(false); fetchAncientsPublic(slug).then(setData).catch(e => setError(e.message || 'not found')) }
            else { setEditMode(true) }
          }}
        >
          {editMode ? '✕ Закрыть' : '✏️ Ввести состав'}
        </button>
      </div>

      <div className="public-summary-divider" />

      <AncientPublicTable
        roster={data.roster}
        quotaThresholds={data.quota_thresholds}
        editMode={editMode}
        collectorSlug={slug}
      />

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Меня нет в списке — добавить себя</div>
        {addSelfSimilar && (
          <div style={{ marginBottom: 8, fontSize: 13, color: '#f9a825' }}>
            Похоже на «{addSelfSimilar}» — использовать это имя?
            <button className="btn-secondary" style={{ fontSize: 12, marginLeft: 8, padding: '2px 8px' }}
              onClick={() => handleAddSelf(addSelfSimilar)}>
              Да, это я
            </button>
            <button className="btn-secondary" style={{ fontSize: 12, marginLeft: 4, padding: '2px 8px' }}
              onClick={() => setAddSelfSimilar('')}>
              Нет, добавить как есть
            </button>
          </div>
        )}
        {addSelfError && (
          <div style={{ marginBottom: 8, fontSize: 13, color: '#F87171' }}>{addSelfError}</div>
        )}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            className="input-dark"
            placeholder="Имя игрока"
            value={addSelfForm.name}
            onChange={e => setAddSelfForm(prev => ({ ...prev, name: e.target.value }))}
            style={{ minWidth: 140 }}
          />
          <select className="input-dark"
            value={addSelfForm.rank}
            onChange={e => setAddSelfForm(prev => ({ ...prev, rank: e.target.value }))}>
            {RANKS.map(r => <option key={r} value={r}>{r || 'Звание'}</option>)}
          </select>
          {['g', 's', 'm'].map(k => (
            <select key={k} className="input-dark" style={{ width: 44 }}
              value={addSelfForm[k]}
              onChange={e => setAddSelfForm(prev => ({ ...prev, [k]: e.target.value }))}>
              <option value="">{k.toUpperCase()}</option>
              {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          ))}
          <button className="btn-primary" disabled={addSelfSaving} onClick={() => handleAddSelf()}>
            Добавить
          </button>
        </div>
      </div>
    </div>
  )
}
