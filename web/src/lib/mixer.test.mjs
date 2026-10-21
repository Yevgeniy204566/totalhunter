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

// Баг 2026-10-21: вписали 20, а получилось 17 — множитель считали как число / округлённое calc(1).
test('solveK: вписанное число даёт ровно это число там, где оно достижимо', async () => {
  const { solveK } = await import('./mixer.js')
  const { computeRow, DEFAULT_SETTINGS } = await import('./emcQuota.js')
  const names = ['hydra', 'undead', 'arachna', 'shadow']
  const keys = ['finalH', 'finalU', 'finalA', 'finalS']
  for (let h = 100; h <= 600; h += 10) {
    names.forEach((n, i) => {
      const calc = k => computeRow(h + 5, { ...DEFAULT_SETTINGS, monsters: { ...DEFAULT_SETTINGS.monsters, [n]: k } })[keys[i]]
      for (const want of [1, 5, 17, 20, 40]) {
        assert.equal(calc(solveK(calc, want, 0.01, 1000)), want, `${n} герой ${h} хочу ${want}`)
      }
    })
    const master = k => computeRow(h + 5, { ...DEFAULT_SETTINGS, global: k }).emc
    assert.equal(master(solveK(master, 20, 0.01, 1000)), 20, `общий герой ${h}`)
  }
})

test('solveK: недостижимое число упирается в границу, а не в мусор', async () => {
  const { solveK } = await import('./mixer.js')
  assert.equal(solveK(k => Math.round(k), 5000, 0.01, 1000), 1000)
})

test('presetMixW: очки типов клана становятся пресетными, прочие и чужие типы не трогаются', async () => {
  const { presetMixW } = await import('./mixer.js')
  const base = { A: 10, B: 40 }
  const types = [{ key: 'A' }, { key: 'B' }, { key: 'C' }]
  const calcFor = x => k => Math.round((base[x.key] ?? 7) * k)
  const withK = (e, k) => ({ ...(e || {}), all: k })
  const w = presetMixW(
    [{ catalog_id: 'A', points: 25 }, { catalog_id: 'Zzz', points: 99 }, { catalog_id: 'B', points: 0 }],
    types, { C: { all: 2, on: false } }, { calcFor, withK, keyOf: id => id })
  assert.equal(calcFor({ key: 'A' })(w.A.all), 25)
  assert.equal(w.A.on, true)
  assert.equal('Zzz' in w, false)   // нет в «Учёте» клана
  assert.equal('B' in w, false)     // 0 очков в пресете — пропуск
  assert.deepEqual(w.C, { all: 2, on: false })
})

test('presetMixW: тип с нулём в шкале при этом Герое пропускается, а не уходит в ×1000', async () => {
  const { presetMixW } = await import('./mixer.js')
  const w = presetMixW([{ catalog_id: 'Z', points: 5 }], [{ key: 'Z' }], {},
    { calcFor: () => k => Math.round(0 * k), withK: (e, k) => ({ ...(e || {}), all: k }), keyOf: id => id })
  assert.equal('Z' in w, false)
})

test('solveK: если при ×1 уже получается нужное число — возвращает ровно 1', async () => {
  const { solveK } = await import('./mixer.js')
  assert.equal(solveK(k => Math.round(135 * k), 135, 0.01, 1000), 1)
})
