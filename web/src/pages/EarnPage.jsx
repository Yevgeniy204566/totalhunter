import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

const MAX_PER_DAY = 5

export default function EarnPage() {
  const { lang } = useLang()
  const isRu = lang === 'ru'
  const [watching, setWatching]     = useState(false)
  const [watched, setWatched]       = useState(0)   // today's count
  const [result,  setResult]        = useState(null) // 'ok' | 'limit' | 'error'
  const [credits, setCredits]       = useState(null)

  useEffect(() => {
    api.me().then(u => setCredits(u.credits))
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(() => {})
  }, [])

  const remaining = Math.max(0, MAX_PER_DAY - watched)

  async function handleWatch() {
    if (remaining === 0 || watching) return
    setWatching(true)
    setResult(null)

    // ── Здесь будет реальный Bitmedia/Lootably плеер ────────────
    // Пока симулируем просмотр 5 секунд
    await new Promise(r => setTimeout(r, 5000))
    // ────────────────────────────────────────────────────────────

    try {
      const data = await api.earnReward()
      if (data.success) {
        setWatched(w => w + 1)
        setCredits(data.credits)
        setResult('ok')
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

      {/* Ad placeholder / player */}
      {watching && (
        <div style={{
          background: '#0a1a2a', border: '2px solid #0066aa',
          borderRadius: 12, height: 250, marginBottom: 24,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 16,
        }}>
          {/* ── Bitmedia/Lootably iframe будет здесь ── */}
          <div style={{
            width: 48, height: 48, border: '4px solid #00CFFF',
            borderTopColor: 'transparent', borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          <span style={{ color: '#4499cc', fontSize: 13 }}>
            {isRu ? 'Загрузка рекламы...' : 'Loading ad...'}
          </span>
        </div>
      )}

      {/* Result message */}
      {result === 'ok' && (
        <div style={{
          background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.3)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 20,
          color: '#00FF88', fontSize: 14, fontWeight: 700, textAlign: 'center',
        }}>
          +5 ◆ {isRu ? 'начислено!' : 'credited!'}
        </div>
      )}
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
