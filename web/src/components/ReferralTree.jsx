import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const COLORS = { l1: '#3D7FFF', l2: '#B060FF', l3: '#FFD166' }

function NodeCard({ node, level, expandedIds, onToggle }) {
  const color = COLORS[level]
  const children = level === 'l1' ? node.l2 : level === 'l2' ? node.l3 : []
  const hasChildren = children.length > 0
  const isExpanded = expandedIds.has(node.id)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div
        onClick={() => hasChildren && onToggle(node.id)}
        style={{
          background: '#0d1628', border: `1px solid ${color}44`,
          borderRadius: 10, padding: '10px 14px', minWidth: 130, textAlign: 'center',
          cursor: hasChildren ? 'pointer' : 'default',
          transition: 'transform 0.15s',
        }}
        onMouseEnter={e => hasChildren && (e.currentTarget.style.transform = 'translateY(-2px)')}
        onMouseLeave={e => (e.currentTarget.style.transform = 'none')}
      >
        <div style={{
          display: 'inline-block', padding: '2px 7px', borderRadius: 4,
          fontSize: 9, fontWeight: 800, letterSpacing: 1, marginBottom: 6,
          background: `${color}18`, color, border: `1px solid ${color}44`,
        }}>
          {level.toUpperCase()}
        </div>
        <div style={{ fontSize: 11, color: '#e0e8ff', fontWeight: 600, marginBottom: 4, fontFamily: 'monospace' }}>
          {node.email_masked}
        </div>
        <div style={{ fontSize: 10, color: '#6070a0', marginBottom: 4 }}>
          {node.created_at}
        </div>
        <div style={{ fontSize: 13, fontWeight: 800, color: '#FFD166', textShadow: '0 0 8px rgba(255,209,102,0.4)' }}>
          {node.credits} ◆
        </div>
        {hasChildren && (
          <button
            onClick={e => { e.stopPropagation(); onToggle(node.id) }}
            style={{
              marginTop: 7, padding: '3px 10px', borderRadius: 5,
              fontSize: 10, fontWeight: 700, border: `1px solid ${color}44`,
              background: `${color}18`, color, cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {isExpanded ? `▲ ${children.length}` : `▶ ${children.length}`}
          </button>
        )}
      </div>

      {hasChildren && isExpanded && (
        <ChildRow nodes={children} level={level === 'l1' ? 'l2' : 'l3'} expandedIds={expandedIds} onToggle={onToggle} />
      )}
    </div>
  )
}

function ChildRow({ nodes, level, expandedIds, onToggle }) {
  const color = COLORS[level]
  return (
    <div style={{ paddingTop: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
      <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: 2, height: 20, background: `${color}44` }} />
      <div style={{ position: 'relative', display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        {nodes.length > 1 && (
          <div style={{ position: 'absolute', top: 0, left: 8, right: 8, height: 2, background: `${color}25` }} />
        )}
        {nodes.map(node => (
          <div key={node.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ width: 2, height: 16, background: `${color}35` }} />
            <NodeCard node={node} level={level} expandedIds={expandedIds} onToggle={onToggle} />
          </div>
        ))}
      </div>
    </div>
  )
}

function DesktopTree({ treeData, currentUser, expandedIds, onToggle, showAllL1, onShowAll, onHideAll }) {
  const visible = showAllL1 ? treeData.l1 : treeData.l1.slice(0, 5)
  const remaining = treeData.l1.length - 5

  return (
    <div style={{ overflowX: 'auto', paddingBottom: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 'max-content' }}>
        {/* Root */}
        <div style={{
          background: 'linear-gradient(135deg,#1e2d50,#2a1a4a)',
          border: '1px solid rgba(61,127,255,0.6)',
          borderRadius: 10, padding: '10px 20px', textAlign: 'center',
        }}>
          <div style={{
            fontSize: 9, fontWeight: 800, padding: '2px 10px', borderRadius: 4,
            display: 'inline-block', background: 'linear-gradient(135deg,#3D7FFF,#B060FF)',
            color: '#fff', marginBottom: 6,
          }}>ВЫ</div>
          <div style={{ fontSize: 11, color: '#e0e8ff', fontFamily: 'monospace' }}>
            {currentUser.email.slice(0, 3)}***
          </div>
        </div>

        {/* L1 row */}
        <div style={{ paddingTop: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
          <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: 2, height: 20, background: 'rgba(61,127,255,0.4)' }} />
          <div style={{ position: 'relative', display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            {visible.length > 1 && (
              <div style={{ position: 'absolute', top: 0, left: 8, right: 8, height: 2, background: 'rgba(61,127,255,0.25)' }} />
            )}
            {visible.map(node => (
              <div key={node.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ width: 2, height: 16, background: 'rgba(61,127,255,0.3)' }} />
                <NodeCard node={node} level="l1" expandedIds={expandedIds} onToggle={onToggle} />
              </div>
            ))}
            {!showAllL1 && remaining > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', paddingTop: 16 }}>
                <button onClick={onShowAll} style={{
                  padding: '8px 18px', borderRadius: 8, fontSize: 11, fontWeight: 700,
                  border: '1px dashed rgba(61,127,255,0.35)', background: 'rgba(61,127,255,0.05)',
                  color: '#3D7FFF', cursor: 'pointer', fontFamily: 'inherit',
                }}>+ ещё {remaining}</button>
              </div>
            )}
            {showAllL1 && treeData.l1.length > 5 && (
              <div style={{ display: 'flex', alignItems: 'center', paddingTop: 16 }}>
                <button onClick={onHideAll} style={{
                  padding: '8px 18px', borderRadius: 8, fontSize: 11, fontWeight: 700,
                  border: '1px dashed rgba(61,127,255,0.35)', background: 'rgba(61,127,255,0.05)',
                  color: '#6070a0', cursor: 'pointer', fontFamily: 'inherit',
                }}>Свернуть</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MobileAccordion({ treeData, expandedIds, onToggle, showAllL1, onShowAll, onHideAll }) {
  const visible = showAllL1 ? treeData.l1 : treeData.l1.slice(0, 5)
  const remaining = treeData.l1.length - 5

  return (
    <div>
      {visible.map(l1 => {
        const l1Open = expandedIds.has(l1.id)
        return (
          <div key={l1.id} style={{ border: '1px solid rgba(61,127,255,0.3)', borderRadius: 10, overflow: 'hidden', marginBottom: 8 }}>
            <div
              onClick={() => l1.l2.length > 0 && onToggle(l1.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', background: '#0d1628', cursor: l1.l2.length > 0 ? 'pointer' : 'default' }}
            >
              <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 7px', borderRadius: 4, background: 'rgba(61,127,255,0.15)', color: '#3D7FFF', border: '1px solid rgba(61,127,255,0.4)' }}>L1</span>
              <span style={{ fontSize: 12, color: '#e0e8ff', fontWeight: 600, flex: 1, fontFamily: 'monospace' }}>{l1.email_masked}</span>
              <span style={{ fontSize: 12, fontWeight: 800, color: '#FFD166' }}>{l1.credits} ◆</span>
              {l1.l2.length > 0 && <span style={{ fontSize: 10, color: '#6070a0' }}>{l1Open ? '▲' : '▶'}</span>}
            </div>
            {l1Open && (
              <div style={{ background: '#070d1a', borderTop: '1px solid rgba(61,127,255,0.15)', padding: '8px 12px' }}>
                {l1.l2.map(l2 => {
                  const l2Open = expandedIds.has(l2.id)
                  return (
                    <div key={l2.id}>
                      <div
                        onClick={() => l2.l3.length > 0 && onToggle(l2.id)}
                        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', cursor: l2.l3.length > 0 ? 'pointer' : 'default' }}
                      >
                        <span style={{ fontSize: 8, fontWeight: 800, padding: '1px 5px', borderRadius: 3, background: 'rgba(176,96,255,0.15)', color: '#B060FF', border: '1px solid rgba(176,96,255,0.3)' }}>L2</span>
                        <span style={{ fontSize: 11, color: '#c0c8e0', flex: 1, fontFamily: 'monospace' }}>{l2.email_masked}</span>
                        <span style={{ fontSize: 11, color: '#FFD166', fontWeight: 700 }}>{l2.credits} ◆</span>
                        {l2.l3.length > 0 && <span style={{ fontSize: 9, color: '#6070a0' }}>{l2Open ? '▲' : '▶'}</span>}
                      </div>
                      {l2Open && (
                        <div style={{ paddingLeft: 16 }}>
                          {l2.l3.map(l3 => (
                            <div key={l3.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                              <span style={{ fontSize: 8, fontWeight: 800, padding: '1px 5px', borderRadius: 3, background: 'rgba(255,209,102,0.12)', color: '#FFD166', border: '1px solid rgba(255,209,102,0.3)' }}>L3</span>
                              <span style={{ fontSize: 11, color: '#a0a8c0', flex: 1, fontFamily: 'monospace' }}>{l3.email_masked}</span>
                              <span style={{ fontSize: 11, color: '#FFD166', fontWeight: 700 }}>{l3.credits} ◆</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
      {!showAllL1 && remaining > 0 && (
        <button onClick={onShowAll} style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px dashed rgba(61,127,255,0.35)', background: 'rgba(61,127,255,0.05)', color: '#3D7FFF', fontSize: 12, fontWeight: 700, cursor: 'pointer', marginTop: 4, fontFamily: 'inherit' }}>
          + ещё {remaining}
        </button>
      )}
      {showAllL1 && treeData.l1.length > 5 && (
        <button onClick={onHideAll} style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px dashed rgba(61,127,255,0.35)', background: 'rgba(61,127,255,0.05)', color: '#6070a0', fontSize: 12, fontWeight: 700, cursor: 'pointer', marginTop: 4, fontFamily: 'inherit' }}>
          Свернуть
        </button>
      )}
    </div>
  )
}

export default function ReferralTree({ currentUser }) {
  const [treeData, setTreeData] = useState(null)
  const [expandedIds, setExpandedIds] = useState(new Set())
  const [showAllL1, setShowAllL1] = useState(false)
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const r = D.referrals

  useEffect(() => {
    api.referralTree()
      .then(setTreeData)
      .catch(() => setTreeData({ l1: [] }))
  }, [])

  function toggle(id) {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const sharedProps = {
    treeData,
    expandedIds,
    onToggle: toggle,
    showAllL1,
    onShowAll: () => setShowAllL1(true),
    onHideAll: () => setShowAllL1(false),
  }

  return (
    <div>
      <h3 style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 16 }}>
        {r.treeTitle}
      </h3>

      {treeData === null && (
        <div style={{ display: 'flex', gap: 12 }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              width: 130, height: 110, borderRadius: 10,
              background: 'rgba(255,255,255,0.05)',
              animation: `rttree-pulse ${1.2 + i * 0.15}s ease-in-out infinite`,
            }} />
          ))}
          <style>{`@keyframes rttree-pulse { 0%,100%{opacity:.3} 50%{opacity:.7} }`}</style>
        </div>
      )}

      {treeData !== null && treeData.l1.length === 0 && (
        <p style={{ fontSize: 14, color: 'var(--on-surface2)', margin: 0 }}>{r.treeEmpty}</p>
      )}

      {treeData !== null && treeData.l1.length > 0 && (
        <>
          <div className="rt-desktop">
            <DesktopTree {...sharedProps} currentUser={currentUser} />
          </div>
          <div className="rt-mobile">
            <MobileAccordion {...sharedProps} />
          </div>
          <style>{`
            .rt-mobile { display: none; }
            @media (max-width: 640px) {
              .rt-desktop { display: none; }
              .rt-mobile  { display: block; }
            }
          `}</style>
        </>
      )}
    </div>
  )
}
