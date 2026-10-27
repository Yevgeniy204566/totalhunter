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

test('опоры модели: Герой 300 — 12 в модели (на странице ≈5), ELDORADO 383 — 45,6 на игрока, Герой 456 — 168 (на странице ≈100)', () => {
  assert.ok(Math.abs(emcTotalAt(300) - 12) < 1e-9)
  assert.ok(Math.abs(emcTotalAt(383) - 5518 / 121) < 1e-9)
  assert.ok(Math.abs(emcTotalAt(456) - 168) < 1e-9)
  // четыре монстра пульта + Chimera = все эпик-монстры
  for (const h of [100, 250, 300, 383, 400, 456, 600]) {
    const sum = baseAt(h).reduce((a, b) => a + b, 0) + emcChimeraAt(h) // emcChimeraAt уже округлена — сверяем с допуском
    assert.ok(Math.abs(sum - emcTotalAt(h)) < 1, `@${h}`)
  }
})

test('что видит игрок на странице: четыре монстра + «прочие» (среднее четырёх) — на 300 около 5, на 456 около 100', () => {
  const shown = h => { const r = computeRow(h); return r.emc + Math.round(r.emc / 4) }
  assert.equal(shown(300), 5)
  assert.ok(Math.abs(shown(456) - 100) <= 2, `456: ${shown(456)}`)
})

test('нарастающий плавный рост: темп за 10 уровней на 300–450 не скачет и плавно гаснет, без изломов на стыках', () => {
  const g = h => emcTotalAt(h + 10) / emcTotalAt(h)
  const rates = []
  for (let h = 300; h <= 500; h += 10) rates.push(g(h))
  for (let i = 1; i < rates.length; i++) {
    assert.ok(Math.abs(rates[i] - rates[i - 1]) < 0.02, `скачок темпа @${300 + i * 10}: ${rates[i - 1].toFixed(3)} → ${rates[i].toFixed(3)}`)
  }
  assert.ok(rates[0] > 1.15 && rates[0] < 1.35, `300: ${rates[0]}`)
})

test('выше 456 EMC продолжает расти и быстрее нормы Crypts (владелец 2026-10-27): доля EMC к норме поднимается', () => {
  const share = h => emcTotalAt(h) / normBase(h)
  for (let h = 470; h < 600; h += 10) assert.ok(share(h + 10) > share(h), `доля @${h + 10}`)
  const g = h => emcTotalAt(h + 10) / emcTotalAt(h)
  for (const h of [470, 500, 560]) assert.ok(g(h) > normBase(h + 10) / normBase(h), `быстрее нормы @${h}`)
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
  // значения посчитаны отдельно на Python по той же модели (2026-10-27): парабола в логарифме через 300 → 12, 383 → 45,6,
  // 456 → 168, выше 456 — норма Crypts плюс 3 пункта за 10 уровней; монстры делятся по долям ELDORADO
  const expected = {
    100: [0, 0, 0, 0, 0], 250: [2, 0, 0, 0, 2], 300: [3, 1, 0, 0, 4],
    360: [9, 3, 1, 2, 15], 383: [13, 5, 2, 3, 23], 400: [17, 6, 3, 3, 29],
    440: [35, 12, 5, 7, 59], 450: [42, 15, 7, 8, 72], 520: [119, 42, 19, 24, 204], 600: [308, 110, 48, 63, 529],
  }
  for (const [hero, vals] of Object.entries(expected)) {
    assert.deepEqual(finals(row(Number(hero))), vals, `Герой ${hero}`)
  }
})

test('базовые значения монстров на Герое 400 (до округления)', () => {
  const [h, u, a, s] = baseAt(400)
  for (const [got, want] of [[h, 16.968], [u, 6.059], [a, 2.647], [s, 3.445]]) assert.ok(Math.abs(got - want) < 0.001)
})

test('общий множитель масштабирует всё', () => {
  const r = row(400, { ...DEFAULT_SETTINGS, global: 1.2 })
  assert.deepEqual(finals(r), [20, 7, 3, 4, 34]) // 16.97, 6.06, 2.65, 3.45 ×1.2 → 20.4, 7.3, 3.2, 4.1
})

test('множитель монстра меняет только своего монстра и EMC', () => {
  const base = row(400)
  const r = row(400, { ...DEFAULT_SETTINGS, monsters: { ...DEFAULT_SETTINGS.monsters, hydra: 1.3 } })
  assert.equal(r.finalH, 22) // 16.97 × 1.3 = 22.06
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
  // Arachna на 400: база 2.647; ×0.65 ×1.3 = 2.24 -> 2. Если бы округляли после каждого шага,
  // вышло бы 3 (2.647×0.65 = 1.72 -> 2; ×1.3 = 2.6 -> 3).
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
  assert.equal(lines[31], '400-409;17;6;3;3;29')
  assert.equal(lines[51], '600;308;110;48;63;529')
})

test('CSV: английский заголовок', () => {
  const csv = quotaCsv(computeTable(DEFAULT_SETTINGS), 'en')
  assert.equal(csv.slice(1).split('\r\n')[0], 'Hero;Hydra;Undead;Arachna;Shadow City;EMC')
})
