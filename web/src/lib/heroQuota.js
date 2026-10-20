// Общий учёт по уровню Героя (квота «очки»): вес каждого типа сундука и общая норма — функции
// уровня Героя. Шкала сведена из стен кланов и таблиц T5–T9 (владелец 2026-10-20):
// чем ниже Герой, тем меньше сундуков нужно и тем больше очков даёт каждый; выше — наоборот.
//
// Опорные уровни = середины диапазонов Героев кланов: Феникс 298 (225–371), ЭДО 387.5 (337–438),
// Берсерки 413 (344–482; таблица T9). Между опорами — линейно; ниже первой опоры вес растёт
// по общему коэффициенту (у эпиков Феникса очки на 11.6% выше, чем у ЭДО, и тренд продолжается);
// выше последней — постоянный. Всё, что не стена клана, — РАСЧЁТ, не требование клана.
// Очки за сундук округляются до кратных 5, общая норма — до сотен.

import { clampMultiplier } from './emcQuota.js'

const P = 298
const E = 387.5
const B = 413
const EPIC_RATIO = 1.116 // средние очки эпик-склепов Феникса / ЭДО на 25–35 ур.

// id → [[Герой, очки], …]; 0 на 387.5 = «в стене ЭДО такого типа нет — не засчитывается».
const W = {
  'Epic Crypt 35': [[P, 150], [E, 135], [B, 135]],
  'Epic Crypt 30': [[P, 90], [E, 80], [B, 80]],
  'Epic Crypt 25': [[P, 50], [E, 45], [B, 45]],
  'Epic Crypt 20': [[P, 30], [E, 25]],
  'Rare Crypt 30': [[P, 80], [E, 65], [B, 65]],
  'Rare Crypt 25': [[P, 45], [E, 35], [B, 20]],
  'Rare Crypt 20': [[P, 25], [E, 0]],
  'Common Crypt 25': [[P, 40], [E, 15], [400, 0]], // владелец: с Героя 400 обычный склеп не считается
  'Common Crypt 20': [[P, 20], [E, 0]],
  'Citadel 30': [[P, 50], [E, 40], [B, 40]],
  'Citadel 25': [[P, 35], [E, 25]],
  'Citadel 20': [[P, 20], [E, 0]],
  // монстры EMC — только таблица T9 (Берсерки, 413); ниже — по общему коэффициенту
  'Epic Shadow City': [[B, 55]], 'Dark Omens Chest': [[B, 45]], 'Epic Briareus': [[B, 45]],
  'Epic Arachne': [[B, 40]], 'Yogwai': [[B, 40]], 'Epic Fire Hydra': [[B, 30]],
  'Epic Basilisk': [[B, 30]], 'Epic Undead': [[B, 25]], 'Epic Chimera': [[B, 20]],
  'Epic Hellforge': [[B, 20]],
}

// Общая норма за 14 дней: Старт 5000 и ЭДО 14000 — стены; Сарацины 4000 и Берсерки 16000 — расчёт.
const NORM = [[213.5, 4000], [279, 5000], [E, 14000], [B, 16000]]
// Ориентир по эпик-склепам: Старт 50, ЭДО 200 — стены; Сарацины 40, Берсерки 250 — расчёт.
const EPIC = [[213.5, 40], [279, 50], [E, 200], [B, 250]]

export const HERO_LEVELS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)
export const DEFAULT_SETTINGS = { norm: 1, weights: 1, ranges: [] }

// Общий коэффициент «слабее Герой — больше очков за сундук».
function g(h) {
  if (h >= E) return 1
  if (h >= P) return 1 + (EPIC_RATIO - 1) * (E - h) / (E - P)
  return EPIC_RATIO + (EPIC_RATIO - 1) / (E - P) * (P - h)
}

function lerp(points, h) {
  if (h >= points[points.length - 1][0]) return points[points.length - 1][1]
  for (let i = 0; i < points.length - 1; i++) {
    const [x0, y0] = points[i]
    const [x1, y1] = points[i + 1]
    if (h >= x0 && h <= x1) return y0 + (y1 - y0) * (h - x0) / (x1 - x0)
  }
  return null
}

const round5 = x => Math.round(x / 5) * 5
const round100 = x => Math.round(x / 100) * 100

// Cursed/Elven-цитадели одного уровня — одна строка шкалы (в стенах просто «цитадель»).
export function weightKey(id) {
  return String(id || '').replace(/^(Cursed|Elven) Citadel /, 'Citadel ')
}

function baseWeight(key, h) {
  const pts = W[key]
  if (!pts) return null
  const [x0, y0] = pts[0]
  if (h < x0) return y0 * g(h) / g(x0)
  return lerp(pts, h)
}

export function weightAt(id, hero, settings = DEFAULT_SETTINGS) {
  const base = baseWeight(weightKey(id), hero)
  if (base == null) return null
  return round5(base * clampMultiplier(settings.weights))
}

function rangeK(hero, ranges) {
  const r = (ranges || []).find(x => hero >= Number(x.from) && hero <= Number(x.to))
  return r ? clampMultiplier(r.k) : 1
}

function curve(points, h) {
  const [x0, y0] = points[0]
  if (h >= x0) {
    if (h > points[points.length - 1][0]) {
      const [xa, ya] = points[points.length - 2]
      const [xb, yb] = points[points.length - 1]
      return yb + (h - xb) * (yb - ya) / (xb - xa)
    }
    return lerp(points, h)
  }
  const [x1, y1] = points[1]
  return y0 - (x0 - h) * (y1 - y0) / (x1 - x0)
}

export function normAt(hero, settings = DEFAULT_SETTINGS) {
  const base = Math.max(1000, curve(NORM, hero))
  return round100(base * rangeK(hero, settings.ranges) * clampMultiplier(settings.norm))
}

export function epicRefAt(hero) {
  return Math.round(Math.max(10, curve(EPIC, hero)))
}

const ANCHOR_LEVELS = new Set([P, E, B])

export function weightTable(hero, settings = DEFAULT_SETTINGS) {
  return Object.keys(W).map(id => ({
    id,
    points: weightAt(id, hero, settings),
    origin: ANCHOR_LEVELS.has(hero) && W[id].some(([x]) => x === hero) ? 'FACT' : 'CALC',
  }))
}

export const DEFAULT_HERO = 400

// Счёт игрока: Σ штук × вес типа при его Герое. Тип вне шкалы — очки клана из «Учёта»
// (запасной вариант, перечислен в fallback). Нет Героя — считаем по 400 и ставим partial.
export function scoreOf(counts, meta, hero, settings = DEFAULT_SETTINGS) {
  const partial = !hero
  const h = hero || DEFAULT_HERO
  let score = 0
  const fallback = []
  for (const [name, n] of Object.entries(counts || {})) {
    if (!n) continue
    const m = meta?.[name]
    const scaled = m ? weightAt(m.id, h, settings) : null
    if (scaled == null) {
      score += n * (m?.points || 0)
      fallback.push(name)
    } else {
      score += n * scaled
    }
  }
  return { score, partial, fallback }
}
