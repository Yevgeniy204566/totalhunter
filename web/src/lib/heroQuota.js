// Общий учёт по уровню Героя (квота «очки»): вес каждого типа сундука и общая норма — функции
// уровня Героя. Шкала сведена из стен кланов и таблиц T5–T9 (владелец 2026-10-20):
// чем ниже Герой, тем меньше сундуков нужно и тем больше очков даёт каждый; выше — наоборот.
//
// Опорные уровни = середины диапазонов Героев кланов: Феникс 298 (225–371), ЭДО 387.5 (337–438),
// Берсерки 450 (средний Герой клана; диапазон 344–482; таблица T9, норма 25 000 очков и 300 эпик-склепов — данные клана
// владельца 2026-10-23). Между опорами — линейно; ниже первой опоры вес растёт
// по общему коэффициенту (у эпиков Феникса очки на 11.6% выше, чем у ЭДО, и тренд продолжается);
// выше последней — постоянный. Всё, что не стена клана, — РАСЧЁТ, не требование клана.
// Очки за сундук округляются до целых (владелец 2026-10-26: шаг 1, не 5), общая норма — до сотен.

import { clampMultiplier, computeRow, bandKey, emcChimeraAt, emcChimeraBaseAt, round as roundEmc } from './emcQuota.js'
import { NORM_LOW, normBase } from './normCurve.js'

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

// Ориентир по эпик-склепам. Опорные стены — Старт 50 (Герой 279) и Берсерки 300 (Герой 450). Стена ЭДО (200 на 387.5)
// выбивалась из общей кривой: у неё эпики×средние очки = 102% нормы, у Старта 81%, у Берсерков 86%, а на 1000 очков
// нормы 14.3 склепа против 10.0 и 12.0 (владелец 2026-10-24: общей кривой доверяем больше, чем частному случаю,
// который скорее всего ошибка или нехватка данных). Поэтому считаем долю нормы, которую закрывают эпики, S(h):
// плавно (smoothstep, без изломов) от доли Старта к доле Берсерков, вне стен — константа; ЭДО на 387.5 выходит ≈165.
const EPIC_WALLS = [[NORM_LOW, 50], [B, 300]]

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

const round1 = x => Math.round(x)
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

// Главный фейдер консоли пульта (владелец 2026-10-26): множитель очков всех типов своей группы —
// склепы и цитадели либо эпические монстры. Группу задаёт сам тип: в шкале склепы/цитадели перечислены в CRYPT_TYPES.
const groupK = (group, settings) => clampMultiplier(settings.mix?.g?.[group]?.all)

// Полная свобода правки (владелец 2026-10-27): на уровне, где шкала даёт 0 («тип не засчитывается»), множитель бессмыслен —
// ноль на любое число равен нулю. Поэтому там правка ступени (mix.w[тип].bands) — это сами очки: считаем от условной единицы.
// Без правки ступени там по-прежнему 0.
export const ZERO_UNIT = 1
const hasBand = (entry, hero) => entry?.bands?.[bandKey(hero)] != null

// Очки типа по шкале на уровне Героя без всяких правок (0 — шкала не засчитывает тип на этом уровне; null — типа нет в шкале).
export function scaleBaseAt(id, hero) {
  return baseWeight(weightKey(id), hero)
}

export function weightAt(id, hero, settings = DEFAULT_SETTINGS) {
  const key = weightKey(id)
  let base = baseWeight(key, hero)
  if (base == null) return null
  const entry = settings.mix?.w?.[key]
  if (!(base > 0) && hasBand(entry, hero)) base = ZERO_UNIT
  const group = CRYPT_TYPES.includes(key) ? 'crypts' : 'emc'
  return round1(base * clampMultiplier(settings.weights) * mixFactor(entry, hero) * groupK(group, settings))
}

// Очки типа на уровне Героя без округления и без поправки ступени: опора, от которой график пересчитывает «желаемые очки»
// в поправку ступени. null — типа нет в шкале. На нулевом уровне шкалы опора — условная единица (чтобы линию можно было вести).
export function weightBase(id, hero, settings = DEFAULT_SETTINGS) {
  const key = weightKey(id)
  let base = baseWeight(key, hero)
  if (base == null) return null
  if (!(base > 0)) base = ZERO_UNIT
  const group = CRYPT_TYPES.includes(key) ? 'crypts' : 'emc'
  return base * clampMultiplier(settings.weights) * clampMultiplier(settings.mix?.w?.[key]?.all) * groupK(group, settings)
}

function rangeK(hero, ranges) {
  const r = (ranges || []).find(x => hero >= Number(x.from) && hero <= Number(x.to))
  return r ? clampMultiplier(r.k) : 1
}

// Норма склепов — стены кланов (Старт 5000, ЭДО 14000, Берсерки 25000) БЕЗ EMC: эти числа были даны до учёта EMC.
export function cryptsBaseAt(hero, settings = DEFAULT_SETTINGS) {
  const base = normBase(hero) // без обрезки: шкала задана на всём диапазоне 100–600 (владелец 2026-10-20)
  return round100(base * rangeK(hero, settings.ranges) * clampMultiplier(settings.norm))
}

// Полная норма очков (владелец 2026-10-27): склепы по стенам + очки EMC (штуки таблицы × очки за монстра по T9 при
// настройках по умолчанию). Рычаги нормы и диапазонов двигают сумму целиком. Ниже Героя 200 EMC нет — норма как у склепов.
export function normAt(hero, settings = DEFAULT_SETTINGS) {
  const base = normBase(hero) + emcPointsAt(hero, undefined, DEFAULT_SETTINGS)
  return round100(base * rangeK(hero, settings.ranges) * clampMultiplier(settings.norm))
}

function avgEpicWeight(hero) {
  return ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']
    .reduce((sum, id) => sum + baseWeight(id, hero), 0) / 4
}

const smoothstep = t => t * t * (3 - 2 * t)

function epicBase(hero) {
  const [[xa, ya], [xc, yc]] = EPIC_WALLS
  const shareA = ya * avgEpicWeight(xa) / normBase(xa) // доля нормы, закрываемая эпиками, у Старта
  const shareC = yc * avgEpicWeight(xc) / normBase(xc) // и у Берсерков
  const t = Math.min(1, Math.max(0, (hero - xa) / (xc - xa)))
  const share = shareA + (shareC - shareA) * smoothstep(t)
  return share * normBase(hero) / avgEpicWeight(hero)
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

// Очки типа вне шкалы: очки клана из «Учёта» с фейдером пульта, главным фейдером группы и mute — одна функция для пульта и счёта.
// Эпические монстры ведут себя одинаково, различается только цена (владелец 2026-10-27): событие EMC вне шкалы (Pumpkin, свои)
// получает ту же зависимость от Героя, что у монстров шкалы (слабее Герой — больше очков, с 387,5 ровно), а цену берёт у клана.
const emcShape = (m, hero) => (typeTab(m?.id, m?.slot) === 'emc' ? g(hero) : 1)

export function fallbackWeight(m, hero, settings = DEFAULT_SETTINGS) {
  const entry = settings.mix?.w?.[m.id]
  const f = mixFactor(entry, hero) * groupK(typeTab(m.id, m.slot), settings)
  // очки клана 0 — тип не считается; правка ступени там задаёт сами очки (как на нулевых уровнях шкалы)
  if (!((m?.points || 0) > 0)) return hasBand(entry, hero) ? Math.round(ZERO_UNIT * f) : 0
  return Math.round((m?.points || 0) * f * emcShape(m, hero))
}

// Точное значение без поправок ступеней (опора графика «Очки»): очки клана × форма по Героям × «все уровни» × главный фейдер группы
export function fallbackBase(m, hero, settings = DEFAULT_SETTINGS) {
  const entry = settings.mix?.w?.[m.id]
  const pts = m?.points || 0
  const unit = pts > 0 ? pts * emcShape(m, hero) : ZERO_UNIT
  return unit * clampMultiplier(entry?.all) * groupK(typeTab(m.id, m.slot), settings)
}

// Значение «по умолчанию» (пунктир графика): очки клана с формой по Героям, без фейдеров
export const fallbackDefault = (m, hero) => Math.round((m?.points || 0) * emcShape(m, hero))

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
      // тип вне шкалы: очки клана из «Учёта»; фейдер пульта (mix.w) и главный фейдер группы двигают их, mute обнуляет
      score += n * (m ? fallbackWeight(m, h, settings) : 0)
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
  return four + emcChimeraAt(hero, clampMultiplier(emcModel?.global)) * (weightAt('Epic Chimera', hero, settings) || 0)
}

export function cryptsNormAt(hero, emcModel, settings = DEFAULT_SETTINGS) {
  return Math.max(0, normAt(hero, settings) - emcPointsAt(hero, emcModel, settings))
}

// Типы для пульта: Crypts — склепы и цитадели, EMC — эпические монстры (очки за сундук).
export const CRYPT_TYPES = ['Common Crypt 20', 'Common Crypt 25', 'Rare Crypt 20', 'Rare Crypt 25', 'Rare Crypt 30',
  'Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35', 'Citadel 20', 'Citadel 25', 'Citadel 30']
export const EMC_TYPES = [...EMC_IDS, 'Dark Omens Chest', 'Epic Briareus', 'Yogwai', 'Epic Basilisk', 'Epic Chimera', 'Epic Hellforge']

// Количество склепов по типам (режим «Количество» пульта) — по данным кланов (владелец 2026-10-21; Rare/Common/Citadel — 2026-10-26):
// клан требует N эпик-склепов любого уровня 20–35 (Старт 50, Берсерки 300 — стены; ЕДО ≈166 по общей кривой) — это
// epicRefAt(Герой). Делим поровну между включёнными эпик-типами (клан уровни не различает). Для Rare/Common/
// Citadel клан штук не называет — база 0 (они считаются только в очках); число можно задать вручную (set).
// Проверка по данным: эпики × средние очки эпика = 102% нормы ЭДО, 81% Старта.
export const EPIC_CRYPTS = ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']

export function countRaw(id, hero, settings) {
  const key = weightKey(id)
  const mixC = settings.mix?.c || {}
  const entry = mixC[key]
  if (entry?.on === false) return 0
  if (entry?.set != null) return Math.max(0, entry.set)
  // тип вне шкалы (свой склеп) — штук нет, число вписывается вручную
  if (!CRYPT_TYPES.includes(key)) return 0
  // очки у типа на этом уровне Героя нулевые — значит, он не учитывается и штук тоже нет (владелец 2026-10-26: очки есть,
  // а штук 0 быть не может, и наоборот)
  if (!EPIC_CRYPTS.includes(key) && !(baseWeight(key, hero) >= 0.5)) return hasBand(entry, hero) ? ZERO_UNIT * mixFactor({ ...entry, on: true }, hero) : 0
  const active = EPIC_CRYPTS.filter(t => mixC[t]?.on !== false)
  // Rare, Common и Citadel — столько же штук, сколько у типа эпик-склепа: клан называет норму только по эпикам, у остальных
  // типов это ориентир, на публичные цели (сумма эпик-склепов) он не влияет
  return epicRefAt(hero, settings) / active.length * mixFactor({ ...entry, on: true }, hero)
}

// Уровень, где у типа склепов нет штук (нет очков в шкале): по умолчанию 0, правка ступени — сами штуки (любое число)
export const countZeroAt = (id, hero) => {
  const key = weightKey(id)
  return CRYPT_TYPES.includes(key) && !EPIC_CRYPTS.includes(key) && !(baseWeight(key, hero) >= 0.5)
}

// Штуки типа без поправки его ступеней (опора графика «Количество»); на нулевом уровне — условная единица × «все уровни»
export function countBaseAt(id, hero, settings = DEFAULT_SETTINGS) {
  const key = weightKey(id)
  const entry = settings.mix?.c?.[key]
  if (countZeroAt(key, hero)) return ZERO_UNIT * clampMultiplier(entry?.all)
  const s2 = { ...settings, mix: { ...(settings.mix || {}), c: { ...(settings.mix?.c || {}), [key]: { ...(entry || {}), bands: {} } } } }
  return countRaw(key, hero, s2)
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
  // общий множитель «все EMC» (главный фейдер пульта, emc.global) — для ВСЕХ монстров, включая Chimera и прочих
  const globalK = clampMultiplier(emcModel?.global)
  const f = mixFactor({ ...entry, on: true }, hero) * globalK
  if (id === 'Epic Chimera') {
    if (emcChimeraBaseAt(hero) >= 1 || !hasBand(entry, hero)) return emcChimeraAt(hero, f)
    return roundEmc(ZERO_UNIT * f) // уровень ниже единицы: вписанная ступень — сами штуки
  }
  const base = computeRow(hero)
  const mean = EMC_FINALS.reduce((sum, k) => sum + base[k], 0) / 4
  if (mean < 1 && hasBand(entry, hero)) return roundEmc(ZERO_UNIT * f)
  return Math.round(mean * f)
}

// Нулевой уровень типа EMC (Chimera и прочие): модель даёт 0 — правка ступени там задаёт сами штуки
export function emcOtherZero(id, hero) {
  if (id === 'Epic Chimera') return !(emcChimeraBaseAt(hero) >= 1)
  const row = computeRow(hero)
  return !(EMC_FINALS.reduce((sum, k) => sum + row[k], 0) / 4 >= 1)
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

// Цель квоты EMC — КОЛИЧЕСТВО (владелец 2026-10-27): какие именно сундуки будут бить игроки и есть ли они в списке типов клана,
// значения не имеет. Поэтому цель = общая цифра модели: четыре монстра по таблице + Chimera, с рычагами пульта; от типов не зависит.
export function emcQuotaTotal(hero, settings = DEFAULT_SETTINGS, emcModel) {
  return computeRow(hero, emcModel || undefined).emc + emcCountAt('Epic Chimera', hero, settings, emcModel)
}

// Обязательная норма клана — эпик-склепы суммой (любой уровень 20–35): Старт 50, Берсерки 300 — стены, между ними и
// выше/ниже — общая кривая (Герой 456 → 317). Сумма долей типов, поэтому фейдеры и mute пульта её меняют.
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

// Количество прочих эпических монстров (всё, кроме четырёх с историей) без округления — опора для графика количества.
export function emcOtherRaw(id, hero, settings = DEFAULT_SETTINGS, emcModel) {
  const entry = settings.mix?.c?.[id]
  const globalK = clampMultiplier(emcModel?.global)
  const f = mixFactor({ ...entry, on: true }, hero)
  // на уровне, где модель даёт меньше единицы (на странице это 0), опора графика — условная единица: правка ступени там — сами штуки
  if (id === 'Epic Chimera') return (emcChimeraBaseAt(hero) >= 1 ? emcChimeraBaseAt(hero) : ZERO_UNIT) * f * globalK
  const row = computeRow(hero)
  const mean = EMC_FINALS.reduce((sum, k) => sum + row[k], 0) / 4
  return (mean >= 1 ? mean : ZERO_UNIT) * f * globalK
}
