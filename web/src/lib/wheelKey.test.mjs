import test from 'node:test'
import assert from 'node:assert/strict'
import { wheelKeyShouldSpin } from './wheelKey.js'

const key = (code, target = { tagName: 'BODY' }) => ({ code, target })
const button = (disabled = false) => ({ disabled })

test('Space и Enter на странице рулетки запускают вращение', () => {
  assert.equal(wheelKeyShouldSpin(key('Space'), button()), true)
  assert.equal(wheelKeyShouldSpin(key('Enter'), button()), true)
})

test('в поле ввода колесо не трогает ни пробел, ни Enter (баг: пробелы не печатались в форме обратной связи)', () => {
  for (const tagName of ['TEXTAREA', 'INPUT', 'SELECT']) {
    assert.equal(wheelKeyShouldSpin(key('Space', { tagName }), button()), false, tagName)
    assert.equal(wheelKeyShouldSpin(key('Enter', { tagName }), button()), false, tagName)
  }
  assert.equal(wheelKeyShouldSpin(key('Space', { tagName: 'DIV', isContentEditable: true }), button()), false)
})

test('нет кнопки вращения на странице (колесо размонтировано) — клавиши не перехватываются', () => {
  assert.equal(wheelKeyShouldSpin(key('Space'), null), false)
  assert.equal(wheelKeyShouldSpin(key('Enter'), undefined), false)
})

test('кнопка заблокирована (идёт вращение) — повторного запуска нет', () => {
  assert.equal(wheelKeyShouldSpin(key('Space'), button(true)), false)
})

test('остальные клавиши колесо не интересуют', () => {
  assert.equal(wheelKeyShouldSpin(key('KeyA'), button()), false)
  assert.equal(wheelKeyShouldSpin(key('Tab'), button()), false)
})
