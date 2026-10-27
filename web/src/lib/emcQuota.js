// Квота Epic Monster Chests (EMC) по уровню Героя — модель на реальных данных двух кланов + множители-рычаги пульта.
// Порядок расчёта фиксирован: база → множитель уровня → множитель монстра → общий → округление.

// Квота EMC — все эпические монстры вместе, штук на игрока за 2 недели. Опоры — реальные данные двух кланов
// (владелец 2026-10-23, итоговый столбец EMC в истории сезона = сумма всех эпик-монстров):
//  • ELDORADO, сезон 24.09–08.10: 121 игрок, 5518 монстров → 45,6 на игрока, средний Герой 383; доли монстров:
//    Hydra 1532, Undead 547, Arachna 239, Shadow City 311, Chimera 2889 (Chimera — больше половины);
//  • Берсерки (Герой в среднем 450): сумма трёх колонок замера у 95 игроков = 20413 → 214,9 на игрока.
// Модель по стилю свободной игры ELDORADO (владелец 2026-10-27). Берсерков берём не как опору, а вдвое меньше замера — они играют
// круглосуточно. Растёт НОРМА (штуки), а не цена монстра: очки за штуку заданы таблицей T9 и от Героя выше 387,5 не зависят.
// Опоры (штук всех эпик-монстров на игрока за 2 недели):
//  • Герой 300 — 5,5 (минимум: эпического монстра на слабом Герое почти не выбить; по монстрам это ровно 5);
//  • ELDORADO 383 — 45,6 (121 игрок, 5518 монстров за сезон 24.09–08.10);
//  • Герой 450 — 100 (Берсерки: замер 214,9 вдвое меньше).
// Рост штук = рост нормы Crypts + добавка, которая затухает с Героем: быстрый старт на 300 и плавный выход к темпу нормы.
//   ln n(h) = ln n(300) + [ln норма(h) − ln норма(300)] + A·L·(1 − e^{−(h−300)/L}); A и L подобраны так, чтобы попасть в 383 и 450.
import { normBase } from './normCurve.js'

const ELDO = { hero: 383, players: 121, total: 5518, split: { hydra: 1532, undead: 547, arachna: 239, shadow: 311, chimera: 2889 } }
const A_ANCHOR = { hero: 300, count: 5.5 }
const B_ANCHOR = { hero: ELDO.hero, count: ELDO.total / ELDO.players }
const C_ANCHOR = { hero: 450, count: 100 }

const lnNormRel = h => Math.log(normBase(h) / normBase(A_ANCHOR.hero))
const lnExtra = (h, amp, len) => amp * len * (1 - Math.exp(-(h - A_ANCHOR.hero) / len))
const needB = Math.log(B_ANCHOR.count / A_ANCHOR.count) - lnNormRel(B_ANCHOR.hero)
const needC = Math.log(C_ANCHOR.count / A_ANCHOR.count) - lnNormRel(C_ANCHOR.hero)
// длину затухания L находим делением пополам (амплитуда A выводится из опоры 383), поэтому обе опоры попадают точно
const dB = B_ANCHOR.hero - A_ANCHOR.hero
const ampFor = len => needB / (len * (1 - Math.exp(-dB / len)))
let lenLo = 5
let lenHi = 400
for (let i = 0; i < 100; i++) {
  const mid = (lenLo + lenHi) / 2
  if (lnExtra(C_ANCHOR.hero, ampFor(mid), mid) > needC) lenHi = mid
  else lenLo = mid
}
const DECAY_LEN = (lenLo + lenHi) / 2
const DECAY_AMP = ampFor(DECAY_LEN)

const emcCount = hero => A_ANCHOR.count * Math.exp(lnNormRel(hero) + lnExtra(hero, DECAY_AMP, DECAY_LEN))

// Слабые Герои не бьют эпических монстров вовсе (владелец 2026-10-23: у Сарацинов и Старта мощи не хватает) — ниже этого
// уровня EMC равен 0.
export const EMC_MIN_HERO = 200

// Все эпик-монстры вместе (до округления)
export const emcTotalAt = hero => (hero < EMC_MIN_HERO ? 0 : emcCount(hero))

// Деление общего EMC по монстрам — доли ELDORADO (у Берсерков в замере монстры не названы: важно число, не название)
const SPLIT = Object.fromEntries(Object.entries(ELDO.split).map(([k, v]) => [k, v / ELDO.total]))

// База четырёх монстров таблицы пульта [Hydra, Undead, Arachna, Shadow City] и Chimera (до округления)
export function baseAt(hero) {
  const total = emcTotalAt(Math.min(600, Math.max(100, hero)))
  return [SPLIT.hydra, SPLIT.undead, SPLIT.arachna, SPLIT.shadow].map(s => s * total)
}
export const emcChimeraBaseAt = hero => SPLIT.chimera * emcTotalAt(Math.min(600, Math.max(100, hero)))

export const HERO_LEVELS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)

// Границы — защита от нуля и бесконечности: числа в пульте вписываются руками (владелец 2026-10-21),
// поэтому потолок не ×3; фейдер ходит только в 0.1…3 (lib/mixer.js)
export const MULTIPLIER_MIN = 0.01
export const MULTIPLIER_MAX = 1000

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

// Пустое/нечисловое поле = 1.00 (рычаг не задан), остальное зажимается в 0.01…1000,
// чтобы опечатка («12» вместо «1.2») не раздула квоту.
export function clampMultiplier(value) {
  if (value === '' || value == null) return 1
  const n = Number(value)
  if (!Number.isFinite(n)) return 1
  return Math.min(MULTIPLIER_MAX, Math.max(MULTIPLIER_MIN, n))
}

// Множитель ступени Героя (поправка одного уровня): от 0 до 1000. Ноль — на этом уровне ровно 0 (полная свобода правки);
// пусто — нет поправки (×1). В отличие от общих рычагов, к минимуму 0.01 не подтягивается.
export const bandMultiplier = v => {
  if (v === '' || v == null) return 1
  const n = Number(v)
  if (!Number.isFinite(n)) return 1
  return Math.min(MULTIPLIER_MAX, Math.max(0, n))
}

// Ступень Героя 100…600 с шагом 10 (в пульте — «Герой 310–319»); ключ ступени — её начало.
export const bandKey = hero => String(Math.min(600, Math.max(100, Math.floor(hero / 10) * 10)))

// Поправка на один уровень Героя (владелец 2026-10-28: точность вплоть до 1, 2, 3): ключ «L405» — ровно Герой 405.
// Она сильнее поправки ступени («400» = 400–409) и действует только на своём уровне; нет её — читается ступень.
export const levelKey = hero => `L${Math.min(600, Math.max(100, Math.floor(hero)))}`
// Правка ступени целиком (пультом) отменяет поправки отдельных уровней внутри неё — иначе они молча перекрыли бы новое значение.
export const hasLevels = (bands, start) => { for (let h = Number(start); h < Number(start) + 10; h++) if (bands?.[`L${h}`] != null) return true; return false }
export const dropLevels = (bands, starts) => { const out = { ...(bands || {}) }; for (const st of starts) for (let h = Number(st); h < Number(st) + 10; h++) delete out[`L${h}`]; return out }
export const levelEntry = (bands, hero) => bands?.[levelKey(hero)] ?? bands?.[bandKey(hero)]

const MONSTER_KEYS = ['hydra', 'undead', 'arachna', 'shadow']

function levelMultiplier(hero, ranges) {
  const r = (ranges || []).find(x => hero >= Number(x.from) && hero <= Number(x.to))
  return r ? clampMultiplier(r.k) : 1
}

// Округление до целого (.5 вверх; 1e-9 гасит «3.4999999» от плавающей точки); меньше 1 — это 0 (владелец 2026-10-23).
export const round = x => (x < 1 ? 0 : Math.floor(x + 0.5 + 1e-9))

// Chimera — пятый эпик-монстр ELDORADO (в таблице пульта нет фейдера, считается как «прочий» тип со своей базой)
export const emcChimeraAt = (hero, k = 1) => round(emcChimeraBaseAt(hero) * k)

export function computeRow(hero, settings = DEFAULT_SETTINGS) {
  const base = baseAt(hero)
  const levelK = levelMultiplier(hero, settings.ranges)
  const m = settings.monsters || {}
  const monsterK = [m.hydra, m.undead, m.arachna, m.shadow].map(clampMultiplier)
  const globalK = clampMultiplier(settings.global)
  // пульт: множитель монстра на конкретную ступень Героя (cells) и «выкл» (off) — поверх прежних рычагов
  const band = bandKey(hero)
  const cellK = MONSTER_KEYS.map(key => bandMultiplier(levelEntry(settings.cells?.[key], hero)))
  const off = settings.off || []
  // Где модель даёт меньше единицы (слабые Герои, ниже ≈250), множитель бессмыслен: вписанная ступень монстра (cells) — сами штуки, от единицы
  // (полная свобода правки, владелец 2026-10-27). Без вписанной ступени там по-прежнему 0.
  const raw = base.map((b, k) => {
    if (off.includes(MONSTER_KEYS[k])) return 0
    // база ниже 1 на странице всё равно округляется в 0, поэтому вписанная ступень там — сами штуки, а не множитель к дроби
    const b0 = b >= 1 ? b : (settings.cells?.[MONSTER_KEYS[k]]?.[band] != null ? 1 : b)
    return b0 * levelK * monsterK[k] * cellK[k] * globalK
  })
  const fin = raw.map(round)
  return {
    raw,
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

// Подпись строки: ступень N действует на уровни N…N+9 (последняя, 600, — один уровень).
export const heroRangeLabel = hero => (hero >= 600 ? '600' : `${hero}-${hero + 9}`)

// CSV для Excel/Google Таблиц: «;» (русская локаль) и BOM, чтобы кириллица открылась верно.
export function quotaCsv(table, lang = 'ru') {
  const head = [lang === 'ru' ? 'Герой' : 'Hero', 'Hydra', 'Undead', 'Arachna', 'Shadow City', 'EMC']
  const lines = [head.join(';')].concat(table.map(r =>
    [heroRangeLabel(r.hero), r.finalH, r.finalU, r.finalA, r.finalS, r.emc].join(';')))
  return '\uFEFF' + lines.join('\r\n') + '\r\n'
}

export const EXTRAPOLATION_NOTES = {
  ru: [
    'Опора 1 — ELDORADO, сезон 24.09–08.10: столбец EMC в истории (все эпик-монстры вместе) в среднем 45,6 на игрока при Герое 383.',
    'Опора 2 — Берсерки (Герой в среднем 450): замер 214,9 на игрока. Игроки этого клана играют круглосуточно, поэтому в общую шкалу взято вдвое меньше — 100 на Герое 450. Минимум — Герой 300: 5.',
    'Рост штук = рост нормы Crypts плюс затухающая добавка: быстрый старт на слабых Героях и плавный выход к темпу нормы. Растёт норма (штуки), а не цена монстра: очки за штуку заданы таблицей T9 и от Героя не зависят. Округление до целого, меньше 1 — 0. Ниже Героя 200 эпических монстров не бьют — EMC 0.',
    'Деление по монстрам — по долям ELDORADO (Chimera 52%, Hydra 28%, Undead 10%, Shadow City 6%, Arachna 4%): у Берсерков монстры в замере не названы.',
  ],
  en: [
    'Anchor 1 — ELDORADO, season 24.09–08.10: the EMC column of the history (all epic monsters together) averages 45.6 per player at Hero 383.',
    'Anchor 2 — Berserki (average Hero 450): measured 214.9 per player. Players of this clan play around the clock, so the common scale takes half of it — 100 at Hero 450. The minimum is Hero 300: 5.',
    'Counts grow like the Crypts norm plus a fading addition: a fast start on weak Heroes and a smooth approach to the pace of the norm. It is the norm (counts) that grows, not the price of a monster: points per chest come from the T9 table and do not depend on Hero. Rounded to an integer, below 1 is 0. Below Hero 200 epic monsters are not killed at all, EMC is 0.',
    'Split by monster follows ELDORADO shares (Chimera 52%, Hydra 28%, Undead 10%, Shadow City 6%, Arachna 4%): Berserki monsters are not named in the sample.',
  ],
}
