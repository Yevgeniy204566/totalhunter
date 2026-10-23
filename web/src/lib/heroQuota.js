// Общий учёт по уровню Героя (квота «очки»): вес каждого типа сундука и общая норма — функции
// уровня Героя. Шкала сведена из стен кланов и таблиц T5–T9 (владелец 2026-10-20):
// чем ниже Герой, тем меньше сундуков нужно и тем больше очков даёт каждый; выше — наоборот.
//
// Опорные уровни = середины диапазонов Героев кланов: Феникс 298 (225–371), ЭДО 387.5 (337–438),
// Берсерки 450 (средний Герой клана; диапазон 344–482; таблица T9, норма 25 000 очков и 300 эпик-склепов — данные клана
// владельца 2026-10-23). Между опорами — линейно; ниже первой опоры вес растёт
// по общему коэффициенту (у эпиков Феникса очки на 11.6% выше, чем у ЭДО, и тренд продолжается);
// выше последней — постоянный. Всё, что не стена клана, — РАСЧЁТ, не требование клана.
// Очки за сундук округляются до кратных 5, общая норма — до сотен.

import { clampMultiplier, computeRow, bandKey, emcChimeraAt } from './emcQuota.js'
import { NORM_LOW, normBase, lnNormSlope } from './normCurve.js'

const P = 298
const E = 387.5
const B = 450 // Берсерки: средний Герой клана
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
  // монстры EMC — только таблица T9 (Берсерки, 450); ниже — по общему коэффициенту
  'Epic Shadow City': [[B, 55]], 'Dark Omens Chest': [[B, 45]], 'Epic Briareus': [[B, 45]],
  'Epic Arachne': [[B, 40]], 'Yogwai': [[B, 40]], 'Epic Fire Hydra': [[B, 30]],
  'Epic Basilisk': [[B, 30]], 'Epic Undead': [[B, 25]], 'Epic Chimera': [[B, 20]],
  'Epic Hellforge': [[B, 20]],
}

// Ориентир по эпик-склепам — стены: Старт 50, ЭДО 200, Берсерки 300 (на Герое 450). Между стенами — гладкая кубическая
// кривая (монотонная, с общими касательными в стыках); ниже Старта и выше Берсерков цель идёт вместе с нормой в очках.
const EPIC_WALLS = [[NORM_LOW, 50], [E, 200], [B, 300]]

export const HERO_LEVELS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)
export const DEFAULT_SETTINGS = { norm: 1, weights: 1, ranges: [] }

// Монстры таблицы EMC → id сундуков шкалы очков (для доли EMC в общей норме).
const EMC_IDS = ['Epic Fire Hydra', 'Epic Undead', 'Epic Arachne', 'Epic Shadow City']

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

// Монотонная кубическая интерполяция (PCHIP) через опорные точки клана: без изломов в стыках и без выбросов за значения
// стен. Для двух точек — просто прямая.
function smoothLerp(points, h) {
  const n = points.length
  if (n < 3) return lerp(points, h)
  if (h >= points[n - 1][0]) return points[n - 1][1]
  const dx = (i) => points[i + 1][0] - points[i][0]
  const d = points.slice(0, -1).map((_, i) => (points[i + 1][1] - points[i][1]) / dx(i))
  const m = new Array(n)
  for (let i = 1; i < n - 1; i++) {
    if (d[i - 1] * d[i] <= 0) { m[i] = 0; continue }
    const w1 = 2 * dx(i) + dx(i - 1)
    const w2 = dx(i) + 2 * dx(i - 1)
    m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
  }
  const edge = (h0, h1, d0, d1) => {
    const v = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
    if (v * d0 <= 0) return 0
    return d0 * d1 <= 0 && Math.abs(v) > 3 * Math.abs(d0) ? 3 * d0 : v
  }
  m[0] = edge(dx(0), dx(1), d[0], d[1])
  m[n - 1] = edge(dx(n - 2), dx(n - 3), d[n - 2], d[n - 3])
  for (let i = 0; i < n - 1; i++) {
    if (h >= points[i][0] && h <= points[i + 1][0]) {
      const [x0, y0] = points[i]
      const [x1, y1] = points[i + 1]
      const t = (h - x0) / (x1 - x0)
      const t2 = t * t
      const t3 = t2 * t
      return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * (x1 - x0) * m[i] + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * (x1 - x0) * m[i + 1]
    }
  }
  return null
}

function baseWeight(key, h) {
  const pts = W[key]
  if (!pts) return null
  const [x0, y0] = pts[0]
  if (h < x0) return y0 * g(h) / g(x0)
  return smoothLerp(pts, h)
}

// Фейдер пульта на тип: «все уровни» × ступень Героя; on === false — тип не считается (mute).
function mixFactor(entry, hero) {
  if (entry?.on === false) return 0
  return clampMultiplier(entry?.all) * clampMultiplier(entry?.bands?.[bandKey(hero)])
}

export function weightAt(id, hero, settings = DEFAULT_SETTINGS) {
  const key = weightKey(id)
  const base = baseWeight(key, hero)
  if (base == null) return null
  return round5(base * clampMultiplier(settings.weights) * mixFactor(settings.mix?.w?.[key], hero))
}

function rangeK(hero, ranges) {
  const r = (ranges || []).find(x => hero >= Number(x.from) && hero <= Number(x.to))
  return r ? clampMultiplier(r.k) : 1
}

export function normAt(hero, settings = DEFAULT_SETTINGS) {
  const base = normBase(hero) // без обрезки: шкала задана на всём диапазоне 100–600 (владелец 2026-10-20)
  return round100(base * rangeK(hero, settings.ranges) * clampMultiplier(settings.norm))
}

function avgEpicWeight(hero) {
  return ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']
    .reduce((sum, id) => sum + baseWeight(id, hero), 0) / 4
}

// Кубический Эрмит между двумя точками с заданными касательными
function hermite(x0, y0, m0, x1, y1, m1, x) {
  const d = x1 - x0
  const t = (x - x0) / d
  const t2 = t * t
  const t3 = t2 * t
  return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * d * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * d * m1
}

function epicBase(hero) {
  const [[xa, ya], [xb, yb], [xc, yc]] = EPIC_WALLS
  // касательные на краях согласованы с хвостами за пределами стен (там цель пропорциональна норме)
  const mLeft = ya * lnNormSlope(xa)
  const mRight = yc * lnNormSlope(xc)
  // средняя касательная — гармоническое среднее наклонов отрезков (стандартный монотонный PCHIP)
  const d0 = (yb - ya) / (xb - xa)
  const d1 = (yc - yb) / (xc - xb)
  const w1 = 2 * (xc - xb) + (xb - xa)
  const w2 = (xc - xb) + 2 * (xb - xa)
  const mMid = (w1 + w2) / (w1 / d0 + w2 / d1)
  if (hero < xa) return (ya * normBase(hero) * avgEpicWeight(xa)) / (normBase(xa) * avgEpicWeight(hero))
  if (hero <= xb) return hermite(xa, ya, mLeft, xb, yb, mMid, hero)
  if (hero <= xc) return hermite(xb, yb, mMid, xc, yc, mRight, hero)
  return (yc * normBase(hero) * avgEpicWeight(xc)) / (normBase(xc) * avgEpicWeight(hero))
}

export function epicRefAt(hero, settings = DEFAULT_SETTINGS) {
  return Math.round(epicBase(hero) * mixFactor(settings.mix?.epic, hero))
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
export function scoreOf(counts, meta, hero, settings = DEFAULT_SETTINGS, slot = null) {
  const partial = !hero
  const h = hero || DEFAULT_HERO
  let score = 0
  const fallback = []
  for (const [name, n] of Object.entries(counts || {})) {
    if (!n) continue
    const m = meta?.[name]
    if (slot != null && m?.slot !== slot) continue
    const scaled = m ? weightAt(m.id, h, settings) : null
    if (scaled == null) {
      // тип вне шкалы: очки клана из «Учёта»; фейдер пульта (mix.w) множит их, mute обнуляет
      const f = m ? mixFactor(settings.mix?.w?.[m.id], h) : 1
      score += n * Math.round((m?.points || 0) * f)
      fallback.push(name)
    } else {
      score += n * scaled
    }
  }
  return { score, partial, fallback }
}

// Очки, которые закладываются на EMC при Герое hero: штуки по таблице EMC × вес монстра шкалы.
// Это «доля EMC» в общей норме; Crypts получает остаток (норма «Всего» − доля EMC, не меньше 0).
export function emcPointsAt(hero, emcModel, settings = DEFAULT_SETTINGS) {
  const row = computeRow(hero, emcModel || undefined)
  const counts = [row.finalH, row.finalU, row.finalA, row.finalS]
  const four = EMC_IDS.reduce((sum, id, k) => sum + counts[k] * (weightAt(id, hero, settings) || 0), 0)
  // Chimera — пятый эпик-монстр (больше половины всего EMC у ELDORADO), считается со своей базой, а не как «прочий»
  return four + emcChimeraAt(hero) * (weightAt('Epic Chimera', hero, settings) || 0)
}

export function cryptsNormAt(hero, emcModel, settings = DEFAULT_SETTINGS) {
  return Math.max(0, normAt(hero, settings) - emcPointsAt(hero, emcModel, settings))
}

// Типы для пульта: Crypts — склепы и цитадели, EMC — эпические монстры (очки за сундук).
export const CRYPT_TYPES = ['Common Crypt 20', 'Common Crypt 25', 'Rare Crypt 20', 'Rare Crypt 25', 'Rare Crypt 30',
  'Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35', 'Citadel 20', 'Citadel 25', 'Citadel 30']
export const EMC_TYPES = [...EMC_IDS, 'Dark Omens Chest', 'Epic Briareus', 'Yogwai', 'Epic Basilisk', 'Epic Chimera', 'Epic Hellforge']

// Количество склепов по типам (режим «Количество» пульта) — по данным кланов (владелец 2026-10-21):
// клан требует N эпик-склепов любого уровня 20–35 (Старт 50, ЭДО 200 — факт; 40 и 250 — расчёт) — это
// epicRefAt(Герой). Делим поровну между включёнными эпик-типами (клан уровни не различает). Для Rare/Common/
// Citadel клан штук не называет — база 0 (они считаются только в очках); число можно задать вручную (set).
// Проверка по данным: эпики × средние очки эпика = 102% нормы ЭДО, 81% Старта.
export const EPIC_CRYPTS = ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']

function countRaw(id, hero, settings) {
  const key = weightKey(id)
  const mixC = settings.mix?.c || {}
  const entry = mixC[key]
  if (entry?.on === false) return 0
  if (entry?.set != null) return Math.max(0, entry.set)
  if (!EPIC_CRYPTS.includes(key)) return 0
  const active = EPIC_CRYPTS.filter(t => mixC[t]?.on !== false)
  return epicRefAt(hero) / active.length * mixFactor({ ...entry, on: true }, hero)
}

export function countAt(id, hero, settings = DEFAULT_SETTINGS) {
  return Math.round(countRaw(id, hero, settings))
}

// Прочие эпические монстры (нет истории штук): база = простое среднее штук четырёх известных монстров
// на этом Герое (владелец 2026-10-21: все события примерно равны по затратам), правится фейдером.
export const EMC_FOUR = { 'Epic Fire Hydra': 0, 'Epic Undead': 1, 'Epic Arachne': 2, 'Epic Shadow City': 3 }
const EMC_FINALS = ['finalH', 'finalU', 'finalA', 'finalS']

export function emcCountAt(id, hero, settings = DEFAULT_SETTINGS, emcModel) {
  const entry = settings.mix?.c?.[id]
  if (entry?.on === false) return 0
  if (entry?.set != null) return Math.max(0, Math.round(entry.set))
  const row = computeRow(hero, emcModel || undefined)
  if (id in EMC_FOUR) return row[EMC_FINALS[EMC_FOUR[id]]]
  if (id === 'Epic Chimera') return emcChimeraAt(hero, mixFactor({ ...entry, on: true }, hero))
  const base = computeRow(hero)
  const mean = EMC_FINALS.reduce((sum, k) => sum + base[k], 0) / 4
  return Math.round(mean * mixFactor({ ...entry, on: true }, hero))
}

// К какой вкладке пульта относится тип — единое правило для пульта и публичной страницы (владелец 2026-10-20):
// статусы «Учёта»: Не в учёте / В учёте / Квота 1 / Квота 2. EMC — ТОЛЬКО «Квота 2» (других трактовок нет);
// Crypts — «Квота 1» и «В учёте» (то, что учитывается без квоты).
export function typeTab(id, slot) {
  return slot === 2 ? 'emc' : 'crypts'
}

// Цель по штукам для типов слота EMC вне четырёх известных монстров (в том числе свои события, «Тыква»).
export function emcOthersTotal(typeMeta, hero, settings = DEFAULT_SETTINGS, emcModel) {
  return Object.values(typeMeta || {})
    .filter(m => m.slot === 2 && !(m.id in EMC_FOUR))
    .reduce((sum, m) => sum + emcCountAt(m.id, hero, settings, emcModel), 0)
}

// Обязательная норма клана — эпик-склепы суммой (любой уровень 20–35): Старт 50, ЭДО 200 — факт, выше/ниже —
// интерполяция (Герой 456 → 334). Сумма долей типов, поэтому фейдеры и mute пульта её меняют.
export function epicCountTotal(hero, settings = DEFAULT_SETTINGS) {
  // сумма до округления: четыре доли по 83.5 дают 334, а не 336
  return Math.round(EPIC_CRYPTS.reduce((sum, id) => sum + countRaw(id, hero, settings), 0))
}

// Сколько эпик-склепов (20–35) набрал игрок: по id типов из мета-данных сводки.
export function epicCryptsOf(counts, meta) {
  let n = 0
  for (const [name, c] of Object.entries(counts || {})) {
    const m = meta?.[name]
    if (m && EPIC_CRYPTS.includes(weightKey(m.id))) n += c || 0
  }
  return n
}
