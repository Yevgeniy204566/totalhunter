import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

// 20 sectors, each 18°. Server picks sector_index for the won prize.
const SECTOR_VALUES = [5, 7, 5, 15, 5, 30, 5, 7, 5, 15, 5, 7, 5, 15, 5, 50, 5, 7, 5, 30]
const N = SECTOR_VALUES.length
const SLICE_DEG = 360 / N // 18

const SECTOR_STYLE = {
  5:  { bg: '#0e1560', stroke: '#3355EE', text: '#6677FF', shadow: '#3355EE', glow: '#3355EE88' },
  7:  { bg: '#003545', stroke: '#00CCEE', text: '#00EEFF', shadow: '#00CCEE', glow: '#00CCEE88' },
  15: { bg: '#003a18', stroke: '#00BB44', text: '#00EE55', shadow: '#00BB44', glow: '#00BB4488' },
  30: { bg: '#550025', stroke: '#EE1166', text: '#FF44AA', shadow: '#EE1166', glow: '#EE116688' },
  50: { bg: '#2a1600', stroke: '#FFD700', text: '#FFE040', shadow: '#FFD700', glow: '#FFD70099' },
}

const MAX_PER_DAY = 5
const SPIN_TURNS = 4 // full rotations before landing
const SPIN_DURATION_MS = 5500

// Easing: fast start, slow finish with cubic ease-out
function easeOut(t) {
  return 1 - Math.pow(1 - t, 3)
}

// Near-miss effect: if won "5" and in decel phase, add slight wobble near jackpot
function easeWithNearMiss(t, earned) {
  const base = easeOut(t)
  if (earned === 5 && t > 0.65 && t < 0.88) {
    const wobble = Math.sin((t - 0.65) / 0.23 * Math.PI) * 0.035
    return Math.max(0, Math.min(1, base - wobble))
  }
  return base
}

function drawWheelStatic(canvas) {
  const ctx = canvas.getContext('2d')
  const W = canvas.width
  const H = canvas.height
  const cx = W / 2
  const cy = H / 2
  const R = W / 2 - 5
  const SLICE = (2 * Math.PI) / N

  ctx.clearRect(0, 0, W, H)

  for (let i = 0; i < N; i++) {
    const val = SECTOR_VALUES[i]
    const c = SECTOR_STYLE[val]
    // Sector 0 centered at top (-PI/2). Going clockwise.
    const centerAngle = -Math.PI / 2 + i * SLICE
    const startAngle = centerAngle - SLICE / 2
    const endAngle = centerAngle + SLICE / 2

    // Fill
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.arc(cx, cy, R, startAngle, endAngle)
    ctx.closePath()
    ctx.fillStyle = c.bg
    ctx.fill()

    // Border glow
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.arc(cx, cy, R, startAngle, endAngle)
    ctx.closePath()
    ctx.strokeStyle = c.stroke
    ctx.lineWidth = 1.5
    ctx.shadowBlur = 12
    ctx.shadowColor = c.shadow
    ctx.stroke()
    ctx.shadowBlur = 0

    // Label
    const midAngle = centerAngle
    const tr = R * 0.68
    const tx = cx + tr * Math.cos(midAngle)
    const ty = cy + tr * Math.sin(midAngle)
    ctx.save()
    ctx.translate(tx, ty)
    ctx.rotate(midAngle + Math.PI / 2)
    ctx.fillStyle = c.text
    ctx.shadowBlur = 16
    ctx.shadowColor = c.shadow
    const fontSize = val === 50 ? 16 : val === 30 ? 15 : 13
    ctx.font = `900 ${fontSize}px 'Courier New', monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(String(val), 0, 0)
    if (val === 50) {
      ctx.shadowBlur = 20
      ctx.font = '700 9px monospace'
      ctx.fillStyle = '#FFD700'
      ctx.fillText('◆', 0, 14)
    }
    ctx.restore()
  }

  // Outer golden ring
  ctx.beginPath()
  ctx.arc(cx, cy, R, 0, 2 * Math.PI)
  ctx.strokeStyle = '#FFD700'
  ctx.lineWidth = 3
  ctx.shadowBlur = 24
  ctx.shadowColor = '#FFD70077'
  ctx.stroke()
  ctx.shadowBlur = 0

  // Alternating gold tick marks on rim
  for (let i = 0; i < N; i++) {
    const angle = -Math.PI / 2 + i * SLICE
    const x1 = cx + (R - 2) * Math.cos(angle)
    const y1 = cy + (R - 2) * Math.sin(angle)
    const x2 = cx + (R - 10) * Math.cos(angle)
    const y2 = cy + (R - 10) * Math.sin(angle)
    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.strokeStyle = '#FFD700'
    ctx.lineWidth = i % 5 === 0 ? 2 : 1
    ctx.stroke()
  }

  // Center hub
  const hubR = 22
  const grad = ctx.createRadialGradient(cx - 4, cy - 4, 2, cx, cy, hubR)
  grad.addColorStop(0, '#2a3060')
  grad.addColorStop(1, '#0a0f1e')
  ctx.beginPath()
  ctx.arc(cx, cy, hubR, 0, 2 * Math.PI)
  ctx.fillStyle = grad
  ctx.fill()
  ctx.strokeStyle = '#FFD700'
  ctx.lineWidth = 2
  ctx.shadowBlur = 12
  ctx.shadowColor = '#FFD700'
  ctx.stroke()
  ctx.shadowBlur = 0
}

function ParticleCanvas({ active, color }) {
  const cvRef = useRef(null)
  const rafRef = useRef(null)

  useEffect(() => {
    if (!active || !cvRef.current) return
    const cv = cvRef.current
    const ctx = cv.getContext('2d')
    const W = cv.width, H = cv.height
    const particles = Array.from({ length: 90 }, () => ({
      x: W / 2 + (Math.random() - 0.5) * 50,
      y: H / 2 + (Math.random() - 0.5) * 50,
      vx: (Math.random() - 0.5) * 14,
      vy: -Math.random() * 16 - 3,
      size: Math.random() * 5 + 2,
      life: 1,
      decay: Math.random() * 0.012 + 0.008,
      hue: [color, '#FFD700', '#ffffff', '#FFB800'][Math.floor(Math.random() * 4)],
    }))

    const tick = () => {
      ctx.clearRect(0, 0, W, H)
      particles.forEach(p => {
        if (p.life <= 0) return
        p.x += p.vx; p.y += p.vy
        p.vy += 0.35; p.vx *= 0.985
        p.life -= p.decay
        ctx.globalAlpha = Math.max(0, p.life)
        ctx.fillStyle = p.hue
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2)
        ctx.fill()
      })
      ctx.globalAlpha = 1
      if (particles.some(p => p.life > 0)) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [active, color])

  return (
    <canvas ref={cvRef} width={340} height={340} style={{
      position: 'absolute', top: 0, left: 0, pointerEvents: 'none',
      opacity: active ? 1 : 0,
    }} />
  )
}

export default function EarnPage() {
  const { lang } = useLang()
  const isRu = lang === 'ru'

  const [watched, setWatched] = useState(0)
  const [credits, setCredits] = useState(null)
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null) // { earned, jackpot } | { limit: true }
  const [showParticles, setShowParticles] = useState(false)
  const [particleColor, setParticleColor] = useState('#FFD700')

  const wheelCanvasRef = useRef(null)
  const wheelContainerRef = useRef(null)
  const rotationRef = useRef(0) // accumulated CSS rotation in degrees
  const rafRef = useRef(null)
  const audioCtxRef = useRef(null)
  const lastTickSectorRef = useRef(-1)

  // Draw static wheel on mount
  useEffect(() => {
    if (wheelCanvasRef.current) drawWheelStatic(wheelCanvasRef.current)
  }, [])

  useEffect(() => {
    api.me().then(u => setCredits(u.credits)).catch(() => {})
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(() => {})
  }, [])

  function getAudioCtx() {
    if (!audioCtxRef.current) {
      try { audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)() } catch(e) {}
    }
    return audioCtxRef.current
  }

  function playTick(freq = 900) {
    try {
      const ctx = getAudioCtx()
      if (!ctx) return
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.12, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.04)
    } catch(e) {}
  }

  const handleSpin = useCallback(async () => {
    if (spinning || Math.max(0, MAX_PER_DAY - watched) === 0) return

    setSpinning(true)
    setResult(null)
    setShowParticles(false)

    // Resume audio (browser requires user gesture)
    try {
      const ctx = getAudioCtx()
      if (ctx?.state === 'suspended') await ctx.resume()
    } catch(e) {}

    // Server calculates result immediately (server-side math, anti-cheat)
    let data
    try { data = await api.earnReward() } catch(e) { setSpinning(false); return }

    if (!data.success) {
      setSpinning(false)
      setResult({ limit: true })
      return
    }

    const { earned, jackpot, sector_index } = data

    // Calculate target CSS rotation:
    // At rot=0: sector 0 is at top. At rot=18: sector 1 is at top, etc.
    // sector_index at top: rotation must end at sector_index * 18 + 9 (mod 360)
    const sectorTopAngle = sector_index * SLICE_DEG + SLICE_DEG / 2
    const cur = rotationRef.current
    const curMod = ((cur % 360) + 360) % 360
    let extraAngle = ((sectorTopAngle - curMod) + 360) % 360
    if (extraAngle === 0) extraAngle = 360
    const finalRot = cur + SPIN_TURNS * 360 + extraAngle

    const startRot = cur
    const delta = finalRot - startRot
    const startTime = performance.now()

    lastTickSectorRef.current = Math.floor(curMod / SLICE_DEG) % N

    function animate(now) {
      const t = Math.min((now - startTime) / SPIN_DURATION_MS, 1)
      const easedT = easeWithNearMiss(t, earned)
      const currentDeg = startRot + delta * easedT
      rotationRef.current = currentDeg

      if (wheelContainerRef.current) {
        wheelContainerRef.current.style.transform = `rotate(${currentDeg}deg)`
      }

      // Ticker: fire when crossing sector boundary
      const modDeg = ((currentDeg % 360) + 360) % 360
      const currentSector = Math.floor(modDeg / SLICE_DEG) % N
      if (currentSector !== lastTickSectorRef.current) {
        const freq = t < 0.25 ? 1400 : t < 0.55 ? 1100 : t < 0.8 ? 850 : 700
        playTick(freq)
        lastTickSectorRef.current = currentSector
      }

      if (t < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        rotationRef.current = finalRot
        if (wheelContainerRef.current) {
          wheelContainerRef.current.style.transform = `rotate(${finalRot}deg)`
        }
        setWatched(w => w + 1)
        setCredits(data.credits)
        setResult({ earned, jackpot })
        setSpinning(false)
        if (earned >= 30) {
          setParticleColor(SECTOR_STYLE[earned]?.stroke || '#FFD700')
          setShowParticles(true)
        }
      }
    }

    rafRef.current = requestAnimationFrame(animate)
  }, [spinning, watched])

  const remaining = Math.max(0, MAX_PER_DAY - watched)

  const PRIZE_LABELS = {
    5:  { label: isRu ? '+5 ◆' : '+5 ◆', color: '#6677FF' },
    7:  { label: isRu ? '✨ НЕПЛОХО!' : '✨ NICE!', color: '#00EEFF' },
    15: { label: isRu ? '⚡ ХОРОШИЙ ДРО́П!' : '⚡ BIG DROP!', color: '#00EE55' },
    30: { label: isRu ? '🔥 MEGA WIN!' : '🔥 MEGA WIN!', color: '#FF44AA' },
    50: { label: isRu ? '🎰 ДЖЕКПОТ!!!' : '🎰 JACKPOT!!!', color: '#FFD700' },
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '32px 20px' }}>

      {/* Title */}
      <h2 style={{
        fontSize: 26, fontWeight: 900, margin: '0 0 6px',
        background: 'linear-gradient(90deg, #FFD700, #FF8800)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
      }}>
        {isRu ? '🎰 Колесо Фортуны' : '🎰 Fortune Wheel'}
      </h2>
      <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, margin: '0 0 24px' }}>
        {isRu
          ? `Крути колесо и выигрывай алмазы. До ${MAX_PER_DAY} раз в день.`
          : `Spin the wheel and win diamonds. Up to ${MAX_PER_DAY} times per day.`}
      </p>

      {/* Balance */}
      {credits !== null && (
        <div style={{
          background: 'rgba(255,215,0,0.06)', border: '1px solid rgba(255,215,0,0.2)',
          borderRadius: 14, padding: '14px 20px', marginBottom: 22,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13 }}>
            {isRu ? 'Баланс' : 'Balance'}
          </span>
          <span style={{ color: '#FFD700', fontSize: 24, fontWeight: 900,
            textShadow: '0 0 16px #FFD70088' }}>
            {credits.toLocaleString()} ◆
          </span>
        </div>
      )}

      {/* Daily progress */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
          <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>
            {isRu ? 'Сегодня' : 'Today'}
          </span>
          <span style={{ color: watched >= MAX_PER_DAY ? '#FF4444' : '#FFD700', fontSize: 12, fontWeight: 700 }}>
            {watched} / {MAX_PER_DAY}
          </span>
        </div>
        <div style={{ height: 5, background: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
          <div style={{
            height: '100%', borderRadius: 3,
            width: `${(watched / MAX_PER_DAY) * 100}%`,
            background: watched >= MAX_PER_DAY
              ? 'linear-gradient(90deg, #FF4444, #FF8800)'
              : 'linear-gradient(90deg, #FFD700, #FF8800)',
            transition: 'width 0.4s ease',
            boxShadow: '0 0 8px #FFD70066',
          }} />
        </div>
      </div>

      {/* Wheel area */}
      <div style={{ position: 'relative', width: 340, margin: '0 auto 24px', userSelect: 'none' }}>

        {/* Dark glow bg */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%,-50%)',
          width: 300, height: 300, borderRadius: '50%',
          background: 'radial-gradient(ellipse, rgba(40,20,0,0.8) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        {/* Pointer arrow at top */}
        <div style={{
          position: 'absolute', top: -6, left: '50%',
          transform: 'translateX(-50%)',
          width: 0, height: 0, zIndex: 10,
          borderLeft: '10px solid transparent',
          borderRight: '10px solid transparent',
          borderTop: '22px solid #FFD700',
          filter: 'drop-shadow(0 0 8px #FFD700)',
        }} />

        {/* Rotating wheel container */}
        <div ref={wheelContainerRef} style={{
          width: 340, height: 340,
          transition: spinning ? 'none' : 'transform 0.3s ease',
          willChange: 'transform',
        }}>
          <canvas ref={wheelCanvasRef} width={340} height={340} style={{ display: 'block' }} />
        </div>

        {/* Particle overlay */}
        <ParticleCanvas active={showParticles} color={particleColor} />

        {/* Center spin button overlay (click the hub) */}
        <button
          onClick={handleSpin}
          disabled={spinning || remaining === 0}
          style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%,-50%)',
            width: 44, height: 44, borderRadius: '50%',
            background: spinning || remaining === 0 ? 'transparent' : 'rgba(255,215,0,0.15)',
            border: 'none', cursor: spinning || remaining === 0 ? 'default' : 'pointer',
            zIndex: 5,
          }}
          aria-label={isRu ? 'Крутить' : 'Spin'}
        />
      </div>

      {/* Win result card */}
      {result && !result.limit && (
        <div style={{
          background: `${SECTOR_STYLE[result.earned]?.glow?.replace('88','11') || 'rgba(0,0,0,0.2)'}`,
          border: `2px solid ${SECTOR_STYLE[result.earned]?.stroke || '#FFD700'}`,
          borderRadius: 16, padding: '22px 20px', marginBottom: 20, textAlign: 'center',
          boxShadow: `0 0 40px ${SECTOR_STYLE[result.earned]?.glow || '#FFD70066'}`,
          animation: 'popIn 0.4s ease',
        }}>
          <style>{`@keyframes popIn{0%{transform:scale(0.7);opacity:0}60%{transform:scale(1.08)}100%{transform:scale(1);opacity:1}}`}</style>
          <div style={{
            fontSize: 15, fontWeight: 900, letterSpacing: '2px', marginBottom: 6,
            color: SECTOR_STYLE[result.earned]?.text || '#FFD700',
          }}>
            {PRIZE_LABELS[result.earned]?.label || `+${result.earned} ◆`}
          </div>
          <div style={{
            fontSize: 68, fontWeight: 900, lineHeight: 1,
            color: SECTOR_STYLE[result.earned]?.text || '#FFD700',
            filter: `drop-shadow(0 0 20px ${SECTOR_STYLE[result.earned]?.shadow || '#FFD700'})`,
          }}>
            {result.earned}
          </div>
          <div style={{
            fontSize: 20, color: SECTOR_STYLE[result.earned]?.text || '#FFD700',
            opacity: 0.8, marginTop: 4,
          }}>◆</div>
        </div>
      )}

      {/* Limit message */}
      {(result?.limit || remaining === 0) && (
        <div style={{
          background: 'rgba(255,80,0,0.08)', border: '1px solid rgba(255,80,0,0.3)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 20,
          color: '#FF8844', fontSize: 13, textAlign: 'center',
        }}>
          {isRu ? '🌙 Лимит на сегодня. Возвращайся завтра!' : '🌙 Daily limit reached. Come back tomorrow!'}
        </div>
      )}

      {/* Main spin button */}
      <button
        onClick={handleSpin}
        disabled={spinning || remaining === 0}
        style={{
          width: '100%', padding: '16px 0',
          background: remaining === 0
            ? 'rgba(255,255,255,0.05)'
            : spinning
              ? 'rgba(255,215,0,0.12)'
              : 'linear-gradient(135deg, #FFB800, #FFD700)',
          color: remaining === 0 ? 'rgba(255,255,255,0.25)' : spinning ? '#FFD700' : '#000',
          border: remaining === 0 ? '1px solid rgba(255,255,255,0.1)' : '1px solid #FFD700',
          borderRadius: 14, fontSize: 16, fontWeight: 900,
          cursor: remaining === 0 || spinning ? 'not-allowed' : 'pointer',
          transition: 'all 0.25s',
          boxShadow: remaining > 0 && !spinning ? '0 0 32px rgba(255,215,0,0.45)' : 'none',
          fontFamily: 'inherit', letterSpacing: '1px',
        }}
      >
        {remaining === 0
          ? (isRu ? '✓ Лимит исчерпан' : '✓ Limit reached')
          : spinning
            ? (isRu ? '🎰 Крутится...' : '🎰 Spinning...')
            : (isRu ? `🎰 КРУТИТЬ  (осталось ${remaining})` : `🎰 SPIN  (${remaining} left)`)}
      </button>

      {/* Prize table */}
      <div style={{ marginTop: 32, borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 24 }}>
        <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11, textAlign: 'center', marginBottom: 14, letterSpacing: '2px', textTransform: 'uppercase' }}>
          {isRu ? 'Таблица призов' : 'Prize Table'}
        </div>
        {[
          [50, '1%',  isRu ? '🎰 ДЖЕКПОТ' : '🎰 JACKPOT'],
          [30, '3%',  isRu ? '🔥 MEGA WIN' : '🔥 MEGA WIN'],
          [15, '6%',  isRu ? '⚡ Хороший дроп' : '⚡ Big Drop'],
          [7,  '12%', isRu ? '✨ Неплохо' : '✨ Nice'],
          [5,  '78%', isRu ? 'Базовый приз' : 'Base prize'],
        ].map(([val, pct, label]) => (
          <div key={val} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '8px 12px', marginBottom: 6, borderRadius: 10,
            background: `${SECTOR_STYLE[val].glow.replace('88','09')}`,
            border: `1px solid ${SECTOR_STYLE[val].stroke}22`,
          }}>
            <span style={{ color: SECTOR_STYLE[val].text, fontWeight: 700, fontSize: 13 }}>{label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ color: SECTOR_STYLE[val].text, fontSize: 20, fontWeight: 900,
                textShadow: `0 0 12px ${SECTOR_STYLE[val].shadow}` }}>
                {val} ◆
              </span>
              <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: 11 }}>{pct}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
