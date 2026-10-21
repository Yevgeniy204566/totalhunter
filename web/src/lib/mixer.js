// Фейдер пульта: положение 0…1000 ⇄ множитель. Середина 500 = ×1, вверх до ×3, вниз до ×0.1;
// ход по логарифму, чтобы вверх и вниз был одинаково удобен. Рядом с серединой (±8 из 1000) прилипает к ×1.
export const MIXER_MIN = 0.1
export const MIXER_MAX = 3

export function posToK(pos) {
  if (Math.abs(pos - 500) <= 8) return 1
  const t = (pos - 500) / 500
  const k = t >= 0 ? MIXER_MAX ** t : MIXER_MIN ** -t
  return Math.round(k * 100) / 100
}

export function kToPos(k) {
  const v = Math.min(MIXER_MAX, Math.max(MIXER_MIN, k))
  return Math.round(500 + (v >= 1
    ? (Math.log(v) / Math.log(MIXER_MAX)) * 500
    : -(Math.log(v) / Math.log(MIXER_MIN)) * 500))
}

// Множитель, при котором округлённый результат calc(k) равен вписанному числу. Делить число на calc(1)
// нельзя: calc(1) уже округлено, и при дробной базе (0,6 → 1) промах огромен (вписали 20 — вышло 17).
// calc не убывает по k, поэтому ищем бисекцией по логарифму; при достижимом числе берём середину площадки
// k, на которой результат равен ему (устойчиво к округлению), иначе — ближайшую границу.
export function solveK(calc, want, kMin, kMax) {
  if (calc(kMax) < want) return kMax
  if (calc(kMin) >= want) return kMin
  if (calc(1) === want) return 1 // уже совпадает со шкалой — оставляем честное ×1
  const bisect = ok => {
    let lo = kMin, hi = kMax
    for (let i = 0; i < 60; i++) {
      const mid = Math.sqrt(lo * hi)
      if (ok(mid)) hi = mid; else lo = mid
    }
    return hi
  }
  const first = bisect(k => calc(k) >= want)
  if (calc(first) !== want) return first
  const last = bisect(k => calc(k) > want)
  return Math.round(Math.sqrt(first * last) * 1e6) / 1e6
}

// Загрузка пресета клана (T5–T9 из «Сундуков») в пульт: пресет хранит очки за сундук, пульт — множители от
// шкалы, поэтому для каждого типа клана, который есть в пресете, подбираем множитель, при котором очки при
// выбранном Герое равны пресетным. Остальные типы не трогаем; типы пресета, которых нет в «Учёте» клана, пропускаем.
// calcFor(x) → k ⇒ очки; withK(entry, k) → запись mix.w с учётом выбора ступеней Героя.
export function presetMixW(items, types, w, { calcFor, withK, keyOf }) {
  const next = { ...(w || {}) }
  for (const item of items || []) {
    const key = keyOf(item.catalog_id)
    const x = types.find(t => t.key === key)
    if (!x || !(item.points > 0)) continue
    const calc = calcFor(x)
    if (!(calc(1000) > 0)) continue // при этом Герое шкала даёт 0 (тип не засчитывается) — множителем не поправить
    const k = solveK(calc, item.points, 0.01, 1000)
    next[key] = { ...withK(next[key], k), on: true }
  }
  return next
}
