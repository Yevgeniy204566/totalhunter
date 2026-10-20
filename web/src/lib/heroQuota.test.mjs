import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_SETTINGS, HERO_LEVELS, weightAt, normAt, epicRefAt, weightTable, scoreOf, weightKey, emcPointsAt, cryptsNormAt, countAt,
} from './heroQuota.js'

const w = (id, hero, s = DEFAULT_SETTINGS) => weightAt(id, hero, s)

test('опора Феникса (298): стена клана воспроизводится после округления до 5', () => {
  const wall = {
    'Epic Crypt 20': 30, 'Epic Crypt 25': 50, 'Epic Crypt 30': 90, 'Epic Crypt 35': 150,
    'Rare Crypt 20': 25, 'Rare Crypt 25': 45, 'Rare Crypt 30': 80,
    'Common Crypt 20': 20, 'Common Crypt 25': 40,
    'Cursed Citadel 20': 20, 'Cursed Citadel 25': 35, 'Elven Citadel 30': 50,
  }
  for (const [id, pts] of Object.entries(wall)) assert.equal(w(id, 298), pts, id)
})

test('опора ЭДО (387.5): стена клана воспроизводится', () => {
  const wall = {
    'Epic Crypt 20': 25, 'Epic Crypt 25': 45, 'Epic Crypt 30': 80, 'Epic Crypt 35': 135,
    'Rare Crypt 25': 35, 'Rare Crypt 30': 65, 'Common Crypt 25': 15,
    'Cursed Citadel 25': 25, 'Elven Citadel 30': 40,
  }
  for (const [id, pts] of Object.entries(wall)) assert.equal(w(id, 387.5), pts, id)
})

test('очки за сундук всегда кратны 5', () => {
  for (const h of HERO_LEVELS) for (const id of ['Epic Crypt 35', 'Rare Crypt 25', 'Common Crypt 25', 'Epic Fire Hydra']) {
    assert.equal(w(id, h) % 5, 0, `${id} @${h}`)
  }
})

test('владелец: Common Crypt 25 = 0 у Героя 400 и выше', () => {
  for (const h of [400, 410, 450, 500, 600]) assert.equal(w('Common Crypt 25', h), 0, `@${h}`)
  assert.ok(w('Common Crypt 25', 390) > 0)
})

test('чем ниже Герой, тем больше очков за сундук (эпик 35 не растёт с уровнем)', () => {
  let prev = Infinity
  for (const h of HERO_LEVELS) {
    const v = w('Epic Crypt 35', h)
    assert.ok(v <= prev, `@${h}`)
    prev = v
  }
  assert.equal(w('Epic Crypt 35', 100) > w('Epic Crypt 35', 300), true)
  assert.equal(w('Epic Crypt 35', 450), 135)
})

test('типы 20 уровня (в стене ЭДО их нет) к 387.5 уходят в 0', () => {
  for (const id of ['Common Crypt 20', 'Rare Crypt 20', 'Elven Citadel 20']) {
    assert.equal(w(id, 400), 0, id)
    assert.ok(w(id, 250) > 0, id)
  }
})

test('монстры EMC (T9, опора 413): на высоких уровнях значения T9, ниже — растут', () => {
  assert.equal(w('Epic Shadow City', 413), 55)
  assert.equal(w('Epic Shadow City', 500), 55)
  assert.ok(w('Epic Shadow City', 200) > 55)
})

test('неизвестный тип сундука — нет веса шкалы (null), решает запасной вариант', () => {
  assert.equal(w('Some New Chest', 300), null)
})

test('общая норма: опоры Старта и ЭДО — факт, Сарацины/Берсерки — расчёт', () => {
  assert.equal(normAt(279), 5000)
  assert.equal(normAt(387.5), 14000)
  assert.equal(normAt(213.5), 4000)
  assert.equal(normAt(413), 16000)
})

test('общая норма на всём диапазоне 100–600: растёт с уровнем, положительна, кратна 100, без обрезки', () => {
  let prev = 0
  for (const h of HERO_LEVELS) {
    const n = normAt(h)
    assert.ok(n >= prev && n > 0, `@${h}`)
    assert.equal(n % 100, 0, `@${h}`)
    prev = n
  }
})

test('рычаги: множитель нормы и множитель весов', () => {
  const s = { ...DEFAULT_SETTINGS, norm: 1.2, weights: 0.5 }
  assert.equal(normAt(387.5, s), 16800)
  assert.equal(w('Epic Crypt 35', 387.5, s), 70) // 135×0.5=67.5 → ближайшее кратное 5
})

test('рычаг по диапазону Героев меняет только норму этого диапазона', () => {
  const s = { ...DEFAULT_SETTINGS, ranges: [{ from: 300, to: 399, k: 2 }] }
  assert.equal(normAt(387.5, s), 28000)
  assert.equal(normAt(279, s), 5000)
})

test('множители зажимаются в 0.1…3', () => {
  assert.equal(normAt(387.5, { ...DEFAULT_SETTINGS, norm: 99 }), 42000)
})

test('ориентир по эпикам: опоры 50 / 200 / 250 / 40', () => {
  assert.equal(epicRefAt(279), 50)
  assert.equal(epicRefAt(387.5), 200)
  assert.equal(epicRefAt(413), 250)
  assert.equal(epicRefAt(213.5), 40)
})

test('weightKey: цитадели Cursed/Elven делят общую строку', () => {
  assert.equal(weightKey('Cursed Citadel 25'), 'Citadel 25')
  assert.equal(weightKey('Elven Citadel 25'), 'Citadel 25')
  assert.equal(weightKey('Epic Crypt 30'), 'Epic Crypt 30')
})

test('счёт игрока: сундуки × вес при его Герое; тип вне шкалы — очки клана', () => {
  const meta = {
    'Epic Crypt 35': { id: 'Epic Crypt 35', points: 135 },
    'Odd Chest': { id: 'Some New Chest', points: 7 },
  }
  const r = scoreOf({ 'Epic Crypt 35': 2, 'Odd Chest': 3 }, meta, 298)
  assert.equal(r.score, 2 * 150 + 3 * 7)
  assert.deepEqual(r.fallback, ['Odd Chest'])
})

test('счёт без уровня Героя — по Герою 400 и partial', () => {
  const r = scoreOf({ 'Epic Crypt 35': 1 }, { 'Epic Crypt 35': { id: 'Epic Crypt 35', points: 135 } }, null)
  assert.equal(r.partial, true)
  assert.equal(r.score, 135)
})

test('таблица весов по уровню: строки для всех типов шкалы', () => {
  const t = weightTable(300)
  assert.equal(t.find(r => r.id === 'Epic Crypt 35').points, 150)
  assert.ok(t.length >= 20)
  assert.ok(t.every(r => ['FACT', 'CALC'].includes(r.origin)))
})

test('счёт по слоту: Crypts (слот 1) и EMC (слот 2) считаются раздельно', () => {
  const meta = {
    'Эпик 35': { id: 'Epic Crypt 35', points: 135, slot: 1 },
    'Hydra': { id: 'Epic Fire Hydra', points: 30, slot: 2 },
    'Прочее': { id: 'Epic Crypt 25', points: 45, slot: null },
  }
  const counts = { 'Эпик 35': 2, 'Hydra': 3, 'Прочее': 1 }
  assert.equal(scoreOf(counts, meta, 413, DEFAULT_SETTINGS, 1).score, 270)
  assert.equal(scoreOf(counts, meta, 413, DEFAULT_SETTINGS, 2).score, 90)
  assert.equal(scoreOf(counts, meta, 413).score, 270 + 90 + 45)
})

test('доля EMC в норме: штуки таблицы × вес монстра; Crypts = норма − доля EMC', () => {
  const h = 400
  const emc = emcPointsAt(h)
  assert.ok(emc > 0 && emc < normAt(h))
  assert.equal(cryptsNormAt(h), normAt(h) - emc)
})

test('цель Crypts не уходит ниже нуля', () => {
  assert.equal(cryptsNormAt(100, undefined, { ...DEFAULT_SETTINGS, norm: 0.1 }) >= 0, true)
})

test('края диапазона: 100 и 600 заданы продолжением наклона крайних отрезков', () => {
  assert.equal(normAt(100), 2300)
  assert.equal(normAt(600), 30700)
  assert.equal(epicRefAt(100), 23)
  assert.equal(epicRefAt(600), 617)
})

// ---- пульт: фейдеры по типам и ступеням Героя ----
import { computeRow, bandKey } from './emcQuota.js'

test('ступень Героя: 310–319 → "310", края 100…600', () => {
  assert.equal(bandKey(319), '310')
  assert.equal(bandKey(310), '310')
  assert.equal(bandKey(50), '100')
  assert.equal(bandKey(999), '600')
})

test('фейдер «все уровни» умножает очки типа на каждой ступени пропорционально', () => {
  const s = { ...DEFAULT_SETTINGS, mix: { w: { 'Epic Crypt 35': { all: 1.2 } } } }
  assert.equal(w('Epic Crypt 35', 387.5, s), 160) // 135×1.2=162 → 160
  assert.equal(w('Epic Crypt 35', 298, s), 180)   // 150×1.2
  assert.equal(w('Epic Crypt 30', 298, s), 90)    // другие типы не затронуты
})

test('фейдер ступени правит только свою ступень, поверх «всех уровней»', () => {
  const s = { ...DEFAULT_SETTINGS, mix: { w: { 'Epic Crypt 35': { all: 1.2, bands: { 380: 0.5 } } } } }
  assert.equal(w('Epic Crypt 35', 385, s), 80)    // 135×1.2×0.5=81 → 80
  assert.equal(w('Epic Crypt 35', 395, s), 160)   // соседняя ступень — только «все уровни»
})

test('mute (on:false) обнуляет тип', () => {
  const s = { ...DEFAULT_SETTINGS, mix: { w: { 'Epic Crypt 35': { on: false } } } }
  assert.equal(w('Epic Crypt 35', 300, s), 0)
  assert.equal(w('Epic Crypt 30', 300, s), 90)
})

test('цитадели Cursed/Elven делят один фейдер', () => {
  const s = { ...DEFAULT_SETTINGS, mix: { w: { 'Citadel 25': { all: 2 } } } }
  assert.equal(w('Cursed Citadel 25', 298, s), 70)
  assert.equal(w('Elven Citadel 25', 298, s), 70)
})

test('ориентир по эпикам: фейдер и mute', () => {
  assert.equal(epicRefAt(387.5, { ...DEFAULT_SETTINGS, mix: { epic: { all: 1.5 } } }), 300)
  assert.equal(epicRefAt(387.5, { ...DEFAULT_SETTINGS, mix: { epic: { on: false } } }), 0)
})

test('EMC: множитель монстра на ступень (cells) и выключатель (off)', () => {
  const base = computeRow(400)
  const cell = computeRow(400, { cells: { hydra: { 400: 0.5 } } })
  assert.equal(cell.finalH, Math.floor(base.base[0] * 0.5 + 0.5 + 1e-9))
  assert.equal(cell.finalU, base.finalU)
  assert.equal(computeRow(400, { cells: { hydra: { 400: 0.5 } } }).finalH === computeRow(410, { cells: { hydra: { 400: 0.5 } } }).finalH, false)
  const off = computeRow(400, { off: ['undead'] })
  assert.equal(off.finalU, 0)
  assert.equal(off.emc, base.emc - base.finalU)
})

test('количество склепов: доля нормы Crypts поровну по включённым типам ÷ очки за сундук', () => {
  const h = 300
  const active = ['Rare Crypt 20', 'Rare Crypt 25', 'Rare Crypt 30', 'Common Crypt 20', 'Common Crypt 25',
    'Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35', 'Citadel 20', 'Citadel 25', 'Citadel 30']
  const share = cryptsNormAt(h) / active.length
  assert.equal(countAt('Epic Crypt 35', h), Math.round(share / weightAt('Epic Crypt 35', h)))
  // дешёвый сундук требуется чаще дорогого
  assert.ok(countAt('Common Crypt 25', h) > countAt('Epic Crypt 35', h))
})

test('количество: фейдер c правит штуки, mute исключает тип и перераспределяет долю', () => {
  const h = 300
  const base = countAt('Epic Crypt 30', h)
  const up = { ...DEFAULT_SETTINGS, mix: { c: { 'Epic Crypt 30': { all: 2 } } } }
  assert.ok(Math.abs(countAt('Epic Crypt 30', h, up) - base * 2) <= 1) // округление до целого
  const off = ['Epic Crypt 35', 'Rare Crypt 20', 'Rare Crypt 25', 'Common Crypt 20', 'Common Crypt 25', 'Citadel 20']
  const muted = { ...DEFAULT_SETTINGS, mix: { c: Object.fromEntries(off.map(id => [id, { on: false }])) } }
  assert.equal(countAt('Epic Crypt 35', h, muted), 0)
  assert.ok(countAt('Epic Crypt 30', h, muted) > base) // доля делится на меньшее число типов
})

test('количество: тип с нулевыми очками (например обычный склеп с 400) не требуется', () => {
  assert.equal(countAt('Common Crypt 25', 450), 0)
})

test('количество зависит от очков: подняли очки за тип — штук нужно меньше', () => {
  const h = 300
  const base = countAt('Epic Crypt 30', h)
  const richer = { ...DEFAULT_SETTINGS, mix: { w: { 'Epic Crypt 30': { all: 2 } } } }
  assert.ok(countAt('Epic Crypt 30', h, richer) < base)
})
