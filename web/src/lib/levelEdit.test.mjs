// Правка одного уровня Героя (владелец 2026-10-28): пульт, диаграмма и страница читают одно и то же.
import test from 'node:test'
import assert from 'node:assert/strict'
import { seriesOf, levelPts, applyDrag, bandsFromTargets, DECADE_PTS } from './curveEdit.js'
import { weightAt, DEFAULT_SETTINGS } from './heroQuota.js'
import { levelEntry, hasLevels, dropLevels } from './emcQuota.js'

const KEY = 'Epic Crypt 35'
const scaleWith = bands => ({ ...DEFAULT_SETTINGS, mix: { w: { [KEY]: { on: true, all: 1, bands } } } })

test('поправка уровня сильнее ступени и действует только на своём уровне', () => {
  const b = { 400: 2, L405: 3 }
  assert.equal(levelEntry(b, 405), 3)
  assert.equal(levelEntry(b, 404), 2)
  assert.equal(levelEntry({ L405: 3 }, 406), undefined)
})

test('правка ступени целиком убирает поправки её уровней', () => {
  assert.equal(hasLevels({ L405: 1 }, 400), true)
  assert.equal(hasLevels({ L415: 1 }, 400), false)
  assert.deepEqual(dropLevels({ L405: 1, L415: 2, 400: 1.2 }, [400]), { L415: 2, 400: 1.2 })
})

test('график по уровням: один уровень ставится ровно, соседи и страница согласованы', () => {
  const s0 = seriesOf(KEY, scaleWith({}))
  const pts = levelPts(440, 460)
  const l = s0.rebuild(pts)
  const i = pts.findIndex(p => p.h === 450)
  const want = Math.round(l.cont[i]) + 7
  const t = applyDrag(l.cont, 450, want - l.cont[i], 0, l.locked, pts)
  const bands = bandsFromTargets(t, l.ref, {}, t.map((v, k) => Math.abs(v - l.cont[k]) > 1e-9), l.zero, pts)
  assert.deepEqual(Object.keys(bands), ['L450'])
  const scale = scaleWith(bands)
  assert.equal(Math.round(weightAt(KEY, 450, scale)), want, 'страница показывает ровно вписанное')
  assert.equal(weightAt(KEY, 449, scale), weightAt(KEY, 449, DEFAULT_SETTINGS), '449 не тронут')
  assert.equal(weightAt(KEY, 451, scale), weightAt(KEY, 451, DEFAULT_SETTINGS), '451 не тронут')
  const l2 = seriesOf(KEY, scale).rebuild(pts)
  assert.equal(Math.round(l2.cur[i]), want, 'диаграмма читает то же')
})

test('правка ступени в обзоре убирает поправки уровней внутри неё', () => {
  const s0 = seriesOf(KEY, scaleWith({ L405: 2 }))
  const i = DECADE_PTS.findIndex(p => p.pos === 400)
  const t = applyDrag(s0.cont, 400, 10, 0, s0.locked)
  const bands = bandsFromTargets(t, s0.ref, { L405: 2 }, t.map((v, k) => Math.abs(v - s0.cont[k]) > 1e-9))
  assert.equal(bands.L405, undefined)
  assert.ok(bands['400'] > 0)
})
