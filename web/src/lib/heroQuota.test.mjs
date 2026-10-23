import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_SETTINGS, HERO_LEVELS, weightAt, normAt, epicRefAt, weightTable, scoreOf, weightKey, emcPointsAt, cryptsNormAt, countAt, emcCountAt, emcOthersTotal, epicCountTotal, epicCryptsOf, typeTab,
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

test('монстры EMC (T9, опора 450): на высоких уровнях значения T9, ниже — растут', () => {
  assert.equal(w('Epic Shadow City', 450), 55)
  assert.equal(w('Epic Shadow City', 500), 55)
  assert.ok(w('Epic Shadow City', 200) > 55)
})

test('неизвестный тип сундука — нет веса шкалы (null), решает запасной вариант', () => {
  assert.equal(w('Some New Chest', 300), null)
})

test('общая норма: кривая проходит ровно через стены Старта, ЭДО и Берсерков (Герой 450, 25 000)', () => {
  assert.equal(normAt(279), 5000)
  assert.equal(normAt(387.5), 14000)
  assert.equal(normAt(450), 25000)
})

test('общая норма гладкая: рост на каждые 10 уровней Героя почти постоянный (≈×1.10), без изломов в стыках', () => {
  for (let h = 230; h <= 450; h += 10) { // ниже норма в тысячах — округление до сотен даёт шум в процентах
    const k = normAt(h) / normAt(h - 10)
    assert.ok(k > 1.06 && k < 1.14, `@${h}: ×${k.toFixed(3)}`) // запас на округление до сотен
  }
  // нет скачка наклона на опорах: рост до и после стыка отличается меньше, чем на округление
  for (const h of [279, 387.5, 450]) {
    const before = normAt(h) / normAt(h - 20)
    const after = normAt(h + 20) / normAt(h)
    assert.ok(Math.abs(after - before) < 0.06, `@${h}: ×${before.toFixed(3)} → ×${after.toFixed(3)}`)
  }
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

test('множители зажимаются в 0.01…1000', () => {
  assert.equal(normAt(387.5, { ...DEFAULT_SETTINGS, norm: 99 }), 1386000)
  assert.equal(normAt(387.5, { ...DEFAULT_SETTINGS, norm: 99999 }), 14000000)
})

test('ориентир по эпикам: проходит через стены 50 / 200 / 300, монотонно растёт на всём диапазоне', () => {
  assert.equal(epicRefAt(279), 50)
  assert.equal(epicRefAt(387.5), 200)
  assert.equal(epicRefAt(450), 300) // Берсерки: 300 эпик-склепов на Герое 450
  let prev = -1
  for (let h = 100; h <= 600; h += 10) {
    const e = epicRefAt(h)
    assert.ok(e >= prev, `@${h}: ${e} < ${prev}`)
    prev = e
  }
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

test('края диапазона: ниже Старта — та же экспонента, выше Берсерков — прямая с тем же наклоном', () => {
  assert.equal(normAt(100), 900)
  assert.equal(normAt(600), 59500)
  assert.equal(epicRefAt(100), 7)
  assert.equal(epicRefAt(600), 714) // выше 450 цель растёт вместе с нормой
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

test('количество эпик-склепов: ориентир клана ÷ 4 типа (200 у ЭДО → по 50)', () => {
  for (const id of ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']) {
    assert.equal(countAt(id, 387.5), 50, id)
  }
  assert.equal(countAt('Epic Crypt 35', 279), 13) // Старт: 50 ÷ 4 = 12.5 → 13
})

test('проверка по данным клана: эпики × средние очки эпика ≈ норма (ЭДО в пределах 3%)', () => {
  const ids = ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']
  const pts = ids.reduce((sum, id) => sum + countAt(id, 387.5) * weightAt(id, 387.5), 0)
  assert.ok(Math.abs(pts / normAt(387.5) - 1) < 0.03, String(pts))
})

test('Rare/Common/Citadel: штук в данных клана нет — база 0, число задаётся вручную (set)', () => {
  assert.equal(countAt('Rare Crypt 30', 300), 0)
  assert.equal(countAt('Citadel 25', 300), 0)
  const s = { ...DEFAULT_SETTINGS, mix: { c: { 'Rare Crypt 30': { set: 25 } } } }
  assert.equal(countAt('Rare Crypt 30', 300, s), 25)
})

test('количество эпиков: фейдер, mute (доля остальных растёт)', () => {
  const up = { ...DEFAULT_SETTINGS, mix: { c: { 'Epic Crypt 30': { all: 2 } } } }
  assert.equal(countAt('Epic Crypt 30', 387.5, up), 100)
  const muted = { ...DEFAULT_SETTINGS, mix: { c: { 'Epic Crypt 35': { on: false } } } }
  assert.equal(countAt('Epic Crypt 35', 387.5, muted), 0)
  assert.equal(countAt('Epic Crypt 30', 387.5, muted), 67) // 200 ÷ 3
})

test('EMC: четыре известных монстра — по истории, прочие — среднее четырёх', () => {
  assert.equal(emcCountAt('Epic Fire Hydra', 400), 19)
  assert.equal(emcCountAt('Epic Shadow City', 400), 4)
  // среднее по 19/10/3/4 = 9
  assert.equal(emcCountAt('Epic Briareus', 400), 9)
  assert.equal(emcCountAt('Yogwai', 400, { ...DEFAULT_SETTINGS, mix: { c: { Yogwai: { all: 2 } } } }), 18)
  assert.equal(emcCountAt('Yogwai', 400, { ...DEFAULT_SETTINGS, mix: { c: { Yogwai: { on: false } } } }), 0)
})

test('EMC: цель «прочих» монстров слота 2 суммируется отдельно', () => {
  const meta = {
    A: { id: 'Epic Briareus', points: 45, slot: 2 }, B: { id: 'Epic Fire Hydra', points: 30, slot: 2 },
    C: { id: 'Yogwai', points: 40, slot: 1 },
  }
  assert.equal(emcOthersTotal(meta, 400), 9) // только Briareus: Hydra — из четырёх, Yogwai вне слота EMC
})

test('тип вне шкалы: очки клана × фейдер, mute обнуляет', () => {
  const meta = { 'Тыква': { id: 'Pumpkin Chest', points: 12, slot: null } }
  assert.equal(scoreOf({ 'Тыква': 3 }, meta, 300).score, 36)
  const up = { ...DEFAULT_SETTINGS, mix: { w: { 'Pumpkin Chest': { all: 2 } } } }
  assert.equal(scoreOf({ 'Тыква': 3 }, meta, 300, up).score, 72)
  const off = { ...DEFAULT_SETTINGS, mix: { w: { 'Pumpkin Chest': { on: false } } } }
  assert.equal(scoreOf({ 'Тыква': 3 }, meta, 300, off).score, 0)
})

test('итоговая норма эпик-склепов: ЭДО ≥ 200, Берсерки 450 → 300, Герой 456 → 317, а не доля типа', () => {
  assert.equal(epicCountTotal(387.5), 200)
  assert.equal(epicCountTotal(450), 300)
  assert.equal(epicCountTotal(456), 317)
  assert.ok(epicCountTotal(400) >= 200)
  assert.equal(epicCountTotal(279), 50)
})

test('норма эпиков следует за фейдерами пульта: mute типа и множитель', () => {
  const muted = { ...DEFAULT_SETTINGS, mix: { c: { 'Epic Crypt 20': { on: false } } } }
  assert.equal(epicCountTotal(387.5, muted), 200) // 200 ÷ 3 на каждый из трёх оставшихся типов
  const up = { ...DEFAULT_SETTINGS, mix: { c: { 'Epic Crypt 35': { all: 2 } } } }
  assert.equal(epicCountTotal(387.5, up), 250)
})

test('эпик-склепы игрока: суммируются по id типов 20–35, прочие не входят', () => {
  const meta = {
    'Эпик 35': { id: 'Epic Crypt 35', slot: 1 }, 'Эпик 25': { id: 'Epic Crypt 25', slot: 1 },
    'Редкий 30': { id: 'Rare Crypt 30', slot: 1 }, 'Hydra': { id: 'Epic Fire Hydra', slot: 2 },
  }
  assert.equal(epicCryptsOf({ 'Эпик 35': 10, 'Эпик 25': 5, 'Редкий 30': 40, Hydra: 7 }, meta), 15)
})

test('согласованность по всей шкале: очки эпиков держатся около нормы (75–110%: у Старта 81%, у ЭДО 102%, у Берсерков 86%) на уровнях 100–600', () => {
  const ids = ['Epic Crypt 20', 'Epic Crypt 25', 'Epic Crypt 30', 'Epic Crypt 35']
  for (let h = 150; h <= 600; h += 10) { // ниже 150 штуки эпиков в единицах — округление по типам дробит процент
    const pts = ids.reduce((sum, id) => sum + countAt(id, h) * weightAt(id, h), 0)
    const ratio = pts / normAt(h)
    assert.ok(ratio > 0.75 && ratio < 1.1, `@${h}: ${(ratio * 100).toFixed(0)}%`)
  }
})

// ---- «Очки» = сумма всех сундуков в учёте: норму можно закрыть склепами, EMC или смесью ----
const META = {
  'Эпик 35': { id: 'Epic Crypt 35', points: 135, slot: 1 },
  'Hydra': { id: 'Epic Fire Hydra', points: 1, slot: 2 },
  'Shadow City': { id: 'Epic Shadow City', points: 1, slot: 2 },
  'Тыква': { id: 'Pumpkin Chest', points: 12, slot: null },
}

test('очки: склепы и EMC складываются в одну сумму по весам шкалы Героя', () => {
  const h = 413
  const a = scoreOf({ 'Эпик 35': 10 }, META, h).score
  const b = scoreOf({ Hydra: 10 }, META, h).score
  const both = scoreOf({ 'Эпик 35': 10, Hydra: 10 }, META, h).score
  assert.equal(a, 1350)                // 135 × 10
  assert.equal(b, 300)                 // 30 × 10: вес Hydra из шкалы, а не «1» из ручных очков клана
  assert.equal(both, a + b)
})

test('очки: норму можно закрыть только склепами, только EMC или смесью — важна сумма', () => {
  const h = 413
  const norm = normAt(h)
  const per = id => weightAt(id, h)
  const onlyCrypts = Math.ceil(norm / per('Epic Crypt 35'))
  const onlyEmc = Math.ceil(norm / per('Epic Shadow City'))
  assert.ok(scoreOf({ 'Эпик 35': onlyCrypts }, META, h).score >= norm)
  assert.ok(scoreOf({ 'Shadow City': onlyEmc }, META, h).score >= norm)
  const half = scoreOf({ 'Эпик 35': Math.ceil(onlyCrypts / 2), 'Shadow City': Math.ceil(onlyEmc / 2) }, META, h).score
  assert.ok(half >= norm)
})

test('очки EMC правятся пультом: поставили очки за монстра — сумма меняется', () => {
  const h = 413
  const base = scoreOf({ Hydra: 10 }, META, h).score
  const up = scoreOf({ Hydra: 10 }, META, h, { ...DEFAULT_SETTINGS, mix: { w: { 'Epic Fire Hydra': { all: 2 } } } }).score
  const off = scoreOf({ Hydra: 10 }, META, h, { ...DEFAULT_SETTINGS, mix: { w: { 'Epic Fire Hydra': { on: false } } } }).score
  assert.equal(up, base * 2)
  assert.equal(off, 0)
})

test('очки: тип вне шкалы (свой) входит в сумму по очкам клана', () => {
  assert.equal(scoreOf({ 'Тыква': 5 }, META, 300).score, 60)
})

test('синхронизация пульта и публичной страницы: EMC — только «Квота 2», остальное учитываемое — Crypts', () => {
  assert.equal(typeTab('Pumpkin Chest', 2), 'emc')
  assert.equal(typeTab('Epic Crypt 30', 1), 'crypts')
  assert.equal(typeTab('Rare Crypt 25', null), 'crypts')
  assert.equal(typeTab('Yogwai', null), 'crypts')            // без «Квоты 2» — не EMC, как бы ни назывался
  assert.equal(typeTab('Epic Fire Hydra', 1), 'crypts')
  const meta = { 'Тыква': { id: 'Pumpkin Chest', points: 1, slot: 2 }, Hydra: { id: 'Epic Fire Hydra', points: 1, slot: 2 } }
  assert.equal(emcOthersTotal(meta, 400), 9)         // «Тыква» = среднее четырёх, как в пульте
  assert.equal(emcCountAt('Pumpkin Chest', 400), 9)
})
