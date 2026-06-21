import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'

export default function ChestSummaryPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchChestSummary(slug).then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug])

  if (error) return <div className="page-content">{error}</div>
  if (!data) return <div className="page-content text-muted">...</div>

  const updatedLabel = data.updated_at
    ? new Date(data.updated_at).toLocaleString()
    : '—'

  return (
    <div className="page-content">
      <h1 className="gradient-text public-summary-title">{data.kingdom} / {data.clan}</h1>
      <div className="public-summary-updated">Последнее обновление: {updatedLabel}</div>
      <div className="public-summary-divider" />

      <div className="public-table-wrap">
        <table className="public-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Очки</th>
              <th>Всего сундуков</th>
              {data.chest_types.map(t => <th key={t}>{t}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.players.map(p => (
              <tr key={p.name}>
                <td>{p.name}</td>
                <td className="public-points-cell">{p.points}</td>
                <td className={p.total === 0 ? 'public-cell-zero' : ''}>{p.total}</td>
                {data.chest_types.map(t => {
                  const value = p.counts[t] || 0
                  return (
                    <td key={t} className={value === 0 ? 'public-cell-zero' : ''}>
                      {value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
