import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useLang } from '../lang.js'

const MAX_DAY = 5

// ─── Adapted CSS from design bundle (scoped to #earn-page-root) ───────────────
const WHEEL_CSS = `
:root {
  --gold-1: #b78a32; --gold-2: #e9c66a; --gold-3: #fff4c2;
  --ink: #f4e9d2; --ink-dim: #b6a585;
}
#earn-page-root {
  position: fixed; inset: 0; z-index: 9999;
  overflow: hidden;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--ink); font-family: 'Manrope', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased; user-select: none;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 240' preserveAspectRatio='none'><filter id='v'><feTurbulence type='fractalNoise' baseFrequency='1.4' numOctaves='2' seed='4' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.06  0 0 0 0 0.04  0 0 0 0 0.18  0.55 0 0 0 -0.2'/></filter><rect width='100%25' height='100%25' filter='url(%23v)'/></svg>"),
    radial-gradient(ellipse 65% 60% at 50% 38%, #1a1444 0%, #0c0830 35%, #050218 75%, #02010c 100%);
}
#earn-page-root::before {
  content: ''; position: fixed; inset: 0;
  background: radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.72) 100%);
  pointer-events: none; z-index: 100;
}
#earn-page-root .topbar {
  position: relative; z-index: 10;
  display: flex; justify-content: center; align-items: center;
  margin-top: 14px; margin-bottom: 10px;
}
#earn-page-root .brand {
  font-family: 'Cormorant SC', 'Cinzel', serif; font-weight: 700;
  font-size: 42px; letter-spacing: 0.10em;
  background: linear-gradient(180deg, #fffce6 0%, #ffe833 30%, #ffd31a 60%, #c98e10 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  filter:
    drop-shadow(0 2px 0 rgba(20,8,2,0.85))
    drop-shadow(0 0 6px rgba(255,230,80,0.25))
    drop-shadow(0 0 14px rgba(120,200,255,0.95))
    drop-shadow(0 0 30px rgba(80,170,255,0.75))
    drop-shadow(0 4px 6px rgba(0,0,0,0.65));
}
#earn-page-root .stage {
  position: relative; width: 640px; height: 640px;
  display: flex; align-items: center; justify-content: center;
}
#earn-page-root .neon-ring {
  position: absolute; inset: -8px; border-radius: 50%;
  background: conic-gradient(
    from 0deg, transparent 0deg,
    rgba(20,90,255,0.85) 30deg, rgba(60,160,255,1) 50deg,
    rgba(20,90,255,0.85) 70deg, transparent 110deg, transparent 180deg,
    rgba(20,90,255,0.5) 210deg, rgba(60,160,255,0.9) 230deg,
    rgba(20,90,255,0.5) 250deg, transparent 290deg, transparent 360deg);
  filter: blur(14px); z-index: 0; pointer-events: none;
  animation: neon-rotate 4s linear infinite; mix-blend-mode: screen; opacity: 0.95;
}
#earn-page-root .neon-ring::after {
  content: ''; position: absolute; inset: 14px; border-radius: 50%; background: #060309;
}
@keyframes neon-rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
#earn-page-root .stage.spinning .neon-ring { animation-duration: 1.4s; }
#earn-page-root .rivets { position: absolute; inset: 0; pointer-events: none; z-index: 3; }
#earn-page-root .rivet {
  position: absolute; width: 32px; height: 32px; border-radius: 50%;
  overflow: hidden; transform: translate(-50%, -50%);
  background: radial-gradient(circle at 35% 30%,
    #fff8d4 0%, #f5d978 14%, #c89020 36%, #8a5c0a 62%, #4a2e04 85%, #1a0c02 100%);
  box-shadow: inset 0 2px 4px rgba(255,240,160,0.5), inset 0 -2px 3px rgba(0,0,0,0.6),
    0 3px 6px rgba(0,0,0,0.8), 0 1px 0 rgba(255,200,100,0.2);
}
#earn-page-root .rivet-spark {
  position: absolute; inset: 15%; border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(255,255,235,1) 0%, rgba(255,235,140,1) 18%, rgba(255,200,60,0.95) 40%, rgba(255,170,30,0.55) 65%, rgba(255,170,30,0) 85%);
  box-shadow: 0 0 12px rgba(255,220,80,0.95), 0 0 24px rgba(255,190,40,0.7);
  filter: blur(0.5px); opacity: 0; animation: rivetFlash 8s ease-in-out infinite;
  pointer-events: none; mix-blend-mode: screen;
}
@keyframes rivetFlash {
  0%,100% { opacity:0; transform:scale(0.5); } 5% { opacity:1; transform:scale(1.35); }
  8% { opacity:1; transform:scale(1.2); } 13% { opacity:0.55; transform:scale(1); }
  18% { opacity:0; transform:scale(0.55); }
}
#earn-page-root .rivet::after { content: none; }
#earn-page-root .wood-base {
  position: absolute; inset: 18px; border-radius: 50%;
  background:
    radial-gradient(ellipse 80% 32% at 50% 12%, rgba(255,230,180,0.35) 0%, transparent 55%),
    radial-gradient(ellipse 65% 25% at 50% 88%, rgba(220,120,60,0.18) 0%, transparent 60%),
    radial-gradient(circle at 50% 50%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.45) 100%),
    url("/textures/red-mahogany.png") center/cover no-repeat,
    #2a0a06;
  box-shadow: 0 0 0 3px #060816, 0 0 0 6px #0a2a8a, 0 0 0 8px #2864ff,
    0 0 0 11px #050816, 0 30px 80px rgba(0,0,0,0.75), inset 0 0 60px rgba(0,0,0,0.55);
  z-index: 1;
}
#earn-page-root .disk-wrap {
  position: absolute; width: 510px; height: 510px; border-radius: 50%;
  will-change: transform; transform-origin: 50% 50%; z-index: 2;
}
#earn-page-root .disk-wrap svg { width: 100%; height: 100%; display: block; }
#earn-page-root .glass {
  position: absolute; width: 510px; height: 510px; border-radius: 50%;
  pointer-events: none; z-index: 5;
  background:
    radial-gradient(ellipse 55% 32% at 32% 16%, rgba(255,255,255,0.52) 0%, rgba(255,255,255,0.14) 32%, transparent 60%),
    radial-gradient(ellipse 18% 55% at 78% 28%, rgba(255,255,255,0.22) 0%, transparent 60%),
    radial-gradient(circle at 50% 50%, transparent 60%, rgba(0,0,0,0.45) 100%);
  mix-blend-mode: screen;
}
#earn-page-root .static-overlay {
  position: absolute; width: 530px; height: 530px; pointer-events: none; z-index: 7;
}
#earn-page-root .static-overlay svg { width: 100%; height: 100%; display: block; }
#earn-page-root .static-overlay .led { animation: led-chase 2.4s linear infinite; }
@keyframes led-chase {
  0% { opacity:0.18; filter:brightness(0.5); } 18% { opacity:1; filter:brightness(2.2); }
  38% { opacity:0.18; filter:brightness(0.5); } 100% { opacity:0.18; filter:brightness(0.5); }
}
#earn-page-root .stage.spinning .static-overlay .led { animation-duration: 0.9s; }
#earn-page-root .static-overlay .light-beams {
  animation: beams-rotate 18s linear infinite; transform-origin: 300px 300px;
}
@keyframes beams-rotate { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
#earn-page-root .stage.spinning .static-overlay .light-beams { animation-duration: 4s; }
#earn-page-root .pointer-wrap {
  position: absolute; top: 10px; left: 50%;
  width: 62px; height: 110px; margin-left: -31px;
  transform-origin: 50% 22px; z-index: 12; will-change: transform;
}
#earn-page-root .pointer-wrap svg {
  width: 100%; height: 100%; display: block;
  filter: drop-shadow(0 6px 8px rgba(0,0,0,0.75)) drop-shadow(0 0 12px rgba(233,198,106,0.6));
}
#earn-page-root .controls {
  margin-top: 22px; position: relative; z-index: 10; display: flex; justify-content: center;
}
#earn-page-root .premium-spin-btn {
  position: relative; isolation: isolate; overflow: visible;
  background: transparent; border: none; padding: 0;
  width: 300px; height: 72px; cursor: pointer; outline: none;
  transition: transform 110ms cubic-bezier(.3,1.6,.4,1), filter 200ms ease;
  animation: btnBreathe 3.6s ease-in-out infinite; will-change: transform;
}
@keyframes btnBreathe {
  0%,100% { transform:translateY(0); filter:brightness(1); }
  50% { transform:translateY(-2px); filter:brightness(1.08); }
}
#earn-page-root .premium-spin-btn:hover:not(:disabled) {
  animation-play-state: paused;
  transform: translateY(-3px) scale(1.02);
  filter: brightness(1.12) saturate(1.15);
}
#earn-page-root .premium-spin-btn:active:not(:disabled) { transform:translateY(5px) scale(0.97); transition-duration:60ms; }
#earn-page-root .premium-spin-btn:disabled { cursor:not-allowed; filter:saturate(0.55) brightness(0.82); animation-play-state:paused; }
#earn-page-root .premium-spin-btn .btn-bg-body {
  position: absolute; z-index: 2; top:0; left:0; width:100%; height:100%; border-radius:999px;
  background:
    radial-gradient(ellipse 90% 65% at 50% -10%, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0) 60%),
    radial-gradient(ellipse 90% 55% at 50% 110%, rgba(0,40,0,0.45) 0%, rgba(0,40,0,0) 60%),
    #39ff14;
  pointer-events: none;
  box-shadow: inset 0 4px 8px rgba(255,255,255,0.7), inset 0 -6px 12px rgba(0,40,0,0.55), inset 0 0 0 1px rgba(0,40,0,0.6);
}
#earn-page-root .premium-spin-btn .btn-glow-ring {
  position: absolute; z-index: 1; top:0; left:0; width:100%; height:100%;
  border-radius: 999px; pointer-events: none;
  box-shadow: 0 0 0 2px #06180a, 0 4px 0 #2a5a08, 0 8px 0 #143a02, 0 12px 0 #061a04,
    0 16px 30px rgba(0,0,0,0.8), 0 0 40px rgba(180,255,40,0.9), 0 0 90px rgba(120,220,40,0.5);
  animation: btnRingPulse 2.4s ease-in-out infinite;
}
@keyframes btnRingPulse { 0%,100% { filter:brightness(1); } 50% { filter:brightness(1.25); } }
#earn-page-root .premium-spin-btn .btn-text-holder {
  position: relative; z-index: 20 !important;
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%; padding: 0 24px;
  font-family: 'Russo One', 'Cinzel', sans-serif; font-weight: 700;
  font-size: 26px; letter-spacing: 0.28em; text-transform: uppercase;
  white-space: nowrap; color: #ffffff !important; opacity: 1 !important;
  mix-blend-mode: normal !important;
  text-shadow: -1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000, -1.5px 1.5px 0 #000,
    1.5px 1.5px 0 #000, 0 -1.5px 0 #000, 0 1.5px 0 #000, -1.5px 0 0 #000,
    1.5px 0 0 #000, 0 2px 4px rgba(0,0,0,0.9);
}
#earn-page-root .premium-spin-btn.show-prize .btn-glow-ring {
  animation: btnPrizePulse 1.6s ease-in-out infinite;
}
@keyframes btnPrizePulse {
  0%,100% { box-shadow: 0 6px 0 #0a3a02, 0 9px 0 #051a04, 0 14px 26px rgba(0,0,0,0.7),
    0 0 60px var(--prize-glow,rgba(255,200,60,0.95)), 0 0 140px var(--prize-glow,rgba(255,180,40,0.55)); }
  50% { box-shadow: 0 6px 0 #0a3a02, 0 9px 0 #051a04, 0 14px 26px rgba(0,0,0,0.7),
    0 0 100px var(--prize-glow,rgba(255,200,60,1)), 0 0 220px var(--prize-glow,rgba(255,180,40,0.7)); }
}
#earn-page-root .premium-spin-btn.show-prize .btn-text-holder { font-size: 34px; letter-spacing: 0.04em; }
#earn-page-root .premium-spin-btn.show-prize.jackpot .btn-text-holder { font-size: 40px; animation: jackpot-shake 700ms ease; }
#earn-page-root .premium-spin-btn.show-prize { animation: prize-pop 700ms cubic-bezier(.2,1.5,.4,1), btnBreathe 3s ease-in-out infinite 0.8s; }
@keyframes prize-pop { 0% { transform:scale(0.82); } 60% { transform:scale(1.14); } 100% { transform:scale(1); } }
@keyframes jackpot-shake { 0%,100% { transform:scale(1); } 25% { transform:scale(1.10) rotate(-1.5deg); } 75% { transform:scale(1.06) rotate(1.5deg); } }
#earn-page-root .btn-spark {
  position: absolute; width: 6px; height: 6px; border-radius: 50%;
  background: radial-gradient(circle, #fff8d4 0%, #ffd960 45%, transparent 75%);
  box-shadow: 0 0 8px #ffd960; pointer-events: none; will-change: transform,opacity; z-index: 30;
}
#earn-page-root .particles { position:absolute; inset:0; pointer-events:none; z-index:25; overflow:hidden; }
#earn-page-root .particle { position:absolute; width:8px; height:8px; border-radius:2px; will-change:transform,opacity; }
#earn-page-root .ambient { position:fixed; inset:0; pointer-events:none; z-index:1; overflow:hidden; }
#earn-page-root .ambient-spark { position:absolute; border-radius:50%; animation:drift 10s linear forwards; opacity:0; }
@keyframes drift {
  0% { transform:translate(0,0) scale(0.4); opacity:0; } 10% { opacity:1; }
  100% { transform:translate(var(--drift,0),-110vh) scale(1.1); opacity:0; }
}
@keyframes jackpot-pulse { 0%,100% { opacity:0.45; } 50% { opacity:1; } }
.jackpot-pulse { animation:jackpot-pulse 1.6s ease-in-out infinite; transform-origin:center; }
/* HUD overlay */
#earn-page-root .earn-hud {
  position: relative; z-index: 200;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  margin-top: 12px; pointer-events: none;
}
#earn-page-root .earn-hud > * { pointer-events: auto; }
#earn-page-root .earn-balance-hud {
  font-family: 'Manrope', sans-serif; font-size: 18px; font-weight: 800;
  color: var(--gold-2);
  text-shadow: 0 0 14px rgba(233,198,106,0.5);
  letter-spacing: 0.06em;
}
#earn-page-root .earn-counter-hud {
  font-size: 11px; letter-spacing: 0.2em; color: var(--ink-dim); text-transform: uppercase;
}
#earn-page-root .earn-result-card {
  margin-top: 4px; padding: 12px 28px; border-radius: 14px; text-align: center;
  border: 2px solid currentColor; background: rgba(0,0,0,0.45);
  animation: prize-pop 0.42s cubic-bezier(.175,.885,.32,1.275);
}
#earn-page-root .earn-result-label { font-size: 12px; letter-spacing: 2px; font-weight: 700; margin-bottom: 4px; }
#earn-page-root .earn-result-value { font-size: 56px; font-weight: 900; line-height: 1; }
#earn-page-root .earn-limit-msg {
  font-size: 12px; color: rgba(255,200,80,0.65); letter-spacing: 0.05em; text-align: center;
}
#earn-page-root .earn-close-btn {
  position: fixed; top: 14px; right: 18px; z-index: 10000;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.5); width: 36px; height: 36px; border-radius: 50%;
  font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background 0.2s, color 0.2s;
}
#earn-page-root .earn-close-btn:hover { background: rgba(255,255,255,0.12); color: #fff; }
@media (max-height: 820px) {
  #earn-page-root .brand { font-size: 32px; }
  #earn-page-root .topbar { margin-bottom: 6px; }
  #earn-page-root .stage { width: 560px; height: 560px; }
  #earn-page-root .disk-wrap, #earn-page-root .glass { width: 440px; height: 440px; }
  #earn-page-root .static-overlay { width: 460px; height: 460px; }
  #earn-page-root .controls { margin-top: 14px; }
}
@media (max-height: 680px) {
  #earn-page-root .stage { width: 460px; height: 460px; }
  #earn-page-root .disk-wrap, #earn-page-root .glass { width: 360px; height: 360px; }
  #earn-page-root .static-overlay { width: 378px; height: 378px; }
  #earn-page-root .pointer-wrap { width: 50px; height: 88px; margin-left: -25px; }
  #earn-page-root .controls { margin-top: 10px; }
  #earn-page-root .earn-hud { margin-top: 8px; gap: 4px; }
}
`

// ─── Adapted wheel logic from design bundle ────────────────────────────────────
function mountWheel() {
  const VALUES = [5,7,5,15,5,30,5,7,5,15,5,7,5,15,5,50,5,7,5,30]
  const N = VALUES.length
  const SECTOR_DEG = 360 / N
  const PALETTE = {
    5:  { outer:'#e7194a', mid:'#9c0c2e', inner:'#3a0410', glow:'#ff5577' },
    7:  { outer:'#3a86c8', mid:'#1a4a7e', inner:'#06182e', glow:'#7fb6ff' },
    15: { outer:'#22a674', mid:'#0e6a48', inner:'#022014', glow:'#5fe6a8' },
    30: { outer:'#8a3eda', mid:'#4a1a8a', inner:'#16043a', glow:'#bc88ff' },
    50: { outer:'#f0c63a', mid:'#a8761a', inner:'#3a2304', glow:'#fff4c2' },
  }
  const CX=300, CY=300, R_OUTER=295, R_INNER=70, R_TEXT=252, R_ICON=198
  const LED_RADIUS=286, LED_COUNT=60
  const deg2rad = d => d*Math.PI/180

  function sectorPath(i) {
    const a0=i*SECTOR_DEG, a1=(i+1)*SECTOR_DEG
    const toXY=(deg,r)=>[CX+r*Math.cos(deg2rad(deg-90)), CY+r*Math.sin(deg2rad(deg-90))]
    const [x0o,y0o]=toXY(a0,R_OUTER), [x1o,y1o]=toXY(a1,R_OUTER)
    const [x0i,y0i]=toXY(a0,R_INNER), [x1i,y1i]=toXY(a1,R_INNER)
    return `M ${x0i},${y0i} L ${x0o},${y0o} A ${R_OUTER},${R_OUTER} 0 0 1 ${x1o},${y1o} L ${x1i},${y1i} A ${R_INNER},${R_INNER} 0 0 0 ${x0i},${y0i} Z`
  }

  function buildWheelSVG() {
    const ns='http://www.w3.org/2000/svg'
    const svg=document.createElementNS(ns,'svg')
    svg.setAttribute('viewBox','0 0 600 600'); svg.setAttribute('xmlns',ns)
    const gradDefs=VALUES.map((v,i)=>{const p=PALETTE[v];return `<radialGradient id="g${i}" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="${p.inner}"/><stop offset="55%" stop-color="${p.mid}"/><stop offset="100%" stop-color="${p.outer}"/></radialGradient>`}).join('')
    const rv=(window.TEXTURES&&window.TEXTURES.redvelvet)||'/textures/red-velvet.jpg'
    const bp=(window.TEXTURES&&window.TEXTURES.blueplaster)||'/textures/blue-plaster.jpg'
    const gv=(window.TEXTURES&&window.TEXTURES.greenvelvet)||'/textures/green-velvet.jpg'
    const pv=(window.TEXTURES&&window.TEXTURES.purplevelvet)||'/textures/purple-velvet.jpg'
    const photoPatterns=`
      <pattern id="pat-5" patternUnits="userSpaceOnUse" x="0" y="0" width="600" height="600"><image href="${rv}" x="0" y="0" width="600" height="600" preserveAspectRatio="xMidYMid slice"/></pattern>
      <pattern id="pat-7" patternUnits="userSpaceOnUse" x="0" y="0" width="600" height="600"><image href="${bp}" x="0" y="0" width="600" height="600" preserveAspectRatio="xMidYMid slice"/></pattern>
      <pattern id="pat-15" patternUnits="userSpaceOnUse" x="0" y="0" width="600" height="600"><image href="${gv}" x="0" y="0" width="600" height="600" preserveAspectRatio="xMidYMid slice"/></pattern>
      <pattern id="pat-30" patternUnits="userSpaceOnUse" x="0" y="0" width="600" height="600"><image href="${pv}" x="0" y="0" width="600" height="600" preserveAspectRatio="xMidYMid slice"/></pattern>`
    const matFilters=`
      <filter id="tex-grain" x="0%" y="0%" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="2.0" numOctaves="2" seed="11" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.15 0"/></filter>
      <filter id="diamond-glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.2"/></filter>`
    const otherDefs=`
      <radialGradient id="depth-shade" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="rgba(0,0,0,0.7)"/><stop offset="42%" stop-color="rgba(0,0,0,0.32)"/><stop offset="85%" stop-color="rgba(0,0,0,0.05)"/><stop offset="100%" stop-color="rgba(0,0,0,0)"/></radialGradient>
      <radialGradient id="top-sheen" cx="50%" cy="14%" r="60%"><stop offset="0%" stop-color="rgba(255,240,210,0.34)"/><stop offset="55%" stop-color="rgba(255,240,210,0)"/></radialGradient>
      <radialGradient id="gold-rim-grad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="transparent"/><stop offset="92%" stop-color="transparent"/><stop offset="93.5%" stop-color="#3a1f08"/><stop offset="95%" stop-color="#fff4c2"/><stop offset="97%" stop-color="#a8741e"/><stop offset="100%" stop-color="#3a1f08"/></radialGradient>
      <radialGradient id="jackpot-flare" cx="50%" cy="50%" r="50%"><stop offset="55%" stop-color="#fff4c2" stop-opacity="0"/><stop offset="100%" stop-color="#ffd960" stop-opacity="0.18"/></radialGradient>
      <linearGradient id="num-shine" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ffffff"/><stop offset="50%" stop-color="#fff4c2"/><stop offset="100%" stop-color="#d4a544"/></linearGradient>
      <linearGradient id="num-shine-jp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#fff8d4"/><stop offset="50%" stop-color="#ffd960"/><stop offset="100%" stop-color="#8e5d18"/></linearGradient>`
    const defs=document.createElementNS(ns,'defs')
    defs.innerHTML=gradDefs+photoPatterns+matFilters+otherDefs
    svg.appendChild(defs)
    const rim=document.createElementNS(ns,'circle')
    rim.setAttribute('cx',CX); rim.setAttribute('cy',CY); rim.setAttribute('r',R_OUTER+4); rim.setAttribute('fill','url(#gold-rim-grad)')
    svg.appendChild(rim)
    const PHOTO_VALUES=new Set([5,7,15,30])
    for(let i=0;i<N;i++){
      const v=VALUES[i],p=document.createElementNS(ns,'path')
      p.setAttribute('d',sectorPath(i)); p.setAttribute('fill',PHOTO_VALUES.has(v)?`url(#pat-${v})`:`url(#g${i})`)
      p.setAttribute('stroke','#0a0508'); p.setAttribute('stroke-width','1'); svg.appendChild(p)
    }
    const grain=document.createElementNS(ns,'circle')
    grain.setAttribute('cx',CX); grain.setAttribute('cy',CY); grain.setAttribute('r',R_OUTER)
    grain.setAttribute('fill','#000'); grain.setAttribute('filter','url(#tex-grain)')
    grain.setAttribute('style','mix-blend-mode:overlay;opacity:0.6'); svg.appendChild(grain)
    for(let i=0;i<N;i++){
      const v=VALUES[i],a0=i*SECTOR_DEG-90,a1=(i+1)*SECTOR_DEG-90,ac=(a0+a1)/2,rad=deg2rad(ac)
      const fi=v===50?56:18,tx=CX+(R_OUTER-fi)*Math.cos(rad),ty=CY+(R_OUTER-fi)*Math.sin(rad)
      const flare=document.createElementNS(ns,'circle')
      flare.setAttribute('cx',tx); flare.setAttribute('cy',ty); flare.setAttribute('r',v===50?24:22)
      flare.setAttribute('fill',PALETTE[v].glow); flare.setAttribute('opacity',v===50?'0.45':'0.32')
      flare.setAttribute('style',`mix-blend-mode:screen;filter:blur(${v===50?8:14}px)`); svg.appendChild(flare)
    }
    const depth=document.createElementNS(ns,'circle'); depth.setAttribute('cx',CX); depth.setAttribute('cy',CY); depth.setAttribute('r',R_OUTER); depth.setAttribute('fill','url(#depth-shade)'); svg.appendChild(depth)
    const sheen=document.createElementNS(ns,'circle'); sheen.setAttribute('cx',CX); sheen.setAttribute('cy',CY); sheen.setAttribute('r',R_OUTER); sheen.setAttribute('fill','url(#top-sheen)'); sheen.setAttribute('style','mix-blend-mode:screen'); svg.appendChild(sheen)
    const jIdx=VALUES.indexOf(50)
    if(jIdx>=0){const halo=document.createElementNS(ns,'path');halo.setAttribute('d',sectorPath(jIdx));halo.setAttribute('fill','url(#jackpot-flare)');halo.setAttribute('class','jackpot-pulse');halo.setAttribute('style','mix-blend-mode:screen');svg.appendChild(halo)}
    for(let i=0;i<N;i++){
      const a=i*SECTOR_DEG-90,rad=deg2rad(a),x1=CX+R_INNER*Math.cos(rad),y1=CY+R_INNER*Math.sin(rad),x2=CX+R_OUTER*Math.cos(rad),y2=CY+R_OUTER*Math.sin(rad)
      const dark=document.createElementNS(ns,'line'); dark.setAttribute('x1',x1);dark.setAttribute('y1',y1);dark.setAttribute('x2',x2);dark.setAttribute('y2',y2);dark.setAttribute('stroke','#0a0408');dark.setAttribute('stroke-width','2.2');svg.appendChild(dark)
      const gold=document.createElementNS(ns,'line'); gold.setAttribute('x1',x1);gold.setAttribute('y1',y1);gold.setAttribute('x2',x2);gold.setAttribute('y2',y2);gold.setAttribute('stroke','#ffe9a8');gold.setAttribute('stroke-width','0.9');gold.setAttribute('opacity','0.85');svg.appendChild(gold)
    }
    const pegR=R_OUTER-14
    for(let i=0;i<N;i++){
      const a=i*SECTOR_DEG-90,rad=deg2rad(a),sx=CX+pegR*Math.cos(rad),sy=CY+pegR*Math.sin(rad)
      const seat=document.createElementNS(ns,'circle');seat.setAttribute('cx',sx);seat.setAttribute('cy',sy);seat.setAttribute('r',6);seat.setAttribute('fill','#0a0408');svg.appendChild(seat)
      const peg=document.createElementNS(ns,'circle');peg.setAttribute('cx',sx);peg.setAttribute('cy',sy);peg.setAttribute('r',4);peg.setAttribute('fill','#dde2e6');svg.appendChild(peg)
      const halo=document.createElementNS(ns,'circle');halo.setAttribute('cx',sx);halo.setAttribute('cy',sy);halo.setAttribute('r',6.5);halo.setAttribute('fill','#ffffff');halo.setAttribute('opacity','0');halo.setAttribute('class','peg-glow');halo.setAttribute('style','filter:blur(3px);mix-blend-mode:screen');svg.appendChild(halo)
      const spec=document.createElementNS(ns,'circle');spec.setAttribute('cx',sx-1.1);spec.setAttribute('cy',sy-1.1);spec.setAttribute('r',1.4);spec.setAttribute('fill','#ffffff');svg.appendChild(spec)
    }
    for(let i=0;i<N;i++){
      const v=VALUES[i],centerDeg=i*SECTOR_DEG+SECTOR_DEG/2,g=document.createElementNS(ns,'g')
      g.setAttribute('transform',`rotate(${centerDeg} ${CX} ${CY})`)
      const dSize=v===50?18:13,dia=document.createElementNS(ns,'g')
      dia.setAttribute('transform',`translate(${CX} ${CY-R_ICON}) rotate(45)`)
      dia.innerHTML=`<rect x="${-dSize/2}" y="${-dSize/2}" width="${dSize}" height="${dSize}" rx="1.5" fill="#1e4ec4" stroke="#0a1a4a" stroke-width="0.8" filter="url(#diamond-glow)"/><rect x="${-dSize/2}" y="${-dSize/2}" width="${dSize}" height="${dSize/2}" rx="1.5" fill="#5a8cff" opacity="0.65"/><circle cx="${-dSize/4}" cy="${-dSize/4}" r="${dSize/7}" fill="#ffffff" opacity="0.95"/>`
      g.appendChild(dia)
      const t=document.createElementNS(ns,'text')
      t.setAttribute('x',CX); t.setAttribute('y',CY-R_TEXT); t.setAttribute('text-anchor','middle')
      t.setAttribute('dominant-baseline','middle'); t.setAttribute('font-family','Cinzel,serif'); t.setAttribute('font-weight','800')
      t.setAttribute('font-size',v===50?'62':v>=15?'50':'46')
      t.setAttribute('fill',v===50?'url(#num-shine-jp)':'url(#num-shine)')
      t.setAttribute('stroke','#0a0408'); t.setAttribute('stroke-width',v===50?'2.4':'2.0'); t.setAttribute('paint-order','stroke fill')
      t.setAttribute('style',`filter:drop-shadow(0 2px 4px rgba(0,0,0,0.9)) drop-shadow(0 0 5px ${PALETTE[v].glow}) drop-shadow(0 0 14px ${PALETTE[v].glow})`)
      t.textContent=v; g.appendChild(t); svg.appendChild(g)
    }
    return svg
  }

  function buildStaticOverlaySVG() {
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg')
    svg.setAttribute('viewBox','0 0 600 600'); svg.setAttribute('xmlns',ns)
    let inner=`<defs>
      <radialGradient id="hub-plate" cx="38%" cy="32%" r="68%"><stop offset="0%" stop-color="#fff8d4"/><stop offset="22%" stop-color="#f0d488"/><stop offset="55%" stop-color="#a87f2c"/><stop offset="85%" stop-color="#3a230a"/><stop offset="100%" stop-color="#0a0508"/></radialGradient>
      <radialGradient id="hub-inner" cx="40%" cy="35%" r="65%"><stop offset="0%" stop-color="#fafafa"/><stop offset="35%" stop-color="#c4c8cc"/><stop offset="75%" stop-color="#5a5e62"/><stop offset="100%" stop-color="#0a0a0a"/></radialGradient>
      <linearGradient id="hub-shine" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(255,255,255,0.65)"/><stop offset="50%" stop-color="rgba(255,255,255,0)"/><stop offset="100%" stop-color="rgba(0,0,0,0.4)"/></linearGradient>
      <radialGradient id="led-bulb" cx="30%" cy="30%" r="70%"><stop offset="0%" stop-color="#ffffff"/><stop offset="35%" stop-color="#ffe9a8"/><stop offset="100%" stop-color="#a8740c"/></radialGradient>
      <radialGradient id="led-glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#ffe9a8" stop-opacity="0.95"/><stop offset="60%" stop-color="#ff9a00" stop-opacity="0.35"/><stop offset="100%" stop-color="#ff9a00" stop-opacity="0"/></radialGradient>
    </defs>`
    let leds=''
    for(let i=0;i<LED_COUNT;i++){
      const a=(i/LED_COUNT)*360-90,rad=deg2rad(a),x=300+LED_RADIUS*Math.cos(rad),y=300+LED_RADIUS*Math.sin(rad),delay=(i/LED_COUNT)*2.4
      leds+=`<g class="led" style="animation-delay:-${delay.toFixed(3)}s;transform-origin:${x}px ${y}px"><circle cx="${x}" cy="${y}" r="11" fill="url(#led-glow)"/><circle cx="${x}" cy="${y}" r="4.5" fill="url(#led-bulb)"/><circle cx="${x-1.2}" cy="${y-1.2}" r="1.4" fill="#ffffff" opacity="0.9"/></g>`
    }
    const beams=`<g class="light-beams"><defs><linearGradient id="beam-grad" x1="0.5" y1="0" x2="0.5" y2="1"><stop offset="0%" stop-color="#fff4c2" stop-opacity="0.9"/><stop offset="100%" stop-color="#fff4c2" stop-opacity="0"/></linearGradient></defs>${[0,1,2,3,4,5].map(i=>{const ang=i*60;return `<polygon points="300,300 ${300+250*Math.cos(deg2rad(ang-4-90))},${300+250*Math.sin(deg2rad(ang-4-90))} ${300+250*Math.cos(deg2rad(ang+4-90))},${300+250*Math.sin(deg2rad(ang+4-90))}" fill="url(#beam-grad)" opacity="0.18" style="mix-blend-mode:screen"/>`}).join('')}</g>`
    const hub=`<circle cx="300" cy="300" r="72" fill="#0a0508"/><circle cx="300" cy="300" r="70" fill="url(#hub-plate)"/><circle cx="300" cy="300" r="56" fill="url(#hub-inner)"/><circle cx="300" cy="300" r="56" fill="url(#hub-shine)" opacity="0.7"/><circle cx="300" cy="300" r="18" fill="url(#hub-plate)" stroke="#1a0c04" stroke-width="1.2"/><circle cx="296" cy="296" r="6" fill="#fff8d4" opacity="0.85"/>`
    inner+=beams+leds+hub; svg.innerHTML=inner; return svg
  }

  function buildPointerSVG() {
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg')
    svg.setAttribute('viewBox','0 0 64 116')
    svg.innerHTML=`<defs>
      <linearGradient id="ptr-gold-blade" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7a4a10"/><stop offset="25%" stop-color="#e6c46a"/><stop offset="48%" stop-color="#fff8d4"/><stop offset="72%" stop-color="#d4a544"/><stop offset="100%" stop-color="#5a3a10"/></linearGradient>
      <radialGradient id="ptr-knob" cx="35%" cy="32%" r="68%"><stop offset="0%" stop-color="#fff8d4"/><stop offset="35%" stop-color="#f0d488"/><stop offset="75%" stop-color="#a87f2c"/><stop offset="100%" stop-color="#3a230a"/></radialGradient>
      <radialGradient id="ptr-gem" cx="35%" cy="30%" r="70%"><stop offset="0%" stop-color="#ffd9d2"/><stop offset="35%" stop-color="#e8324a"/><stop offset="100%" stop-color="#5c0a14"/></radialGradient>
    </defs>
    <circle cx="32" cy="11" r="9.5" fill="url(#ptr-knob)" stroke="#2a1606" stroke-width="1"/>
    <circle cx="32" cy="11" r="4.5" fill="url(#ptr-gem)" stroke="#2a0608" stroke-width="0.6"/>
    <circle cx="30.5" cy="9.5" r="1.3" fill="#fff" opacity="0.9"/>
    <path d="M 30,20 L 34,20 L 34,26 L 30,26 Z" fill="url(#ptr-knob)" stroke="#2a1606" stroke-width="0.6"/>
    <path d="M 32,25 C 40,35 41,55 36,80 C 34.5,92 33,103 32,114 C 31,103 29.5,92 28,80 C 23,55 24,35 32,25 Z" fill="url(#ptr-gold-blade)" stroke="#2a1606" stroke-width="1.1" stroke-linejoin="round"/>
    <path d="M 32,28 L 32,108" stroke="rgba(255,255,210,0.7)" stroke-width="0.9" fill="none" stroke-linecap="round"/>
    <circle cx="32" cy="27.5" r="3.5" fill="url(#ptr-knob)" stroke="#2a1606" stroke-width="0.7"/>
    <circle cx="32" cy="27.5" r="1.2" fill="#2a1606"/>`
    return svg
  }

  function spawnAmbientSparks() {
    const layer=document.getElementById('ambient'); if(!layer) return
    function emit() {
      if(document.hidden) return setTimeout(emit,800)
      const s=document.createElement('div'); s.className='ambient-spark'
      const size=2+Math.random()*4; s.style.width=size+'px'; s.style.height=size+'px'
      s.style.left=(Math.random()*100)+'%'; s.style.top=(90+Math.random()*30)+'%'
      const drift=(Math.random()-0.5)*80,dur=6+Math.random()*5
      s.style.animationDuration=dur+'s'; s.style.setProperty('--drift',drift+'px')
      const tone=Math.random()
      s.style.background=tone<0.5?'#fff4c2':tone<0.85?'#d4a544':'#ffe9a8'
      s.style.boxShadow=`0 0 8px ${s.style.background}`
      layer.appendChild(s); setTimeout(()=>s.remove(),dur*1000)
      setTimeout(emit,220+Math.random()*380)
    }
    for(let i=0;i<4;i++) setTimeout(emit,i*600)
  }

  const diskWrap=document.getElementById('disk')
  const overlay=document.getElementById('static-overlay')
  const pointerEl=document.getElementById('pointer')
  if(!diskWrap||!overlay||!pointerEl) return
  diskWrap.appendChild(buildWheelSVG())
  overlay.appendChild(buildStaticOverlaySVG())
  pointerEl.appendChild(buildPointerSVG())
  spawnAmbientSparks()

  if(window.TEXTURES&&window.TEXTURES.wood){
    const wb=document.querySelector('.wood-base')
    if(wb) {
      wb.style.backgroundImage=`radial-gradient(ellipse 80% 32% at 50% 12%,rgba(255,230,180,0.35) 0%,transparent 55%),radial-gradient(ellipse 65% 25% at 50% 88%,rgba(220,120,60,0.18) 0%,transparent 60%),radial-gradient(circle at 50% 50%,rgba(0,0,0,0) 60%,rgba(0,0,0,0.45) 100%),url("${window.TEXTURES.wood}")`
      wb.style.backgroundSize='auto,auto,auto,cover'; wb.style.backgroundPosition='center,center,center,center'
    }
  }

  ;(function placeRivets(){
    const layer=document.getElementById('rivets'); if(!layer) return
    for(let i=0;i<6;i++){
      const a=(i/6)*360-60,rad=a*Math.PI/180,x=50+43.5*Math.cos(rad),y=50+43.5*Math.sin(rad)
      const r=document.createElement('div'); r.className='rivet'
      r.style.left=x+'%'; r.style.top=y+'%'
      const delay=-(Math.random()*8),dur=7+Math.random()*5
      const spark=document.createElement('div'); spark.className='rivet-spark'
      spark.style.animationDelay=delay+'s'; spark.style.animationDuration=dur+'s'
      r.appendChild(spark); layer.appendChild(r)
    }
  })()

  let angle=0,pendingSector=-1,pAngle=0,pVel=0
  const PK=320,PC=18
  let spinning=false,spinStart=0,spinDur=0,fromAngle=0,totalDelta=0

  function easeOutSmooth(t){ return 1-Math.pow(1-t,4) }

  function startSpin(targetSectorIndex){
    if(spinning) return
    if(targetSectorIndex==null) targetSectorIndex=Math.floor(Math.random()*N)
    pendingSector=targetSectorIndex
    const sectorRad=2*Math.PI/N
    let target=-(targetSectorIndex+0.5)*sectorRad
    target+=((Math.random()-0.5)*sectorRad*0.45)
    target=((target%(2*Math.PI))+2*Math.PI)%(2*Math.PI)
    const cur=((angle%(2*Math.PI))+2*Math.PI)%(2*Math.PI)
    let delta=target-cur; if(delta<=0) delta+=2*Math.PI
    totalDelta=5*2*Math.PI+delta; fromAngle=angle
    spinStart=performance.now(); spinDur=7200+Math.random()*800
    spinning=true
    const spinBtn=document.getElementById('spin')
    if(spinBtn) spinBtn.disabled=true
    document.querySelector('#earn-page-root .stage')?.classList.add('spinning')
  }

  function currentSectorIndex(){
    const sectorRad=2*Math.PI/N
    const ea=(((-angle)%(2*Math.PI))+2*Math.PI)%(2*Math.PI)
    return Math.floor(ea/sectorRad)%N
  }

  function hexToRgba(hex,a){
    const h=hex.replace('#',''),n=h.length===3?h.split('').map(c=>parseInt(c+c,16)):[parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]
    return `rgba(${n[0]},${n[1]},${n[2]},${a})`
  }

  let prizeRevertT
  function showPrize(v){
    const spinBtn=document.getElementById('spin'); if(!spinBtn) return
    const holder=spinBtn.querySelector('.btn-text-holder')
    if(holder) holder.textContent='+'+v
    spinBtn.classList.add('show-prize')
    if(v===50) spinBtn.classList.add('jackpot')
    const glow=(PALETTE[v]&&PALETTE[v].glow)||'#ffd960'
    spinBtn.style.setProperty('--prize-glow',hexToRgba(glow,0.9))
    clearTimeout(prizeRevertT)
    prizeRevertT=setTimeout(()=>{
      spinBtn.classList.remove('show-prize','jackpot')
      spinBtn.style.removeProperty('--prize-glow')
      if(holder) holder.textContent=window.__wheelSpinLabel||'КРУТИТЬ'
    },2600)
  }

  function onLanded(){
    const visualIdx=currentSectorIndex()
    const idx=pendingSector>=0?pendingSector:visualIdx
    const value=VALUES[idx]
    showPrize(value)
    burstParticles(PALETTE[value].glow,PALETTE[value].outer,value===50)
    playWin(value===50)
    document.querySelector('#earn-page-root .stage')?.classList.remove('spinning')
    pendingSector=-1
    const spinBtn=document.getElementById('spin')
    if(spinBtn) spinBtn.disabled=false
    if(typeof window.__wheelOnLanded==='function') window.__wheelOnLanded(value)
  }

  const _diskEl=document.getElementById('disk')
  const _ptrEl=document.getElementById('pointer')
  let lastTime=performance.now()
  function tick(now){
    const dt=Math.min(0.05,(now-lastTime)/1000); lastTime=now
    if(spinning){
      const t=Math.min(1,(now-spinStart)/spinDur),eased=easeOutSmooth(t),prev=angle
      angle=fromAngle+totalDelta*eased
      detectBoundaryCrossings(prev,angle)
      if(t>=1){ angle=fromAngle+totalDelta; spinning=false; onLanded() }
    }
    pVel+=(-PK*pAngle-PC*pVel)*dt; pAngle+=pVel*dt
    if(Math.abs(pAngle)<0.0005&&Math.abs(pVel)<0.001){pAngle=0;pVel=0}
    if(_diskEl) _diskEl.style.transform=`rotate(${angle}rad)`
    if(_ptrEl) _ptrEl.style.transform=`rotate(${pAngle*0.55}rad)`
    requestAnimationFrame(tick)
  }

  function detectBoundaryCrossings(prev,curr){
    const sectorRad=2*Math.PI/N,prevIdx=Math.floor(prev/sectorRad),currIdx=Math.floor(curr/sectorRad)
    if(currIdx===prevIdx) return
    const speed=curr-prev,kick=Math.min(0.9,speed*1.4); pVel+=kick*28
    document.querySelectorAll('.peg-glow').forEach(p=>{p.style.opacity='1';setTimeout(()=>{p.style.opacity='0'},80)})
    // tick sound removed per user request
  }

  let audioCtx=null
  function ensureAudio(){
    if(audioCtx) return audioCtx
    const AC=window.AudioContext||window.webkitAudioContext
    if(!AC) return null
    audioCtx=new AC(); return audioCtx
  }
  const PENTATONIC=[220,246.94,293.66,329.63,392,440,493.88,587.33]
  let lastTickAt=0
  function playTick(velocityScale=1){
    const ctx=ensureAudio(); if(!ctx||ctx.state==='suspended') ctx?.resume?.(); if(!ctx) return
    const t=ctx.currentTime; if(t-lastTickAt<0.045) return; lastTickAt=t
    const v=Math.max(0.2,Math.min(1,velocityScale)),freq=PENTATONIC[Math.floor(Math.random()*PENTATONIC.length)]
    const osc1=ctx.createOscillator(); osc1.type='sine'; osc1.frequency.setValueAtTime(freq,t)
    const osc2=ctx.createOscillator(); osc2.type='triangle'; osc2.frequency.setValueAtTime(freq*1.005,t)
    const lp=ctx.createBiquadFilter(); lp.type='lowpass'; lp.Q.value=6
    lp.frequency.setValueAtTime(400,t); lp.frequency.exponentialRampToValueAtTime(1600,t+0.12); lp.frequency.exponentialRampToValueAtTime(700,t+0.55)
    const g=ctx.createGain(),peak=Math.min(0.10,0.04+0.07*v)
    g.gain.setValueAtTime(0.0001,t); g.gain.exponentialRampToValueAtTime(peak,t+0.06)
    g.gain.linearRampToValueAtTime(peak*0.6,t+0.20); g.gain.exponentialRampToValueAtTime(0.0001,t+0.55)
    osc1.connect(lp); osc2.connect(lp); lp.connect(g).connect(ctx.destination)
    osc1.start(t); osc2.start(t); osc1.stop(t+0.6); osc2.stop(t+0.6)
  }
  function playWin(jackpot){
    const ctx=ensureAudio(); if(!ctx) return; ctx.resume?.()
    const t=ctx.currentTime,notes=jackpot?[523,659,784,1047,1319]:[659,880,1175]
    notes.forEach((freq,i)=>{
      const osc=ctx.createOscillator(); osc.type='triangle'; osc.frequency.setValueAtTime(freq,t+i*0.09)
      const g=ctx.createGain(); g.gain.setValueAtTime(0.0001,t+i*0.09); g.gain.exponentialRampToValueAtTime(0.18,t+i*0.09+0.02); g.gain.exponentialRampToValueAtTime(0.0001,t+i*0.09+0.4)
      osc.connect(g).connect(ctx.destination); osc.start(t+i*0.09); osc.stop(t+i*0.09+0.45)
    })
  }

  const particleLayer=document.getElementById('particles')
  function burstParticles(c1,c2,jackpot){
    if(!particleLayer) return
    const count=jackpot?160:80,rect=particleLayer.getBoundingClientRect(),cx=rect.width/2,cy=rect.height/2
    for(let i=0;i<count;i++){
      const p=document.createElement('div'); p.className='particle'
      const tone=i%3===0?'#fff4c2':(i%3===1?c2:c1); p.style.background=tone; p.style.boxShadow=`0 0 10px ${tone}`
      const size=4+Math.random()*8; p.style.width=size+'px'; p.style.height=(size*(0.6+Math.random()*0.8))+'px'
      p.style.left=cx+'px'; p.style.top=cy+'px'; p.style.borderRadius=Math.random()<0.3?'50%':'2px'
      particleLayer.appendChild(p)
      const ang=Math.random()*Math.PI*2,speed=200+Math.random()*400
      let vx=Math.cos(ang)*speed,vy=Math.sin(ang)*speed-80
      const gravity=800,drag=0.985,rot0=Math.random()*360,rotV=(Math.random()-0.5)*720
      const t0=performance.now(),life=1400+Math.random()*1000
      function pstep(now){ const dt=1/60; vx*=drag; vy=vy*drag+gravity*dt; const elapsed=now-t0,u=elapsed/life; if(u>=1){p.remove();return} const x=(elapsed/1000)*vx,y=(elapsed/1000)*vy+0.5*gravity*Math.pow(elapsed/1000,2); p.style.transform=`translate(${x}px,${y}px) rotate(${rot0+rotV*(elapsed/1000)}deg)`; p.style.opacity=String(1-u*u); requestAnimationFrame(pstep) }
      requestAnimationFrame(pstep)
    }
  }

  function burstButtonSparks(){
    const spinBtn=document.getElementById('spin'); if(!spinBtn) return
    const shell=spinBtn.parentElement; if(!shell) return
    const rect=spinBtn.getBoundingClientRect(),shellRect=shell.getBoundingClientRect()
    const cx=rect.left-shellRect.left+rect.width/2,cy=rect.top-shellRect.top+rect.height/2
    for(let i=0;i<14;i++){
      const s=document.createElement('div'); s.className='btn-spark'
      s.style.left=cx+'px'; s.style.top=cy+'px'; shell.appendChild(s)
      const ang=(i/14)*Math.PI*2+(Math.random()-0.5)*0.4,dist=60+Math.random()*70
      const dx=Math.cos(ang)*dist,dy=Math.sin(ang)*dist,dur=520+Math.random()*220
      s.animate([{transform:'translate(-50%,-50%) translate(0,0) scale(1)',opacity:1},{transform:`translate(-50%,-50%) translate(${dx*0.6}px,${dy*0.6}px) scale(1.2)`,opacity:1,offset:0.5},{transform:`translate(-50%,-50%) translate(${dx}px,${dy}px) scale(0.4)`,opacity:0}],{duration:dur,easing:'cubic-bezier(.2,.7,.3,1)',fill:'forwards'})
      setTimeout(()=>s.remove(),dur+20)
    }
  }

  const sectorRad=2*Math.PI/N
  angle=(((-0.5*sectorRad)%(2*Math.PI)+2*Math.PI)%(2*Math.PI))
  const diskEl=document.getElementById('disk')
  if(diskEl) diskEl.style.transform=`rotate(${angle}rad)`

  window.addEventListener('keydown',e=>{if((e.code==='Space'||e.code==='Enter')&&!document.getElementById('spin')?.disabled){e.preventDefault();startSpin()}})
  requestAnimationFrame(tick)

  window.__wheel={ startSpin, currentSectorIndex, VALUES, burstButtonSparks, ensureAudio, getAngle:()=>angle }
}

// ─── Component ────────────────────────────────────────────────────────────────
const TIER = {
  50: { l: '🎰 JACKPOT!!!', c: '#f0c63a' },
  30: { l: '🔥 MEGA WIN!',  c: '#bc88ff' },
  15: { l: '⚡ BIG DROP!',  c: '#5fe6a8' },
  7:  { l: '✨ NICE!',      c: '#7fb6ff' },
  5:  { l: '+5 ◆',          c: '#ff9999' },
}

export default function EarnPage() {
  const { lang } = useLang()
  const navigate  = useNavigate()
  const isRu      = lang === 'ru'

  const [credits,  setCredits]  = useState(null)
  const [watched,  setWatched]  = useState(0)
  const [spinning, setSpinning] = useState(false)
  const [result,   setResult]   = useState(null)

  const spinTextRef  = useRef(null)
  const wheelReady   = useRef(false)

  // ── Load initial data ──────────────────────────────────────────
  useEffect(() => {
    api.me().then(u => setCredits(u.credits)).catch(() => {})
    api.earnStatus().then(d => setWatched(d.today ?? 0)).catch(() => {})
  }, [])

  // ── Mount wheel once after DOM is ready ───────────────────────
  useEffect(() => {
    if (wheelReady.current) return
    wheelReady.current = true

    // Fonts
    const link = document.createElement('link')
    link.rel  = 'stylesheet'
    link.href = 'https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700;800&family=Cormorant+SC:wght@500;600;700&family=Russo+One&family=Manrope:wght@400;500;600;700;800&display=swap'
    document.head.appendChild(link)

    // Textures
    window.TEXTURES = {
      wood:         '/textures/red-mahogany.png',
      redvelvet:    '/textures/red-velvet.jpg',
      blueplaster:  '/textures/blue-plaster.jpg',
      greenvelvet:  '/textures/green-velvet.jpg',
      purplevelvet: '/textures/purple-velvet.jpg',
      rivet:        '/textures/rivet.webp',
    }

    mountWheel()

    return () => {
      link.remove()
      window.TEXTURES      = undefined
      window.__wheel       = undefined
      window.__wheelOnLanded = undefined
    }
  }, [])

  // ── Keep button text in sync ───────────────────────────────────
  useEffect(() => {
    const el = spinTextRef.current
    if (!el) return
    // Don't overwrite while show-prize animation is running
    const btn = document.getElementById('spin')
    if (btn?.classList.contains('show-prize')) return
    const label = spinning
      ? (isRu ? '🎰 Крутится...' : '🎰 Spinning...')
      : watched >= MAX_DAY
        ? (isRu ? '✓ Лимит исчерпан' : '✓ Limit reached')
        : (isRu ? 'КРУТИТЬ' : 'SPIN')
    el.textContent = label
    window.__wheelSpinLabel = isRu ? 'КРУТИТЬ' : 'SPIN'
  }, [spinning, watched, isRu])

  // ── Spin handler ───────────────────────────────────────────────
  const handleSpin = useCallback(async () => {
    if (spinning || watched >= MAX_DAY) return
    setSpinning(true)
    setResult(null)

    try {
      const ac = window.__wheel?.ensureAudio?.()
      if (ac?.state === 'suspended') await ac.resume()
    } catch (_) {}
    window.__wheel?.burstButtonSparks?.()

    let data
    try {
      data = await api.earnReward()
    } catch (_) {
      setSpinning(false)
      return
    }

    if (!data.success) {
      setSpinning(false)
      setResult({ limit: true })
      return
    }

    window.__wheelOnLanded = () => {
      // Delay state update so show-prize animation finishes first
      setTimeout(() => {
        setWatched(w => w + 1)
        setCredits(data.credits)
        setResult({ earned: data.earned, jackpot: data.jackpot })
        setSpinning(false)
        window.__wheelOnLanded = null
      }, 2700)
    }

    window.__wheel?.startSpin?.(data.sector_index)
  }, [spinning, watched])

  const remaining = Math.max(0, MAX_DAY - watched)

  return (
    <div id="earn-page-root">
      <style>{WHEEL_CSS}</style>

      {/* Close button */}
      <button className="earn-close-btn" onClick={() => navigate('/dashboard')} title="Назад">✕</button>

      {/* Ambient sparks layer */}
      <div id="ambient" className="ambient" />

      {/* Brand header */}
      <div className="topbar">
        <div className="brand">Fortuna Royale</div>
        <span id="balance" style={{ display: 'none' }} />
      </div>

      {/* Wheel stage */}
      <div className="stage">
        <div className="neon-ring" />
        <div className="wood-base" />
        <div className="rivets" id="rivets" />
        <div id="disk" className="disk-wrap" />
        <div className="glass" />
        <div id="static-overlay" className="static-overlay" />
        <div id="pointer" className="pointer-wrap" />
        <div id="particles" className="particles" />
      </div>

      {/* Spin button */}
      <div className="controls">
        <button
          id="spin"
          className="premium-spin-btn"
          type="button"
          onClick={handleSpin}
          disabled={spinning || remaining === 0}
          aria-label={isRu ? 'Крутить' : 'Spin'}
        >
          <div className="btn-glow-ring" />
          <div className="btn-bg-body" />
          <div className="btn-text-holder" ref={spinTextRef}>
            {isRu ? 'КРУТИТЬ' : 'SPIN'}
          </div>
        </button>
      </div>

      {/* HUD: balance + counter */}
      <div className="earn-hud">
        {credits !== null && (
          <div className="earn-balance-hud">{credits.toLocaleString()} ◆</div>
        )}
        <div className="earn-counter-hud">
          {watched} / {MAX_DAY} {isRu ? 'сегодня' : 'today'}
        </div>
      </div>
    </div>
  )
}
