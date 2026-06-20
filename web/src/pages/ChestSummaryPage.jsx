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

  return (
    <div className="page-content">
      <h2>{data.kingdom} / {data.clan}</h2>
      <table style={{ width: '100%' }}>
        <thead>
          <tr>
            <th>Player</th>
            {data.chest_types.map(t => <th key={t}>{t}</th>)}
            <th>Total</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          {data.players.map(p => (
            <tr key={p.name}>
              <td>{p.name}</td>
              {data.chest_types.map(t => <td key={t}>{p.counts[t] || 0}</td>)}
              <td>{p.total}</td>
              <td>{p.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
