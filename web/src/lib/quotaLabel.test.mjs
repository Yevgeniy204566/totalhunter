import test from 'node:test'
import assert from 'node:assert/strict'
import { quotaLabel } from './quotaLabel.js'

test('название переводится на выбранный язык', () => {
  assert.equal(quotaLabel('Склепы', 'ru'), 'Склепы')
  assert.equal(quotaLabel('Склепы', 'en'), 'Crypts')
  assert.equal(quotaLabel('Склепы', 'de'), 'Krypten')
  assert.equal(quotaLabel('Склепы', 'uk'), 'Склепи')
  assert.equal(quotaLabel('Crypts', 'ru'), 'Склепы')
})
test('название вне словаря и пустое остаются как есть', () => {
  assert.equal(quotaLabel('EMC', 'de'), 'EMC')
  assert.equal(quotaLabel('Супер-норма', 'en'), 'Супер-норма')
  assert.equal(quotaLabel('', 'en'), '')
})
