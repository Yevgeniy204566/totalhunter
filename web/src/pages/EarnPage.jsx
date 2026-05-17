import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'

// ═══════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════
const N       = 20
const SECTORS = [5, 7, 5, 15, 5, 30, 5, 7, 5, 15, 5, 7, 5, 15, 5, 50, 5, 7, 5, 30]
const SLICE   = (2 * Math.PI) / N
const MAX_DAY = 5

const DPR  = 2
const SIZE = 360
const CS   = SIZE * DPR      // 720 canvas pixels
const CCX  = CS / 2
const CCY  = CS / 2
const R_RIM  = 172 * DPR
const R_DISC = 151 * DPR
const R_HUB  = 22 * DPR

// Real photo texture URLs (Unsplash, CORS-open, free license)
const TEX_WOOD  = 'https://images.unsplash.com/photo-1546484396-fb3fc6f95f98?w=600&q=88'
const TEX_WALNUT= 'https://images.unsplash.com/photo-1736506159893-22cca29b8018?w=600&q=88'
const TEX_GOLD  = 'https://images.unsplash.com/photo-1545873509-33e944ca7655?w=512&q=88'

// Neon colours per prize value — VIVID, casino-bright
const SC = {
  5:  { d:'#08104A', m:'#1530A0', e:'#2C55EE', g:'#4466FF', t:'#99BBFF', p:'#4466FF' },
  7:  { d:'#002235', m:'#004480', e:'#0077CC', g:'#00AAEE', t:'#55DDFF', p:'#00AAEE' },
  15: { d:'#001F08', m:'#004A18', e:'#008844', g:'#00CC55', t:'#55EE99', p:'#00CC55' },
  30: { d:'#3A0015', m:'#780030', e:'#CC0055', g:'#EE2266', t:'#FF66AA', p:'#EE2266' },
  50: { d:'#1F1000', m:'#4A2800', e:'#8A5200', g:'#DDAA00', t:'#FFD700', p:'#DDAA00' },
}

// ═══════════════════════════════════════════════════════════════
//  TEXTURE LOADER — crossOrigin anonymous, graceful fallback
// ═══════════════════════════════════════════════════════════════
function loadImg(url) {
  return new Promise(resolve => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload  = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = url
  })
}

async function loadTextures() {
  const [wood, walnut, gold] = await Promise.all([
    loadImg(TEX_WOOD), loadImg(TEX_WALNUT), loadImg(TEX_GOLD),
  ])
  // Pick darkest/best wood available
  return { wood: walnut || wood, gold }
}

// ═══════════════════════════════════════════════════════════════
//  BASE LAYER — real mahogany wood rim + real gold foil accents
// ═══════════════════════════════════════════════════════════════
function buildBase(woodImg, goldImg) {
  const oc = document.createElement('canvas')
  oc.width = oc.height = CS
  const ctx = oc.getContext('2d')

  // Dark backdrop
  ctx.beginPath(); ctx.arc(CCX, CCY, R_RIM + 12, 0, Math.PI * 2)
  ctx.fillStyle = '#020408'; ctx.fill()

  // Outer glow ring (casino neon atmosphere)
  const og = ctx.createRadialGradient(CCX, CCY, R_RIM - 8, CCX, CCY, R_RIM + 12)
  og.addColorStop(0, 'rgba(255,160,0,0)'); og.addColorStop(1, 'rgba(255,100,0,0.25)')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_RIM + 12, 0, Math.PI * 2)
  ctx.fillStyle = og; ctx.fill()

  // ── REAL WOOD TEXTURE for the rim ring ───────────────────────
  if (woodImg) {
    const pat = ctx.createPattern(woodImg, 'repeat')
    // Scale texture so grain is visible at canvas resolution
    const scale = (CS / woodImg.width) * 0.75
    pat.setTransform(new DOMMatrix([scale, 0, 0, scale, 0, 0]))

    ctx.save()
    ctx.beginPath()
    ctx.arc(CCX, CCY, R_RIM, 0, Math.PI * 2)
    ctx.arc(CCX, CCY, R_DISC - 3, 0, Math.PI * 2, true)
    ctx.fillStyle = pat
    ctx.fill('evenodd')
    ctx.restore()

    // Light lacquer — let the wood grain show through
    const lac = ctx.createRadialGradient(
      CCX - R_RIM * 0.32, CCY - R_RIM * 0.28, 8,
      CCX, CCY, R_RIM
    )
    lac.addColorStop(0,    'rgba(80,30,5,0.10)')
    lac.addColorStop(0.38, 'rgba(20,8,2,0.28)')
    lac.addColorStop(0.72, 'rgba(5,2,0,0.38)')
    lac.addColorStop(1,    'rgba(0,0,0,0.50)')
    ctx.beginPath()
    ctx.arc(CCX, CCY, R_RIM, 0, Math.PI * 2)
    ctx.arc(CCX, CCY, R_DISC - 3, 0, Math.PI * 2, true)
    ctx.fillStyle = lac; ctx.fill('evenodd')

    // Specular sheen (light catching polished surface)
    const sh = ctx.createRadialGradient(
      CCX - R_RIM * 0.30, CCY - R_RIM * 0.34, 4,
      CCX, CCY, R_RIM * 0.85
    )
    sh.addColorStop(0,    'rgba(255,200,100,0.55)')
    sh.addColorStop(0.45, 'rgba(200,150,60,0.20)')
    sh.addColorStop(1,    'rgba(0,0,0,0)')
    ctx.beginPath()
    ctx.arc(CCX, CCY, R_RIM, 0, Math.PI * 2)
    ctx.arc(CCX, CCY, R_DISC - 3, 0, Math.PI * 2, true)
    ctx.fillStyle = sh; ctx.fill('evenodd')
  } else {
    // Fallback: rich polished mahogany gradient (visible even without texture)
    const rg = ctx.createRadialGradient(CCX - R_RIM*0.34, CCY - R_RIM*0.28, 6, CCX, CCY, R_RIM)
    rg.addColorStop(0,    '#F0C060')  // bright warm highlight
    rg.addColorStop(0.18, '#D09030')  // polished gold
    rg.addColorStop(0.40, '#8A5A14')  // medium mahogany
    rg.addColorStop(0.62, '#5C3208')  // deep brown
    rg.addColorStop(0.80, '#7A4A10')  // edge catch light
    rg.addColorStop(1,    '#201006')  // dark edge
    ctx.beginPath()
    ctx.arc(CCX, CCY, R_RIM, 0, Math.PI * 2)
    ctx.arc(CCX, CCY, R_DISC - 3, 0, Math.PI * 2, true)
    ctx.fillStyle = rg; ctx.fill('evenodd')
  }

  // ── REAL GOLD FOIL TEXTURE for inner ring band ───────────────
  if (goldImg) {
    const gp = ctx.createPattern(goldImg, 'repeat')
    const gs = (CS / goldImg.width) * 0.30
    gp.setTransform(new DOMMatrix([gs, 0, 0, gs, 0, 0]))

    ctx.beginPath()
    ctx.arc(CCX, CCY, R_DISC + 6 * DPR, 0, Math.PI * 2)
    ctx.arc(CCX, CCY, R_DISC - 6 * DPR, 0, Math.PI * 2, true)
    ctx.fillStyle = gp; ctx.fill('evenodd')

    // Gold colour boost
    ctx.beginPath()
    ctx.arc(CCX, CCY, R_DISC + 6 * DPR, 0, Math.PI * 2)
    ctx.arc(CCX, CCY, R_DISC - 6 * DPR, 0, Math.PI * 2, true)
    ctx.fillStyle = 'rgba(255,200,0,0.28)'; ctx.fill('evenodd')
  }

  // Inner ring glow
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC + 4 * DPR, 0, Math.PI * 2)
  ctx.strokeStyle = '#FFD700'; ctx.lineWidth = 3 * DPR
  ctx.shadowBlur = 20 * DPR; ctx.shadowColor = 'rgba(255,215,0,0.7)'; ctx.stroke()
  ctx.shadowBlur = 0

  // Outer rim border
  ctx.beginPath(); ctx.arc(CCX, CCY, R_RIM - 1, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(255,195,40,0.55)'; ctx.lineWidth = 2 * DPR
  ctx.shadowBlur = 10 * DPR; ctx.shadowColor = '#FFD700'; ctx.stroke()
  ctx.shadowBlur = 0

  // ── STUDS with real gold texture ─────────────────────────────
  const nS = 40, sRad = R_RIM - 22 * DPR
  for (let i = 0; i < nS; i++) {
    const a = (i / nS) * Math.PI * 2
    const sx = CCX + Math.cos(a) * sRad, sy = CCY + Math.sin(a) * sRad
    const big = i % 5 === 0, r = big ? 5.5 * DPR : 3.5 * DPR

    ctx.save()
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.clip()

    if (goldImg) {
      const gp2 = ctx.createPattern(goldImg, 'repeat')
      const gs2 = 0.10
      gp2.setTransform(new DOMMatrix([gs2, 0, 0, gs2, -sx * gs2, -sy * gs2]))
      ctx.fillStyle = gp2; ctx.fillRect(sx - r, sy - r, r * 2, r * 2)
      // Highlight
      const hl = ctx.createRadialGradient(sx - r * 0.35, sy - r * 0.35, 0, sx, sy, r)
      hl.addColorStop(0, 'rgba(255,255,200,0.45)'); hl.addColorStop(1, 'rgba(0,0,0,0.40)')
      ctx.fillStyle = hl; ctx.fillRect(sx - r, sy - r, r * 2, r * 2)
    } else {
      const sg = ctx.createRadialGradient(sx - r*0.38, sy - r*0.38, 0, sx, sy, r)
      sg.addColorStop(0, '#FFFAE0'); sg.addColorStop(0.45, '#CC9900'); sg.addColorStop(1, '#3A2500')
      ctx.fillStyle = sg; ctx.fillRect(sx - r, sy - r, r * 2, r * 2)
    }
    ctx.restore()

    if (big) {
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(0,0,0,0.35)'; ctx.lineWidth = 0.5 * DPR; ctx.stroke()
    }
  }

  // Inner depth shadow at disc boundary
  const ds = ctx.createRadialGradient(CCX, CCY, R_DISC - 14*DPR, CCX, CCY, R_DISC + 8*DPR)
  ds.addColorStop(0, 'rgba(0,0,0,0)'); ds.addColorStop(1, 'rgba(0,0,0,0.65)')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC + 8*DPR, 0, Math.PI * 2)
  ctx.fillStyle = ds; ctx.fill()

  return oc
}

// ═══════════════════════════════════════════════════════════════
//  DISC LAYER — neon sectors, 2× resolution, correct text
// ═══════════════════════════════════════════════════════════════
function buildDisc() {
  const oc = document.createElement('canvas')
  oc.width = oc.height = CS
  const ctx = oc.getContext('2d')

  for (let i = 0; i < N; i++) {
    const v = SECTORS[i], c = SC[v]
    const sA = -Math.PI / 2 + i * SLICE
    const eA = sA + SLICE, mA = sA + SLICE / 2

    // 3D pocket gradient: very dark at inner + outer edges, vivid in middle
    const irx = CCX + Math.cos(mA) * R_DISC * 0.06
    const iry = CCY + Math.sin(mA) * R_DISC * 0.06
    const orx = CCX + Math.cos(mA) * R_DISC * 0.97
    const ory = CCY + Math.sin(mA) * R_DISC * 0.97
    const gr = ctx.createLinearGradient(irx, iry, orx, ory)
    gr.addColorStop(0,    c.d)
    gr.addColorStop(0.15, c.d)
    gr.addColorStop(0.42, c.m)
    gr.addColorStop(0.70, c.e)
    gr.addColorStop(1,    c.d)
    ctx.beginPath(); ctx.moveTo(CCX, CCY)
    ctx.arc(CCX, CCY, R_DISC, sA, eA); ctx.closePath()
    ctx.fillStyle = gr; ctx.fill()

    // LED neon strip at outer rim of each sector — INTENSE
    ctx.save()
    ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC * 0.88, sA + 0.022, eA - 0.022)
    ctx.strokeStyle = c.g; ctx.lineWidth = R_DISC * 0.11
    ctx.shadowBlur = 44 * DPR; ctx.shadowColor = c.g; ctx.globalAlpha = 0.85
    ctx.stroke(); ctx.restore()
    // Second, tighter inner glow ring
    ctx.save()
    ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC * 0.82, sA + 0.03, eA - 0.03)
    ctx.strokeStyle = c.t; ctx.lineWidth = R_DISC * 0.04
    ctx.shadowBlur = 20 * DPR; ctx.shadowColor = c.g; ctx.globalAlpha = 0.50
    ctx.stroke(); ctx.restore()

    // Text — flip bottom half to prevent upside-down rendering
    const tr = R_DISC * 0.61
    const tx = CCX + Math.cos(mA) * tr, ty = CCY + Math.sin(mA) * tr
    ctx.save(); ctx.translate(tx, ty)
    let rot = mA + Math.PI / 2
    const nm = ((mA % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2)
    if (nm >= Math.PI / 2 && nm <= 3 * Math.PI / 2) rot += Math.PI
    ctx.rotate(rot)
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'

    const fs = R_DISC * (v === 50 ? 0.172 : v >= 15 ? 0.152 : 0.130)
    ctx.font = `900 ${fs | 0}px 'Arial Black', Arial, sans-serif`
    ctx.fillStyle = '#ffffff'
    ctx.shadowBlur = 22 * DPR; ctx.shadowColor = c.g
    ctx.fillText(String(v), 0, -(fs * 0.30))

    ctx.font = `700 ${(fs * 0.56) | 0}px Arial, sans-serif`
    ctx.fillStyle = c.t; ctx.shadowBlur = 16 * DPR
    ctx.fillText('◆', 0, fs * 0.66)
    ctx.restore()
  }

  // Gold metallic divider lines between sectors
  for (let i = 0; i < N; i++) {
    const a = -Math.PI / 2 + i * SLICE
    const x1 = CCX + Math.cos(a) * R_DISC * 0.12
    const y1 = CCY + Math.sin(a) * R_DISC * 0.12
    const x2 = CCX + Math.cos(a) * R_DISC * 0.99
    const y2 = CCY + Math.sin(a) * R_DISC * 0.99
    const dl = ctx.createLinearGradient(x1, y1, x2, y2)
    dl.addColorStop(0,    'rgba(255,215,0,0.0)')
    dl.addColorStop(0.28, 'rgba(255,215,0,0.65)')
    dl.addColorStop(0.78, 'rgba(255,215,0,0.55)')
    dl.addColorStop(1,    'rgba(255,215,0,0.18)')
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2)
    ctx.strokeStyle = dl; ctx.lineWidth = 1.5 * DPR
    ctx.shadowBlur = 5 * DPR; ctx.shadowColor = '#FFD700'; ctx.stroke()
  }
  ctx.shadowBlur = 0

  // Outer disc border ring
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(255,215,0,0.72)'; ctx.lineWidth = 2 * DPR
  ctx.shadowBlur = 14 * DPR; ctx.shadowColor = '#FFD700'; ctx.stroke()
  ctx.shadowBlur = 0

  // Chrome centre hub
  const hg = ctx.createRadialGradient(
    CCX - R_HUB * 0.38, CCY - R_HUB * 0.38, 1, CCX, CCY, R_HUB)
  hg.addColorStop(0, '#CCCCEE'); hg.addColorStop(0.38, '#2535A0')
  hg.addColorStop(0.72, '#0E1530'); hg.addColorStop(1, '#040810')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_HUB, 0, Math.PI * 2)
  ctx.fillStyle = hg; ctx.fill()
  ctx.strokeStyle = 'rgba(255,215,0,0.7)'; ctx.lineWidth = 2 * DPR
  ctx.shadowBlur = 12 * DPR; ctx.shadowColor = '#FFD700'; ctx.stroke()
  ctx.shadowBlur = 0
  return oc
}

// ═══════════════════════════════════════════════════════════════
//  GLASS LAYER — PBR specular overlay (static, wheel spins under it)
// ═══════════════════════════════════════════════════════════════
function buildGlass() {
  const oc = document.createElement('canvas')
  oc.width = oc.height = CS
  const ctx = oc.getContext('2d')

  // Primary specular highlight (upper-left light source)
  const g1 = ctx.createRadialGradient(
    CCX - 110 * DPR, CCY - 130 * DPR, 8 * DPR, CCX, CCY, R_DISC)
  g1.addColorStop(0,    'rgba(255,255,255,0.19)')
  g1.addColorStop(0.38, 'rgba(255,255,255,0.07)')
  g1.addColorStop(0.72, 'rgba(255,255,255,0.02)')
  g1.addColorStop(1,    'rgba(255,255,255,0.00)')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC, 0, Math.PI * 2)
  ctx.fillStyle = g1; ctx.fill()

  // Glint streak (lens flare effect)
  ctx.save(); ctx.globalAlpha = 0.065
  ctx.beginPath()
  ctx.ellipse(CCX - 54*DPR, CCY - 104*DPR, 98*DPR, 20*DPR, -0.44, 0, Math.PI * 2)
  ctx.fillStyle = '#ffffff'; ctx.fill()
  ctx.restore()

  // Bottom vignette
  const vg = ctx.createRadialGradient(CCX, CCY + R_DISC * 0.5, R_DISC*0.2, CCX, CCY, R_DISC)
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.28)')
  ctx.beginPath(); ctx.arc(CCX, CCY, R_DISC, 0, Math.PI * 2)
  ctx.fillStyle = vg; ctx.fill()
  return oc
}

// ═══════════════════════════════════════════════════════════════
//  POINTER — 3D chrome-gold arrow with spring physics
// ═══════════════════════════════════════════════════════════════
function drawPointer(ctx, deflection) {
  const px = CCX, py = CCY - R_RIM + 7 * DPR
  ctx.save()
  ctx.translate(px, py + 14*DPR); ctx.rotate(deflection); ctx.translate(-px, -(py + 14*DPR))

  // Drop shadow
  ctx.shadowBlur = 9 * DPR; ctx.shadowColor = 'rgba(0,0,0,0.65)'
  ctx.beginPath()
  ctx.moveTo(px - 14*DPR, py + 6*DPR); ctx.lineTo(px + 14*DPR, py + 6*DPR)
  ctx.lineTo(px, py - 22*DPR); ctx.closePath()
  ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.fill()
  ctx.shadowBlur = 0

  // Chrome-gold body gradient
  const pg = ctx.createLinearGradient(px - 14*DPR, py, px + 14*DPR, py)
  pg.addColorStop(0,    '#6A4000')
  pg.addColorStop(0.16, '#CC8800')
  pg.addColorStop(0.50, '#FFE860')
  pg.addColorStop(0.84, '#CC8800')
  pg.addColorStop(1,    '#6A4000')
  ctx.beginPath()
  ctx.moveTo(px - 13*DPR, py + 5*DPR); ctx.lineTo(px + 13*DPR, py + 5*DPR)
  ctx.lineTo(px, py - 21*DPR); ctx.closePath()
  ctx.fillStyle = pg
  ctx.shadowBlur = 24 * DPR; ctx.shadowColor = '#FFD700'; ctx.fill()
  ctx.shadowBlur = 0

  // Edge highlight
  ctx.beginPath()
  ctx.moveTo(px - 13*DPR, py + 5*DPR); ctx.lineTo(px + 13*DPR, py + 5*DPR)
  ctx.lineTo(px, py - 21*DPR); ctx.closePath()
  ctx.strokeStyle = 'rgba(255,255,220,0.38)'; ctx.lineWidth = 1.5 * DPR; ctx.stroke()
  ctx.restore()
}

// ═══════════════════════════════════════════════════════════════
//  RATCHET SOUND — noise burst (sampled mechanical click)
// ═══════════════════════════════════════════════════════════════
function playRatchet(actx, pitch = 1.0) {
  try {
    const sr = actx.sampleRate, len = (sr * 0.054) | 0
    const buf = actx.createBuffer(1, len, sr), d = buf.getChannelData(0)
    for (let i = 0; i < len; i++) {
      const t = i / len
      d[i] = ((Math.random()*2-1)*Math.exp(-t*30)
              + Math.sin(Math.PI*2*2200*pitch*t)*Math.exp(-t*75)*0.5) * 0.42
    }
    const src = actx.createBufferSource(); src.buffer = buf
    const bpf = actx.createBiquadFilter()
    bpf.type = 'bandpass'; bpf.frequency.value = 3500 * pitch; bpf.Q.value = 0.45
    const g = actx.createGain(); g.gain.value = 0.28
    src.connect(bpf); bpf.connect(g); g.connect(actx.destination)
    src.start(actx.currentTime)
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════════════
//  PARTICLES
// ═══════════════════════════════════════════════════════════════
function ParticleCanvas({ active, color }) {
  const cvRef = useRef(null), rafRef = useRef(null)
  useEffect(() => {
    if (!active || !cvRef.current) return
    const cv = cvRef.current, ctx = cv.getContext('2d')
    const pts = Array.from({ length: 115 }, () => ({
      x: SIZE/2+(Math.random()-.5)*40, y: SIZE/2+(Math.random()-.5)*40,
      vx: (Math.random()-.5)*16, vy: -Math.random()*20-2,
      r: Math.random()*5+1.5, life: 1, decay: Math.random()*0.012+0.007,
      hue: [color,'#FFD700','#fff',color][Math.floor(Math.random()*4)],
    }))
    const tick = () => {
      ctx.clearRect(0,0,SIZE,SIZE); let alive = false
      pts.forEach(p => {
        if (p.life<=0) return; alive=true
        p.x+=p.vx; p.y+=p.vy; p.vy+=0.42; p.vx*=0.984; p.life-=p.decay
        ctx.globalAlpha=Math.max(0,p.life); ctx.fillStyle=p.hue
        ctx.beginPath(); ctx.arc(p.x,p.y,p.r*p.life,0,Math.PI*2); ctx.fill()
      })
      ctx.globalAlpha=1
      if (alive) rafRef.current=requestAnimationFrame(tick)
    }
    rafRef.current=requestAnimationFrame(tick)
    return ()=>{ if(rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [active, color])
  return <canvas ref={cvRef} width={SIZE} height={SIZE}
    style={{position:'absolute',top:0,left:0,pointerEvents:'none',opacity:active?1:0}}/>
}

// ═══════════════════════════════════════════════════════════════
//  MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════
export default function EarnPage() {
  const { lang } = useLang(); const isRu = lang === 'ru'

  const [watched,   setWatched]   = useState(0)
  const [credits,   setCredits]   = useState(null)
  const [spinning,  setSpinning]  = useState(false)
  const [result,    setResult]    = useState(null)
  const [particles, setParticles] = useState(false)
  const [partColor, setPartColor] = useState('#FFD700')
  const [btnDown,   setBtnDown]   = useState(false)
  const [loading,   setLoading]   = useState(true)

  const cvRef    = useRef(null)
  const baseOff  = useRef(null)
  const discOff  = useRef(null)
  const glassOff = useRef(null)
  const audioRef = useRef(null)
  const rafId    = useRef(null)
  const phys     = useRef({ angle:0, omega:0, phase:'idle',
    target:0, alpha:0, earned:0, frame:0, _data:null })
  const ptr      = useRef({ a:0, v:0 })
  const lastSec  = useRef(-1)

  // ── Load real photo textures, then render ──────────────────
  useEffect(() => {
    let cancelled = false
    async function init() {
      const { wood, gold } = await loadTextures()
      if (cancelled) return
      baseOff.current  = buildBase(wood, gold)
      discOff.current  = buildDisc()
      glassOff.current = buildGlass()
      setLoading(false)
      // Let React re-render, then draw
      setTimeout(renderFrame, 0)
    }
    init()
    return () => { cancelled = true }
  }, [])

  // Re-draw after loading=false
  useEffect(() => {
    if (!loading) renderFrame()
  }, [loading])

  useEffect(() => {
    api.me().then(u=>setCredits(u.credits)).catch(()=>{})
    api.earnStatus().then(d=>setWatched(d.today??0)).catch(()=>{})
  }, [])

  function getAudio() {
    if (!audioRef.current)
      try { audioRef.current = new (window.AudioContext||window.webkitAudioContext)() } catch(e){}
    return audioRef.current
  }

  function renderFrame() {
    const cv = cvRef.current; if (!cv) return
    const ctx = cv.getContext('2d')
    ctx.clearRect(0, 0, CS, CS)

    // Layer 1: real wood rim + gold foil accents
    if (baseOff.current) ctx.drawImage(baseOff.current, 0, 0)

    // Layer 2: rotating neon disc (motion blur at high speed)
    if (discOff.current) {
      const blur = Math.min(Math.abs(phys.current.omega) * 1500, 13)
      if (blur > 0.5) ctx.filter = `blur(${blur.toFixed(1)}px)`
      ctx.save()
      ctx.translate(CCX, CCY); ctx.rotate(phys.current.angle)
      ctx.drawImage(discOff.current, -R_DISC, -R_DISC, R_DISC*2, R_DISC*2)
      ctx.restore()
      if (blur > 0.5) ctx.filter = 'none'
    }

    // Layer 3: glass specular
    if (glassOff.current) ctx.drawImage(glassOff.current, 0, 0)

    // Layer 4: animated pointer
    drawPointer(ctx, ptr.current.a)
  }

  function loop() {
    const p = phys.current, pt = ptr.current
    p.frame++

    // Pointer spring physics
    pt.v += (-96 * pt.a) * 0.016
    pt.v *= 0.73; pt.a += pt.v * 0.016
    pt.a = Math.max(-0.52, Math.min(0.52, pt.a))

    // Ratchet trigger on sector crossing
    const modA   = ((p.angle%(Math.PI*2))+Math.PI*2)%(Math.PI*2)
    const curSec = Math.floor(modA/SLICE)%N
    if (curSec !== lastSec.current) {
      const ac = getAudio()
      if (ac) playRatchet(ac, Math.min(0.55+Math.abs(p.omega)*1000, 2.4))
      pt.v += 0.30; lastSec.current = curSec
    }

    const PEAK=0.075, ACCEL=0.003

    if (p.phase==='accel') {
      p.omega = Math.min(p.omega+ACCEL, PEAK); p.angle+=p.omega
      if (p.omega>=PEAK) { p.phase='coast'; p.frame=0 }
    }
    else if (p.phase==='coast') {
      p.angle+=PEAK
      const rem=(( p.target-p.angle)%(Math.PI*2)+Math.PI*2)%(Math.PI*2)
      const dd=(PEAK*PEAK)/(2*p.alpha)
      if (rem<=dd+0.08) { p.phase='decel'; p.omega=PEAK; p.frame=0 }
    }
    else if (p.phase==='decel') {
      p.omega=Math.max(0,p.omega-p.alpha); p.angle+=p.omega
      if (p.omega<0.0008) {
        p.angle=p.target; p.omega=-0.0045; p.phase='settle'; p.frame=0
      }
    }
    else if (p.phase==='settle') {
      const diff=p.target-p.angle
      p.omega=p.omega*0.76+diff*0.07; p.angle+=p.omega
      if (p.frame>28||Math.abs(diff)<0.0003) {
        p.angle=p.target; p.omega=0; p.phase='idle'
        const ac=getAudio(); if(ac) playRatchet(ac, 1.9)
        const data=p._data
        setWatched(w=>w+1); setCredits(data.credits)
        setResult({ earned:p.earned, jackpot:data.jackpot }); setSpinning(false)
        if (p.earned>=30) { setPartColor(SC[p.earned]?.p||'#FFD700'); setParticles(true) }
        renderFrame(); return
      }
    }

    renderFrame(); rafId.current=requestAnimationFrame(loop)
  }

  const handleSpin = useCallback(async () => {
    if (spinning||Math.max(0,MAX_DAY-watched)===0||loading) return
    setSpinning(true); setResult(null); setParticles(false)

    try { const ac=getAudio(); if(ac?.state==='suspended') await ac.resume() } catch(e){}

    let data
    try { data=await api.earnReward() } catch(e) { setSpinning(false); return }
    if (!data.success) { setSpinning(false); setResult({limit:true}); return }

    const { earned, sector_index }=data, p=phys.current
    const sCenter=-Math.PI/2+sector_index*SLICE+SLICE/2
    const rawTarget=-sCenter
    let norm=((rawTarget-p.angle)%(Math.PI*2)+Math.PI*2)%(Math.PI*2)
    if (norm===0) norm=Math.PI*2
    p.omega=0; p.phase='accel'
    p.target=p.angle+4*Math.PI*2+norm
    p.alpha=(0.075*0.075)/(2*2.5)
    p.frame=0; p.earned=earned; p._data=data
    lastSec.current=Math.floor((((-p.angle)%(Math.PI*2)+Math.PI*2)%(Math.PI*2))/SLICE)%N
    if (rafId.current) cancelAnimationFrame(rafId.current)
    rafId.current=requestAnimationFrame(loop)
  }, [spinning, watched, loading])

  const remaining=Math.max(0,MAX_DAY-watched)
  const TIER={
    50:{l:isRu?'🎰 ДЖЕКПОТ!!!':'🎰 JACKPOT!!!',c:'#FFD700'},
    30:{l:isRu?'🔥 MEGA WIN!':'🔥 MEGA WIN!',c:'#FF3366'},
    15:{l:isRu?'⚡ БОЛЬШОЙ ДРО́П!':'⚡ BIG DROP!',c:'#33CC55'},
    7: {l:isRu?'✨ НЕПЛОХО!':'✨ NICE!',c:'#44CCEE'},
    5: {l:'+5 ◆',c:'#7090FF'},
  }

  return (
    <div style={{maxWidth:480,margin:'0 auto',padding:'24px 20px'}}>

      <h2 style={{
        fontSize:28,fontWeight:900,margin:'0 0 5px',
        background:'linear-gradient(90deg,#FFD700 0%,#FF8800 50%,#FFD700 100%)',
        WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',backgroundClip:'text',
        letterSpacing:'1px',
      }}>
        {isRu ? '🎰 Колесо Фортуны' : '🎰 Fortune Wheel'}
      </h2>
      <p style={{color:'rgba(255,255,255,0.35)',fontSize:13,margin:'0 0 18px'}}>
        {isRu?`Крути и выигрывай алмазы — до ${MAX_DAY} раз в день`
              :`Spin and win diamonds — up to ${MAX_DAY} times per day`}
      </p>

      {credits!==null&&(
        <div style={{
          background:'rgba(255,215,0,0.05)',border:'1px solid rgba(255,215,0,0.18)',
          borderRadius:12,padding:'12px 18px',marginBottom:18,
          display:'flex',alignItems:'center',justifyContent:'space-between',
        }}>
          <span style={{color:'rgba(255,255,255,0.4)',fontSize:12}}>
            {isRu?'Баланс':'Balance'}
          </span>
          <span style={{color:'#FFD700',fontSize:22,fontWeight:900,
            textShadow:'0 0 14px rgba(255,215,0,0.5)'}}>
            {credits.toLocaleString()} ◆
          </span>
        </div>
      )}

      <div style={{marginBottom:20}}>
        <div style={{display:'flex',justifyContent:'space-between',marginBottom:6}}>
          <span style={{color:'rgba(255,255,255,0.3)',fontSize:11,letterSpacing:'1px'}}>
            {isRu?'СЕГОДНЯ':'TODAY'}
          </span>
          <span style={{color:watched>=MAX_DAY?'#FF4444':'#FFD700',fontSize:11,fontWeight:700}}>
            {watched} / {MAX_DAY}
          </span>
        </div>
        <div style={{height:4,background:'rgba(255,255,255,0.07)',borderRadius:2}}>
          <div style={{
            height:'100%',borderRadius:2,width:`${(watched/MAX_DAY)*100}%`,
            background:watched>=MAX_DAY?'linear-gradient(90deg,#FF4444,#FF8800)'
              :'linear-gradient(90deg,#FFD700,#FF8800)',
            boxShadow:'0 0 6px rgba(255,215,0,0.45)',transition:'width 0.4s',
          }}/>
        </div>
      </div>

      {/* Wheel — 2× DPR canvas shown at SIZE×SIZE */}
      <div style={{
        position:'relative',width:SIZE,margin:'0 auto 20px',
        filter:'drop-shadow(0 8px 44px rgba(255,140,0,0.38))',
      }}>
        {loading && (
          <div style={{
            position:'absolute',inset:0,display:'flex',alignItems:'center',
            justifyContent:'center',color:'rgba(255,215,0,0.7)',fontSize:13,
            borderRadius:'50%',background:'rgba(5,8,18,0.9)',
          }}>
            {isRu?'Загружаю текстуры...':'Loading textures...'}
          </div>
        )}
        <canvas ref={cvRef} width={CS} height={CS}
          style={{width:SIZE,height:SIZE,display:'block'}}/>
        <ParticleCanvas active={particles} color={partColor}/>
      </div>

      {result&&!result.limit&&(()=>{
        const t=TIER[result.earned]||TIER[5]
        return (
          <div style={{
            border:`2px solid ${t.c}`,borderRadius:16,padding:'18px 20px',
            marginBottom:16,textAlign:'center',background:`${t.c}0e`,
            boxShadow:`0 0 44px ${t.c}44,inset 0 0 24px ${t.c}08`,
            animation:'popIn .42s cubic-bezier(.175,.885,.32,1.275)',
          }}>
            <style>{`@keyframes popIn{0%{transform:scale(.55);opacity:0}100%{transform:scale(1);opacity:1}}`}</style>
            <div style={{color:t.c,fontWeight:900,fontSize:14,letterSpacing:'2px',marginBottom:5}}>
              {t.l}
            </div>
            <div style={{fontSize:70,fontWeight:900,lineHeight:1,
              color:t.c,filter:`drop-shadow(0 0 20px ${t.c})`}}>
              {result.earned}
            </div>
            <div style={{color:t.c,fontSize:22,opacity:.8,marginTop:2}}>◆</div>
          </div>
        )
      })()}

      {(result?.limit||remaining===0)&&(
        <div style={{
          background:'rgba(255,80,0,0.07)',border:'1px solid rgba(255,80,0,0.25)',
          borderRadius:10,padding:'12px 16px',marginBottom:16,
          color:'#FF8844',fontSize:13,textAlign:'center',
        }}>
          {isRu?'🌙 Лимит исчерпан. Возвращайся завтра!':'🌙 Daily limit reached. Come back tomorrow!'}
        </div>
      )}

      <button
        onPointerDown={()=>setBtnDown(true)}
        onPointerUp={()=>setBtnDown(false)}
        onPointerLeave={()=>setBtnDown(false)}
        onClick={handleSpin}
        disabled={spinning||remaining===0||loading}
        style={{
          width:'100%',padding:'18px 0',
          background:remaining===0||loading?'rgba(255,255,255,0.05)'
            :spinning?'rgba(255,215,0,0.08)'
            :btnDown?'linear-gradient(180deg,#BB7A00 0%,#996600 100%)'
            :'linear-gradient(180deg,#FFE855 0%,#EAAD00 55%,#B88000 100%)',
          color:remaining===0||loading?'rgba(255,255,255,0.2)':spinning?'#FFD700':'#160900',
          border:remaining===0||loading?'1px solid rgba(255,255,255,0.08)'
            :spinning?'1px solid rgba(255,215,0,0.25)':'1px solid #A07000',
          borderBottom:(!spinning&&remaining>0&&!btnDown&&!loading)?'4px solid #7A5000':undefined,
          borderRadius:14,fontSize:17,fontWeight:900,letterSpacing:'2px',
          cursor:remaining===0||spinning||loading?'not-allowed':'pointer',
          transition:'all .1s',
          transform:btnDown?'translateY(3px) scale(.988)':'none',
          boxShadow:remaining>0&&!spinning&&!loading
            ?btnDown?'0 1px 10px rgba(255,170,0,.4)'
                    :'0 5px 0 #6A4200,0 0 34px rgba(255,160,0,.55)':'none',
          fontFamily:'inherit',
          animation:remaining>0&&!spinning&&!result&&!loading?'pulseBtn 2.2s ease-in-out infinite':'none',
        }}
      >
        <style>{`@keyframes pulseBtn{0%,100%{box-shadow:0 5px 0 #6A4200,0 0 26px rgba(255,160,0,.5)}50%{box-shadow:0 5px 0 #6A4200,0 0 56px rgba(255,190,0,.85)}}`}</style>
        {loading?(isRu?'⏳ Загрузка...':'⏳ Loading...')
          :remaining===0?(isRu?'✓ Лимит исчерпан':'✓ Limit reached')
          :spinning?(isRu?'🎰  Крутится...':'🎰  Spinning...')
          :(isRu?`🎰  КРУТИТЬ  (осталось ${remaining})`:`🎰  SPIN  (${remaining} left)`)}
      </button>

      <div style={{marginTop:28,borderTop:'1px solid rgba(255,255,255,0.06)',paddingTop:20}}>
        <div style={{color:'rgba(255,255,255,0.22)',fontSize:10,letterSpacing:'3px',
          textAlign:'center',marginBottom:12,textTransform:'uppercase'}}>
          {isRu?'Таблица призов':'Prize Table'}
        </div>
        {[[50,'1%',TIER[50].l],[30,'3%',TIER[30].l],[15,'6%',TIER[15].l],
          [7,'12%',TIER[7].l],[5,'78%',isRu?'Базовый приз':'Base prize']
        ].map(([v,pct,lbl])=>(
          <div key={v} style={{
            display:'flex',alignItems:'center',justifyContent:'space-between',
            padding:'9px 14px',marginBottom:5,borderRadius:10,
            background:`${SC[v].g}0a`,border:`1px solid ${SC[v].g}20`,
          }}>
            <span style={{color:SC[v].t,fontSize:13,fontWeight:700}}>{lbl}</span>
            <div style={{display:'flex',alignItems:'center',gap:10}}>
              <span style={{color:SC[v].t,fontSize:20,fontWeight:900,
                textShadow:`0 0 12px ${SC[v].g}`}}>{v}◆</span>
              <span style={{color:'rgba(255,255,255,0.2)',fontSize:11}}>{pct}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
