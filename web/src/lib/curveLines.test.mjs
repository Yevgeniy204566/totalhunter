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
    st = writeBands(st, l.target, bandsFromTargets(t, l.ref, l.bands, changed, l.zero))
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

test('график «Очки»: тип вне шкалы без очков клана тоже есть и открыт для правки с нуля (полная свобода, 2026-10-27)', () => {
  const lines = pointsLines([{ key: 'Nothing', title: 'N', points: 0, slot: 2 }], { ...DEFAULT_SETTINGS, mix: {} })
  assert.equal(lines.length, 1)
  assert.ok(lines[0].cur.every(v => v === 0))
  assert.equal(lines[0].locked.size, 0)
  assert.ok(lines[0].zero.every(Boolean))
})

test('«Количество»: нулевые уровни открыты для правки (Rare Crypt 20 с 387,5; Hydra ниже Героя 200) — линия ведётся и возвращается без следа', () => {
  const rare = countLines('crypts', [{ key: 'Rare Crypt 20', title: 'R20' }], { ...DEFAULT_SETTINGS, mix: {} }, structuredClone(EMC_DEFAULTS), {})
  const l = rare.find(x => x.key === 'Rare Crypt 20')
  assert.ok(l, 'линия есть')
  assert.equal(l.locked.size, 0)
  assert.equal(l.zero[BANDS.indexOf(450)], true)
  assert.equal(l.zero[BANDS.indexOf(300)], false)
  let st = { mix: {}, emc: structuredClone(EMC_DEFAULTS) }
  const lineOf = () => countLines('crypts', [{ key: 'Rare Crypt 20', title: 'R20' }], { ...DEFAULT_SETTINGS, mix: st.mix }, st.emc, {}).find(x => x.key === 'Rare Crypt 20')
  const i = BANDS.indexOf(450)
  const l0 = lineOf()
  const up = applyDrag(l0.cont, 450, 25, 0, l0.locked)
  st = writeBands(st, l0.target, bandsFromTargets(up, l0.ref, l0.bands, up.map((v, k) => Math.abs(v - l0.cont[k]) > 1e-9), l0.zero))
  assert.equal(lineOf().cur[i], 25)
  const l1 = lineOf()
  const down = applyDrag(l1.cont, 450, -25, 0, l1.locked)
  st = writeBands(st, l1.target, bandsFromTargets(down, l1.ref, l1.bands, down.map((v, k) => Math.abs(v - l1.cont[k]) > 1e-9), l1.zero))
  assert.deepEqual(lineOf().bands, {})
  assert.equal(lineOf().cur[i], 0)
  // EMC: Hydra ниже 200
  const emcL = countLines('emc', [{ key: 'Epic Fire Hydra', title: 'H' }], { ...DEFAULT_SETTINGS, mix: {} }, structuredClone(EMC_DEFAULTS), {}).find(x => x.key === 'Epic Fire Hydra')
  assert.ok(emcL)
  assert.equal(emcL.locked.size, 0)
  assert.equal(emcL.zero[BANDS.indexOf(150)], true)
  assert.equal(emcL.zero[BANDS.indexOf(400)], false)
})

test('«Количество»: Chimera и прочие EMC на слабых Героях (модель меньше единицы) — линия открыта, вписанное число становится штуками', () => {
  const list = [{ key: 'Epic Chimera', title: 'C' }, { key: 'Yogwai', title: 'Y' }]
  for (const key of ['Epic Chimera', 'Yogwai']) {
    let st = { mix: {}, emc: structuredClone(EMC_DEFAULTS) }
    const lineOf = () => countLines('emc', list, { ...DEFAULT_SETTINGS, mix: st.mix }, st.emc, {}).find(x => x.key === key)
    const i = BANDS.indexOf(210)
    const l0 = lineOf()
    assert.equal(l0.zero[i], true, `${key}: 210 — нулевой уровень`)
    assert.equal(l0.locked.size, 0)
    const up = applyDrag(l0.cont, 210, 20, 0, l0.locked)
    st = writeBands(st, l0.target, bandsFromTargets(up, l0.ref, l0.bands, up.map((v, k) => Math.abs(v - l0.cont[k]) > 1e-9), l0.zero))
    assert.equal(lineOf().cur[i], 20, `${key}: вписано 20 штук`)
    const l1 = lineOf()
    const down = applyDrag(l1.cont, 210, -20, 0, l1.locked)
    st = writeBands(st, l1.target, bandsFromTargets(down, l1.ref, l1.bands, down.map((v, k) => Math.abs(v - l1.cont[k]) > 1e-9), l1.zero))
    assert.deepEqual(lineOf().bands, {}, `${key}: возврат без следа`)
  }
})
