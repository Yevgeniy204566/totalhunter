import test from 'node:test'
import assert from 'node:assert/strict'
import { loadPinned, savePinned, pinFirst } from './pinnedPlayer.js'

const P = ['A', 'B', 'C', 'D'].map(name => ({ name }))
const names = a => a.map(p => p.name)

test('закреплённый игрок становится первым, остальной порядок не меняется', () => {
  assert.deepEqual(names(pinFirst(P, 'C')), ['C', 'A', 'B', 'D'])
  assert.deepEqual(names(pinFirst(P, 'D')), ['D', 'A', 'B', 'C'])
})

test('уже первый, не найден или не выбран — список тот же', () => {
  assert.equal(pinFirst(P, 'A'), P)
  assert.equal(pinFirst(P, 'Нет такого'), P)
  assert.equal(pinFirst(P, null), P)
})

test('исходный массив не мутируется', () => {
  const copy = names(P)
  pinFirst(P, 'C')
  assert.deepEqual(names(P), copy)
})

test('без localStorage страница не падает', () => {
  assert.equal(typeof globalThis.localStorage, 'undefined')
  assert.equal(loadPinned('clan'), null)
  savePinned('clan', 'A')
})

test('сохранение и очистка по клану', () => {
  const store = {}
  globalThis.localStorage = {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v) },
    removeItem: k => { delete store[k] },
  }
  try {
    savePinned('clan1', 'Игрок')
    assert.equal(loadPinned('clan1'), 'Игрок')
    assert.equal(loadPinned('clan2'), null)
    savePinned('clan1', null)
    assert.equal(loadPinned('clan1'), null)
    assert.equal(loadPinned(null), null)
  } finally { delete globalThis.localStorage }
})
