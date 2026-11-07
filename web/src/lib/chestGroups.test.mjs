import test from 'node:test'
import assert from 'node:assert/strict'
import { chestGroup, groupColor, GROUP_COLOR, groupTitle } from './chestGroups.js'
import { orderChestTypes } from './chestTypeOrder.js'

test('группы по каталожному id', () => {
  assert.equal(chestGroup('Epic Fenrir'), 'squad')
  assert.equal(chestGroup('Epic Jormungander'), 'squad')
  for (const id of ['Tartaros Crypt 35', 'Tartaros Crypt 10', 'Epic Briareus', 'Epic Chimera', 'Epic Basilisk']) {
    assert.equal(chestGroup(id), 'tartaros', id)
  }
  assert.equal(chestGroup('Epic Crypt 30'), 'epicCrypt')
  assert.equal(chestGroup('Rare Crypt 25'), 'rare')
  assert.equal(chestGroup('Common Crypt 20'), 'common')
  for (const id of ['Epic Fire Hydra', 'Epic Undead', 'Epic Arachne', 'Epic Shadow City', 'Yogwai', 'Dark Omens Chest']) {
    assert.equal(chestGroup(id), 'emc', id)
  }
  assert.equal(chestGroup('Elven Citadel 30'), null)
  assert.equal(chestGroup('Свой тип'), null)
  assert.equal(chestGroup(null), null)
})

test('шесть цветов, все разные; светло-синий (редкие) и тёмно-синий (отряды) — не один цвет', () => {
  const colors = Object.values(GROUP_COLOR)
  assert.equal(new Set(colors).size, 6)
  assert.notEqual(groupColor('Rare Crypt 25'), groupColor('Epic Fenrir'))
  assert.equal(groupColor('Elven Citadel 25'), null)
})

test('названия групп: ru и en, на других языках — английские', () => {
  assert.equal(groupTitle('tartaros', 'ru'), 'Олимп')
  assert.equal(groupTitle('squad', 'ru'), 'Рагнарек')
  assert.equal(groupTitle('tartaros', 'en'), 'Olympus')
  assert.equal(groupTitle('squad', 'en'), 'Ragnarok')
  assert.equal(groupTitle('rare', 'de'), 'Rare crypts')
})

test('на публичной странице столбцы одной группы стоят рядом (полоска над ними непрерывна)', () => {
  const ids = ['Epic Crypt 35', 'Epic Fenrir', 'Tartaros Crypt 35', 'Rare Crypt 30', 'Epic Briareus', 'Epic Fire Hydra',
    'Epic Jormungander', 'Epic Chimera', 'Common Crypt 25', 'Tartaros Crypt 30', 'Epic Basilisk', 'Epic Undead']
  const meta = Object.fromEntries(ids.map(id => [id, { id, points: 10, slot: /^Epic (?!Crypt)/.test(id) ? 2 : null }]))
  const out = orderChestTypes(ids, meta)
  assert.equal(out.length, ids.length)
  // эпик-склепы по-прежнему первыми
  assert.equal(out[0], 'Epic Crypt 35')
  const seen = []
  for (const n of out) {
    const g = chestGroup(n)
    if (g && seen[seen.length - 1] !== g) {
      assert.ok(!seen.includes(g), `группа ${g} разорвана: ${out.join(' | ')}`)
      seen.push(g)
    }
  }
})

test('всё из квоты EMC (slot 2), что не в Олимпе и Рагнареке, — «Эпические монстры»', () => {
  assert.equal(chestGroup('Pumpkin', 2), 'emc')
  assert.equal(chestGroup('Свой монстр', 2), 'emc')
  assert.equal(chestGroup('Epic Briareus', 2), 'tartaros')
  assert.equal(chestGroup('Epic Fenrir', 2), 'squad')
  assert.equal(chestGroup('Pumpkin', null), null)
})
