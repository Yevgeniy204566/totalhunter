import { useEffect, useRef } from 'react'

// ── A-Ads publisher IDs ──────────────────────────────────────────
// После регистрации на a-ads.com → замени значения на свои ID зон
const AADS_ID = {
  leaderboard: 'TODO_AADS_LEADERBOARD_ID',  // 728×90
  rectangle:   'TODO_AADS_RECTANGLE_ID',    // 300×250
  mobile:      'TODO_AADS_MOBILE_ID',       // 320×50
}

const AD_SIZES = {
  leaderboard: { w: 728,  h: 90,  size: '728x90'  },
  rectangle:   { w: 300,  h: 250, size: '300x250' },
  mobile:      { w: 320,  h: 50,  size: '320x50'  },
}

export default function AdSlot({ size = 'leaderboard', style = {} }) {
  const s    = AD_SIZES[size] || AD_SIZES.leaderboard
  const id   = AADS_ID[size]  || AADS_ID.leaderboard
  const isReady = !id.startsWith('TODO_')

  if (!isReady) {
    // Заглушка до получения реального ID от A-Ads
    return (
      <div
        style={{
          width: s.w, maxWidth: '100%', height: s.h,
          background: '#0a1a2a', border: '1px dashed #1a3a5a',
          borderRadius: 8, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          fontSize: 12, color: '#2a5a7a', letterSpacing: '1px',
          flexShrink: 0, ...style,
        }}
      >
        AD · {s.size}
      </div>
    )
  }

  return (
    <div
      className={`ad-slot ad-slot-${size}`}
      style={{ width: s.w, maxWidth: '100%', height: s.h, flexShrink: 0, ...style }}
    >
      <iframe
        src={`//ad.a-ads.com/${id}?size=${s.size}`}
        style={{ width: s.w, height: s.h, border: 0, padding: 0, overflow: 'hidden', background: 'transparent' }}
        scrolling="no"
        title="advertisement"
      />
    </div>
  )
}
