// Квота Epic Monster Chests (EMC) по уровню Героя — базовая модель + множители-рычаги.
// База — ELDORADO229, сезон 24.09–08.10.2026 (окно ±10, ×1,19 до полного сезона), зона 360–440
// опирается на реальную выборку; ниже/выше — допущения (см. EXTRAPOLATION_NOTES).
// Порядок расчёта фиксирован: база → множитель уровня → множитель монстра → общий → округление.

// [Герой, [Hydra, Undead, Arachna, Shadow City]] — штук на игрока за полный сезон, без округления.
export const ANCHORS = [
  [100, [1.3387, 0.6115, 0.1818, 0.6446]],
  [300, [5.3550, 2.4461, 0.7272, 2.5783]],
  [360, [5.8939, 4.9218, 2.3317, 3.3925]],
  [370, [7.7769, 5.7009, 2.8238, 3.9277]],
  [380, [13.5991, 8.4854, 3.4793, 4.3868]],
  [390, [18.3756, 9.5011, 3.4793, 4.3868]],
  [400, [19.1058, 9.5011, 3.4793, 4.3868]],
  [410, [19.1058, 9.5011, 3.6762, 4.3868]],
  [420, [19.1058, 9.5011, 4.1359, 4.3868]],
  [430, [19.8703, 9.5011, 4.1359, 4.3868]],
  [440, [20.4639, 10.2472, 4.1359, 4.6939]],
  [600, [25.8965, 13.2318, 6.7623, 5.9224]],
]

export const HERO_LEVELS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)

export const MULTIPLIER_MIN = 0.1
export const MULTIPLIER_MAX = 3

export const DEFAULT_SETTINGS = {
  global: 1,
  monsters: { hydra: 1, undead: 1, arachna: 1, shadow: 1 },
  ranges: [
    { from: 100, to: 299, k: 1 },
    { from: 300, to: 399, k: 1 },
    { from: 400, to: 499, k: 1 },
    { from: 500, to: 600, k: 1 },
  ],
}

// Пустое/нечисловое поле = 1.00 (рычаг не задан), остальное зажимается в 0.1…3.0,
// чтобы опечатка («12» вместо «1.2») не раздула квоту.
export function clampMultiplier(value) {
  if (value === '' || value == null) return 1
  const n = Number(value)
  if (!Number.isFinite(n)) return 1
  return Math.min(MULTIPLIER_MAX, Math.max(MULTIPLIER_MIN, n))
}

export function baseAt(hero) {
  const lv = Math.min(600, Math.max(100, hero))
  for (let i = 0; i < ANCHORS.length - 1; i++) {
    const [x0, v0] = ANCHORS[i]
    const [x1, v1] = ANCHORS[i + 1]
    if (lv >= x0 && lv <= x1) {
      const t = (lv - x0) / (x1 - x0)
      return v0.map((a, k) => a + (v1[k] - a) * t)
    }
  }
  return ANCHORS[ANCHORS.length - 1][1].slice()
}

function levelMultiplier(hero, ranges) {
  const r = (ranges || []).find(x => hero >= Number(x.from) && hero <= Number(x.to))
  return r ? clampMultiplier(r.k) : 1
}

// Округление .5 вверх; 1e-9 гасит «3.4999999» от плавающей точки.
const round = x => Math.floor(x + 0.5 + 1e-9)

export function computeRow(hero, settings = DEFAULT_SETTINGS) {
  const base = baseAt(hero)
  const levelK = levelMultiplier(hero, settings.ranges)
  const m = settings.monsters || {}
  const monsterK = [m.hydra, m.undead, m.arachna, m.shadow].map(clampMultiplier)
  const globalK = clampMultiplier(settings.global)
  const fin = base.map((b, k) => round(b * levelK * monsterK[k] * globalK))
  return {
    hero,
    base,
    levelK,
    monsterK,
    globalK,
    finalH: fin[0], finalU: fin[1], finalA: fin[2], finalS: fin[3],
    emc: fin[0] + fin[1] + fin[2] + fin[3],
  }
}

export function computeTable(settings = DEFAULT_SETTINGS) {
  return HERO_LEVELS.map(h => computeRow(h, settings))
}

export const EXTRAPOLATION_NOTES = {
  ru: [
    '360–440 — реальная выборка ELDORADO229 (окно ±10, ×1,19 до полного сезона, сглажено и не убывает).',
    '300–360 — линейно к точке 300: среднее 18 игроков с Героем 290–359.',
    '100–300 — допущение: линейно вниз до 25% значения на 300 (данных ниже 270 нет).',
    '440–600 — допущение: продолжение с наклоном верхней зоны 400→440 (игроков с Героем выше 456 в выборке нет).',
  ],
  en: [
    '360–440 — real ELDORADO229 sample (±10 window, ×1.19 to a full season, smoothed, non-decreasing).',
    '300–360 — linear to the 300 point: average of 18 players with Hero 290–359.',
    '100–300 — assumption: linear down to 25% of the value at 300 (no data below 270).',
    '440–600 — assumption: continue with the slope of the 400→440 zone (no players above Hero 456 in the sample).',
  ],
}
