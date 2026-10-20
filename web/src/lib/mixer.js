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
