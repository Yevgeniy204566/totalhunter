import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchAncientsPublic } from '../api.js'
import AncientPublicTable from '../components/AncientPublicTable.jsx'

export default function PublicAncientsPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [editMode, setEditMode] = useState(false)

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
    </div>
  )
}
