import test from 'node:test'
import assert from 'node:assert/strict'
import { orderChestTypes } from './chestTypeOrder.js'

// набор типов ELDORADO: имена столбцов → id и очки клана (как отдаёт сервер в chest_type_meta)
const META = {
  'Epic Crypt 30': { id: 'Epic Crypt 30', points: 80, slot: 1 },
  'Epic Crypt 35': { id: 'Epic Crypt 35', points: 135, slot: 1 },
  'Epic Crypt 25': { id: 'Epic Crypt 25', points: 45, slot: 1 },
  'Epic Crypt 20': { id: 'Epic Crypt 20', points: 25, slot: 1 },
  Pumpkin: { id: 'Pumpkin', points: 1, slot: 2 },
  Hydra: { id: 'Epic Fire Hydra', points: 1, slot: 2 },
  Undead: { id: 'Epic Undead', points: 1, slot: 2 },
  'Epic Shadow City': { id: 'Epic Shadow City', points: 1, slot: 2 },
  Arachna: { id: 'Epic Arachne', points: 1, slot: 2 },
  'Common Crypt 25': { id: 'Common Crypt 25', points: 15, slot: null },
  'Rare Crypt 30': { id: 'Rare Crypt 30', points: 65, slot: null },
  'Rare Crypt 25': { id: 'Rare Crypt 25', points: 35, slot: null },
  'Elven Citadel 30': { id: 'Elven Citadel 30', points: 40, slot: null },
  'Elven Citadel 25': { id: 'Elven Citadel 25', points: 25, slot: null },
}
// порядок, в котором сервер отдаёт столбцы (по квоте и количеству) — перемешан
const SERVER = ['Epic Crypt 30', 'Epic Crypt 35', 'Epic Crypt 25', 'Epic Crypt 20', 'Pumpkin', 'Hydra', 'Undead', 'Epic Shadow City',
  'Arachna', 'Common Crypt 25', 'Rare Crypt 30', 'Rare Crypt 25', 'Elven Citadel 30', 'Elven Citadel 25']

test('порядок столбцов: эпик-склепы 35/30/25/20, потом монстры EMC, потом остальные по типам от старшего к младшему', () => {
  const out = orderChestTypes(SERVER, META)
  assert.deepEqual(out.slice(0, 4), ['Epic Crypt 35', 'Epic Crypt 30', 'Epic Crypt 25', 'Epic Crypt 20'])
  // монстры EMC по очкам таблицы T9 (у ELDORADO очки клана за них 1, поэтому берём таблицу), события вроде Pumpkin — в конец группы
  assert.deepEqual(out.slice(4, 9), ['Epic Shadow City', 'Arachna', 'Hydra', 'Undead', 'Pumpkin'])
  // остальные: типы по убыванию лучшего сундука, внутри типа — уровни по убыванию (цитадели 30/25, обычный склеп 25)
  assert.deepEqual(out.slice(9), ['Rare Crypt 30', 'Rare Crypt 25', 'Elven Citadel 30', 'Elven Citadel 25', 'Common Crypt 25'])
  assert.equal(out.length, SERVER.length) // ничего не потеряно и не задвоено
})

test('в порядке только те типы, которые бьют игроки: нет Epic Crypt 15 — столбца нет', () => {
  assert.ok(!orderChestTypes(SERVER, META).includes('Epic Crypt 15'))
  const some = orderChestTypes(['Common Crypt 25', 'Epic Crypt 35'], META)
  assert.deepEqual(some, ['Epic Crypt 35', 'Common Crypt 25'])
})

test('Cursed и Elven цитадели одного уровня идут рядом, уровни по убыванию', () => {
  const meta = { ...META, 'Cursed Citadel 25': { id: 'Cursed Citadel 25', points: 25, slot: null } }
  const out = orderChestTypes([...SERVER, 'Cursed Citadel 25'], meta)
  const i30 = out.indexOf('Elven Citadel 30'), i25a = out.indexOf('Cursed Citadel 25'), i25b = out.indexOf('Elven Citadel 25')
  assert.ok(i30 < i25a && i30 < i25b && Math.abs(i25a - i25b) === 1)
})

test('нет метаданных типов (старый архив) — порядок сервера не меняется', () => {
  assert.deepEqual(orderChestTypes(SERVER, null), SERVER)
  assert.deepEqual(orderChestTypes(SERVER, undefined), SERVER)
})

test('неизвестные и нестандартные типы уходят в конец, но не теряются', () => {
  const meta = { ...META, 'Свой тип': { id: 'Свой тип', points: 7, slot: null }, Arena: { id: 'Arena', points: 3, slot: null } }
  const out = orderChestTypes([...SERVER, 'Свой тип', 'Arena'], meta)
  assert.deepEqual(out.slice(-2).sort(), ['Arena', 'Свой тип'].sort())
  assert.equal(out.length, SERVER.length + 2)
})
