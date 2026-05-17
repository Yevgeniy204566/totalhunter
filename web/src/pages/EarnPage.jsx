import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

// ═══════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════
const N   = 20
const SECTORS = [5, 7, 5, 15, 5, 30, 5, 7, 5, 15, 5, 7, 5, 15, 5, 50, 5, 7, 5, 30]
const SLICE   = (2 * Math.PI) / N
const MAX_DAY = 5

// Main canvas
const W = 360, H = 360, CX = 180, CY = 180
const R_OUTER = 174  // metallic rim outer radius
const R_DISC  = 155  // spinning disc radius
const R_HUB   = 23   // centre hub radius

// Offscreen pre-render disc (2× resolution for crispness)
const D_SIZE = 640, D_CX = 320, D_CY = 320, D_R = 310

// Colour palette per prize value
const C = {
  5:  { dark:'#060c42', mid:'#0f1e80', edge:'#1a33cc',
        glow:'#3355EE', text:'#8899FF', line:'#3355EE' },
  7:  { dark:'#011828', mid:'#023350', edge:'#044c78',
        glow:'#00BBDD', text:'#55DDFF', line:'#00BBDD' },
  15: { dark:'#011808', mid:'#022e12', edge:'#04551e',
        glow:'#00AA33', text:'#44DD66', line:'#00AA33' },
  30: { dark:'#2a0010', mid:'#550022', edge:'#880038',
        glow:'#DD1155', text:'#FF5588', line:'#DD1155' },
  50: { dark:'#150c00', mid:'#2a1800', edge:'#4a2d00',
        glow:'#DDC000', text:'#FFE040', line:'#FFD700' },
}

// ═══════════════════════════════════════════════════════
//  PRE-RENDER: DISC (called once, at high resolution)
// ═══════════════════════════════════════════════════════
function buildDisc() {
  const oc  = document.createElement('canvas')
  oc.width  = D_SIZE; oc.height = D_SIZE
  const ctx = oc.getContext('2d')

  // --- Sectors ---
  for (let i = 0; i < N; i++) {
    const val   = SECTORS[i]
    const c     = C[val]
    const sA    = -Math.PI / 2 + i * SLICE
    const eA    = sA + SLICE
    const mA    = sA + SLICE / 2

    // Deep gradient: dark centre → vivid edge
    const gx1 = D_CX + Math.cos(mA) * D_R * 0.08
    const gy1 = D_CY + Math.sin(mA) * D_R * 0.08
    const gx2 = D_CX + Math.cos(mA) * D_R * 0.97
    const gy2 = D_CY + Math.sin(mA) * D_R * 0.97
    const gr  = ctx.createLinearGradient(gx1, gy1, gx2, gy2)
    gr.addColorStop(0,    c.dark)
    gr.addColorStop(0.45, c.mid)
    gr.addColorStop(1,    c.edge)
    ctx.beginPath(); ctx.moveTo(D_CX, D_CY)
    ctx.arc(D_CX, D_CY, D_R, sA, eA); ctx.closePath()
    ctx.fillStyle = gr; ctx.fill()

    // Bright neon arc at outer edge of each sector
    ctx.save()
    ctx.beginPath()
    ctx.arc(D_CX, D_CY, D_R * 0.92, sA + 0.015, eA - 0.015)
    ctx.strokeStyle = c.glow
    ctx.lineWidth   = D_R * 0.10
    ctx.shadowBlur  = 28
    ctx.shadowColor = c.glow
    ctx.globalAlpha = 0.55
    ctx.stroke()
    ctx.restore()

    // ── Text: ALWAYS READABLE (upside-down fix) ──────────────
    const tr = D_R * 0.64
    const tx = D_CX + Math.cos(mA) * tr
    const ty = D_CY + Math.sin(mA) * tr
    ctx.save()
    ctx.translate(tx, ty)
    let rot = mA + Math.PI / 2
    const nm = ((mA % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)
    if (nm >= Math.PI / 2 && nm <= 3 * Math.PI / 2) rot += Math.PI
    ctx.rotate(rot)
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'

    // Number (large, bold, white + coloured shadow)
    const fs = D_R * (val === 50 ? 0.175 : val >= 15 ? 0.155 : 0.135)
    ctx.font      = `900 ${fs.toFixed(0)}px 'Courier New', monospace`
    ctx.fillStyle = '#ffffff'
    ctx.shadowBlur  = 22; ctx.shadowColor = c.glow
    ctx.fillText(String(val), 0, -fs * 0.35)

    // Diamond ◆ icon below number
    ctx.font      = `700 ${(fs * 0.6).toFixed(0)}px monospace`
    ctx.fillStyle = c.text
    ctx.shadowBlur = 18; ctx.shadowColor = c.glow
    ctx.fillText('◆', 0, fs * 0.72)
    ctx.restore()
  }

  // --- Metallic gold divider lines ---
  ctx.shadowBlur = 6; ctx.shadowColor = '#FFD700'
  for (let i = 0; i < N; i++) {
    const a = -Math.PI / 2 + i * SLICE
    const x1 = D_CX + Math.cos(a) * D_R * 0.12
    const y1 = D_CY + Math.sin(a) * D_R * 0.12
    const x2 = D_CX + Math.cos(a) * D_R * 0.99
    const y2 = D_CY + Math.sin(a) * D_R * 0.99
    const dg = ctx.createLinearGradient(x1, y1, x2, y2)
    dg.addColorStop(0, 'rgba(255,215,0,0.0)')
    dg.addColorStop(0.3, 'rgba(255,215,0,0.7)')
    dg.addColorStop(1, 'rgba(255,215,0,0.4)')
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2)
    ctx.strokeStyle = dg; ctx.lineWidth = 1.5; ctx.stroke()
  }
  ctx.shadowBlur = 0

  // --- Outer disc rim ring ---
  ctx.beginPath(); ctx.arc(D_CX, D_CY, D_R, 0, 2 * Math.PI)
  ctx.strokeStyle = 'rgba(255,215,0,0.65)'; ctx.lineWidth = 2
  ctx.shadowBlur = 14; ctx.shadowColor = '#FFD700'; ctx.stroke()
  ctx.shadowBlur = 0

  // --- Centre hub ---
  const hR  = D_R * 0.10
  const hg  = ctx.createRadialGradient(D_CX - hR * 0.4, D_CY - hR * 0.4, 0, D_CX, D_CY, hR)
  hg.addColorStop(0, '#9999CC'); hg.addColorStop(0.4, '#1a2040'); hg.addColorStop(1, '#050810')
  ctx.beginPath(); ctx.arc(D_CX, D_CY, hR, 0, 2 * Math.PI)
  ctx.fillStyle = hg; ctx.fill()
  ctx.strokeStyle = 'rgba(255,215,0,0.7)'; ctx.lineWidth = 1.5
  ctx.shadowBlur = 10; ctx.shadowColor = '#FFD700'; ctx.stroke()
  ctx.shadowBlur = 0

  return oc
}

// ═══════════════════════════════════════════════════════
//  PRE-RENDER: METALLIC BASE / RIM
// ═══════════════════════════════════════════════════════
function buildBase() {
  const oc  = document.createElement('canvas')
  oc.width  = W; oc.height = H
  const ctx = oc.getContext('2d')

  // Outer background glow
  const bg = ctx.createRadialGradient(CX, CY, R_DISC, CX, CY, R_OUTER + 8)
  bg.addColorStop(0, 'rgba(255,180,0,0)'); bg.addColorStop(1, 'rgba(255,120,0,0.18)')
  ctx.beginPath(); ctx.arc(CX, CY, R_OUTER + 8, 0, 2 * Math.PI)
  ctx.fillStyle = bg; ctx.fill()

  // Metallic rim body (annular ring)
  const rg = ctx.createRadialGradient(CX - 60, CY - 60, 10, CX, CY, R_OUTER)
  rg.addColorStop(0,    '#E8D060')   // bright highlight
  rg.addColorStop(0.28, '#C89820')   // gold
  rg.addColorStop(0.52, '#806010')   // shadow
  rg.addColorStop(0.74, '#503808')   // dark
  rg.addColorStop(0.88, '#705510')   // subtle catch light
  rg.addColorStop(1,    '#1a1204')   // very dark edge
  ctx.beginPath()
  ctx.arc(CX, CY, R_OUTER, 0, 2 * Math.PI)
  ctx.arc(CX, CY, R_DISC - 1, 0, 2 * Math.PI, true)
  ctx.fillStyle = rg; ctx.fill('evenodd')

  // Inner chrome ring (edge between rim and disc)
  ctx.beginPath(); ctx.arc(CX, CY, R_DISC + 2, 0, 2 * Math.PI)
  ctx.strokeStyle = '#FFD700'; ctx.lineWidth = 2
  ctx.shadowBlur = 18; ctx.shadowColor = '#FFD70066'; ctx.stroke()
  ctx.shadowBlur = 0

  // Outer gold border
  ctx.beginPath(); ctx.arc(CX, CY, R_OUTER - 1, 0, 2 * Math.PI)
  ctx.strokeStyle = 'rgba(255,200,0,0.5)'; ctx.lineWidth = 1.5
  ctx.shadowBlur = 8; ctx.shadowColor = '#FFD700'; ctx.stroke()
  ctx.shadowBlur = 0

  // Studs (pins) — alternating large/small, 3D with radial gradient
  const nStuds = 40, sR = R_OUTER - 11
  for (let i = 0; i < nStuds; i++) {
    const a = (i / nStuds) * 2 * Math.PI
    const sx = CX + sR * Math.cos(a), sy = CY + sR * Math.sin(a)
    const big = i % 5 === 0
    const sr2 = big ? 4.5 : 3
    const sg = ctx.createRadialGradient(sx - sr2 * 0.4, sy - sr2 * 0.4, 0, sx, sy, sr2)
    sg.addColorStop(0, '#FFFBE0'); sg.addColorStop(0.4, '#CC9900'); sg.addColorStop(1, '#443300')
    ctx.beginPath(); ctx.arc(sx, sy, sr2, 0, 2 * Math.PI)
    ctx.fillStyle = sg; ctx.fill()
    if (big) {
      ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.lineWidth = 0.5; ctx.stroke()
    }
  }

  // Inner shadow ring (depth under disc)
  const sh = ctx.createRadialGradient(CX, CY, R_DISC - 10, CX, CY, R_DISC + 6)
  sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.65)')
  ctx.beginPath(); ctx.arc(CX, CY, R_DISC + 6, 0, 2 * Math.PI)
  ctx.fillStyle = sh; ctx.fill()

  return oc
}

// ═══════════════════════════════════════════════════════
//  PRE-RENDER: GLASS SPECULAR OVERLAY
// ═══════════════════════════════════════════════════════
function buildGlass() {
  const oc  = document.createElement('canvas')
  oc.width  = W; oc.height = H
  const ctx = oc.getContext('2d')

  // Large soft highlight (upper-left)
  const g1 = ctx.createRadialGradient(CX - 52, CY - 62, 6, CX, CY, R_DISC)
  g1.addColorStop(0, 'rgba(255,255,255,0.17)')
  g1.addColorStop(0.4, 'rgba(255,255,255,0.06)')
  g1.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.beginPath(); ctx.arc(CX, CY, R_DISC, 0, 2 * Math.PI)
  ctx.fillStyle = g1; ctx.fill()

  // Bright glint streak
  ctx.save(); ctx.globalAlpha = 0.07
  ctx.beginPath()
  ctx.ellipse(CX - 28, CY - 52, 52, 13, -0.44, 0, 2 * Math.PI)
  ctx.fillStyle = '#ffffff'; ctx.fill()
  ctx.restore()

  // Subtle bottom vignette (darkens bottom edge)
  const v = ctx.createRadialGradient(CX, CY + R_DISC * 0.4, R_DISC * 0.3, CX, CY, R_DISC)
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.22)')
  ctx.beginPath(); ctx.arc(CX, CY, R_DISC, 0, 2 * Math.PI)
  ctx.fillStyle = v; ctx.fill()

  return oc
}

// ═══════════════════════════════════════════════════════
//  PER-FRAME: POINTER (spring physics applied outside)
// ═══════════════════════════════════════════════════════
function renderPointer(ctx, deflection) {
  const px = CX, py = CY - R_OUTER + 5

  ctx.save()
  ctx.translate(px, py + 10); ctx.rotate(deflection); ctx.translate(-px, -(py + 10))

  // Drop shadow
  ctx.beginPath()
  ctx.moveTo(px - 12, py + 4); ctx.lineTo(px + 12, py + 4); ctx.lineTo(px, py - 18)
  ctx.closePath(); ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fill()

  // 3D gradient pointer
  const pg = ctx.createLinearGradient(px - 12, py, px + 12, py)
  pg.addColorStop(0, '#996600'); pg.addColorStop(0.22, '#EEB800')
  pg.addColorStop(0.5, '#FFEE60'); pg.addColorStop(0.78, '#EEB800')
  pg.addColorStop(1, '#996600')
  ctx.beginPath()
  ctx.moveTo(px - 11, py + 3); ctx.lineTo(px + 11, py + 3); ctx.lineTo(px, py - 17)
  ctx.closePath()
  ctx.fillStyle = pg
  ctx.shadowBlur = 20; ctx.shadowColor = '#FFD700'; ctx.fill()
  ctx.shadowBlur = 0

  // Highlight edge
  ctx.beginPath()
  ctx.moveTo(px - 11, py + 3); ctx.lineTo(px + 11, py + 3); ctx.lineTo(px, py - 17)
  ctx.closePath()
  ctx.strokeStyle = 'rgba(255,255,200,0.35)'; ctx.lineWidth = 0.8; ctx.stroke()

  ctx.restore()
}

// ═══════════════════════════════════════════════════════
//  RATCHET SOUND — noise-based (realistic mechanical click)
// ═══════════════════════════════════════════════════════
function playRatchet(audioCtx, pitch = 1.0) {
  try {
    const sr   = audioCtx.sampleRate
    const len  = Math.floor(sr * 0.055)
    const buf  = audioCtx.createBuffer(1, len, sr)
    const data = buf.getChannelData(0)
    for (let i = 0; i < len; i++) {
      const t     = i / len
      const noise = (Math.random() * 2 - 1)
      const click = Math.sin(2 * Math.PI * 1800 * pitch * t)
      data[i]     = (noise * Math.exp(-t * 28) + click * Math.exp(-t * 60) * 0.4) * 0.45
    }
    const src = audioCtx.createBufferSource()
    src.buffer = buf
    const bpf = audioCtx.createBiquadFilter()
    bpf.type = 'bandpass'; bpf.frequency.value = 2800 * pitch; bpf.Q.value = 0.5
    const gain = audioCtx.createGain(); gain.gain.value = 0.28
    src.connect(bpf); bpf.connect(gain); gain.connect(audioCtx.destination)
    src.start(audioCtx.currentTime)
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════
//  PARTICLES
// ═══════════════════════════════════════════════════════
function ParticleCanvas({ active, color }) {
  const cvRef = useRef(null), rafRef = useRef(null)
  useEffect(() => {
    if (!active || !cvRef.current) return
    const cv = cvRef.current, ctx = cv.getContext('2d')
    const pts = Array.from({ length: 110 }, () => ({
      x: W / 2 + (Math.random() - 0.5) * 44,
      y: H / 2 + (Math.random() - 0.5) * 44,
      vx: (Math.random() - 0.5) * 17, vy: -Math.random() * 19 - 2,
      r: Math.random() * 5 + 1.5, life: 1,
      decay: Math.random() * 0.012 + 0.007,
      hue: [color, '#FFD700', '#ffffff', color][Math.floor(Math.random() * 4)],
    }))
    const tick = () => {
      ctx.clearRect(0, 0, W, H); let alive = false
      pts.forEach(p => {
        if (p.life <= 0) return; alive = true
        p.x += p.vx; p.y += p.vy; p.vy += 0.42; p.vx *= 0.984; p.life -= p.decay
        ctx.globalAlpha = Math.max(0, p.life)
        ctx.fillStyle = p.hue; ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * p.life, 0, Math.PI * 2); ctx.fill()
      })
      ctx.globalAlpha = 1
      if (alive) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [active, color])
  return (
    <canvas ref={cvRef} width={W} height={H}
      style={{ position:'absolute', top:0, left:0, pointerEvents:'none', opacity: active ? 1 : 0 }} />
  )
}

// ═══════════════════════════════════════════════════════
//  MAIN COMPONENT
// ═══════════════════════════════════════════════════════
export default function EarnPage() {
  const { lang }   = useLang()
  const isRu       = lang === 'ru'

  const [watched,    setWatched]    = useState(0)
  const [credits,    setCredits]    = useState(null)
  const [spinning,   setSpinning]   = useState(false)
  const [result,     setResult]     = useState(null)
  const [particles,  setParticles]  = useState(false)
  const [partColor,  setPartColor]  = useState('#FFD700')
  const [btnDown,    setBtnDown]    = useState(false)

  const cvRef      = useRef(null)
  const offBase    = useRef(null)
  const offDisc    = useRef(null)
  const offGlass   = useRef(null)
  const audioCtx   = useRef(null)
  const rafId      = useRef(null)

  // Physics state
  const phys = useRef({
    angle:  0,      // current wheel angle (rad)
    omega:  0,      // angular velocity (rad/frame)
    phase:  'idle', // 'accel'|'coast'|'decel'|'settle'|'idle'
    target: 0,      // target angle
    alpha:  0,      // deceleration (positive = slow down)
    frame:  0,      // frames in current phase
    earned: 0,
  })

  // Pointer spring
  const ptr = useRef({ a: 0, v: 0 })
  const lastSec = useRef(-1)

  // ── Build offscreen textures once ──────────────────────
  useEffect(() => {
    offBase.current  = buildBase()
    offDisc.current  = buildDisc()
    offGlass.current = buildGlass()
    renderFrame()
  }, [])

  // ── Data load ──────────────────────────────────────────
  useEffect(() => {
    api.me().then(u => setCredits(u.credits)).catch(() => {})
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(() => {})
  }, [])

  // ── Audio context ──────────────────────────────────────
  function getAudio() {
    if (!audioCtx.current)
      try { audioCtx.current = new (window.AudioContext || window.webkitAudioContext)() } catch(e) {}
    return audioCtx.current
  }

  // ── Render a single frame ──────────────────────────────
  function renderFrame() {
    const cv = cvRef.current; if (!cv) return
    const ctx = cv.getContext('2d')
    ctx.clearRect(0, 0, W, H)

    // Layer 1: metallic base/rim
    if (offBase.current) ctx.drawImage(offBase.current, 0, 0)

    // Layer 2: rotating disc (with motion blur when fast)
    if (offDisc.current) {
      const blur = Math.min(Math.abs(phys.current.omega) * 260, 9)
      if (blur > 0.4) ctx.filter = `blur(${blur.toFixed(1)}px)`
      ctx.save()
      ctx.translate(CX, CY)
      ctx.rotate(phys.current.angle)
      const ds = R_DISC * 2
      ctx.drawImage(offDisc.current, -R_DISC, -R_DISC, ds, ds)
      ctx.restore()
      if (blur > 0.4) ctx.filter = 'none'
    }

    // Layer 3: glass overlay
    if (offGlass.current) ctx.drawImage(offGlass.current, 0, 0)

    // Layer 4: pointer with spring deflection
    renderPointer(ctx, ptr.current.a)
  }

  // ── Physics + render loop ─────────────────────────────
  function animationLoop() {
    const p   = phys.current
    const pt  = ptr.current
    const ctx = getAudio()  // just to keep ref alive — not audio

    p.frame++

    // Pointer spring physics (always active)
    const K = 95, D = 0.74
    pt.v += (-K * pt.a) * 0.016
    pt.v *= D
    pt.a += pt.v * 0.016
    pt.a  = Math.max(-0.5, Math.min(0.5, pt.a))

    // Sector crossing → ratchet click + pointer impulse
    const modA      = ((p.angle % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)
    const curSec    = Math.floor(modA / SLICE) % N
    if (curSec !== lastSec.current) {
      const ac = getAudio()
      if (ac) {
        const speed  = Math.abs(p.omega)
        const pitch  = 0.6 + speed * 12
        playRatchet(ac, Math.min(pitch, 2.2))
      }
      pt.v += 0.28   // pointer kick
      lastSec.current = curSec
    }

    // Phase state machine ──────────────────────────────
    const PEAK   = 0.075   // rad/frame peak velocity
    const ACCEL  = 0.0028  // rad/frame² acceleration

    if (p.phase === 'accel') {
      p.omega = Math.min(p.omega + ACCEL, PEAK)
      p.angle += p.omega
      if (p.omega >= PEAK) { p.phase = 'coast'; p.frame = 0 }
    }
    else if (p.phase === 'coast') {
      p.omega  = PEAK
      p.angle += p.omega
      // Switch to decel when remaining distance ≈ what we need to stop
      const remaining = ((p.target - p.angle) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI)
      const decelDist = (PEAK * PEAK) / (2 * p.alpha)
      if (remaining <= decelDist + 0.05) { p.phase = 'decel'; p.frame = 0 }
    }
    else if (p.phase === 'decel') {
      p.omega  = Math.max(0, p.omega - p.alpha)
      p.angle += p.omega
      // When essentially stopped, snap to target
      if (p.omega < 0.001) {
        p.angle = p.target
        p.omega = -0.004   // tiny elastic reverse bounce
        p.phase = 'settle'; p.frame = 0
      }
    }
    else if (p.phase === 'settle') {
      // Elastic settle: spring to target
      const diff = p.target - p.angle
      p.omega = p.omega * 0.78 + diff * 0.06
      p.angle += p.omega
      if (p.frame > 30 || Math.abs(diff) < 0.0004) {
        p.angle = p.target
        p.omega = 0
        p.phase = 'idle'
        // Final ratchet (victory) click
        const ac = getAudio()
        if (ac) playRatchet(ac, 1.8)
        // Reveal result
        const data = p._data
        setWatched(w => w + 1)
        setCredits(data.credits)
        setResult({ earned: p.earned, jackpot: data.jackpot })
        setSpinning(false)
        if (p.earned >= 30) {
          setPartColor(C[p.earned]?.glow || '#FFD700')
          setParticles(true)
        }
        return   // stop loop
      }
    }

    renderFrame()
    rafId.current = requestAnimationFrame(animationLoop)
  }

  // ── Spin handler ───────────────────────────────────────
  const handleSpin = useCallback(async () => {
    if (spinning || Math.max(0, MAX_DAY - watched) === 0) return
    setSpinning(true); setResult(null); setParticles(false)

    try {
      const ac = getAudio()
      if (ac?.state === 'suspended') await ac.resume()
    } catch(e) {}

    let data
    try { data = await api.earnReward() } catch(e) { setSpinning(false); return }
    if (!data.success) { setSpinning(false); setResult({ limit: true }); return }

    const { earned, sector_index } = data
    const p = phys.current

    // Compute target angle where sector_index is at pointer (top = -PI/2)
    const sectorMid = -Math.PI / 2 + sector_index * SLICE + SLICE / 2
    const raw       = -sectorMid   // angle that puts this sector at top
    // Add full turns so we always spin forward ≥ 4 revolutions
    let norm = ((raw - p.angle) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI)
    if (norm === 0) norm = 2 * Math.PI
    const targetAngle = p.angle + 4 * 2 * Math.PI + norm

    // Compute friction coefficient for exact stop
    const PEAK   = 0.075
    const dist   = targetAngle - p.angle
    // Leave ~2.5 rad for decel phase
    const decelDist  = 2.5
    const coastDist  = dist - decelDist - 0.5  // 0.5 for accel
    const alpha      = (PEAK * PEAK) / (2 * decelDist)

    p.angle  = p.angle
    p.omega  = 0
    p.phase  = 'accel'
    p.target = targetAngle
    p.alpha  = alpha
    p.frame  = 0
    p.earned = earned
    p._data  = data
    lastSec.current = Math.floor((((-p.angle) % (2*Math.PI) + 2*Math.PI) % (2*Math.PI)) / SLICE) % N

    if (rafId.current) cancelAnimationFrame(rafId.current)
    rafId.current = requestAnimationFrame(animationLoop)
  }, [spinning, watched])

  const remaining = Math.max(0, MAX_DAY - watched)

  const TIER = {
    50: { label: isRu ? '🎰 ДЖЕКПОТ!!!' : '🎰 JACKPOT!!!', c: '#FFD700' },
    30: { label: isRu ? '🔥 MEGA WIN!'  : '🔥 MEGA WIN!',  c: '#FF3377' },
    15: { label: isRu ? '⚡ БОЛЬШОЙ ДРО́П!' : '⚡ BIG DROP!', c: '#00CC44' },
    7:  { label: isRu ? '✨ НЕПЛОХО!'   : '✨ NICE!',      c: '#00DDFF' },
    5:  { label: '+5 ◆', c: '#6688FF' },
  }

  // ── Render ─────────────────────────────────────────────
  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '24px 20px' }}>

      <h2 style={{
        fontSize: 28, fontWeight: 900, margin: '0 0 5px',
        background: 'linear-gradient(90deg,#FFD700 0%,#FF8800 50%,#FFD700 100%)',
        WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text',
        letterSpacing: '1px',
      }}>
        {isRu ? '🎰 Колесо Фортуны' : '🎰 Fortune Wheel'}
      </h2>
      <p style={{ color:'rgba(255,255,255,0.35)', fontSize:13, margin:'0 0 18px' }}>
        {isRu ? `Крути и выигрывай алмазы — до ${MAX_DAY} раз в день`
               : `Spin and win diamonds — up to ${MAX_DAY} times per day`}
      </p>

      {/* Balance */}
      {credits !== null && (
        <div style={{
          background:'rgba(255,215,0,0.05)', border:'1px solid rgba(255,215,0,0.18)',
          borderRadius:12, padding:'12px 18px', marginBottom:18,
          display:'flex', alignItems:'center', justifyContent:'space-between',
        }}>
          <span style={{ color:'rgba(255,255,255,0.4)', fontSize:12 }}>
            {isRu ? 'Баланс' : 'Balance'}
          </span>
          <span style={{ color:'#FFD700', fontSize:22, fontWeight:900,
            textShadow:'0 0 14px rgba(255,215,0,0.5)' }}>
            {credits.toLocaleString()} ◆
          </span>
        </div>
      )}

      {/* Progress */}
      <div style={{ marginBottom:20 }}>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
          <span style={{ color:'rgba(255,255,255,0.3)', fontSize:11, letterSpacing:'1px' }}>
            {isRu ? 'СЕГОДНЯ' : 'TODAY'}
          </span>
          <span style={{ color: watched >= MAX_DAY ? '#FF4444' : '#FFD700',
            fontSize:11, fontWeight:700 }}>
            {watched} / {MAX_DAY}
          </span>
        </div>
        <div style={{ height:4, background:'rgba(255,255,255,0.07)', borderRadius:2 }}>
          <div style={{
            height:'100%', borderRadius:2,
            width:`${(watched / MAX_DAY) * 100}%`,
            background: watched >= MAX_DAY
              ? 'linear-gradient(90deg,#FF4444,#FF8800)'
              : 'linear-gradient(90deg,#FFD700,#FF8800)',
            boxShadow:'0 0 6px rgba(255,215,0,0.45)',
            transition:'width 0.4s',
          }} />
        </div>
      </div>

      {/* Wheel */}
      <div style={{
        position:'relative', width:W, margin:'0 auto 20px',
        filter:'drop-shadow(0 6px 36px rgba(255,160,0,0.3))',
      }}>
        <canvas ref={cvRef} width={W} height={H} style={{ display:'block' }} />
        <ParticleCanvas active={particles} color={partColor} />
      </div>

      {/* Win result */}
      {result && !result.limit && (() => {
        const t = TIER[result.earned] || TIER[5]
        return (
          <div style={{
            border:`2px solid ${t.c}`, borderRadius:16, padding:'18px 20px',
            marginBottom:16, textAlign:'center',
            background:`${t.c}10`,
            boxShadow:`0 0 42px ${t.c}44, inset 0 0 20px ${t.c}08`,
            animation:'popIn 0.42s cubic-bezier(0.175,0.885,0.32,1.275)',
          }}>
            <style>{`@keyframes popIn{0%{transform:scale(0.55);opacity:0}100%{transform:scale(1);opacity:1}}`}</style>
            <div style={{ color:t.c, fontWeight:900, fontSize:14,
              letterSpacing:'2px', marginBottom:5 }}>{t.label}</div>
            <div style={{ fontSize:70, fontWeight:900, lineHeight:1,
              color:t.c, filter:`drop-shadow(0 0 20px ${t.c})` }}>
              {result.earned}
            </div>
            <div style={{ color:t.c, fontSize:22, opacity:0.8, marginTop:2 }}>◆</div>
          </div>
        )
      })()}

      {/* Limit */}
      {(result?.limit || remaining === 0) && (
        <div style={{
          background:'rgba(255,80,0,0.07)', border:'1px solid rgba(255,80,0,0.25)',
          borderRadius:10, padding:'12px 16px', marginBottom:16,
          color:'#FF8844', fontSize:13, textAlign:'center',
        }}>
          {isRu ? '🌙 Лимит исчерпан. Возвращайся завтра!'
                : '🌙 Daily limit reached. Come back tomorrow!'}
        </div>
      )}

      {/* 3D Spin button */}
      <button
        onPointerDown={() => setBtnDown(true)}
        onPointerUp={() => setBtnDown(false)}
        onPointerLeave={() => setBtnDown(false)}
        onClick={handleSpin}
        disabled={spinning || remaining === 0}
        style={{
          width:'100%', padding:'18px 0',
          background: remaining === 0
            ? 'rgba(255,255,255,0.05)'
            : spinning
              ? 'rgba(255,215,0,0.08)'
              : btnDown
                ? 'linear-gradient(180deg,#CC8800 0%,#AA6600 100%)'
                : 'linear-gradient(180deg,#FFE050 0%,#EEB000 55%,#BB8000 100%)',
          color: remaining === 0 ? 'rgba(255,255,255,0.2)'
               : spinning ? '#FFD700' : '#1a0900',
          border: remaining === 0 ? '1px solid rgba(255,255,255,0.07)'
                : spinning ? '1px solid rgba(255,215,0,0.25)'
                : `1px solid #AA7700`,
          borderBottom: (!spinning && remaining > 0 && !btnDown)
            ? '4px solid #7A5500' : undefined,
          borderRadius:14, fontSize:17, fontWeight:900, letterSpacing:'2px',
          cursor: remaining === 0 || spinning ? 'not-allowed' : 'pointer',
          transition:'all 0.1s',
          transform: btnDown ? 'translateY(3px) scale(0.988)' : 'none',
          boxShadow: remaining > 0 && !spinning
            ? btnDown
              ? '0 1px 10px rgba(255,170,0,0.4)'
              : '0 5px 0 #6A4400, 0 0 32px rgba(255,170,0,0.5)'
            : 'none',
          fontFamily:'inherit',
          animation: remaining > 0 && !spinning && !result
            ? 'pulseBtn 2.2s ease-in-out infinite' : 'none',
        }}
      >
        <style>{`
          @keyframes pulseBtn {
            0%,100%{ box-shadow:0 5px 0 #6A4400,0 0 24px rgba(255,170,0,0.45); }
            50%    { box-shadow:0 5px 0 #6A4400,0 0 50px rgba(255,190,0,0.80); }
          }
        `}</style>
        {remaining === 0 ? (isRu ? '✓ Лимит исчерпан' : '✓ Limit reached')
         : spinning ? (isRu ? '🎰  Крутится...' : '🎰  Spinning...')
         : (isRu ? `🎰  КРУТИТЬ  (осталось ${remaining})` : `🎰  SPIN  (${remaining} left)`)}
      </button>

      {/* Prize table */}
      <div style={{ marginTop:28, borderTop:'1px solid rgba(255,255,255,0.06)', paddingTop:20 }}>
        <div style={{ color:'rgba(255,255,255,0.22)', fontSize:10, letterSpacing:'3px',
          textAlign:'center', marginBottom:12, textTransform:'uppercase' }}>
          {isRu ? 'Таблица призов' : 'Prize Table'}
        </div>
        {[[50,'1%',TIER[50].label],[30,'3%',TIER[30].label],
          [15,'6%',TIER[15].label],[7,'12%',TIER[7].label],
          [5,'78%',isRu?'Базовый приз':'Base prize']
        ].map(([v, pct, lbl]) => (
          <div key={v} style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'8px 14px', marginBottom:5, borderRadius:10,
            background:`${C[v].glow}0a`, border:`1px solid ${C[v].glow}20`,
          }}>
            <span style={{ color:C[v].text, fontSize:13, fontWeight:700 }}>{lbl}</span>
            <div style={{ display:'flex', alignItems:'center', gap:10 }}>
              <span style={{ color:C[v].text, fontSize:20, fontWeight:900,
                textShadow:`0 0 12px ${C[v].glow}` }}>{v}◆</span>
              <span style={{ color:'rgba(255,255,255,0.2)', fontSize:11 }}>{pct}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
