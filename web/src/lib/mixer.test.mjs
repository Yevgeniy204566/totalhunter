import test from 'node:test'
import assert from 'node:assert/strict'
import { posToK, kToPos, MIXER_MIN, MIXER_MAX } from './mixer.js'

test('середина фейдера = ×1, края = ×0.1 и ×3', () => {
  assert.equal(posToK(500), 1)
  assert.equal(posToK(0), MIXER_MIN)
  assert.equal(posToK(1000), MIXER_MAX)
})

test('прилипание к ×1 рядом с серединой', () => {
  assert.equal(posToK(505), 1)
  assert.equal(posToK(495), 1)
})

test('вверх и вниз ход одинаков по логарифму: четверть хода вверх/вниз симметрична', () => {
  assert.equal(posToK(750), Math.round(MIXER_MAX ** 0.5 * 100) / 100)
  assert.equal(posToK(250), Math.round(MIXER_MIN ** 0.5 * 100) / 100)
})

test('kToPos обратна posToK с точностью до округления множителя', () => {
  for (const k of [0.1, 0.25, 0.5, 0.9, 1, 1.2, 1.5, 2, 3]) {
    const back = posToK(kToPos(k))
    assert.ok(Math.abs(back - k) / k < 0.03, `${k} → ${back}`)
  }
})

test('kToPos зажимает значения вне диапазона', () => {
  assert.equal(kToPos(99), 1000)
  assert.equal(kToPos(0.001), 0)
})
