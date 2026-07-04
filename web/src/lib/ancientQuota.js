export function rowShortfallClass(shortfallPct, thresholds) {
  if (shortfallPct == null || !thresholds) return ''
  if (shortfallPct <= thresholds.light_pct) return ''
  if (shortfallPct <= thresholds.medium_pct) return 'row-quota-light'
  if (shortfallPct <= thresholds.critical_pct) return 'row-lagging'
  return 'row-danger'
}
