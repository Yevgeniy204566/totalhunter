import test from 'node:test'
import assert from 'node:assert/strict'
import { quotaLabel } from './quotaLabel.js'

test('русский язык — название как задано', () => {
  assert.equal(quotaLabel('Склепы', 'ru'), 'Склепы')
})
test('любой не русский язык — английское слово', () => {
  for (const l of ['en', 'uk', 'de', 'ja', 'ko']) assert.equal(quotaLabel('Склепы', l), 'Crypts')
})
test('английское название не ломается, своё слово клана остаётся', () => {
  assert.equal(quotaLabel('Crypts', 'de'), 'Crypts')
  assert.equal(quotaLabel('EMC', 'de'), 'EMC')
  assert.equal(quotaLabel('Супер-норма', 'en'), 'Супер-норма')
  assert.equal(quotaLabel('', 'en'), '')
})
