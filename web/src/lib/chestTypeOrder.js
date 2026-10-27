// Порядок столбцов типов сундуков на публичной странице (владелец 2026-10-27):
//  1) эпические склепы — 35 / 30 / 25 / 20 / 15 (только те, что бьют игроки);
//  2) монстры EMC (эпические монстры и свои события квоты EMC) — по очкам клана от большего к меньшему;
//  3) остальные сундуки по типам от старшего к младшему: типы — по лучшему сундуку (очки клана), внутри типа — уровни по
//     убыванию (цитадели 30/25, обычный склеп 25/20); Cursed и Elven цитадели — один тип;
//  4) всё нестандартное (без уровня) — в конце.
// Без метаданных типов (старый архив) порядок сервера не меняем: имена столбцов там локализованы, id неизвестны.
import { weightAt } from './heroQuota.js'

const levelOf = id => { const m = /(\d+)\s*$/.exec(String(id || '')); return m ? Number(m[1]) : null }
const familyOf = id => String(id || '').replace(/\s*\d+\s*$/, '').replace(/^(Cursed|Elven) Citadel$/, 'Citadel')

export function orderChestTypes(chestTypes, meta) {
  if (!meta) return chestTypes
  const info = chestTypes.map((name, i) => {
    const m = meta[name]
    const id = m?.id ?? name
    const lvl = levelOf(id)
    const epicCrypt = /^Epic Crypt\s+\d+$/.test(id)
    const emc = !epicCrypt && (m?.slot === 2 || /^Epic /.test(id) || id === 'Dark Omens Chest' || id === 'Yogwai')
    // очки для порядка: таблица T9 (если тип в ней есть), иначе очки клана; у ELDORADO очки клана за монстров EMC — заглушки
    const points = Math.max(weightAt(id, 450) ?? 0, m?.points || 0)
    return { name, i, id, lvl, points, epicCrypt, emc, family: familyOf(id) }
  })
  const epic = info.filter(x => x.epicCrypt).sort((a, b) => b.lvl - a.lvl || a.i - b.i)
  const emc = info.filter(x => x.emc).sort((a, b) => b.points - a.points || a.i - b.i)
  const rest = info.filter(x => !x.epicCrypt && !x.emc)
  const leveled = rest.filter(x => x.lvl != null)
  const bestOf = new Map()
  for (const x of leveled) bestOf.set(x.family, Math.max(bestOf.get(x.family) ?? -1, x.points))
  leveled.sort((a, b) => (bestOf.get(b.family) - bestOf.get(a.family)) || a.family.localeCompare(b.family)
    || b.lvl - a.lvl || a.id.localeCompare(b.id))
  const other = rest.filter(x => x.lvl == null).sort((a, b) => b.points - a.points || a.i - b.i)
  return [...epic, ...emc, ...leveled, ...other].map(x => x.name)
}
