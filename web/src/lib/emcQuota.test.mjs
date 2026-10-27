import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_SETTINGS, HERO_LEVELS, baseAt, computeRow, computeTable, quotaCsv, emcTotalAt, emcChimeraAt, round,
} from './emcQuota.js'
import { normBase } from './normCurve.js'

const row = (hero, settings = DEFAULT_SETTINGS) => computeRow(hero, settings)
const finals = r => [r.finalH, r.finalU, r.finalA, r.finalS, r.emc]

test('таблица: каждый уровень 100..600 с шагом 10', () => {
  assert.equal(HERO_LEVELS.length, 51)
  assert.equal(HERO_LEVELS[0], 100)
  assert.equal(HERO_LEVELS[50], 600)
  assert.equal(computeTable(DEFAULT_SETTINGS).length, 51)
})

test('опоры модели (по свободной игре ELDORADO и Берсеркам вдвое меньше): 300 — минимум 5,5; ELDORADO 383 — 45,6; Берсерки 450 — 100', () => {
  assert.ok(Math.abs(emcTotalAt(300) - 5.5) < 1e-9)
  assert.ok(Math.abs(emcTotalAt(383) - 5518 / 121) < 1e-9)
  assert.ok(Math.abs(emcTotalAt(450) - 100) < 1e-9)
  // четыре монстра пульта + Chimera = все эпик-монстры
  for (const h of [100, 250, 300, 383, 400, 450, 600]) {
    const sum = baseAt(h).reduce((a, b) => a + b, 0) + emcChimeraAt(h) // emcChimeraAt уже округлена — сверяем с допуском
    assert.ok(Math.abs(sum - emcTotalAt(h)) < 1, `@${h}`)
  }
})

test('сумма штук по монстрам (как её показывает сайт) на опорных Героях: 300 — 5, 450 — 100', () => {
  const total = h => computeRow(h).emc + emcChimeraAt(h)
  assert.equal(total(300), 5)
  assert.equal(total(450), 100)
})

test('гармонизация: темп роста штук за 10 уровней только затухает — от быстрого старта на 300 к темпу нормы Crypts, без скачков', () => {
  const g = h => emcTotalAt(h + 10) / emcTotalAt(h)
  const rates = []
  for (let h = 300; h <= 590; h += 10) rates.push(g(h))
  let prevDrop = Infinity
  for (let i = 1; i < rates.length; i++) {
    const drop = rates[i - 1] - rates[i]
    assert.ok(drop >= -1e-9, `темп вырос @${300 + i * 10}: ${rates[i - 1].toFixed(3)} → ${rates[i].toFixed(3)}`)
    assert.ok(drop <= prevDrop + 1e-9, `спад темпа ускорился @${300 + i * 10}`) // затухание выпуклое: изломов нет
    prevDrop = drop
  }
  assert.ok(rates[0] > 1.4 && rates[0] < 1.7, `300: ${rates[0]}`)
  assert.ok(rates[rates.length - 1] < 1.11, `600: ${rates[rates.length - 1]}`)
})

test('EMC растёт быстрее нормы Crypts на всём диапазоне, поэтому доля EMC к норме только поднимается', () => {
  const share = h => emcTotalAt(h) / normBase(h)
  for (let h = 300; h < 600; h += 10) assert.ok(share(h + 10) > share(h), `доля @${h + 10}`)
  const g = h => emcTotalAt(h + 10) / emcTotalAt(h)
  for (const h of [310, 400, 450, 500, 560]) assert.ok(g(h) > normBase(h + 10) / normBase(h), `быстрее нормы @${h}`)
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
  // значения посчитаны отдельно на Python по той же модели (2026-10-27): рост штук = рост нормы Crypts плюс затухающая добавка,
  // опоры 300 → 5,5, 383 → 45,6 (ELDORADO), 450 → 100 (Берсерки вдвое меньше); монстры делятся по долям ELDORADO
  const expected = {
    100: [0, 0, 0, 0, 0], 250: [0, 0, 0, 0, 0], 300: [2, 0, 0, 0, 2],
    360: [9, 3, 1, 2, 15], 383: [13, 5, 2, 3, 23], 400: [16, 6, 2, 3, 27],
    440: [25, 9, 4, 5, 43], 450: [28, 10, 4, 6, 48], 520: [54, 19, 8, 11, 92], 600: [112, 40, 17, 23, 192],
  }
  for (const [hero, vals] of Object.entries(expected)) {
    assert.deepEqual(finals(row(Number(hero))), vals, `Герой ${hero}`)
  }
})

test('базовые значения монстров на Герое 400 (до округления)', () => {
  const [h, u, a, s] = baseAt(400)
  for (const [got, want] of [[h, 15.898], [u, 5.676], [a, 2.48], [s, 3.227]]) assert.ok(Math.abs(got - want) < 0.001)
})

test('общий множитель масштабирует всё', () => {
  const r = row(400, { ...DEFAULT_SETTINGS, global: 1.2 })
  assert.deepEqual(finals(r), [19, 7, 3, 4, 33]) // 15.90, 5.68, 2.48, 3.23 ×1.2 → 19.1, 6.8, 3.0, 3.9
})

test('множитель монстра меняет только своего монстра и EMC', () => {
  const base = row(400)
  const r = row(400, { ...DEFAULT_SETTINGS, monsters: { ...DEFAULT_SETTINGS.monsters, hydra: 1.3 } })
  assert.equal(r.finalH, 21) // 15.90 × 1.3 = 20.7
  assert.equal(r.finalU, base.finalU)
  assert.equal(r.finalA, base.finalA)
  assert.equal(r.finalS, base.finalS)
  assert.equal(r.emc, base.emc - base.finalH + 21)
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
  // Arachna на 400: база 2.48; ×0.65 ×1.3 = 2.10 -> 2. Если бы округляли после каждого шага,
  // вышло бы 3 (2.48×0.65 = 1.61 -> 2; ×1.3 = 2.6 -> 3).
  const s = {
    global: 1.3, monsters: { hydra: 1, undead: 1, arachna: 0.65, shadow: 1 },
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
  assert.equal(lines[31], '400-409;16;6;2;3;27')
  assert.equal(lines[51], '600;112;40;17;23;192')
})

test('CSV: английский заголовок', () => {
  const csv = quotaCsv(computeTable(DEFAULT_SETTINGS), 'en')
  assert.equal(csv.slice(1).split('\r\n')[0], 'Hero;Hydra;Undead;Arachna;Shadow City;EMC')
})

test('слабые Герои (ниже 200) бьют ноль, но правка ступени задаёт сами штуки монстра (полная свобода, 2026-10-27)', () => {
  assert.equal(row(150).emc, 0)
  const withHydra = { ...DEFAULT_SETTINGS, cells: { hydra: { 150: 7 } } }
  assert.equal(row(155, withHydra).finalH, 7)
  assert.equal(row(155, withHydra).finalU, 0)
  assert.equal(row(255, withHydra).finalH, row(255).finalH, 'уровни со шкалой не тронуты')
  const withTwo = { ...DEFAULT_SETTINGS, global: 2, monsters: { ...DEFAULT_SETTINGS.monsters, hydra: 3 }, cells: { hydra: { 150: 5 } } }
  assert.equal(row(155, withTwo).finalH, 30, 'вписанное уважает общий множитель и множитель монстра: 5 × 2 × 3')
})
