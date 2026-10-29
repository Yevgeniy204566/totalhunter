import test from 'node:test'
import assert from 'node:assert/strict'
import { LABEL_INDEX, LABEL_ORDER, LABEL_ROWS_COUNT } from './labelDict.js'

test('у каждой строки словаря есть перевод на все языки бота', () => {
  assert.equal(LABEL_ORDER.length, 17)
  const rows = new Set(LABEL_INDEX.values())
  assert.equal(rows.size, LABEL_ROWS_COUNT)
  for (const row of rows) {
    for (const code of LABEL_ORDER) {
      assert.ok(row[code] && row[code].trim(), `пустой перевод: «${row.ru}» → ${code}`)
    }
  }
})

test('название сайта не входит в словарь (его нельзя подменять)', () => {
  assert.equal(LABEL_INDEX.has('hunter'), false)
  assert.equal(LABEL_INDEX.has('total hunter'), false)
  assert.equal(LABEL_INDEX.has('total battle'), false)
})

test('поиск не зависит от регистра английского заголовка', () => {
  // так ищет protectLabels.js: сначала как есть, потом в нижнем регистре
  const find = s => LABEL_INDEX.get(s) || LABEL_INDEX.get(s.toLowerCase())
  assert.equal(find('Referral Program'), find('Referral program'))
  assert.equal(find('Referral Program').uk, 'Реферальна програма')
})
