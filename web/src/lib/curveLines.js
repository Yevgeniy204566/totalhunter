// Линии графика пульта по режимам (владелец 2026-10-26): «Очки» — очки за сундук по уровням Героя; «Количество» —
// штуки на игрока по уровням Героя (эпик-склепы, монстры EMC). Хранение прежнее:
//   очки — mix.w[тип].bands; штуки склепов и прочих монстров — mix.c[тип].bands; четыре монстра с историей — emc.cells[монстр].
// Типы, у которых нет базового числа по уровням (Rare/Citadel/Common со вписанным числом), на графике количества не показываются.
import { makeSeries, seriesOf } from './curveEdit.js'
import { DEFAULT_SETTINGS, countRaw, countAt, emcCountAt, emcOtherRaw, EPIC_CRYPTS, EMC_FOUR } from './heroQuota.js'
import { computeRow, DEFAULT_SETTINGS as EMC_DEFAULTS } from './emcQuota.js'

const MONSTER_BY_ID = { 'Epic Fire Hydra': 'hydra', 'Epic Undead': 'undead', 'Epic Arachne': 'arachna', 'Epic Shadow City': 'shadow' }
const FINAL_BY_ID = { 'Epic Fire Hydra': 'finalH', 'Epic Undead': 'finalU', 'Epic Arachne': 'finalA', 'Epic Shadow City': 'finalS' }
const RAW_INDEX = { 'Epic Fire Hydra': 0, 'Epic Undead': 1, 'Epic Arachne': 2, 'Epic Shadow City': 3 }

// без своей поправки ступеней: ref считается от записи типа с пустыми bands
const withoutBands = (scale, key) => ({ ...scale, mix: { ...scale.mix, c: { ...(scale.mix?.c || {}), [key]: { ...(scale.mix?.c?.[key] || {}), bands: {} } } } })

export function pointsLines(list, scale) {
  return list
    .map(x => ({ key: x.key, title: x.title, unit: 'points', target: { path: 'w', key: x.key }, muted: scale.mix?.w?.[x.key]?.on === false, ...seriesOf(x.key, scale) }))
    .filter(x => x.ref.some(r => r > 0) || x.base.some(b => b > 0))
}

export function countLines(tab, list, scale, emc) {
  const mix = scale.mix || {}
  const out = []
  list.forEach(x => {
    const key = x.key
    const entry = mix.c?.[key]
    if (entry?.set != null) return // число вписано вручную — по уровням Героя не меняется
    const muted = entry?.on === false
    if (tab === 'crypts') {
      if (!EPIC_CRYPTS.includes(key)) return
      const s2 = withoutBands(scale, key)
      out.push({ key, title: x.title, unit: 'count', target: { path: 'c', key }, muted,
        ...makeSeries({ cur: h => countAt(key, h, scale), base: h => countAt(key, h, DEFAULT_SETTINGS),
          ref: h => countRaw(key, h, s2) }, entry?.bands || {}) })
      return
    }
    if (key in EMC_FOUR) {
      const mk = MONSTER_BY_ID[key]
      const noCell = { ...emc, cells: { ...(emc.cells || {}), [mk]: {} } }
      out.push({ key, title: x.title, unit: 'count', target: { path: 'cell', key: mk }, muted: (emc.off || []).includes(mk),
        ...makeSeries({ cur: h => computeRow(h, emc)[FINAL_BY_ID[key]], base: h => computeRow(h, EMC_DEFAULTS)[FINAL_BY_ID[key]],
          ref: h => computeRow(h, noCell).raw[RAW_INDEX[key]] }, emc.cells?.[mk] || {}) })
      return
    }
    const s2 = withoutBands(scale, key)
    out.push({ key, title: x.title, unit: 'count', target: { path: 'c', key }, muted,
      ...makeSeries({ cur: h => emcCountAt(key, h, scale, emc), base: h => emcCountAt(key, h, DEFAULT_SETTINGS, EMC_DEFAULTS),
        ref: h => emcOtherRaw(key, h, s2, emc) }, entry?.bands || {}) })
  })
  return out.filter(x => x.ref.some(r => r > 0) || x.base.some(b => b > 0))
}

// Записывает поправки ступеней линии в данные пульта (mix / emc) и возвращает новые копии.
export function writeBands({ mix, emc }, target, bands) {
  if (target.path === 'cell') return { mix, emc: { ...emc, cells: { ...(emc.cells || {}), [target.key]: bands } } }
  const grp = target.path
  return { mix: { ...mix, [grp]: { ...(mix[grp] || {}), [target.key]: { ...(mix[grp]?.[target.key] || {}), bands } } }, emc }
}
