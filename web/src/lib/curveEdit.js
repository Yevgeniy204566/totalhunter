// Правка очков за сундук по уровням Героя «кривой» (владелец 2026-10-26): тянешь точку, соседние идут плавно.
// Хранение прежнее — поправки ступеней Героя mix.w[тип].bands; график показывает и пишет только очки.
import { weightAt, weightBase, DEFAULT_SETTINGS } from './heroQuota.js'
import { MULTIPLIER_MIN, MULTIPLIER_MAX } from './emcQuota.js'

export const BANDS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)
// ручки — через каждые 50 уровней: 100, 150 … 600
export const HANDLE_BANDS = BANDS.filter(b => (b - 100) % 50 === 0)
// очки ступени считаем по её середине (ступень 400 — Герой 405); последняя ступень — 600
export const centerOf = band => (band >= 600 ? 600 : band + 5)

// Колокол влияния на соседей: softness 0 — только сама ступень, 100 — широкая волна (σ = 150 уровней).
export function kernel(dist, softness) {
  if (!(softness > 0)) return dist === 0 ? 1 : 0
  const sigma = softness * 1.5
  if (dist > 3 * sigma) return 0
  return Math.exp(-0.5 * (dist / sigma) ** 2)
}

// Новые очки по всем ступеням, когда ручку на ступени handleBand сдвинули на delta очков.
// start — очки в момент нажатия (не накапливаем ошибку на каждом движении); locked — ступени, где в шкале 0 и поднять нельзя.
export function applyDrag(start, handleBand, delta, softness, locked = new Set()) {
  return BANDS.map((band, i) => {
    if (locked.has(band)) return start[i]
    return Math.max(0, start[i] + delta * kernel(Math.abs(band - handleBand), softness))
  })
}

// Ряды для графика: текущие очки, очки по шкале (пунктир), опора для пересчёта и «закрытые» ступени.
export function seriesOf(key, scale) {
  const cur = [], base = [], ref = []
  const locked = new Set()
  BANDS.forEach(band => {
    const h = centerOf(band)
    cur.push(weightAt(key, h, scale) ?? 0)
    base.push(weightAt(key, h, DEFAULT_SETTINGS) ?? 0)
    const r = weightBase(key, h, scale) ?? 0
    ref.push(r)
    if (!(r > 0)) locked.add(band)
  })
  return { cur, base, ref, locked }
}

// Ступени Героя из желаемых очков: поправка = желаемое / расчётное. Трогаем только ступени, где очки изменились
// (changed[i]); близкое к шкале значение стирается, чтобы в данных не копился шум.
export function bandsFromTargets(target, ref, existing = {}, changed = null) {
  const out = { ...existing }
  BANDS.forEach((band, i) => {
    if (changed && !changed[i]) return
    if (!(ref[i] > 0)) return
    const k = Math.min(MULTIPLIER_MAX, Math.max(MULTIPLIER_MIN, target[i] / ref[i]))
    // очки кратны 5: если на странице получится то же, что и по шкале, поправка не нужна
    if (Math.round(target[i] / 5) === Math.round(ref[i] / 5)) delete out[String(band)]
    else out[String(band)] = Math.round(k * 10000) / 10000
  })
  return out
}
