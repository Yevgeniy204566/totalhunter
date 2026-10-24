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

test('сглаживание: опоры не сдвинуты, а переход 383→450 без изломов (скорость роста плавно набирается и гасится)', () => {
  assert.ok(Math.abs(emcTotalAt(383) - 5518 / 121) < 1e-9)
  assert.ok(Math.abs(emcTotalAt(450) - 20413 / 95) < 1e-9)
  // темп роста за 10 уровней: у границ переход почти равен темпу нормы (×1.10), а не скачет
  const g = h => emcTotalAt(h + 10) / emcTotalAt(h)
  assert.ok(g(380) < 1.13, `380: ${g(380)}`)
  assert.ok(g(440) < 1.2, `440: ${g(440)}`)
  assert.ok(g(450) < 1.12, `450: ${g(450)}`)
  const rates = [380, 390, 400, 410, 420, 430, 440, 450].map(g)
  const peak = rates.indexOf(Math.max(...rates))
  for (let i = 1; i <= peak; i++) assert.ok(rates[i] >= rates[i - 1] - 1e-9, 'темп сначала только растёт')
  for (let i = peak + 1; i < rates.length; i++) assert.ok(rates[i] <= rates[i - 1] + 1e-9, 'потом только падает')
})

test('EMC растёт с уровнем Героя без провалов и на всём диапазоне 100–600', () => {
  let prev = -1
  for (let h = 100; h <= 600; h += 10) {
    const t = emcTotalAt(h)
    assert.ok(h < 200 ? t === 0 : t > prev, `@${h}`)
    prev = t
  }
})

test('слабые Герои (ниже 200) эпических монстров не бьют: EMC равен 0, включая Chimera', () => {
  for (const h of [100, 150, 199]) {
    assert.equal(emcTotalAt(h), 0)
    assert.equal(emcChimeraAt(h), 0)
    assert.equal(row(h).emc, 0)
  }
  assert.ok(emcTotalAt(200) > 0)
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
    360: [10, 4, 2, 2, 18], 383: [13, 5, 2, 3, 23], 400: [17, 6, 3, 3, 29],
    440: [51, 18, 8, 10, 87], 450: [60, 21, 9, 12, 102], 520: [113, 40, 18, 23, 194], 600: [231, 82, 36, 47, 396],
  }
  for (const [hero, vals] of Object.entries(expected)) {
    assert.deepEqual(finals(row(Number(hero))), vals, `Герой ${hero}`)
  }
})

test('базовые значения монстров на Герое 400 (до округления)', () => {
  const [h, u, a, s] = baseAt(400)
  for (const [got, want] of [[h, 17.225], [u, 6.15], [a, 2.687], [s, 3.497]]) assert.ok(Math.abs(got - want) < 0.001)
})

test('общий множитель масштабирует всё', () => {
  const r = row(400, { ...DEFAULT_SETTINGS, global: 1.2 })
  assert.deepEqual(finals(r), [21, 7, 3, 4, 35]) // 17.23, 6.15, 2.69, 3.50 ×1.2 → 20.7, 7.4, 3.2, 4.2
})

test('множитель монстра меняет только своего монстра и EMC', () => {
  const base = row(400)
  const r = row(400, { ...DEFAULT_SETTINGS, monsters: { ...DEFAULT_SETTINGS.monsters, hydra: 1.3 } })
  assert.equal(r.finalH, 22) // 17.23 × 1.3 = 22.4
  assert.equal(r.finalU, base.finalU)
  assert.equal(r.finalA, base.finalA)
  assert.equal(r.finalS, base.finalS)
  assert.equal(r.emc, base.emc - base.finalH + 22)
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
  // Arachna на 400: база 2.687; ×0.55 ×1.1 = 1.63 -> 2. Если бы округляли после каждого шага,
  // вышло бы 1 (2.687×0.55 = 1.48 -> 1; ×1.1 = 1.1 -> 1).
  const s = {
    global: 1.1, monsters: { hydra: 1, undead: 1, arachna: 0.55, shadow: 1 },
    ranges: [{ from: 100, to: 600, k: 1 }],
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
  assert.equal(lines[31], '400-409;17;6;3;3;29')
  assert.equal(lines[51], '600;231;82;36;47;396')
})

test('CSV: английский заголовок', () => {
  const csv = quotaCsv(computeTable(DEFAULT_SETTINGS), 'en')
  assert.equal(csv.slice(1).split('\r\n')[0], 'Hero;Hydra;Undead;Arachna;Shadow City;EMC')
})
