import test from 'node:test'
import assert from 'node:assert/strict'
import { BANDS, centerOf, applyDrag, bandsFromTargets } from './curveEdit.js'
import { pointsLines, countLines, writeBands } from './curveLines.js'
import { DEFAULT_SETTINGS } from './heroQuota.js'
import { DEFAULT_SETTINGS as EMC_DEFAULTS } from './emcQuota.js'

const CRYPTS = ['Epic Crypt 35', 'Epic Crypt 30', 'Epic Crypt 25', 'Epic Crypt 20', 'Rare Crypt 30'].map(key => ({ key, title: key }))
const EMC = ['Epic Fire Hydra', 'Epic Undead', 'Epic Arachne', 'Epic Shadow City', 'Epic Chimera', 'Pumpkin'].map(key => ({ key, title: key }))

function roundTrip(tab, list, key, band, delta, soft) {
  let st = { mix: {}, emc: structuredClone(EMC_DEFAULTS) }
  const lineOf = () => countLines(tab, list, { ...DEFAULT_SETTINGS, mix: st.mix }, st.emc).find(l => l.key === key)
  const step = d => {
    const l = lineOf()
    const t = applyDrag(l.cont, band, d, soft, l.locked)
    const changed = t.map((v, i) => Math.abs(v - l.cont[i]) > 1e-9)
    st = writeBands(st, l.target, bandsFromTargets(t, l.ref, l.bands, changed))
  }
  const base = lineOf()
  step(delta)
  const moved = lineOf()
  assert.ok(Object.keys(moved.bands).length > 0, `${key}: после правки поправок нет`)
  assert.notDeepEqual(moved.cur, base.cur, `${key}: линия не изменилась`)
  step(-delta)
  const back = lineOf()
  assert.deepEqual(back.bands, {}, `${key}/${soft}/${band}: после возврата остались поправки`)
  assert.deepEqual(back.cur, base.cur, `${key}: значения не вернулись`)
}

test('количество склепов: линия есть у каждого типа шкалы (и Rare, и Citadel), у типа вне шкалы и со вписанным числом линии нет', () => {
  const list = [...CRYPTS, { key: 'Citadel 30', title: 'C30' }, { key: 'My Crypt', title: 'My' }]
  const lines = countLines('crypts', list, { ...DEFAULT_SETTINGS, mix: { c: { 'Epic Crypt 25': { set: 9 } } } }, structuredClone(EMC_DEFAULTS))
  assert.deepEqual(lines.map(l => l.key), ['Epic Crypt 35', 'Epic Crypt 30', 'Epic Crypt 20', 'Rare Crypt 30', 'Citadel 30'])
})

test('количество склепов: вверх и обратно возвращает исходное без следа (в том числе у Rare)', () => {
  for (const key of ['Epic Crypt 30', 'Rare Crypt 30']) for (const soft of [0, 30, 80]) for (const [band, d] of [[300, 6], [450, -4], [200, 3]]) roundTrip('crypts', CRYPTS, key, band, d, soft)
})

test('количество EMC: четыре монстра (emc.cells), Chimera и прочие (mix.c) — вверх и обратно без следа', () => {
  for (const key of ['Epic Fire Hydra', 'Epic Undead', 'Epic Arachne', 'Epic Shadow City']) roundTrip('emc', EMC, key, 450, 20, 40)
  roundTrip('emc', EMC, 'Epic Chimera', 450, 10, 40)
  roundTrip('emc', EMC, 'Pumpkin', 450, 8, 40)
})

test('четыре монстра пишут в emc.cells, прочие — в mix.c', () => {
  const lines = countLines('emc', EMC, { ...DEFAULT_SETTINGS, mix: {} }, structuredClone(EMC_DEFAULTS))
  assert.equal(lines.find(l => l.key === 'Epic Undead').target.path, 'cell')
  assert.equal(lines.find(l => l.key === 'Epic Chimera').target.path, 'c')
})

test('очки: линия на каждый тип шкалы, значения целые', () => {
  const lines = pointsLines(CRYPTS, { ...DEFAULT_SETTINGS, mix: {} })
  assert.ok(lines.length >= 5)
  assert.ok(lines.every(l => l.cur.every(Number.isInteger)))
})

test('writeBands: пустые поправки не создают записей и не оставляют пустых', () => {
  const st = { mix: {}, emc: { cells: {} } }
  assert.equal(writeBands(st, { path: 'c', key: 'Epic Crypt 30' }, {}).mix, st.mix)
  assert.equal(writeBands(st, { path: 'cell', key: 'hydra' }, {}).emc, st.emc)
  const withCell = writeBands(st, { path: 'cell', key: 'hydra' }, { 400: 2 })
  assert.deepEqual(writeBands(withCell, { path: 'cell', key: 'hydra' }, {}).emc.cells, {})
})

// ---- Событие EMC вне шкалы (Pumpkin) есть и в пульте, и на графике «Очки» ----
test('график «Очки»: событие вне шкалы (Pumpkin) рисуется, как и фейдер в пульте, и правится без следа', () => {
  const list = [{ key: 'Epic Fire Hydra', title: 'Hydra', points: 1, slot: 2 }, { key: 'Pumpkin', title: 'Pumpkin', points: 1, slot: 2 }]
  const scale = { ...DEFAULT_SETTINGS, mix: { w: { Pumpkin: { all: 25 } } } }
  const lines = pointsLines(list, scale)
  const line = lines.find(l => l.key === 'Pumpkin')
  assert.ok(line, 'линия Pumpkin есть')
  assert.deepEqual(line.target, { path: 'w', key: 'Pumpkin' })
  const i450 = BANDS.indexOf(450), i300 = BANDS.indexOf(300)
  assert.equal(line.cur[i450], 25) // 1 очко клана × 25 на уровнях, где слабый Герой уже не прибавляет
  assert.ok(line.cur[i300] > line.cur[i450]) // слабее Герой — больше очков, как у монстров шкалы
  assert.ok(lines.some(l => l.key === 'Epic Fire Hydra'))
  // правка и возврат без следа
  let st = { mix: { w: { Pumpkin: { all: 25 } } }, emc: structuredClone(EMC_DEFAULTS) }
  const lineOf = () => pointsLines(list, { ...DEFAULT_SETTINGS, mix: st.mix }).find(l => l.key === 'Pumpkin')
  const base = lineOf()
  const step = d => { const l = lineOf(); const t = applyDrag(l.cont, 450, d, 30, l.locked); st = writeBands(st, l.target, bandsFromTargets(t, l.ref, l.bands, t.map((v, k) => Math.abs(v - l.cont[k]) > 1e-9))) }
  step(10)
  assert.ok(lineOf().cur[i450] > base.cur[i450])
  step(-10)
  assert.deepEqual(lineOf().bands, {})
  assert.deepEqual(lineOf().cur, base.cur)
})

test('график «Очки»: тип без очков клана и вне шкалы линии не даёт (рисовать нечего)', () => {
  const lines = pointsLines([{ key: 'Nothing', title: 'N', points: 0, slot: 2 }], { ...DEFAULT_SETTINGS, mix: {} })
  assert.equal(lines.length, 0)
})
