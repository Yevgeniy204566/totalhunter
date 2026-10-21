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
