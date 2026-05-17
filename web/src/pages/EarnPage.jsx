import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

// ═══════════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════════
const N       = 20
const SECTORS = [5, 7, 5, 15, 5, 30, 5, 7, 5, 15, 5, 7, 5, 15, 5, 50, 5, 7, 5, 30]
const SLICE   = (2 * Math.PI) / N   // 18° per sector
const MAX_DAY = 5

// Canvas rendered at 2× for retina crispness
const DPR   = 2
const SIZE  = 360                    // CSS px
const CS    = SIZE * DPR             // canvas px = 720
const CCX   = CS / 2, CCY = CS / 2  // 360, 360
const R_RIM = 174 * DPR              // outer rim radius px
const R_DISC = 153 * DPR             // sector disc radius px
const R_HUB  = 22 * DPR             // hub radius px

// Sector colours: dark/mid/edge for gradient, glow for neon, text for label
const SC = {
  5:  { d:'#060c3e', m:'#0d1c6e', e:'#1530a8', g:'#2244CC', t:'#7090FF', p:'#2244CC' },
  7:  { d:'#001624', m:'#012840', e:'#024a70', g:'#0099BB', t:'#44CCEE', p:'#0099BB' },
  15: { d:'#011508', m:'#022610', e:'#044020', g:'#009922', t:'#33CC55', p:'#009922' },
  30: { d:'#280010', m:'#4a001e', e:'#780033', g:'#CC0044', t:'#FF3366', p:'#CC0044' },
  50: { d:'#120900', m:'#271400', e:'#402000', g:'#CCAA00', t:'#FFD700', p:'#CCAA00' },
}

// ═══════════════════════════════════════════════════════════════════
//  ASYNC TEXTURE BUILDER — SVG feTurbulence + feSpecularLighting
//  This produces a REAL physically-based metallic texture, not a gradient
// ═══════════════════════════════════════════════════════════════════
async function loadSVGTexture(svgStr, w, h) {
  return new Promise(resolve => {
    const img = new Image()
    img.onload  = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgStr)}`
  })
}

// Gold metallic rim texture with physical specular lighting
function buildRimSVG() {
  const S = CS, cx = CCX, cy = CCY
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}">
<defs>
  <radialGradient id="gBase" cx="38%" cy="35%" r="68%">
    <stop offset="0%"   stop-color="#F4DC6A"/>
    <stop offset="22%"  stop-color="#C8940A"/>
    <stop offset="48%"  stop-color="#8C6410"/>
    <stop offset="72%"  stop-color="#4A3208"/>
    <stop offset="88%"  stop-color="#6A4C0C"/>
    <stop offset="100%" stop-color="#180E02"/>
  </radialGradient>
  <filter id="mf" x="-2%" y="-2%" width="104%" height="104%" color-interpolation-filters="sRGB">
    <feTurbulence type="turbulence" baseFrequency="0.018 0.038" numOctaves="5" seed="7" result="noise"/>
    <feColorMatrix type="saturate" values="0" in="noise" result="gn"/>
    <feSpecularLighting surfaceScale="7" specularConstant="1.4" specularExponent="28"
      lighting-color="#FFF0C0" in="gn" result="spec">
      <feDistantLight azimuth="215" elevation="48"/>
    </feSpecularLighting>
    <feComposite operator="arithmetic" k1="0" k2="0.52" k3="0.48" k4="0"
      in="spec" in2="SourceGraphic" result="out"/>
    <feBlend in="SourceGraphic" in2="out" mode="screen"/>
  </filter>
  <radialGradient id="iShadow" cx="50%" cy="50%" r="50%">
    <stop offset="82%" stop-color="rgba(0,0,0,0)"/>
    <stop offset="100%" stop-color="rgba(0,0,0,0.75)"/>
  </radialGradient>
  <radialGradient id="oGlow" cx="50%" cy="50%" r="50%">
    <stop offset="92%" stop-color="rgba(255,200,0,0)"/>
    <stop offset="100%" stop-color="rgba(255,160,0,0.35)"/>
  </radialGradient>
</defs>
<circle cx="${cx}" cy="${cy}" r="${R_RIM+8}" fill="url(#oGlow)"/>
<circle cx="${cx}" cy="${cy}" r="${R_RIM}" fill="url(#gBase)" filter="url(#mf)"/>
<circle cx="${cx}" cy="${cy}" r="${R_DISC+2}" fill="#060810"/>
<circle cx="${cx}" cy="${cy}" r="${R_RIM}" fill="url(#iShadow)"/>
</svg>`
}

// Pre-rendered sector disc at DPR×DPR quality
function buildDiscCanvas() {
  const oc = document.createElement('canvas')
  oc.width = oc.height = CS
  const ctx = oc.getContext('2d')

  for (let i = 0; i < N; i++) {
    const v  = SECTORS[i], c = SC[v]
    const sA = -Math.PI / 2 + i * SLICE
    const eA = sA + SLICE
    const mA = sA + SLICE / 2

    // 3D pocket effect: dark inner edge → mid floor → lit outer rim
    const irx = CCX + Math.cos(mA) * R_DISC * 0.05
    const iry = CCY + Math.sin(mA) * R_DISC * 0.05
    const orx = CCX + Math.cos(mA) * R_DISC * 0.98
    const ory = CCY + Math.sin(mA) * R_DISC * 0.98
    const gr = ctx.createLinearGradient(irx, iry, orx, ory)
    gr.addColorStop(0,    c.d)
    gr.addColorStop(0.18, c.d)
    gr.addColorStop(0.45, c.m)
    gr.addColorStop(0.75, c.e)
    gr.addColorStop(1,    c.d)  // outer shadow
    ctx.beginPath()
    ctx.moveTo(CCX, CCY)
    ctx.arc(CCX, CCY, R_DISC, sA, eA)
    ctx.closePath()
    ctx.fillStyle = gr
    ctx.fill()

    // Neon LED strip at the outer edge of each sector
    ctx.save()
    ctx.beginPath()
    ctx.arc(CCX, CCY, R_DISC * 0.91, sA + 0.018, eA - 0.018)
    ctx.strokeStyle = c.g
    ctx.lineWidth   = R_DISC * 0.09
    ctx.shadowBlur  = 32 * DPR
    ctx.shadowColor = c.g
    ctx.globalAlpha = 0.6
    ctx.stroke()
    ctx.restore()

    // ── Readable text: normAngle flip so bottom half never inverts ──
    const tr  = R_DISC * 0.62
    const tx  = CCX + Math.cos(mA) * tr
    const ty  = CCY + Math.sin(mA) * tr
    ctx.save()
    ctx.translate(tx, ty)
    let rot = mA + Math.PI / 2
    const nm = ((mA % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)
    if (nm >= Math.PI / 2 && nm <= 3 * Math.PI / 2) rot += Math.PI
    ctx.rotate(rot)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    // Main number — large white with neon glow
    const fs = R_DISC * (v === 50 ? 0.175 : v >= 15 ? 0.155 : 0.135)
    ctx.font      = `900 ${fs | 0}px 'Arial Black', sans-serif`
    ctx.fillStyle = '#ffffff'
    ctx.shadowBlur  = 24 * DPR
    ctx.shadowColor = c.g
    ctx.fillText(String(v), 0, -(fs * 0.3))

    // Diamond icon below number
    ctx.font        = `700 ${(fs * 0.58) | 0}px sans-serif`
    ctx.fillStyle   = c.t
    ctx.shadowBlur  = 16 * DPR
    ctx.shadowColor = c.g
    ctx.fillText('◆', 0, fs * 0.68)
    ctx.restore()
  }

  // Metallic divider lines between sectors
  for (let i = 0; i < N; i++) {
    const a  = -Math.PI / 2 + i * SLICE
    const x1 = CCX + Math.cos(a) * R_DISC * 0.14
    const y1 = CCY + Math.sin(a) * R_DISC * 0.14
    const x2 = CCX + Math.cos(a) * R_DISC * 0.99
    const y2 = CCY + Math.sin(a) * R_DISC * 0.99
    const dl = ctx.createLinearGradient(x1, y1, x2, y2)
    dl.addColorStop(0,   'rgba(255,215,0,0.0)')
    dl.addColorStop(0.25,'rgba(255,215,0,0.6)')
    dl.addColorStop(0.75,'rgba(255,215,0,0.55)')
    dl.addColorStop(1,   'rgba(255,215,0,0.2)')
    ctx.beginPath()
    ctx.moveTo(x1, y1); ctx.lineTo(x2, y2)
    ctx.strokeStyle = dl
    ctx.lineWidth = 1.5 * DPR
    ctx.shadowBlur = 4 * DPR
    ctx.shadowColor = '#FFD700'
    ctx.stroke()
  }
  ctx.shadowBlur = 0

  // Outer disc border ring
  ctx.beginPath()
  ctx.arc(CCX, CCY, R_DISC, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(255,215,0,0.7)'
  ctx.lineWidth = 2 * DPR
  ctx.shadowBlur = 12 * DPR
  ctx.shadowColor = '#FFD700'
  ctx.stroke()
  ctx.shadowBlur = 0

  // Centre hub with chrome gradient
  const hg = ctx.createRadialGradient(
    CCX - R_HUB * 0.38, CCY - R_HUB * 0.38, 1,
    CCX, CCY, R_HUB
  )
  hg.addColorStop(0,   '#CCCCEE')
  hg.addColorStop(0.35,'#3040A0')
  hg.addColorStop(0.7, '#10163A')
  hg.addColorStop(1,   '#04060C')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_HUB, 0, Math.PI * 2)
  ctx.fillStyle = hg; ctx.fill()
  ctx.strokeStyle = 'rgba(255,215,0,0.75)'
  ctx.lineWidth = 2 * DPR
  ctx.shadowBlur = 10 * DPR
  ctx.shadowColor = '#FFD700'
  ctx.stroke()
  ctx.shadowBlur = 0
  return oc
}

// Glass specular overlay (drawn over everything, wheel spins UNDER this)
function buildGlassCanvas() {
  const oc = document.createElement('canvas')
  oc.width = oc.height = CS
  const ctx = oc.getContext('2d')

  // Soft PBR specular — physically-based highlight from upper-left light source
  const g1 = ctx.createRadialGradient(
    CCX - 100 * DPR, CCY - 120 * DPR, 8 * DPR,
    CCX, CCY, R_DISC
  )
  g1.addColorStop(0,    'rgba(255,255,255,0.18)')
  g1.addColorStop(0.38, 'rgba(255,255,255,0.07)')
  g1.addColorStop(0.72, 'rgba(255,255,255,0.02)')
  g1.addColorStop(1,    'rgba(255,255,255,0.00)')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC, 0, Math.PI * 2)
  ctx.fillStyle = g1; ctx.fill()

  // Secondary glint (lens-flare style)
  ctx.save()
  ctx.globalAlpha = 0.06
  ctx.beginPath()
  ctx.ellipse(CCX - 52*DPR, CCY - 100*DPR, 96*DPR, 22*DPR, -0.44, 0, Math.PI * 2)
  ctx.fillStyle = '#ffffff'; ctx.fill()
  ctx.restore()

  // Bottom vignette to push eye toward centre
  const vg = ctx.createRadialGradient(CCX, CCY + R_DISC * 0.5, R_DISC * 0.2, CCX, CCY, R_DISC)
  vg.addColorStop(0, 'rgba(0,0,0,0)')
  vg.addColorStop(1, 'rgba(0,0,0,0.28)')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC, 0, Math.PI * 2)
  ctx.fillStyle = vg; ctx.fill()
  return oc
}

// Gold studs drawn directly onto main canvas each frame (they're on the rim)
function drawStuds(ctx) {
  const n = 40, sr = R_RIM - 20 * DPR
  for (let i = 0; i < n; i++) {
    const a  = (i / n) * Math.PI * 2
    const sx = CCX + Math.cos(a) * sr, sy = CCY + Math.sin(a) * sr
    const big = i % 5 === 0, r = big ? 5 * DPR : 3.5 * DPR
    const sg = ctx.createRadialGradient(sx - r*0.4, sy - r*0.4, 0, sx, sy, r)
    sg.addColorStop(0, '#FFFAE0')
    sg.addColorStop(0.45, '#CC9900')
    sg.addColorStop(1, '#3A2500')
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2)
    ctx.fillStyle = sg; ctx.fill()
    if (big) {
      ctx.strokeStyle = 'rgba(0,0,0,0.3)'
      ctx.lineWidth = 0.5 * DPR
      ctx.stroke()
    }
  }
}

// Inner golden ring border (between rim and disc)
function drawInnerRing(ctx) {
  ctx.beginPath()
  ctx.arc(CCX, CCY, R_DISC + 4 * DPR, 0, Math.PI * 2)
  ctx.strokeStyle = '#FFD700'
  ctx.lineWidth = 3 * DPR
  ctx.shadowBlur = 22 * DPR
  ctx.shadowColor = 'rgba(255,215,0,0.7)'
  ctx.stroke()
  ctx.shadowBlur = 0
}

// Animated pointer with spring physics
function drawPointer(ctx, deflection) {
  const px = CCX, py = CCY - R_RIM + 8 * DPR
  ctx.save()
  ctx.translate(px, py + 14*DPR); ctx.rotate(deflection); ctx.translate(-px, -(py + 14*DPR))

  // Emboss shadow
  ctx.shadowBlur = 8 * DPR; ctx.shadowColor = 'rgba(0,0,0,0.6)'
  ctx.beginPath()
  ctx.moveTo(px - 13*DPR, py + 5*DPR)
  ctx.lineTo(px + 13*DPR, py + 5*DPR)
  ctx.lineTo(px, py - 20*DPR)
  ctx.closePath(); ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fill()
  ctx.shadowBlur = 0

  // Chrome-gold pointer body
  const pg = ctx.createLinearGradient(px - 13*DPR, py, px + 13*DPR, py)
  pg.addColorStop(0,    '#7A4E00')
  pg.addColorStop(0.18, '#D4920A')
  pg.addColorStop(0.5,  '#FFE860')
  pg.addColorStop(0.82, '#D4920A')
  pg.addColorStop(1,    '#7A4E00')
  ctx.beginPath()
  ctx.moveTo(px - 12*DPR, py + 4*DPR)
  ctx.lineTo(px + 12*DPR, py + 4*DPR)
  ctx.lineTo(px, py - 19*DPR)
  ctx.closePath()
  ctx.fillStyle = pg
  ctx.shadowBlur = 22 * DPR; ctx.shadowColor = '#FFD700'; ctx.fill()
  ctx.shadowBlur = 0

  // Specular highlight line along top edge
  ctx.beginPath()
  ctx.moveTo(px - 12*DPR, py + 4*DPR); ctx.lineTo(px + 12*DPR, py + 4*DPR)
  ctx.lineTo(px, py - 19*DPR); ctx.closePath()
  ctx.strokeStyle = 'rgba(255,255,220,0.4)'; ctx.lineWidth = 1.5 * DPR; ctx.stroke()
  ctx.restore()
}

// ═══════════════════════════════════════════════════════════════════
//  RATCHET SOUND — noise burst (sampled ratchet click simulation)
// ═══════════════════════════════════════════════════════════════════
function playRatchet(actx, pitch = 1.0) {
  try {
    const sr  = actx.sampleRate, len = (sr * 0.052) | 0
    const buf = actx.createBuffer(1, len, sr), d = buf.getChannelData(0)
    for (let i = 0; i < len; i++) {
      const t = i / len
      // White noise + high-pitched click component + exponential decay
      d[i] = ((Math.random() * 2 - 1) * Math.exp(-t * 32)
              + Math.sin(2 * Math.PI * 2200 * pitch * t) * Math.exp(-t * 80) * 0.5) * 0.4
    }
    const src = actx.createBufferSource(); src.buffer = buf
    const bpf = actx.createBiquadFilter()
    bpf.type = 'bandpass'; bpf.frequency.value = 3500 * pitch; bpf.Q.value = 0.45
    const g = actx.createGain(); g.gain.value = 0.3
    src.connect(bpf); bpf.connect(g); g.connect(actx.destination)
    src.start(actx.currentTime)
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════════════════
//  PARTICLES
// ═══════════════════════════════════════════════════════════════════
function ParticleCanvas({ active, color }) {
  const cvRef = useRef(null), rafRef = useRef(null)
  useEffect(() => {
    if (!active || !cvRef.current) return
    const cv = cvRef.current, ctx = cv.getContext('2d')
    const pts = Array.from({ length: 110 }, () => ({
      x: SIZE/2 + (Math.random()-.5)*40, y: SIZE/2 + (Math.random()-.5)*40,
      vx: (Math.random()-.5)*16, vy: -Math.random()*19-2,
      r: Math.random()*5+1.5, life: 1, decay: Math.random()*0.012+0.007,
      hue: [color,'#FFD700','#fff',color][Math.floor(Math.random()*4)],
    }))
    const tick = () => {
      ctx.clearRect(0, 0, SIZE, SIZE); let alive = false
      pts.forEach(p => {
        if (p.life <= 0) return; alive = true
        p.x+=p.vx; p.y+=p.vy; p.vy+=0.42; p.vx*=0.985; p.life-=p.decay
        ctx.globalAlpha = Math.max(0, p.life)
        ctx.fillStyle = p.hue; ctx.beginPath()
        ctx.arc(p.x, p.y, p.r*p.life, 0, Math.PI*2); ctx.fill()
      })
      ctx.globalAlpha = 1
      if (alive) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [active, color])
  return (
    <canvas ref={cvRef} width={SIZE} height={SIZE}
      style={{ position:'absolute',top:0,left:0,pointerEvents:'none',opacity:active?1:0 }}/>
  )
}

// ═══════════════════════════════════════════════════════════════════
//  MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════
export default function EarnPage() {
  const { lang } = useLang(); const isRu = lang === 'ru'

  const [watched,   setWatched]   = useState(0)
  const [credits,   setCredits]   = useState(null)
  const [spinning,  setSpinning]  = useState(false)
  const [result,    setResult]    = useState(null)
  const [particles, setParticles] = useState(false)
  const [partColor, setPartColor] = useState('#FFD700')
  const [btnDown,   setBtnDown]   = useState(false)

  const cvRef   = useRef(null)
  const rimImg  = useRef(null)   // SVG texture (Image)
  const discOff = useRef(null)   // pre-rendered disc (Canvas)
  const glassOff= useRef(null)   // pre-rendered glass (Canvas)
  const audioRef= useRef(null)
  const rafId   = useRef(null)

  // Physics state
  const phys = useRef({ angle:0, omega:0, phase:'idle',
    target:0, alpha:0, earned:0, frame:0, _data:null })
  // Pointer spring
  const ptr     = useRef({ a:0, v:0 })
  const lastSec = useRef(-1)

  // ── Load all textures, then do initial render ──────────────────
  useEffect(() => {
    let cancelled = false
    async function init() {
      // SVG metallic rim texture (real PBR specular lighting)
      const svgStr = buildRimSVG()
      const img    = await loadSVGTexture(svgStr, CS, CS)
      if (cancelled) return
      rimImg.current  = img
      discOff.current = buildDiscCanvas()
      glassOff.current= buildGlassCanvas()
      renderFrame()
    }
    init()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    api.me().then(u => setCredits(u.credits)).catch(()=>{})
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(()=>{})
  }, [])

  function getAudio() {
    if (!audioRef.current)
      try { audioRef.current = new (window.AudioContext || window.webkitAudioContext)() } catch(e){}
    return audioRef.current
  }

  // ── Composite all layers each frame ───────────────────────────
  function renderFrame() {
    const cv = cvRef.current; if (!cv) return
    const ctx = cv.getContext('2d')
    ctx.clearRect(0, 0, CS, CS)

    // Layer 1 — SVG metallic rim texture
    if (rimImg.current) ctx.drawImage(rimImg.current, 0, 0)

    // Draw studs + inner gold ring on top of rim
    drawStuds(ctx)
    drawInnerRing(ctx)

    // Layer 2 — rotating disc (motion blur when fast)
    if (discOff.current) {
      const blur = Math.min(Math.abs(phys.current.omega) * 1400, 12)
      if (blur > 0.4) ctx.filter = `blur(${blur.toFixed(1)}px)`
      ctx.save()
      ctx.translate(CCX, CCY); ctx.rotate(phys.current.angle)
      ctx.drawImage(discOff.current, -R_DISC, -R_DISC, R_DISC*2, R_DISC*2)
      ctx.restore()
      if (blur > 0.4) ctx.filter = 'none'
    }

    // Layer 3 — glass specular overlay
    if (glassOff.current) ctx.drawImage(glassOff.current, 0, 0)

    // Layer 4 — pointer (spring physics)
    drawPointer(ctx, ptr.current.a)
  }

  // ── Animation loop: physics + render ─────────────────────────
  function loop() {
    const p = phys.current, pt = ptr.current
    p.frame++

    // Pointer spring (always active for natural feel)
    pt.v += (-95 * pt.a) * 0.016
    pt.v *= 0.73
    pt.a += pt.v * 0.016
    pt.a  = Math.max(-0.52, Math.min(0.52, pt.a))

    // Ratchet trigger on sector crossing
    const modA   = ((p.angle % (Math.PI*2)) + Math.PI*2) % (Math.PI*2)
    const curSec = (Math.floor(modA / SLICE)) % N
    if (curSec !== lastSec.current) {
      const ac = getAudio()
      if (ac) {
        const spd = Math.abs(p.omega)
        playRatchet(ac, Math.min(0.55 + spd * 1000, 2.4))
      }
      pt.v += 0.30   // pointer impulse
      lastSec.current = curSec
    }

    // Angular friction physics (4 phases)
    const PEAK = 0.075, ACCEL = 0.003

    if (p.phase === 'accel') {
      p.omega  = Math.min(p.omega + ACCEL, PEAK)
      p.angle += p.omega
      if (p.omega >= PEAK) { p.phase = 'coast'; p.frame = 0 }
    }
    else if (p.phase === 'coast') {
      p.angle += PEAK
      // Transition to decel when remaining ≤ decel distance
      const rem      = ((p.target - p.angle) % (Math.PI*2) + Math.PI*2) % (Math.PI*2)
      const decelDst = (PEAK * PEAK) / (2 * p.alpha)
      if (rem <= decelDst + 0.08) { p.phase = 'decel'; p.omega = PEAK; p.frame = 0 }
    }
    else if (p.phase === 'decel') {
      p.omega  = Math.max(0, p.omega - p.alpha)
      p.angle += p.omega
      if (p.omega < 0.0008) {
        p.angle  = p.target
        p.omega  = -0.0045  // elastic reverse impulse
        p.phase  = 'settle'; p.frame = 0
      }
    }
    else if (p.phase === 'settle') {
      const diff = p.target - p.angle
      p.omega = p.omega * 0.76 + diff * 0.07
      p.angle += p.omega
      if (p.frame > 28 || Math.abs(diff) < 0.0003) {
        p.angle = p.target; p.omega = 0; p.phase = 'idle'
        // Victory click
        const ac = getAudio(); if (ac) playRatchet(ac, 1.9)
        const data = p._data
        setWatched(w => w + 1)
        setCredits(data.credits)
        setResult({ earned: p.earned, jackpot: data.jackpot })
        setSpinning(false)
        if (p.earned >= 30) {
          setPartColor(SC[p.earned]?.p || '#FFD700')
          setParticles(true)
        }
        renderFrame(); return  // stop loop after idle
      }
    }

    renderFrame()
    rafId.current = requestAnimationFrame(loop)
  }

  // ── Spin handler ──────────────────────────────────────────────
  const handleSpin = useCallback(async () => {
    if (spinning || Math.max(0, MAX_DAY - watched) === 0) return
    setSpinning(true); setResult(null); setParticles(false)

    try { const ac = getAudio(); if (ac?.state==='suspended') await ac.resume() } catch(e){}

    let data
    try { data = await api.earnReward() } catch(e) { setSpinning(false); return }
    if (!data.success) { setSpinning(false); setResult({ limit:true }); return }

    const { earned, sector_index } = data
    const p = phys.current

    // Target wheel angle: sector_index at pointer (top = -PI/2)
    // Sector i center at: -PI/2 + i*SLICE + SLICE/2 in disc frame
    // For it to be at pointer (world angle = 0): wheelAngle = -(sectorCenter)
    const sCenter = -Math.PI/2 + sector_index*SLICE + SLICE/2
    const rawTarget = -sCenter
    let norm = ((rawTarget - p.angle) % (Math.PI*2) + Math.PI*2) % (Math.PI*2)
    if (norm === 0) norm = Math.PI*2
    const target = p.angle + 4 * Math.PI*2 + norm

    // Friction coefficient for exact stop over ~2.5 rad decel
    p.omega = 0; p.angle = p.angle; p.phase = 'accel'
    p.target = target; p.alpha = (0.075*0.075) / (2*2.5)
    p.frame = 0; p.earned = earned; p._data = data
    lastSec.current = (Math.floor((((-p.angle) % (Math.PI*2) + Math.PI*2) % (Math.PI*2)) / SLICE)) % N

    if (rafId.current) cancelAnimationFrame(rafId.current)
    rafId.current = requestAnimationFrame(loop)
  }, [spinning, watched])

  const remaining = Math.max(0, MAX_DAY - watched)

  const TIER = {
    50: { l: isRu?'🎰 ДЖЕКПОТ!!!':'🎰 JACKPOT!!!', c:'#FFD700' },
    30: { l: isRu?'🔥 MEGA WIN!':'🔥 MEGA WIN!',  c:'#FF3366' },
    15: { l: isRu?'⚡ БОЛЬШОЙ ДРО́П!':'⚡ BIG DROP!', c:'#33CC55' },
    7:  { l: isRu?'✨ НЕПЛОХО!':'✨ NICE!',         c:'#44CCEE' },
    5:  { l: '+5 ◆', c:'#7090FF' },
  }

  // ── JSX ───────────────────────────────────────────────────────
  return (
    <div style={{ maxWidth:480, margin:'0 auto', padding:'24px 20px' }}>

      <h2 style={{
        fontSize:28, fontWeight:900, margin:'0 0 5px',
        background:'linear-gradient(90deg,#FFD700 0%,#FF8800 50%,#FFD700 100%)',
        WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text',
        letterSpacing:'1px',
      }}>
        {isRu ? '🎰 Колесо Фортуны' : '🎰 Fortune Wheel'}
      </h2>
      <p style={{ color:'rgba(255,255,255,0.35)', fontSize:13, margin:'0 0 18px' }}>
        {isRu
          ? `Крути и выигрывай алмазы — до ${MAX_DAY} раз в день`
          : `Spin and win diamonds — up to ${MAX_DAY} times per day`}
      </p>

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

      <div style={{ marginBottom:20 }}>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
          <span style={{ color:'rgba(255,255,255,0.3)', fontSize:11, letterSpacing:'1px' }}>
            {isRu ? 'СЕГОДНЯ' : 'TODAY'}
          </span>
          <span style={{ color: watched>=MAX_DAY?'#FF4444':'#FFD700', fontSize:11, fontWeight:700 }}>
            {watched} / {MAX_DAY}
          </span>
        </div>
        <div style={{ height:4, background:'rgba(255,255,255,0.07)', borderRadius:2 }}>
          <div style={{
            height:'100%', borderRadius:2, width:`${(watched/MAX_DAY)*100}%`,
            background: watched>=MAX_DAY
              ? 'linear-gradient(90deg,#FF4444,#FF8800)'
              : 'linear-gradient(90deg,#FFD700,#FF8800)',
            boxShadow:'0 0 6px rgba(255,215,0,0.45)', transition:'width 0.4s',
          }}/>
        </div>
      </div>

      {/* Wheel — canvas at 2× DPR shown at SIZE×SIZE via CSS */}
      <div style={{
        position:'relative', width:SIZE, margin:'0 auto 20px',
        filter:'drop-shadow(0 8px 40px rgba(255,150,0,0.35))',
      }}>
        <canvas ref={cvRef} width={CS} height={CS}
          style={{ width:SIZE, height:SIZE, display:'block' }}/>
        <ParticleCanvas active={particles} color={partColor}/>
      </div>

      {result && !result.limit && (() => {
        const t = TIER[result.earned] || TIER[5]
        return (
          <div style={{
            border:`2px solid ${t.c}`, borderRadius:16, padding:'18px 20px',
            marginBottom:16, textAlign:'center',
            background:`${t.c}0e`,
            boxShadow:`0 0 44px ${t.c}44, inset 0 0 24px ${t.c}08`,
            animation:'popIn .42s cubic-bezier(.175,.885,.32,1.275)',
          }}>
            <style>{`@keyframes popIn{0%{transform:scale(.55);opacity:0}100%{transform:scale(1);opacity:1}}`}</style>
            <div style={{ color:t.c, fontWeight:900, fontSize:14, letterSpacing:'2px', marginBottom:5 }}>
              {t.l}
            </div>
            <div style={{ fontSize:70, fontWeight:900, lineHeight:1,
              color:t.c, filter:`drop-shadow(0 0 20px ${t.c})` }}>
              {result.earned}
            </div>
            <div style={{ color:t.c, fontSize:22, opacity:.8, marginTop:2 }}>◆</div>
          </div>
        )
      })()}

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

      {/* 3D golden spin button */}
      <button
        onPointerDown={() => setBtnDown(true)}
        onPointerUp={() => setBtnDown(false)}
        onPointerLeave={() => setBtnDown(false)}
        onClick={handleSpin}
        disabled={spinning || remaining === 0}
        style={{
          width:'100%', padding:'18px 0',
          background: remaining===0
            ? 'rgba(255,255,255,0.05)'
            : spinning ? 'rgba(255,215,0,0.08)'
            : btnDown ? 'linear-gradient(180deg,#BB7A00 0%,#996600 100%)'
            : 'linear-gradient(180deg,#FFE855 0%,#EAAD00 55%,#B88000 100%)',
          color: remaining===0?'rgba(255,255,255,0.2)':spinning?'#FFD700':'#160900',
          border: remaining===0?'1px solid rgba(255,255,255,0.08)'
            :spinning?'1px solid rgba(255,215,0,0.25)':'1px solid #A07000',
          borderBottom: (!spinning&&remaining>0&&!btnDown) ? '4px solid #7A5000' : undefined,
          borderRadius:14, fontSize:17, fontWeight:900, letterSpacing:'2px',
          cursor: remaining===0||spinning ? 'not-allowed':'pointer',
          transition:'all .1s',
          transform: btnDown ? 'translateY(3px) scale(.988)':'none',
          boxShadow: remaining>0&&!spinning
            ? btnDown ? '0 1px 10px rgba(255,170,0,.4)'
                       : '0 5px 0 #6A4200,0 0 34px rgba(255,160,0,.55)'
            : 'none',
          fontFamily:'inherit',
          animation: remaining>0&&!spinning&&!result ? 'pulseBtn 2.2s ease-in-out infinite':'none',
        }}
      >
        <style>{`@keyframes pulseBtn{0%,100%{box-shadow:0 5px 0 #6A4200,0 0 26px rgba(255,160,0,.5)}50%{box-shadow:0 5px 0 #6A4200,0 0 56px rgba(255,190,0,.85)}}`}</style>
        {remaining===0 ? (isRu?'✓ Лимит исчерпан':'✓ Limit reached')
          :spinning ? (isRu?'🎰  Крутится...':'🎰  Spinning...')
          :(isRu?`🎰  КРУТИТЬ  (осталось ${remaining})`:`🎰  SPIN  (${remaining} left)`)}
      </button>

      <div style={{ marginTop:28, borderTop:'1px solid rgba(255,255,255,0.06)', paddingTop:20 }}>
        <div style={{ color:'rgba(255,255,255,0.22)', fontSize:10, letterSpacing:'3px',
          textAlign:'center', marginBottom:12, textTransform:'uppercase' }}>
          {isRu ? 'Таблица призов' : 'Prize Table'}
        </div>
        {[[50,'1%',TIER[50].l],[30,'3%',TIER[30].l],[15,'6%',TIER[15].l],
          [7,'12%',TIER[7].l],[5,'78%',isRu?'Базовый приз':'Base prize']
        ].map(([v,pct,lbl]) => (
          <div key={v} style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'9px 14px', marginBottom:5, borderRadius:10,
            background:`${SC[v].g}0a`, border:`1px solid ${SC[v].g}20`,
          }}>
            <span style={{ color:SC[v].t, fontSize:13, fontWeight:700 }}>{lbl}</span>
            <div style={{ display:'flex', alignItems:'center', gap:10 }}>
              <span style={{ color:SC[v].t, fontSize:20, fontWeight:900,
                textShadow:`0 0 12px ${SC[v].g}` }}>{v}◆</span>
              <span style={{ color:'rgba(255,255,255,0.2)', fontSize:11 }}>{pct}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
