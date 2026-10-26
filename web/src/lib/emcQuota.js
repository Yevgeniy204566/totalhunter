// Квота Epic Monster Chests (EMC) по уровню Героя — модель на реальных данных двух кланов + множители-рычаги пульта.
// Порядок расчёта фиксирован: база → множитель уровня → множитель монстра → общий → округление.

// Квота EMC — все эпические монстры вместе, штук на игрока за 2 недели. Опоры — реальные данные двух кланов
// (владелец 2026-10-23, итоговый столбец EMC в истории сезона = сумма всех эпик-монстров):
//  • ELDORADO, сезон 24.09–08.10: 121 игрок, 5518 монстров → 45,6 на игрока, средний Герой 383; доли монстров:
//    Hydra 1532, Undead 547, Arachna 239, Shadow City 311, Chimera 2889 (Chimera — больше половины);
//  • Берсерки (Герой в среднем 450): сумма трёх колонок замера у 95 игроков = 20413 → 214,9 на игрока.
// Внутри ELDORADO EMC растёт с Героем так же, как норма в очках (×1.10 на 10 уровней), поэтому EMC = норма × доля,
// где доля EMC в норме: ниже ELDORADO — как у ELDORADO, между ELDORADO и Берсерками плавно (в логарифме) растёт
// до доли Берсерков, выше — как у Берсерков. Без искусственных обрезаний хвостов.
import { normBase, B as HERO_BERSERK } from './normCurve.js'

const ELDO = { hero: 383, players: 121, total: 5518, split: { hydra: 1532, undead: 547, arachna: 239, shadow: 311, chimera: 2889 } }
const BERS = { hero: HERO_BERSERK, players: 95, total: 20413 }

const shareEldo = (ELDO.total / ELDO.players) / normBase(ELDO.hero)
const shareBers = (BERS.total / BERS.players) / normBase(BERS.hero)

// Переход доли от ELDORADO к Берсеркам идёт по smoothstep в логарифме: значения в обеих опорах те же (ELDORADO 45,6 на
// Герое 383, Берсерки 214,9 на 450), но без изломов на 383 и 450 — касательная плавно выходит из полки и входит в неё
// (владелец 2026-10-24: сглаживать общей кривой, опоры не менять). Один закон на все кланы.
const smoothstep = t => t * t * (3 - 2 * t)
function emcShare(hero) {
  if (hero <= ELDO.hero) return shareEldo
  if (hero >= BERS.hero) return shareBers
  const t = smoothstep((hero - ELDO.hero) / (BERS.hero - ELDO.hero))
  return Math.exp(Math.log(shareEldo) + (Math.log(shareBers) - Math.log(shareEldo)) * t)
}

// Слабые Герои не бьют эпических монстров вовсе (владелец 2026-10-23: у Сарацинов и Старта мощи не хватает) — ниже этого
// уровня EMC равен 0.
export const EMC_MIN_HERO = 200

// Все эпик-монстры вместе (до округления)
export const emcTotalAt = hero => (hero < EMC_MIN_HERO ? 0 : emcShare(hero) * normBase(hero))

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

// Ступень Героя 100…600 с шагом 10 (в пульте — «Герой 310–319»); ключ ступени — её начало.
export const bandKey = hero => String(Math.min(600, Math.max(100, Math.floor(hero / 10) * 10)))

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
  const cellK = MONSTER_KEYS.map(key => clampMultiplier(settings.cells?.[key]?.[band]))
  const off = settings.off || []
  const raw = base.map((b, k) => (off.includes(MONSTER_KEYS[k]) ? 0 : b * levelK * monsterK[k] * cellK[k] * globalK))
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
    'Опора 1 — ELDORADO, сезон 24.09–08.10: столбец EMC в истории (все эпик-монстры вместе) в среднем 45,6 на игрока при Герое 383; внутри клана EMC растёт с Героем так же, как норма очков.',
    'Опора 2 — Берсерки (Герой в среднем 450): 214,9 на игрока — сумма трёх колонок замера.',
    'EMC = норма × доля. Ниже Героя 383 доля как у ELDORADO, между 383 и 450 доля плавно растёт до доли Берсерков, выше 450 — как у Берсерков. Округление до целого, меньше 1 — 0. Ниже Героя 200 эпических монстров не бьют — EMC 0.',
    'Деление по монстрам — по долям ELDORADO (Chimera 52%, Hydra 28%, Undead 10%, Shadow City 6%, Arachna 4%): у Берсерков монстры в замере не названы.',
  ],
  en: [
    'Anchor 1 — ELDORADO, season 24.09–08.10: the EMC column of the history (all epic monsters together) averages 45.6 per player at Hero 383; inside the clan EMC grows with Hero like the points norm.',
    'Anchor 2 — Berserki (average Hero 450): 214.9 per player, the sum of the three sample columns.',
    'EMC = norm × share. Below Hero 383 the share is ELDORADO\'s, between 383 and 450 it grows smoothly to the Berserki share, above 450 it stays as Berserki\'s. Rounded to an integer, below 1 is 0. Below Hero 200 epic monsters are not killed at all, EMC is 0.',
    'Split by monster follows ELDORADO shares (Chimera 52%, Hydra 28%, Undead 10%, Shadow City 6%, Arachna 4%): Berserki monsters are not named in the sample.',
  ],
}
