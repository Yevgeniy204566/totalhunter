// Цвет полосы прогресса (владелец 2026-10-27): на 1% — фиолетовый, к 99% плавно синий, на 100% и выше — зелёный.
// Раньше оттенок шёл от фиолетового через бирюзовый к зелёному и «зеленел» уже к 80–90%.
export const BAR_DONE = '#287A50'
const HUE_VIOLET = 260
const HUE_BLUE = 220

// доля пути фиолетовый → синий: 1% — 0, 99% — 1 (ниже 1% и мусор считаются как 1%)
function pathK(pct) {
  const n = Number(pct)
  if (!Number.isFinite(n)) return 0
  return Math.min(Math.max((n - 1) / 98, 0), 1)
}

// Заливка полосы (BarCell): HSL от тёмно-фиолетового к насыщенному синему; 100% и выше — зелёный
export function barFillColor(pct) {
  if (Number(pct) >= 100) return BAR_DONE
  const k = pathK(pct)
  return `hsl(${Math.round(HUE_VIOLET - k * (HUE_VIOLET - HUE_BLUE))} ${Math.round(45 + k * 6)}% ${Math.round(40 - k * 8)}%)`
}

// Тихая заливка ячейки целиком (ProgressCell): тот же закон, но приглушённо, чтобы не перебивать цифры
export function barColor(pct) {
  if (Number(pct) >= 100) return 'hsl(150 28% 16%)'
  const k = pathK(pct)
  return `hsl(${Math.round(HUE_VIOLET - k * (HUE_VIOLET - HUE_BLUE))} ${Math.round(18 + k * 10)}% ${Math.round(12 + k * 4)}%)`
}
