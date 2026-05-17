import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

// ─── Constants ───────────────────────────────────────────────────────────────
const N = 20
const SECTOR_VALUES = [5, 7, 5, 15, 5, 30, 5, 7, 5, 15, 5, 7, 5, 15, 5, 50, 5, 7, 5, 30]
const SLICE = (2 * Math.PI) / N
const MAX_PER_DAY = 5
const SPIN_TURNS = 4
const SPIN_MS = 5800
const W = 340, H = 340, CX = W / 2, CY = H / 2
const R_OUTER = 164   // metallic rim outer radius
const R_SECTOR = 148  // sector area radius
const R_HUB = 22      // center hub radius

const COLORS = {
  5:  { from: '#0b1050', to: '#1a2488', stroke: '#3355EE', text: '#6688FF', shadow: '#2244DD', particle: '#3355EE' },
  7:  { from: '#001e30', to: '#003550', stroke: '#00AACC', text: '#00DDFF', shadow: '#008899', particle: '#00AACC' },
  15: { from: '#001e0c', to: '#003318', stroke: '#009933', text: '#00CC44', shadow: '#007722', particle: '#00AA33' },
  30: { from: '#2e0012', to: '#550022', stroke: '#CC0044', text: '#FF3377', shadow: '#990033', particle: '#DD1155' },
  50: { from: '#160b00', to: '#2e1600', stroke: '#DDC000', text: '#FFD700', shadow: '#BB9900', particle: '#FFD700' },
}

// ─── Easing ──────────────────────────────────────────────────────────────────
function easeOut4(t) { return 1 - Math.pow(1 - t, 4) }

function easeWithEffects(t, earned) {
  if (t >= 1) return 1
  // Bounce at the end: slight overshoot then settle
  let base
  if (t < 0.9) {
    base = easeOut4(t / 0.9)
  } else {
    const bt = (t - 0.9) / 0.1
    base = 1 + 0.022 * Math.sin(bt * Math.PI)
  }
  // Near-miss for small win: wobble past jackpot sector
  if (earned === 5 && t > 0.68 && t < 0.87) {
    base -= 0.025 * Math.sin(((t - 0.68) / 0.19) * Math.PI)
  }
  return base
}

// ─── Drawing helpers ─────────────────────────────────────────────────────────
function drawRim(ctx) {
  // Deep metallic gradient ring
  const grad = ctx.createRadialGradient(CX - 55, CY - 55, 20, CX, CY, R_OUTER)
  grad.addColorStop(0,    '#C89A1A')
  grad.addColorStop(0.35, '#F0C030')
  grad.addColorStop(0.6,  '#A07818')
  grad.addColorStop(0.82, '#604808')
  grad.addColorStop(1,    '#2a1e04')
  ctx.beginPath()
  ctx.arc(CX, CY, R_OUTER, 0, 2 * Math.PI)
  ctx.fillStyle = grad
  ctx.fill()

  // Outer glow ring
  ctx.beginPath()
  ctx.arc(CX, CY, R_OUTER, 0, 2 * Math.PI)
  ctx.strokeStyle = '#FFD700'
  ctx.lineWidth = 2.5
  ctx.shadowBlur = 20
  ctx.shadowColor = '#FFD70055'
  ctx.stroke()
  ctx.shadowBlur = 0

  // Studs (pins) around inner rim edge
  const nStuds = 40
  const studR = R_OUTER - 8
  for (let i = 0; i < nStuds; i++) {
    const a = (i / nStuds) * 2 * Math.PI
    const sx = CX + studR * Math.cos(a)
    const sy = CY + studR * Math.sin(a)
    const sg = ctx.createRadialGradient(sx - 0.8, sy - 0.8, 0, sx, sy, 3)
    sg.addColorStop(0, '#FFF0A0')
    sg.addColorStop(1, '#886600')
    ctx.beginPath()
    ctx.arc(sx, sy, i % 5 === 0 ? 3 : 2, 0, 2 * Math.PI)
    ctx.fillStyle = sg
    ctx.fill()
  }

  // Inner shadow ring (depth under sector disk)
  const innerGrad = ctx.createRadialGradient(CX, CY, R_SECTOR - 6, CX, CY, R_SECTOR + 4)
  innerGrad.addColorStop(0, 'rgba(0,0,0,0.6)')
  innerGrad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.beginPath()
  ctx.arc(CX, CY, R_SECTOR + 4, 0, 2 * Math.PI)
  ctx.fillStyle = innerGrad
  ctx.fill()
}

function drawSectors(ctx, wheelAngle, speed) {
  // Motion blur: draw faint ghost frames when spinning fast
  const blur = Math.min(Math.abs(speed) * 10, 9)
  if (blur > 0.3) ctx.filter = `blur(${blur.toFixed(1)}px)`

  ctx.save()
  ctx.translate(CX, CY)
  ctx.rotate(wheelAngle)

  for (let i = 0; i < N; i++) {
    const val = SECTOR_VALUES[i]
    const c = COLORS[val]
    const startA = -Math.PI / 2 + i * SLICE
    const endA   = startA + SLICE
    const midA   = startA + SLICE / 2

    // Radial gradient: dark center → lit edge
    const gx1 = Math.cos(midA) * R_SECTOR * 0.15
    const gy1 = Math.sin(midA) * R_SECTOR * 0.15
    const gx2 = Math.cos(midA) * R_SECTOR * 0.95
    const gy2 = Math.sin(midA) * R_SECTOR * 0.95
    const grad = ctx.createLinearGradient(gx1, gy1, gx2, gy2)
    grad.addColorStop(0, c.from)
    grad.addColorStop(1, c.to)

    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.arc(0, 0, R_SECTOR, startA, endA)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    // Neon sector border
    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.arc(0, 0, R_SECTOR, startA, endA)
    ctx.closePath()
    ctx.strokeStyle = c.stroke
    ctx.lineWidth = 1
    ctx.shadowBlur = 10
    ctx.shadowColor = c.shadow
    ctx.stroke()
    ctx.shadowBlur = 0

    // ── Text — ALWAYS READABLE (no upside-down bug) ──────────────────────────
    const tr = R_SECTOR * 0.67
    const tx = Math.cos(midA) * tr
    const ty = Math.sin(midA) * tr

    ctx.save()
    ctx.translate(tx, ty)

    // Perpendicular to radius; flip bottom half so text never inverts
    let textRot = midA + Math.PI / 2
    const normA = ((midA % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)
    if (normA >= Math.PI / 2 && normA <= 3 * Math.PI / 2) textRot += Math.PI

    ctx.rotate(textRot)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    // Neon glow
    ctx.shadowBlur = 18
    ctx.shadowColor = c.shadow
    ctx.fillStyle = c.text
    ctx.font = `900 ${val === 50 ? 16 : val >= 15 ? 14 : 13}px 'Courier New', monospace`
    ctx.fillText(String(val), 0, 0)

    // Diamond sign for jackpot
    if (val === 50) {
      ctx.font = '700 9px monospace'
      ctx.fillStyle = '#FFD700'
      ctx.fillText('◆', 0, 15)
    }
    ctx.shadowBlur = 0
    ctx.restore()
  }

  ctx.restore()
  ctx.filter = 'none'

  // ── Center hub ──────────────────────────────────────────────────────────────
  const hubGrad = ctx.createRadialGradient(CX - 7, CY - 7, 2, CX, CY, R_HUB)
  hubGrad.addColorStop(0, '#2a3060')
  hubGrad.addColorStop(1, '#080c18')
  ctx.beginPath()
  ctx.arc(CX, CY, R_HUB, 0, 2 * Math.PI)
  ctx.fillStyle = hubGrad
  ctx.fill()
  ctx.strokeStyle = '#FFD700'
  ctx.lineWidth = 2
  ctx.shadowBlur = 12
  ctx.shadowColor = '#FFD700'
  ctx.stroke()
  ctx.shadowBlur = 0
}

function drawGlassOverlay(ctx) {
  // Specular highlight — fixed gloss stripe (wheel spins under this)
  ctx.save()
  const gloss = ctx.createRadialGradient(CX - 50, CY - 60, 5, CX, CY, R_SECTOR)
  gloss.addColorStop(0,    'rgba(255,255,255,0.14)')
  gloss.addColorStop(0.38, 'rgba(255,255,255,0.06)')
  gloss.addColorStop(1,    'rgba(255,255,255,0)')
  ctx.beginPath()
  ctx.arc(CX, CY, R_SECTOR, 0, 2 * Math.PI)
  ctx.fillStyle = gloss
  ctx.fill()

  // Secondary glint streak
  ctx.globalAlpha = 0.07
  ctx.beginPath()
  ctx.ellipse(CX - 30, CY - 55, 55, 14, -0.45, 0, 2 * Math.PI)
  ctx.fillStyle = '#ffffff'
  ctx.fill()
  ctx.globalAlpha = 1
  ctx.restore()
}

function drawPointer(ctx, deflection) {
  const px = CX, py = CY - R_OUTER + 4

  ctx.save()
  ctx.translate(px, py + 10)
  ctx.rotate(deflection)
  ctx.translate(-px, -(py + 10))

  // Drop shadow
  ctx.beginPath()
  ctx.moveTo(px - 11, py + 4)
  ctx.lineTo(px + 11, py + 4)
  ctx.lineTo(px, py - 16)
  ctx.closePath()
  ctx.fillStyle = 'rgba(0,0,0,0.55)'
  ctx.fill()

  // Gradient pointer body
  const pGrad = ctx.createLinearGradient(px - 11, py, px + 11, py)
  pGrad.addColorStop(0,   '#CC8800')
  pGrad.addColorStop(0.5, '#FFE050')
  pGrad.addColorStop(1,   '#CC8800')
  ctx.beginPath()
  ctx.moveTo(px - 10, py + 3)
  ctx.lineTo(px + 10, py + 3)
  ctx.lineTo(px, py - 15)
  ctx.closePath()
  ctx.fillStyle = pGrad
  ctx.shadowBlur = 18
  ctx.shadowColor = '#FFD700'
  ctx.fill()
  ctx.shadowBlur = 0

  ctx.restore()
}

// ─── Particles ────────────────────────────────────────────────────────────────
function ParticleCanvas({ active, color }) {
  const cvRef = useRef(null)
  const rafRef = useRef(null)

  useEffect(() => {
    if (!active || !cvRef.current) return
    const cv = cvRef.current
    const ctx = cv.getContext('2d')
    const particles = Array.from({ length: 100 }, () => ({
      x: W / 2 + (Math.random() - 0.5) * 40,
      y: H / 2 + (Math.random() - 0.5) * 40,
      vx: (Math.random() - 0.5) * 16,
      vy: -Math.random() * 18 - 2,
      size: Math.random() * 5 + 2,
      life: 1,
      decay: Math.random() * 0.013 + 0.007,
      hue: [color, '#FFD700', '#ffffff'][Math.floor(Math.random() * 3)],
    }))
    const tick = () => {
      ctx.clearRect(0, 0, W, H)
      let alive = false
      particles.forEach(p => {
        if (p.life <= 0) return
        alive = true
        p.x += p.vx; p.y += p.vy; p.vy += 0.4; p.vx *= 0.985; p.life -= p.decay
        ctx.globalAlpha = Math.max(0, p.life)
        ctx.fillStyle = p.hue
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2)
        ctx.fill()
      })
      ctx.globalAlpha = 1
      if (alive) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [active, color])

  return <canvas ref={cvRef} width={W} height={H}
    style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none', opacity: active ? 1 : 0 }} />
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function EarnPage() {
  const { lang } = useLang()
  const isRu = lang === 'ru'

  const [watched, setWatched]       = useState(0)
  const [credits, setCredits]       = useState(null)
  const [spinning, setSpinning]     = useState(false)
  const [result, setResult]         = useState(null)
  const [particles, setParticles]   = useState(false)
  const [partColor, setPartColor]   = useState('#FFD700')
  const [btnPressed, setBtnPressed] = useState(false)

  const cvRef    = useRef(null)
  const rafRef   = useRef(null)
  const rotRef   = useRef(0)           // accumulated wheel rotation (rad)
  const speedRef = useRef(0)           // current angular speed (rad/frame)
  const ptrRef   = useRef({ a: 0, v: 0 }) // pointer spring state
  const lastSecRef = useRef(-1)        // last sector index at pointer
  const audioRef = useRef(null)

  // Initial draw
  useEffect(() => {
    const cv = cvRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    ctx.clearRect(0, 0, W, H)
    drawRim(ctx)
    drawSectors(ctx, 0, 0)
    drawGlassOverlay(ctx)
    drawPointer(ctx, 0)
  }, [])

  useEffect(() => {
    api.me().then(u => setCredits(u.credits)).catch(() => {})
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(() => {})
  }, [])

  function getAudioCtx() {
    if (!audioRef.current) {
      try { audioRef.current = new (window.AudioContext || window.webkitAudioContext)() } catch(e) {}
    }
    return audioRef.current
  }

  function playTick(freq) {
    try {
      const ctx = getAudioCtx()
      if (!ctx) return
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain); gain.connect(ctx.destination)
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.1, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.045)
      osc.start(); osc.stop(ctx.currentTime + 0.045)
    } catch(e) {}
  }

  const handleSpin = useCallback(async () => {
    if (spinning || Math.max(0, MAX_PER_DAY - watched) === 0) return

    setSpinning(true)
    setResult(null)
    setParticles(false)

    try {
      const actx = getAudioCtx()
      if (actx?.state === 'suspended') await actx.resume()
    } catch(e) {}

    let data
    try { data = await api.earnReward() } catch(e) { setSpinning(false); return }
    if (!data.success) { setSpinning(false); setResult({ limit: true }); return }

    const { earned, jackpot, sector_index } = data
    const SLICE_RAD = (2 * Math.PI) / N

    // Target rotation: sector_index at pointer (top = -PI/2)
    const sectorMid = -Math.PI / 2 + sector_index * SLICE_RAD + SLICE_RAD / 2
    // We want: rotEnd ≡ -sectorMid (so that sectorMid ends up at -PI/2 in world frame)
    const targetAngle = -sectorMid  // angle where sector_index is at top
    const curRot = rotRef.current
    // Normalize: choose targetAngle that is > curRot + 3*2PI
    let norm = ((targetAngle - curRot) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI)
    if (norm === 0) norm = 2 * Math.PI
    const finalRot = curRot + SPIN_TURNS * 2 * Math.PI + norm

    const delta = finalRot - curRot
    const startTime = performance.now()
    lastSecRef.current = Math.floor(((-curRot % (2*Math.PI) + 2*Math.PI) % (2*Math.PI)) / SLICE_RAD) % N

    const animate = (now) => {
      const t = Math.min((now - startTime) / SPIN_MS, 1)
      const et = easeWithEffects(t, earned)
      const currentRot = curRot + delta * et
      rotRef.current = currentRot

      // Angular speed for motion blur & ticker freq
      const prevRot = curRot + delta * easeWithEffects(Math.max(0, t - 0.016 / SPIN_MS), earned)
      speedRef.current = Math.abs(currentRot - prevRot)

      // Ticker: detect sector crossings at pointer
      const pointerAngle = ((-currentRot % (2*Math.PI)) + 2*Math.PI) % (2*Math.PI)
      const curSec = Math.floor(pointerAngle / SLICE_RAD) % N
      if (curSec !== lastSecRef.current) {
        const freq = t < 0.25 ? 1500 : t < 0.5 ? 1200 : t < 0.75 ? 950 : 750
        playTick(freq)
        // Pointer impulse — deflect in spin direction
        ptrRef.current.v += 0.22
        lastSecRef.current = curSec
      }

      // Pointer spring physics
      const ptr = ptrRef.current
      const dt = 0.016
      const K = 90, D = 0.72
      ptr.v += (-K * ptr.a - D * ptr.v) * dt
      ptr.a += ptr.v * dt
      ptr.a = Math.max(-0.5, Math.min(0.5, ptr.a))

      // Draw frame
      const cv = cvRef.current
      if (cv) {
        const ctx = cv.getContext('2d')
        ctx.clearRect(0, 0, W, H)
        drawRim(ctx)
        drawSectors(ctx, currentRot, speedRef.current / 0.05)
        drawGlassOverlay(ctx)
        drawPointer(ctx, ptr.a)
      }

      if (t < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        // Snap to exact final rotation
        rotRef.current = finalRot
        speedRef.current = 0
        ptrRef.current = { a: 0, v: 0 }
        const cv = cvRef.current
        if (cv) {
          const ctx = cv.getContext('2d')
          ctx.clearRect(0, 0, W, H)
          drawRim(ctx)
          drawSectors(ctx, finalRot, 0)
          drawGlassOverlay(ctx)
          drawPointer(ctx, 0)
        }
        setWatched(w => w + 1)
        setCredits(data.credits)
        setResult({ earned, jackpot })
        setSpinning(false)
        if (earned >= 30) {
          setPartColor(COLORS[earned]?.particle || '#FFD700')
          setParticles(true)
        }
      }
    }

    rafRef.current = requestAnimationFrame(animate)
  }, [spinning, watched])

  const remaining = Math.max(0, MAX_PER_DAY - watched)

  const TIER = {
    50: { label: isRu ? '🎰 ДЖЕКПОТ!!!' : '🎰 JACKPOT!!!', color: '#FFD700' },
    30: { label: isRu ? '🔥 MEGA WIN!' : '🔥 MEGA WIN!', color: '#FF3377' },
    15: { label: isRu ? '⚡ БОЛЬШОЙ ДРОП!' : '⚡ BIG DROP!', color: '#00CC44' },
    7:  { label: isRu ? '✨ НЕПЛОХО!' : '✨ NICE!', color: '#00DDFF' },
    5:  { label: '+5 ◆', color: '#6688FF' },
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '28px 20px' }}>

      {/* Title */}
      <h2 style={{
        fontSize: 28, fontWeight: 900, margin: '0 0 6px',
        background: 'linear-gradient(90deg, #FFD700 0%, #FF8800 50%, #FFD700 100%)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
        letterSpacing: '1px',
      }}>
        {isRu ? '🎰 Колесо Фортуны' : '🎰 Fortune Wheel'}
      </h2>
      <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13, margin: '0 0 20px' }}>
        {isRu
          ? `Крути и выигрывай алмазы — до ${MAX_PER_DAY} раз в день`
          : `Spin and win diamonds — up to ${MAX_PER_DAY} times per day`}
      </p>

      {/* Balance */}
      {credits !== null && (
        <div style={{
          background: 'rgba(255,215,0,0.05)', border: '1px solid rgba(255,215,0,0.18)',
          borderRadius: 12, padding: '12px 18px', marginBottom: 18,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
            {isRu ? 'Баланс' : 'Balance'}
          </span>
          <span style={{ color: '#FFD700', fontSize: 22, fontWeight: 900,
            textShadow: '0 0 14px rgba(255,215,0,0.5)' }}>
            {credits.toLocaleString()} ◆
          </span>
        </div>
      )}

      {/* Daily progress */}
      <div style={{ marginBottom: 22 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11 }}>
            {isRu ? 'СЕГОДНЯ' : 'TODAY'}
          </span>
          <span style={{
            color: watched >= MAX_PER_DAY ? '#FF4444' : '#FFD700',
            fontSize: 11, fontWeight: 700,
          }}>
            {watched} / {MAX_PER_DAY}
          </span>
        </div>
        <div style={{ height: 4, background: 'rgba(255,255,255,0.07)', borderRadius: 2 }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${(watched / MAX_PER_DAY) * 100}%`,
            background: watched >= MAX_PER_DAY
              ? 'linear-gradient(90deg,#FF4444,#FF8800)'
              : 'linear-gradient(90deg,#FFD700,#FF8800)',
            boxShadow: '0 0 6px rgba(255,215,0,0.4)',
            transition: 'width 0.4s',
          }} />
        </div>
      </div>

      {/* ── Wheel ── */}
      <div style={{
        position: 'relative', width: W, margin: '0 auto 22px',
        filter: 'drop-shadow(0 0 28px rgba(255,180,0,0.25))',
      }}>
        <canvas ref={cvRef} width={W} height={H} style={{ display: 'block' }} />
        <ParticleCanvas active={particles} color={partColor} />
      </div>

      {/* Win result */}
      {result && !result.limit && (() => {
        const tier = TIER[result.earned] || TIER[5]
        return (
          <div style={{
            border: `2px solid ${tier.color}`,
            borderRadius: 16, padding: '20px', marginBottom: 18, textAlign: 'center',
            background: `${tier.color}11`,
            boxShadow: `0 0 40px ${tier.color}44`,
            animation: 'popIn 0.4s cubic-bezier(0.175,0.885,0.32,1.275)',
          }}>
            <style>{`@keyframes popIn{0%{transform:scale(0.6);opacity:0}100%{transform:scale(1);opacity:1}}`}</style>
            <div style={{ color: tier.color, fontWeight: 900, fontSize: 14, letterSpacing: '2px', marginBottom: 6 }}>
              {tier.label}
            </div>
            <div style={{
              fontSize: 72, fontWeight: 900, lineHeight: 1,
              color: tier.color, filter: `drop-shadow(0 0 18px ${tier.color})`,
            }}>
              {result.earned}
            </div>
            <div style={{ color: tier.color, fontSize: 22, opacity: 0.8, marginTop: 2 }}>◆</div>
          </div>
        )
      })()}

      {/* Limit message */}
      {(result?.limit || remaining === 0) && (
        <div style={{
          background: 'rgba(255,80,0,0.07)', border: '1px solid rgba(255,80,0,0.25)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 18,
          color: '#FF8844', fontSize: 13, textAlign: 'center',
        }}>
          {isRu ? '🌙 Лимит исчерпан. Возвращайся завтра!' : '🌙 Daily limit reached. Come back tomorrow!'}
        </div>
      )}

      {/* ── Spin button — 3D with pulse ── */}
      <button
        onMouseDown={() => setBtnPressed(true)}
        onMouseUp={() => setBtnPressed(false)}
        onMouseLeave={() => setBtnPressed(false)}
        onClick={handleSpin}
        disabled={spinning || remaining === 0}
        style={{
          width: '100%', padding: '18px 0',
          background: remaining === 0
            ? 'rgba(255,255,255,0.05)'
            : spinning
              ? 'rgba(255,215,0,0.1)'
              : 'linear-gradient(180deg, #FFE050 0%, #FFB800 55%, #CC8800 100%)',
          color: remaining === 0
            ? 'rgba(255,255,255,0.2)'
            : spinning ? '#FFD700' : '#1a0d00',
          border: remaining === 0
            ? '1px solid rgba(255,255,255,0.08)'
            : spinning
              ? '1px solid rgba(255,215,0,0.3)'
              : '1px solid #CC8800',
          borderBottom: remaining === 0 || spinning ? undefined : '3px solid #996600',
          borderRadius: 14,
          fontSize: 17, fontWeight: 900, letterSpacing: '2px',
          cursor: remaining === 0 || spinning ? 'not-allowed' : 'pointer',
          transition: 'all 0.12s',
          transform: btnPressed ? 'translateY(2px) scale(0.985)' : 'translateY(0) scale(1)',
          boxShadow: remaining > 0 && !spinning
            ? btnPressed
              ? '0 1px 12px rgba(255,180,0,0.4)'
              : '0 4px 0 #886600, 0 0 30px rgba(255,180,0,0.45)'
            : 'none',
          fontFamily: 'inherit',
          animation: remaining > 0 && !spinning && !result ? 'pulsBtn 2s ease-in-out infinite' : 'none',
        }}
      >
        <style>{`
          @keyframes pulsBtn {
            0%,100% { box-shadow: 0 4px 0 #886600, 0 0 20px rgba(255,180,0,0.4); }
            50%      { box-shadow: 0 4px 0 #886600, 0 0 45px rgba(255,180,0,0.75); }
          }
        `}</style>
        {remaining === 0
          ? (isRu ? '✓ Лимит исчерпан' : '✓ Limit reached')
          : spinning
            ? (isRu ? '🎰  Крутится...' : '🎰  Spinning...')
            : (isRu ? `🎰  КРУТИТЬ  (осталось ${remaining})` : `🎰  SPIN  (${remaining} left)`)}
      </button>

      {/* Prize table */}
      <div style={{ marginTop: 30, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 22 }}>
        <div style={{
          color: 'rgba(255,255,255,0.25)', fontSize: 10, letterSpacing: '3px',
          textAlign: 'center', marginBottom: 14, textTransform: 'uppercase',
        }}>
          {isRu ? 'Таблица призов' : 'Prize Table'}
        </div>
        {[
          [50, '1%',  TIER[50].label],
          [30, '3%',  TIER[30].label],
          [15, '6%',  TIER[15].label],
          [7,  '12%', TIER[7].label],
          [5,  '78%', isRu ? 'Базовый приз' : 'Base prize'],
        ].map(([val, pct, label]) => (
          <div key={val} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '9px 14px', marginBottom: 5, borderRadius: 10,
            background: `${COLORS[val].stroke}0a`,
            border: `1px solid ${COLORS[val].stroke}22`,
          }}>
            <span style={{ color: COLORS[val].text, fontSize: 13, fontWeight: 700 }}>{label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{
                color: COLORS[val].text, fontSize: 20, fontWeight: 900,
                textShadow: `0 0 12px ${COLORS[val].shadow}`,
              }}>
                {val}◆
              </span>
              <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 11 }}>{pct}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
