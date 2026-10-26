import test from 'node:test'
import assert from 'node:assert/strict'
import { BANDS, HANDLE_BANDS, centerOf, kernel, applyDrag, seriesOf, bandsFromTargets } from './curveEdit.js'
import { weightAt, DEFAULT_SETTINGS } from './heroQuota.js'

test('ручки — каждые 50 уровней, 11 штук; ступень считается по середине', () => {
  assert.equal(HANDLE_BANDS.length, 11)
  assert.deepEqual([HANDLE_BANDS[0], HANDLE_BANDS[10]], [100, 600])
  assert.equal(centerOf(400), 405)
  assert.equal(centerOf(600), 600)
})

test('колокол: сама точка = 1, дальше убывает; мягкость 0 — только своя ступень', () => {
  assert.equal(kernel(0, 40), 1)
  assert.ok(kernel(50, 40) > kernel(100, 40) && kernel(100, 40) > 0)
  assert.equal(kernel(10, 0), 0)
  assert.equal(kernel(0, 0), 1)
  assert.equal(kernel(1000, 40), 0)
})

test('applyDrag: ручка уходит ровно на delta, соседи плавно, далёкие не двигаются, не ниже 0', () => {
  const start = BANDS.map(() => 40)
  const t = applyDrag(start, 300, 20, 30)
  assert.equal(t[BANDS.indexOf(300)], 60)
  assert.ok(t[BANDS.indexOf(310)] < 60 && t[BANDS.indexOf(310)] > t[BANDS.indexOf(350)])
  assert.equal(t[BANDS.indexOf(600)], 40)
  assert.ok(applyDrag(start, 300, -500, 30).every(v => v >= 0))
  assert.equal(applyDrag(start, 300, 20, 0)[BANDS.indexOf(310)], 40)
})

test('applyDrag не трогает закрытые ступени (в шкале 0)', () => {
  const start = BANDS.map(() => 10)
  const locked = new Set([410])
  assert.equal(applyDrag(start, 400, 30, 40, locked)[BANDS.indexOf(410)], 10)
})

test('круг: график → поправки ступеней → очки на странице совпадают с желаемыми (до округления в 5)', () => {
  for (const key of ['Epic Crypt 30', 'Rare Crypt 25', 'Citadel 30', 'Epic Fire Hydra']) {
    const scale = { ...DEFAULT_SETTINGS, mix: {} }
    const s = seriesOf(key, scale)
    const i = BANDS.indexOf(300)
    const target = s.cur.map(v => v)
    target[i] = s.cur[i] + 30
    const changed = target.map((v, j) => j === i)
    const bands = bandsFromTargets(target, s.ref, {}, changed)
    const after = { ...scale, mix: { w: { [key]: { on: true, all: 1, bands } } } }
    const got = weightAt(key, centerOf(300), after)
    assert.ok(Math.abs(got - target[i]) <= 5, `${key}: хотели ${target[i]}, получили ${got}`)
    // остальные ступени не изменились
    assert.equal(weightAt(key, centerOf(500), after), s.cur[BANDS.indexOf(500)])
  }
})

test('поправка около шкалы стирается, чтобы не копить шум', () => {
  const s = seriesOf('Epic Crypt 30', { ...DEFAULT_SETTINGS, mix: {} })
  const bands = bandsFromTargets(s.cur, s.ref, { 300: 1.5 }, s.cur.map((_, j) => BANDS[j] === 300))
  assert.equal('300' in bands, false)
})

test('тип без очков в шкале на этих уровнях закрыт для правки', () => {
  const s = seriesOf('Common Crypt 25', { ...DEFAULT_SETTINGS, mix: {} })
  assert.ok(s.locked.has(500))
  assert.ok(!s.locked.has(200))
})
