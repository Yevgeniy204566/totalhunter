import { useEffect, useState } from 'react'
import { api } from '../api.js'

const TYPE_LABEL = {
  purchase:      'Purchase',
  credit_use:    'Hunt',
  trial:         'Trial bonus',
  ref_welcome:   'Referral welcome',
  ref_earning:   'Referral earning',
  ref_transfer:  'Ref → main',
  manual_adjust: 'Manual adjustment',
}

export default function TransactionsPage() {
  const [data, setData] = useState(null)

  useEffect(() => { api.transactions().then(setData) }, [])

  if (!data) return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>Transactions</h2>
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ color: 'var(--on-surface2)' }}>
              <th style={{ textAlign: 'left', padding: '8px 0' }}>Type</th>
              <th style={{ textAlign: 'right', padding: '8px 0' }}>Amount</th>
              <th style={{ textAlign: 'left', padding: '8px 12px' }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr><td colSpan={3} className="text-muted" style={{ padding: '16px 0' }}>No transactions yet</td></tr>
            )}
            {data.items.map((t, i) => (
              <tr key={i} style={{ borderTop: '1px solid var(--separator)' }}>
                <td style={{ padding: '8px 0' }}>{TYPE_LABEL[t.type] || t.type}</td>
                <td style={{
                  padding: '8px 0', textAlign: 'right', fontWeight: 500,
                  color: t.amount > 0 ? '#4caf50' : 'var(--error-text)',
                }}>
                  {t.amount > 0 ? '+' : ''}{t.amount}
                </td>
                <td style={{ padding: '8px 12px' }} className="text-muted">
                  {t.created_at.slice(0, 16).replace('T', ' ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
