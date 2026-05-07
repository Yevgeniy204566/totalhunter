import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

const MAX_PER_DAY = 5

const TIERS = [
  { min: 50, label: '🎰 JACKPOT!',  color: '#FFD700', glow: 'rgba(255,215,0,0.8)',  bg: 'rgba(255,180,0,0.15)' },
  { min: 30, label: '🔥 MEGA WIN!', color: '#FF6600', glow: 'rgba(255,100,0,0.7)',  bg: 'rgba(255,80,0,0.12)'  },
  { min: 20, label: '⚡ BIG WIN!',  color: '#CC44FF', glow: 'rgba(180,0,255,0.6)',  bg: 'rgba(150,0,255,0.10)' },
  { min: 10, label: '✨ NICE!',     color: '#00CFFF', glow: 'rgba(0,200,255,0.5)',  bg: 'rgba(0,150,255,0.08)' },
  { min: 0,  label: '+5 ◆',        color: '#00FF88', glow: 'rgba(0,255,136,0.4)',  bg: 'rgba(0,255,136,0.06)' },
]

function getTier(earned) {
  return TIERS.find(t => earned >= t.min) || TIERS[TIERS.length - 1]
}

export default function EarnPage() {
  const { lang } = useLang()
  const isRu = lang === 'ru'
  const [watching,  setWatching]  = useState(false)
  const [spinning,  setSpinning]  = useState(false)
  const [watched,   setWatched]   = useState(0)
  const [result,    setResult]    = useState(null) // 'ok' | 'limit' | 'error'
  const [earned,    setEarned]    = useState(null)
  const [credits,   setCredits]   = useState(null)
  const [slotNum,   setSlotNum]   = useState('?')

  useEffect(() => {
    api.me().then(u => setCredits(u.credits))
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(() => {})
  }, [])

  const remaining = Math.max(0, MAX_PER_DAY - watched)

  async function handleWatch() {
    if (remaining === 0 || watching) return
    setWatching(true)
    setResult(null)
    setEarned(null)

    // Simulate ad watching (5 seconds)
    await new Promise(r => setTimeout(r, 5000))

    try {
      const data = await api.earnReward()
      if (data.success) {
        setWatched(w => w + 1)
        setCredits(data.credits)
        // Casino spin animation
        setSpinning(true)
        const finalVal = data.earned
        let count = 0
        const interval = setInterval(() => {
          setSlotNum([5,10,20,30,50][Math.floor(Math.random()*5)])
          count++
          if (count > 18) {
            clearInterval(interval)
            setSlotNum(finalVal)
            setEarned(finalVal)
            setSpinning(false)
            setResult('ok')
          }
        }, 80)
      } else {
        setResult('limit')
      }
    } catch {
      setResult('error')
    } finally {
      setWatching(false)
    }
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '32px 20px' }}>
      <h2 style={{
        fontSize: 26, fontWeight: 900, color: '#fff', marginBottom: 8,
        background: 'linear-gradient(90deg, #00FF88, #00CFFF)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }}>
        {isRu ? '◆ Бесплатные алмазы' : '◆ Free Diamonds'}
      </h2>
      <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13, marginBottom: 32 }}>
        {isRu
          ? 'Смотри короткую рекламу и получай +5 алмазов. До 5 раз в день.'
          : 'Watch a short ad and earn +5 diamonds. Up to 5 times per day.'}
      </p>

      {/* Balance */}
      {credits !== null && (
        <div style={{
          background: 'rgba(0,255,136,0.06)', border: '1px solid rgba(0,255,136,0.2)',
          borderRadius: 14, padding: '16px 20px', marginBottom: 28,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
            {isRu ? 'Баланс' : 'Balance'}
          </span>
          <span style={{ color: '#00CFFF', fontSize: 24, fontWeight: 900 }}>
            {credits.toLocaleString()} ◆
          </span>
        </div>
      )}

      {/* Progress */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
            {isRu ? 'Сегодня' : 'Today'}
          </span>
          <span style={{ color: '#00FF88', fontSize: 12, fontWeight: 700 }}>
            {watched} / {MAX_PER_DAY}
          </span>
        </div>
        <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
          <div style={{
            height: '100%', borderRadius: 3,
            width: `${(watched / MAX_PER_DAY) * 100}%`,
            background: 'linear-gradient(90deg, #00FF88, #00CFFF)',
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>

      {/* Ad watching spinner */}
      {watching && (
        <div style={{
          background: '#0a1a2a', border: '2px solid #0066aa',
          borderRadius: 12, height: 160, marginBottom: 24,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 14,
        }}>
          <div style={{
            width: 42, height: 42, border: '4px solid #00CFFF',
            borderTopColor: 'transparent', borderRadius: '50%',
            animation: 'spin 0.7s linear infinite',
          }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}} @keyframes pop{0%{transform:scale(0.5);opacity:0}60%{transform:scale(1.2)}100%{transform:scale(1);opacity:1}}`}</style>
          <span style={{ color: '#4499cc', fontSize: 13 }}>
            {isRu ? 'Смотрю рекламу...' : 'Watching ad...'}
          </span>
        </div>
      )}

      {/* Casino slot result */}
      {(spinning || result === 'ok') && earned !== null && (() => {
        const tier = getTier(earned)
        return (
          <div style={{
            background: tier.bg,
            border: `2px solid ${tier.color}`,
            borderRadius: 16, padding: '28px 20px', marginBottom: 24,
            textAlign: 'center',
            boxShadow: `0 0 40px ${tier.glow}, 0 0 80px ${tier.glow}55`,
            animation: !spinning ? 'pop 0.4s ease' : 'none',
          }}>
            <div style={{ fontSize: 14, color: tier.color, fontWeight: 700, letterSpacing: '3px', marginBottom: 8 }}>
              {spinning ? '🎰 ...' : tier.label}
            </div>
            <div style={{
              fontSize: 72, fontWeight: 900, lineHeight: 1,
              color: tier.color,
              filter: `drop-shadow(0 0 24px ${tier.glow})`,
              fontVariantNumeric: 'tabular-nums',
              animation: spinning ? 'spin 0.08s linear infinite' : 'none',
              transition: 'all 0.1s',
            }}>
              {slotNum}
            </div>
            <div style={{ fontSize: 18, color: tier.color, opacity: 0.8, marginTop: 4 }}>◆</div>
            {!spinning && earned >= 10 && (
              <div style={{ fontSize: 22, marginTop: 10 }}>
                {earned >= 50 ? '🎉🎰🎉' : earned >= 30 ? '🔥🔥🔥' : earned >= 20 ? '⚡⚡' : '✨'}
              </div>
            )}
          </div>
        )
      })()}

      {/* Limit / error messages */}
      {result === 'limit' && (
        <div style={{
          background: 'rgba(255,100,0,0.08)', border: '1px solid rgba(255,100,0,0.3)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 20,
          color: '#ff9944', fontSize: 13, textAlign: 'center',
        }}>
          {isRu ? 'Лимит на сегодня исчерпан. Приходи завтра!' : 'Daily limit reached. Come back tomorrow!'}
        </div>
      )}

      {/* Main button */}
      <button
        onClick={handleWatch}
        disabled={watching || remaining === 0}
        style={{
          width: '100%', padding: '16px 0',
          background: remaining === 0
            ? 'rgba(255,255,255,0.06)'
            : watching
              ? 'rgba(0,200,100,0.15)'
              : 'linear-gradient(135deg, #00CC66, #00FF88)',
          color: remaining === 0 ? 'rgba(255,255,255,0.3)' : watching ? '#00FF88' : '#000',
          border: 'none', borderRadius: 12,
          fontSize: 16, fontWeight: 900, cursor: remaining === 0 ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s',
          boxShadow: remaining > 0 && !watching ? '0 0 30px rgba(0,255,136,0.4)' : 'none',
          fontFamily: 'inherit', letterSpacing: '1px',
        }}
      >
        {remaining === 0
          ? (isRu ? '✓ На сегодня всё' : '✓ Done for today')
          : watching
            ? (isRu ? '⏳ Смотрю...' : '⏳ Watching...')
            : (isRu ? `▶ Смотреть рекламу  +5 ◆  (осталось ${remaining})` : `▶ Watch Ad  +5 ◆  (${remaining} left)`)}
      </button>

      <p style={{ color: 'rgba(255,255,255,0.2)', fontSize: 11, textAlign: 'center', marginTop: 16 }}>
        {isRu
          ? 'Не закрывай вкладку пока идёт реклама'
          : 'Do not close the tab while the ad is playing'}
      </p>
    </div>
  )
}
