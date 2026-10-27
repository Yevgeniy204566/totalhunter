import test from 'node:test'
import assert from 'node:assert/strict'
import { barFillColor, barColor, BAR_DONE } from './progressColor.js'

const hue = c => Number(/^hsl\((\d+)/.exec(c)[1])

test('полоса прогресса: от фиолетового (ноль) к синему (99%), оттенок только сдвигается к синему', () => {
  assert.equal(hue(barFillColor(0)), 260) // фиолетовый
  let prev = 261
  for (let pct = 0; pct <= 99; pct++) {
    const h = hue(barFillColor(pct))
    assert.ok(h <= prev, `оттенок вернулся назад @${pct}%`)
    assert.ok(h >= 215 && h <= 260, `вне диапазона фиолетовый→синий @${pct}%: ${h}`)
    prev = h
  }
  const h99 = hue(barFillColor(99))
  assert.ok(h99 >= 215 && h99 <= 225, `99% должна быть синей: ${h99}`)
})

test('полоса прогресса: на 100% и выше — зелёная, и только на них', () => {
  for (const pct of [100, 101, 150, 480]) assert.equal(barFillColor(pct), BAR_DONE, `${pct}%`)
  for (let pct = 0; pct < 100; pct++) assert.notEqual(barFillColor(pct), BAR_DONE, `${pct}% ещё не зелёная`)
  assert.equal(BAR_DONE, '#287A50')
})

test('плохие значения процента не ломают цвет', () => {
  assert.equal(hue(barFillColor(-20)), 260)
  assert.equal(hue(barFillColor(NaN)), 260)
  assert.equal(barFillColor(Infinity), BAR_DONE)
})

test('заливка ячейки (тихая палитра): тот же закон — фиолетовый → синий до 99%, зелёная на 100% и выше', () => {
  assert.equal(hue(barColor(0)), 260)
  let prev = 261
  for (let pct = 0; pct <= 99; pct++) { const h = hue(barColor(pct)); assert.ok(h <= prev && h >= 215, `@${pct}%`); prev = h }
  const h99 = hue(barColor(99)); assert.ok(h99 >= 215 && h99 <= 225, `99%: ${h99}`)
  for (const pct of [100, 130, 480]) assert.equal(hue(barColor(pct)), 150, `${pct}% зелёная`)
})
