import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function HuntsPage() {
  const [data, setData] = useState(null)

  useEffect(() => { api.hunts().then(setData) }, [])

  if (!data) return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>Hunt History</h2>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard title="Today"  value={data.today} />
        <StatCard title="7 days" value={data.week} />
        <StatCard title="Total"  value={data.total} />
      </div>
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ color: 'var(--on-surface2)' }}>
              <th style={{ textAlign: 'left', padding: '8px 0' }}>Type</th>
              <th style={{ textAlign: 'left', padding: '8px 0' }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr><td colSpan={2} className="text-muted" style={{ padding: '16px 0' }}>No hunts yet</td></tr>
            )}
            {data.items.map((h, i) => (
              <tr key={i} style={{ borderTop: '1px solid var(--separator)' }}>
                <td style={{ padding: '8px 0', textTransform: 'capitalize' }}>{h.hunt_type}</td>
                <td style={{ padding: '8px 0' }} className="text-muted">
                  {h.created_at.slice(0, 16).replace('T', ' ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatCard({ title, value }) {
  return (
    <div className="card" style={{ minWidth: 120 }}>
      <div className="text-muted" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 600 }}>{value}</div>
    </div>
  )
}
