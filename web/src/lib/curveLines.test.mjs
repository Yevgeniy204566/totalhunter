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

test('количество склепов: график даёт линии только эпик-склепам, ручные типы не показываются', () => {
  const lines = countLines('crypts', CRYPTS, { ...DEFAULT_SETTINGS, mix: {} }, structuredClone(EMC_DEFAULTS))
  assert.deepEqual(lines.map(l => l.key), ['Epic Crypt 35', 'Epic Crypt 30', 'Epic Crypt 25', 'Epic Crypt 20'])
})

test('количество склепов: вверх и обратно возвращает исходное без следа', () => {
  for (const soft of [0, 30, 80]) for (const [band, d] of [[300, 6], [450, -4], [200, 3]]) roundTrip('crypts', CRYPTS, 'Epic Crypt 30', band, d, soft)
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
