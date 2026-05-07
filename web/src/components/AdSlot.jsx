/**
 * AdSlot — рекламный слот.
 * Сейчас показывает заглушку. Заменить на код Coinzilla:
 *   1. Удалить <div className="ad-placeholder">...</div>
 *   2. Вставить <script> от Coinzilla внутри return
 *
 * size: 'leaderboard' = 728x90 | 'rectangle' = 300x250 | 'mobile' = 320x50
 */

export default function AdSlot({ size = 'leaderboard', style = {} }) {
  const sizes = {
    leaderboard: { width: 728, height: 90,  label: '728×90 — Leaderboard' },
    rectangle:   { width: 300, height: 250, label: '300×250 — Rectangle' },
    mobile:      { width: 320, height: 50,  label: '320×50 — Mobile Banner' },
  }

  const s = sizes[size] || sizes.leaderboard

  return (
    <div
      className={`ad-slot ad-slot-${size}`}
      style={{
        width: s.width, maxWidth: '100%', height: s.height,
        background: '#0a1a2a',
        border: '2px solid #0066aa',
        borderRadius: 8,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, color: '#4499cc',
        letterSpacing: '2px', fontFamily: 'monospace', fontWeight: 700,
        flexShrink: 0,
        overflow: 'hidden',
        ...style,
      }}
      data-ad-size={size}
    >
      {/* ── COINZILLA: вставить сюда <script> код зоны ── */}
      <span>AD · {s.label}</span>
    </div>
  )
}
