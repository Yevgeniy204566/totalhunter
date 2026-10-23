import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_SETTINGS, HERO_LEVELS, baseAt, computeRow, computeTable, quotaCsv, emcTotalAt, emcChimeraAt, round,
} from './emcQuota.js'

const row = (hero, settings = DEFAULT_SETTINGS) => computeRow(hero, settings)
const finals = r => [r.finalH, r.finalU, r.finalA, r.finalS, r.emc]

test('таблица: каждый уровень 100..600 с шагом 10', () => {
  assert.equal(HERO_LEVELS.length, 51)
  assert.equal(HERO_LEVELS[0], 100)
  assert.equal(HERO_LEVELS[50], 600)
  assert.equal(computeTable(DEFAULT_SETTINGS).length, 51)
})

test('опоры модели: ELDORADO — 45,6 на игрока при Герое 383, Берсерки — 214,9 при Герое 450 (все эпик-монстры)', () => {
  assert.ok(Math.abs(emcTotalAt(383) - 5518 / 121) < 1e-9)
  assert.ok(Math.abs(emcTotalAt(450) - 20413 / 95) < 1e-9)
  // четыре монстра пульта + Chimera = все эпик-монстры
  for (const h of [100, 250, 383, 400, 450, 600]) {
    const sum = baseAt(h).reduce((a, b) => a + b, 0) + emcChimeraAt(h) // emcChimeraAt уже округлена — сверяем с допуском
    assert.ok(Math.abs(sum - emcTotalAt(h)) < 1, `@${h}`)
  }
})

test('EMC растёт с уровнем Героя без провалов и на всём диапазоне 100–600', () => {
  let prev = -1
  for (let h = 100; h <= 600; h += 10) {
    const t = emcTotalAt(h)
    assert.ok(t > prev, `@${h}`)
    prev = t
  }
})

test('округление: меньше 1 — это 0, от 1 — до целого', () => {
  assert.equal(round(0.99), 0)
  assert.equal(round(0.5), 0)
  assert.equal(round(1), 1)
  assert.equal(round(1.49), 1)
  assert.equal(round(1.5), 2)
})

test('при множителях 1.00 итог = таблица модели (сверено независимым расчётом)', () => {
  // значения посчитаны отдельно на Python по той же формуле: EMC = норма × доля, доли монстров ELDORADO
  const expected = {
    100: [0, 0, 0, 0, 0], 250: [4, 1, 0, 0, 5], 300: [6, 2, 0, 1, 9],
    360: [10, 4, 2, 2, 18], 383: [13, 5, 2, 3, 23], 400: [19, 7, 3, 4, 33],
    440: [47, 17, 7, 10, 81], 450: [60, 21, 9, 12, 102], 520: [113, 40, 18, 23, 194], 600: [231, 82, 36, 47, 396],
  }
  for (const [hero, vals] of Object.entries(expected)) {
    assert.deepEqual(finals(row(Number(hero))), vals, `Герой ${hero}`)
  }
})

test('базовые значения монстров на Герое 400 (до округления)', () => {
  const [h, u, a, s] = baseAt(400)
  for (const [got, want] of [[h, 18.782], [u, 6.706], [a, 2.93], [s, 3.813]]) assert.ok(Math.abs(got - want) < 0.001)
})

test('общий множитель масштабирует всё', () => {
  const r = row(400, { ...DEFAULT_SETTINGS, global: 1.2 })
  assert.deepEqual(finals(r), [23, 8, 4, 5, 40]) // 18.78, 6.71, 2.93, 3.81 ×1.2 → 22.5, 8.05, 3.5, 4.6
})

test('множитель монстра меняет только своего монстра и EMC', () => {
  const base = row(400)
  const r = row(400, { ...DEFAULT_SETTINGS, monsters: { ...DEFAULT_SETTINGS.monsters, hydra: 1.3 } })
  assert.equal(r.finalH, 24) // 18.78 × 1.3 = 24.4
  assert.equal(r.finalU, base.finalU)
  assert.equal(r.finalA, base.finalA)
  assert.equal(r.finalS, base.finalS)
  assert.equal(r.emc, base.emc - base.finalH + 24)
})

test('множитель диапазона уровней меняет только уровни этого диапазона', () => {
  const s = {
    ...DEFAULT_SETTINGS,
    ranges: [
      { from: 100, to: 299, k: 1 }, { from: 300, to: 399, k: 1 },
      { from: 400, to: 499, k: 1.1 }, { from: 500, to: 600, k: 1 },
    ],
  }
  assert.deepEqual(finals(row(390, s)), finals(row(390)))
  assert.equal(row(400, s).levelK, 1.1)
  assert.notDeepEqual(finals(row(400, s)), finals(row(400)))
  assert.deepEqual(finals(row(500, s)), finals(row(500)))
})

test('уровень вне всех диапазонов получает множитель 1.00', () => {
  const s = { ...DEFAULT_SETTINGS, ranges: [{ from: 400, to: 499, k: 2 }] }
  assert.equal(row(300, s).levelK, 1)
})

test('порядок: округление один раз в конце, промежуточные значения дробные', () => {
  // Arachna на 400: база 2.93; ×0.7 ×0.7 ×1.1 = 1.58 -> 2. Если бы округляли после каждого шага,
  // вышло бы 1 (2.93×0.7 = 2.05 -> 2; ×0.7 = 1.4 -> 1; ×1.1 = 1.1 -> 1).
  const s = {
    global: 1.1, monsters: { hydra: 1, undead: 1, arachna: 0.7, shadow: 1 },
    ranges: [{ from: 100, to: 600, k: 0.7 }],
  }
  assert.equal(row(400, s).finalA, 2)
})

test('плохие значения множителей считаются как 1.00 / ограничиваются 0.01..1000', () => {
  assert.equal(row(400, { ...DEFAULT_SETTINGS, global: NaN }).emc, row(400).emc)
  assert.equal(row(400, { ...DEFAULT_SETTINGS, global: 12 }).globalK, 12)
  assert.equal(row(400, { ...DEFAULT_SETTINGS, global: 99999 }).globalK, 1000)
  assert.equal(row(400, { ...DEFAULT_SETTINGS, global: 0 }).globalK, 0.01)
})

test('при пустом поле множителя (строка "") берётся 1.00', () => {
  assert.equal(row(400, { ...DEFAULT_SETTINGS, global: '' }).emc, row(400).emc)
})

test('CSV: заголовок, 51 строка, итоги совпадают с таблицей, разделитель ; и BOM для Excel', () => {
  const csv = quotaCsv(computeTable(DEFAULT_SETTINGS), 'ru')
  assert.ok(csv.startsWith('\uFEFF'))
  const lines = csv.slice(1).trim().split('\r\n')
  assert.equal(lines.length, 52)
  assert.equal(lines[0], 'Герой;Hydra;Undead;Arachna;Shadow City;EMC')
  assert.equal(lines[1], '100-109;0;0;0;0;0')
  assert.equal(lines[31], '400-409;19;7;3;4;33')
  assert.equal(lines[51], '600;231;82;36;47;396')
})

test('CSV: английский заголовок', () => {
  const csv = quotaCsv(computeTable(DEFAULT_SETTINGS), 'en')
  assert.equal(csv.slice(1).split('\r\n')[0], 'Hero;Hydra;Undead;Arachna;Shadow City;EMC')
})
