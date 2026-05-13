import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import ReferralTree from '../components/ReferralTree.jsx'

const HEADER_H = 52

export default function ReferralTreePage() {
  const [user, setUser] = useState(null)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const r = D.referrals

  useEffect(() => { api.me().then(setUser).catch(() => {}) }, [])

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)', overflow: 'hidden' }}>

      {/* Top bar */}
      <div style={{
        height: HEADER_H, flexShrink: 0,
        background: 'var(--header-bg, rgba(8,12,26,0.95))',
        borderBottom: '1px solid var(--outline)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        display: 'flex', alignItems: 'center', padding: '0 20px', gap: 16,
        boxShadow: '0 2px 24px rgba(61,127,255,0.08)',
      }}>
        <Link to="/dashboard/referrals" style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontSize: 13, fontWeight: 700, color: 'var(--accent)',
          textDecoration: 'none', padding: '6px 12px', borderRadius: 8,
          border: '1px solid rgba(61,127,255,0.3)',
          background: 'rgba(61,127,255,0.08)',
          transition: 'background 0.15s',
        }}>← {lang === 'ru' ? 'Назад' : 'Back'}</Link>

        <span style={{ fontSize: 15, fontWeight: 800, color: '#fff', letterSpacing: 0.3 }}>
          {r.treeTitle}
        </span>

        {user && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--on-surface2)', fontFamily: 'monospace' }}>
            {user.email.slice(0, 3)}*** · {user.referrals?.l1 ?? 0} L1 · {user.referrals?.l2 ?? 0} L2 · {user.referrals?.l3 ?? 0} L3
          </span>
        )}
      </div>

      {/* Full-height canvas */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {user
          ? <ReferralTree currentUser={user} canvasHeight={`calc(100vh - ${HEADER_H}px)`} />
          : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
                {D.loading}
              </div>
            </div>
          )
        }
      </div>
    </div>
  )
}
