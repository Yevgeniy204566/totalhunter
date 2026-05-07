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
        background: 'rgba(255,255,255,0.02)',
        border: '1px dashed rgba(255,255,255,0.08)',
        borderRadius: 8,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, color: 'rgba(255,255,255,0.18)',
        letterSpacing: '1px', fontFamily: 'monospace',
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
