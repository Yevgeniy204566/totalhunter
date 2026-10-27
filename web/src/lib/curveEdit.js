// Правка очков за сундук по уровням Героя «кривой» (владелец 2026-10-26): тянешь точку, соседние идут плавно.
// Хранение прежнее — поправки ступеней Героя mix.w[тип].bands; график показывает и пишет только очки.
import { weightAt, weightBase, scaleBaseAt, fallbackWeight, fallbackBase, fallbackDefault, DEFAULT_SETTINGS } from './heroQuota.js'
import { MULTIPLIER_MAX, clampMultiplier, bandMultiplier, levelEntry } from './emcQuota.js'

export const BANDS = Array.from({ length: 51 }, (_, i) => 100 + i * 10)
// ручки — через каждые 50 уровней: 100, 150 … 600
export const HANDLE_BANDS = BANDS.filter(b => (b - 100) % 50 === 0)
// очки ступени считаем по её середине (ступень 400 — Герой 405); последняя ступень — 600
export const centerOf = band => (band >= 600 ? 600 : band + 5)

// Точки графика (владелец 2026-10-28: приближение до одного уровня). Обзор — по ступени на точку (ключ «400», уровень по середине),
// приближение — по уровню на точку (ключ «L405», ровно Герой 405). pos — положение точки по оси Героя, key — ключ в данных.
export const DECADE_PTS = BANDS.map(b => ({ key: String(b), pos: b, h: centerOf(b) }))
export const levelPts = (lo, hi) => Array.from({ length: hi - lo + 1 }, (_, i) => ({ key: `L${lo + i}`, pos: lo + i, h: lo + i }))

// Колокол влияния на соседей: softness 0 — только сама ступень, 100 — широкая волна (σ = 150 уровней).
export function kernel(dist, softness) {
  if (!(softness > 0)) return dist === 0 ? 1 : 0
  const sigma = softness * 1.5
  if (dist > 3 * sigma) return 0
  return Math.exp(-0.5 * (dist / sigma) ** 2)
}

// Новые очки по всем ступеням, когда ручку на ступени handleBand сдвинули на delta очков.
// start — очки в момент нажатия (не накапливаем ошибку на каждом движении); locked — ступени, где в шкале 0 и поднять нельзя.
export function applyDrag(start, handleBand, delta, softness, locked = new Set(), pts = DECADE_PTS) {
  return pts.map((pt, i) => {
    if (locked.has(pt.pos)) return start[i]
    return Math.max(0, start[i] + delta * kernel(Math.abs(pt.pos - handleBand), softness))
  })
}

// Ряды для графика по функциям уровня Героя: cur — что показывается сейчас (округлено), base — по умолчанию,
// ref — точное значение без поправки ступени этой линии (опора для пересчёта), zero(h) — шкала на этом уровне даёт 0.
// bands — её поправки ступеней сейчас. На нулевом уровне шкалы поправка — сами очки (штуки): опора там — условная единица,
// правка стартует с 0, а «значение шкалы» для магнита и возврата — 0 (полная свобода правки, владелец 2026-10-27).
export function makeSeries({ cur, base, ref, zero }, bands = {}, pts = DECADE_PTS) {
  // curAt/baseAt — значение на любом уровне Героя (график рисует каждый уровень, а не середины ступеней: те же функции читают пульт и страница);
  // rebuild — те же функции на другом наборе точек (приближение до одного уровня)
  const out = { cur: [], base: [], ref: [], cont: [], scaleV: [], zero: [], locked: new Set(), bands, pts, curAt: cur, baseAt: base,
    rebuild: p => makeSeries({ cur, base, ref, zero }, bands, p) }
  pts.forEach(pt => {
    const h = pt.h
    out.cur.push(cur(h))
    out.base.push(base(h))
    const r = ref(h) || 0
    const z = zero ? !!zero(h) : false
    const own = levelEntry(bands, h) // та же поправка, что читают пульт и страница: уровень сильнее ступени
    out.ref.push(r)
    out.zero.push(z)
    out.scaleV.push(z ? 0 : r)
    // точные значения без округления: правка стартует от них, поэтому «вверх и обратно» возвращает исходное без следа
    out.cont.push(z && own == null ? 0 : r * bandMultiplier(own))
    if (!(r > 0)) out.locked.add(pt.pos)
  })
  return out
}

// Очки за сундук (режим «Очки»)
export function seriesOf(key, scale) {
  return makeSeries({
    cur: h => weightAt(key, h, scale) ?? 0,
    base: h => weightAt(key, h, DEFAULT_SETTINGS) ?? 0,
    ref: h => weightBase(key, h, scale) ?? 0,
    zero: h => scaleBaseAt(key, h) === 0,
  }, scale.mix?.w?.[key]?.bands || {})
}

// Тип вне шкалы (Pumpkin, свои события): очки клана с той же формой по Героям, что у монстров шкалы; m = { id, slot, points }
export function fallbackSeriesOf(m, scale) {
  return makeSeries({
    cur: h => fallbackWeight(m, h, scale),
    base: h => fallbackDefault(m, h),
    ref: h => fallbackBase(m, h, scale),
    zero: () => !((m?.points || 0) > 0),
  }, scale.mix?.w?.[m.id]?.bands || {})
}

// Ступени Героя из желаемых очков: поправка = желаемое / расчётное. Трогаем только ступени, где очки изменились
// (changed[i]); близкое к шкале значение стирается, чтобы в данных не копился шум.
// Правка ступени «за границей» (множитель вне MULTIPLIER_MIN…MAX) — такое значение вписать нельзя. Проверка отдельно, чтобы
// интерфейс отказал в правке и сказал почему (владелец 2026-10-27: ничего не обрезать молча).
export function bandsOutOfRange(target, ref, changed = null, zero = null) {
  return target.some((_, i) => {
    if (changed && !changed[i]) return false
    if (!(ref[i] > 0)) return false
    const scale = zero?.[i] ? 0 : ref[i]
    if (Math.abs(target[i] - scale) < 0.5) return false // возврат к шкале — не правка
    const k = target[i] / ref[i]
    return !(k >= 0 && k <= MULTIPLIER_MAX)
  })
}

export function bandsFromTargets(target, ref, existing = {}, changed = null, zero = null, pts = DECADE_PTS) {
  const out = { ...existing }
  const scaleAt = i => (zero?.[i] ? 0 : ref[i]) // значение шкалы на ступени: на нулевом уровне — 0, а не опора
  pts.forEach((pt, i) => {
    const key = pt.key
    if (changed && !changed[i]) return
    if (!(ref[i] > 0)) return
    // правка ступени целиком отменяет поправки отдельных уровней внутри неё, иначе они молча перекрыли бы новое значение
    if (!key.startsWith('L')) for (let h = pt.pos; h < pt.pos + 10; h++) delete out[`L${h}`]
    const ratio = target[i] / ref[i]
    // отличие меньше полуочка (штуки) на странице не видно и не нужно; порог абсолютный и симметричный, поэтому «вверх и обратно»
    // возвращает шкалу без следа и при больших значениях шаг 1 всё равно двигает ступень. Шесть знаков — чтобы округление
    // хранимой поправки не сдвигало порог при возврате
    if (Math.abs(target[i] - scaleAt(i)) < 0.5) delete out[key]
    // за границей множителя ступень не трогаем (прежняя поправка остаётся): значение не подтягивается к границе молча
    else if (ratio >= 0 && ratio <= MULTIPLIER_MAX) out[key] = Math.round(ratio * 1e6) / 1e6
  })
  // если ни на одной ступени значение на странице не отличается от шкалы — в данных не должно оставаться ничего
  // (уровни вне окна приближения проверить здесь нельзя, поэтому пустым результат считаем, только если в данных вообще ничего не осталось)
  if (!Object.keys(out).length) return {}
  if (pts !== DECADE_PTS) return out
  const visible = pts.some((pt, i) => ref[i] > 0 && out[pt.key] != null
    && Math.round(ref[i] * bandMultiplier(out[pt.key])) !== Math.round(scaleAt(i)))
  return visible || Object.keys(out).some(k => k.startsWith('L')) ? out : {}
}
