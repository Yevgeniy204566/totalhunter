// Правка очков за сундук по уровням Героя «кривой» (владелец 2026-10-26): тянешь точку, соседние идут плавно.
// Хранение прежнее — поправки ступеней Героя mix.w[тип].bands; график показывает и пишет только очки.
import { weightAt, weightBase, fallbackWeight, fallbackBase, fallbackDefault, DEFAULT_SETTINGS } from './heroQuota.js'
import { MULTIPLIER_MIN, MULTIPLIER_MAX, clampMultiplier } from './emcQuota.js'

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

// Ряды для графика по трём функциям уровня Героя: cur — что показывается сейчас (округлено), base — по умолчанию,
// ref — точное значение без поправки ступени этой линии (опора для пересчёта). bands — её поправки ступеней сейчас.
export function makeSeries({ cur, base, ref }, bands = {}) {
  const out = { cur: [], base: [], ref: [], cont: [], locked: new Set(), bands }
  BANDS.forEach(band => {
    const h = centerOf(band)
    out.cur.push(cur(h))
    out.base.push(base(h))
    const r = ref(h) || 0
    out.ref.push(r)
    // точные значения без округления: правка стартует от них, поэтому «вверх и обратно» возвращает исходное без следа
    out.cont.push(r * clampMultiplier(bands[String(band)]))
    if (!(r > 0)) out.locked.add(band)
  })
  return out
}

// Очки за сундук (режим «Очки»)
export function seriesOf(key, scale) {
  return makeSeries({
    cur: h => weightAt(key, h, scale) ?? 0,
    base: h => weightAt(key, h, DEFAULT_SETTINGS) ?? 0,
    ref: h => weightBase(key, h, scale) ?? 0,
  }, scale.mix?.w?.[key]?.bands || {})
}

// Тип вне шкалы (Pumpkin, свои события): очки клана с той же формой по Героям, что у монстров шкалы; m = { id, slot, points }
export function fallbackSeriesOf(m, scale) {
  return makeSeries({
    cur: h => fallbackWeight(m, h, scale),
    base: h => fallbackDefault(m, h),
    ref: h => fallbackBase(m, h, scale),
  }, scale.mix?.w?.[m.id]?.bands || {})
}

// Ступени Героя из желаемых очков: поправка = желаемое / расчётное. Трогаем только ступени, где очки изменились
// (changed[i]); близкое к шкале значение стирается, чтобы в данных не копился шум.
export function bandsFromTargets(target, ref, existing = {}, changed = null) {
  const out = { ...existing }
  BANDS.forEach((band, i) => {
    if (changed && !changed[i]) return
    if (!(ref[i] > 0)) return
    const ratio = target[i] / ref[i]
    // отличие меньше полуочка (штуки) на странице не видно и не нужно; порог абсолютный и симметричный, поэтому «вверх и обратно»
    // возвращает шкалу без следа и при больших значениях шаг 1 всё равно двигает ступень. Шесть знаков — чтобы округление
    // хранимой поправки не сдвигало порог при возврате
    if (Math.abs(target[i] - ref[i]) < 0.5) delete out[String(band)]
    else out[String(band)] = Math.round(Math.min(MULTIPLIER_MAX, Math.max(MULTIPLIER_MIN, ratio)) * 1e6) / 1e6
  })
  // если ни на одной ступени значение на странице не отличается от шкалы — в данных не должно оставаться ничего
  const visible = BANDS.some((band, i) => ref[i] > 0 && out[String(band)] != null
    && Math.round(ref[i] * clampMultiplier(out[String(band)])) !== Math.round(ref[i]))
  return visible ? out : {}
}
