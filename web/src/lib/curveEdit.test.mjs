import test from 'node:test'
import assert from 'node:assert/strict'
import { BANDS, HANDLE_BANDS, centerOf, kernel, applyDrag, seriesOf, bandsFromTargets, bandsOutOfRange } from './curveEdit.js'
import { weightAt, DEFAULT_SETTINGS } from './heroQuota.js'
import { writeBands } from './curveLines.js'

test('ручки — каждые 50 уровней, 11 штук; ступень считается по середине', () => {
  assert.equal(HANDLE_BANDS.length, 11)
  assert.deepEqual([HANDLE_BANDS[0], HANDLE_BANDS[10]], [100, 600])
  assert.equal(centerOf(400), 405)
  assert.equal(centerOf(600), 600)
})

test('колокол: сама точка = 1, дальше убывает; мягкость 0 — только своя ступень', () => {
  assert.equal(kernel(0, 40), 1)
  assert.ok(kernel(50, 40) > kernel(100, 40) && kernel(100, 40) > 0)
  assert.equal(kernel(10, 0), 0)
  assert.equal(kernel(0, 0), 1)
  assert.equal(kernel(1000, 40), 0)
})

test('applyDrag: ручка уходит ровно на delta, соседи плавно, далёкие не двигаются, не ниже 0', () => {
  const start = BANDS.map(() => 40)
  const t = applyDrag(start, 300, 20, 30)
  assert.equal(t[BANDS.indexOf(300)], 60)
  assert.ok(t[BANDS.indexOf(310)] < 60 && t[BANDS.indexOf(310)] > t[BANDS.indexOf(350)])
  assert.equal(t[BANDS.indexOf(600)], 40)
  assert.ok(applyDrag(start, 300, -500, 30).every(v => v >= 0))
  assert.equal(applyDrag(start, 300, 20, 0)[BANDS.indexOf(310)], 40)
})

test('applyDrag не трогает закрытые ступени (в шкале 0)', () => {
  const start = BANDS.map(() => 10)
  const locked = new Set([410])
  assert.equal(applyDrag(start, 400, 30, 40, locked)[BANDS.indexOf(410)], 10)
})

test('круг: график → поправки ступеней → очки на странице совпадают с желаемыми (до округления в 5)', () => {
  for (const key of ['Epic Crypt 30', 'Rare Crypt 25', 'Citadel 30', 'Epic Fire Hydra']) {
    const scale = { ...DEFAULT_SETTINGS, mix: {} }
    const s = seriesOf(key, scale)
    const i = BANDS.indexOf(300)
    const target = s.cur.map(v => v)
    target[i] = s.cur[i] + 30
    const changed = target.map((v, j) => j === i)
    const bands = bandsFromTargets(target, s.ref, {}, changed)
    const after = { ...scale, mix: { w: { [key]: { on: true, all: 1, bands } } } }
    const got = weightAt(key, centerOf(300), after)
    assert.ok(Math.abs(got - target[i]) <= 5, `${key}: хотели ${target[i]}, получили ${got}`)
    // остальные ступени не изменились
    assert.equal(weightAt(key, centerOf(500), after), s.cur[BANDS.indexOf(500)])
  }
})

test('поправка около шкалы стирается, чтобы не копить шум', () => {
  const s = seriesOf('Epic Crypt 30', { ...DEFAULT_SETTINGS, mix: {} })
  const bands = bandsFromTargets(s.cont, s.ref, { 300: 1.5 }, s.cont.map((_, j) => BANDS[j] === 300))
  assert.equal('300' in bands, false)
})

test('тип без очков в шкале на этих уровнях открыт для правки (полная свобода, 2026-10-27): блокировок нет, ручку можно вести', () => {
  const s = seriesOf('Common Crypt 25', { ...DEFAULT_SETTINGS, mix: {} })
  assert.ok(!s.locked.has(500))
  assert.ok(!s.locked.has(200))
  assert.equal(s.zero[BANDS.indexOf(500)], true)
})

test('правка в обе стороны: вверх и обратно возвращает шкалу без следа в данных', () => {
  for (const key of ['Epic Crypt 30', 'Rare Crypt 25', 'Epic Fire Hydra', 'Citadel 30']) {
    for (const soft of [0, 30, 80]) {
      for (const [band, delta] of [[300, 40], [450, -15], [100, 60], [600, 25]]) {
        let mix = { w: { [key]: { on: true, all: 1, bands: {} } } }
        const step = d => {
          const sc = { ...DEFAULT_SETTINGS, mix }
          const s = seriesOf(key, sc)
          const t = applyDrag(s.cont, band, d, soft, s.locked)
          const changed = t.map((v, i) => Math.abs(v - s.cont[i]) > 1e-9)
          mix = { w: { [key]: { on: true, all: 1, bands: bandsFromTargets(t, s.ref, mix.w[key].bands, changed) } } }
        }
        step(delta)
        assert.ok(Object.keys(mix.w[key].bands).length > 0, `${key}/${soft}/${band}: после правки поправок нет`)
        step(-delta)
        assert.deepEqual(mix.w[key].bands, {}, `${key}/${soft}/${band}: после возврата остались поправки`)
        assert.equal(weightAt(key, centerOf(band), { ...DEFAULT_SETTINGS, mix }), weightAt(key, centerOf(band), DEFAULT_SETTINGS))
      }
    }
  }
})

test('несколько правок подряд и возврат по одной в обратном порядке дают исходное', () => {
  const key = 'Epic Crypt 35'
  let mix = { w: { [key]: { on: true, all: 1, bands: {} } } }
  const step = (band, d, soft) => {
    const s = seriesOf(key, { ...DEFAULT_SETTINGS, mix })
    const t = applyDrag(s.cont, band, d, soft, s.locked)
    mix = { w: { [key]: { on: true, all: 1, bands: bandsFromTargets(t, s.ref, mix.w[key].bands, t.map((v, i) => Math.abs(v - s.cont[i]) > 1e-9)) } } }
  }
  const ops = [[200, 30, 40], [350, -20, 40], [500, 25, 60]]
  ops.forEach(o => step(...o))
  ;[...ops].reverse().forEach(([b, d, soft]) => step(b, -d, soft))
  assert.deepEqual(mix.w[key].bands, {})
})

// Мелкие жесты: следы после возврата и шаг при больших значениях (отчёт проверки пульта 2026-10-26)
function gesture(key, all, ops) {
  let mix = { w: { [key]: { on: true, all, bands: {} } } }
  const scale = () => ({ ...DEFAULT_SETTINGS, mix })
  for (const [band, d, soft, snap] of ops) {
    const s = seriesOf(key, scale())
    const i = BANDS.indexOf(band)
    const delta = snap ? s.ref[i] - s.cont[i] : d
    const t = applyDrag(s.cont, band, delta, soft, s.locked)
    mix = { w: { [key]: { on: true, all, bands: bandsFromTargets(t, s.ref, mix.w[key].bands, t.map((v, j) => Math.abs(v - s.cont[j]) > 1e-9)) } } }
  }
  return { bands: mix.w[key].bands, at: h => weightAt(key, h, scale()) }
}

test('+1 и возврат магнитом, стрелки ↑×3 и ↓×3 не оставляют следов', () => {
  for (const key of ['Epic Crypt 30', 'Epic Crypt 35', 'Rare Crypt 25']) for (const soft of [0, 40, 100]) {
    assert.deepEqual(gesture(key, 1, [[250, 1, soft], [250, 0, soft, true]]).bands, {}, `${key}/${soft} магнит`)
    assert.deepEqual(gesture(key, 1, [[250, 1, soft], [250, 1, soft], [250, 1, soft], [250, -1, soft], [250, -1, soft], [250, -1, soft]]).bands, {}, `${key}/${soft} стрелки`)
  }
})

test('шаг 1 двигает ступень и при больших значениях', () => {
  const g = gesture('Epic Crypt 35', 3, [[300, 1, 40]])
  const base = gesture('Epic Crypt 35', 3, [])
  assert.equal(g.at(305), base.at(305) + 1)
})

test('если на странице ничего не отличается от шкалы, в данных пусто', () => {
  const s = seriesOf('Epic Crypt 30', { ...DEFAULT_SETTINGS, mix: {} })
  const tiny = s.cont.map(v => v + 0.3)
  assert.deepEqual(bandsFromTargets(tiny, s.ref, { 200: 1.001, 300: 0.999 }), {})
})

// ---- Нулевые уровни шкалы редактируются: Common Crypt 25 с Героя 400 (владелец 2026-10-27) ----
test('линия типа с нулём в шкале: ручки не заблокированы, на нулевых ступенях значение 0, опора > 0', () => {
  const id = 'Common Crypt 25'
  const line = seriesOf(id, { ...DEFAULT_SETTINGS, mix: {} })
  assert.equal(line.locked.size, 0, 'нет заблокированных ступеней')
  const i = BANDS.indexOf(450)
  assert.equal(line.cur[i], 0)
  assert.equal(line.cont[i], 0, 'правка стартует с 0, а не с единицы опоры')
  assert.ok(line.ref[i] > 0)
  assert.equal(line.zero[i], true)
  assert.equal(line.zero[BANDS.indexOf(300)], false)
})

test('правка нулевой ступени ручкой: поднимаем до 40 очков и возвращаем в 0 без следа в данных', () => {
  const id = 'Common Crypt 25'
  let st = { mix: {}, emc: {} }
  const lineOf = () => seriesOf(id, { ...DEFAULT_SETTINGS, mix: st.mix })
  const i = BANDS.indexOf(450)
  const l0 = lineOf()
  const up = applyDrag(l0.cont, 450, 40, 0, l0.locked)
  assert.equal(up[i], 40)
  st = writeBands(st, { path: 'w', key: id }, bandsFromTargets(up, l0.ref, l0.bands, up.map((v, k) => Math.abs(v - l0.cont[k]) > 1e-9), l0.zero))
  assert.equal(lineOf().cur[i], 40)
  assert.equal(weightAt(id, 455, { ...DEFAULT_SETTINGS, mix: st.mix }), 40)
  const l1 = lineOf()
  const down = applyDrag(l1.cont, 450, -40, 0, l1.locked)
  st = writeBands(st, { path: 'w', key: id }, bandsFromTargets(down, l1.ref, l1.bands, down.map((v, k) => Math.abs(v - l1.cont[k]) > 1e-9), l1.zero))
  assert.deepEqual(lineOf().bands, {})
  assert.equal(lineOf().cur[i], 0)
})

test('мягкая ручка на нуле: соседние нулевые ступени идут следом, ступени со шкалой — как всегда (множитель)', () => {
  const id = 'Common Crypt 25'
  const l0 = seriesOf(id, { ...DEFAULT_SETTINGS, mix: {} })
  const t = applyDrag(l0.cont, 400, 30, 60, l0.locked)
  const next = bandsFromTargets(t, l0.ref, l0.bands, t.map((v, k) => Math.abs(v - l0.cont[k]) > 1e-9), l0.zero)
  const s = { ...DEFAULT_SETTINGS, mix: { w: { [id]: { bands: next } } } }
  assert.ok(weightAt(id, 405, s) >= 29, 'ручка 30 на 400')
  assert.ok(weightAt(id, 455, s) > 0, 'сосед справа потянулся')
})

// ---- Ничего не обрезать молча (владелец 2026-10-27): значение за границами не записывается, а не подтягивается к границе ----
test('граница множителя 0,01…1000: ступень, которая вышла бы за неё, не записывается (без молчаливого обрезания)', () => {
  const line = seriesOf('Epic Crypt 35', { ...DEFAULT_SETTINGS, mix: {} })
  const i = BANDS.indexOf(400)
  const changed = BANDS.map((_, k) => k === i)
  const up = line.cont.map((v, k) => (k === i ? line.ref[k] * 5000 : v))      // ×5000 — за границей
  assert.equal(bandsOutOfRange(up, line.ref, changed, line.zero), true)
  assert.deepEqual(bandsFromTargets(up, line.ref, {}, changed, line.zero), {}, 'ничего не записано')
  const keep = bandsFromTargets(up, line.ref, { 400: 2 }, changed, line.zero)
  assert.equal(keep[400], 2, 'прежняя поправка осталась как была, а не стала 1000')
  const down = line.cont.map((v, k) => (k === i ? 0 : v))                     // 0 очков при базе 135 — множитель 0 за границей
  assert.equal(bandsOutOfRange(down, line.ref, changed, line.zero), true)
})

test('в границах и возврат к шкале — не «за границей»', () => {
  const line = seriesOf('Epic Crypt 35', { ...DEFAULT_SETTINGS, mix: {} })
  const i = BANDS.indexOf(400)
  const changed = BANDS.map((_, k) => k === i)
  assert.equal(bandsOutOfRange(line.cont.map((v, k) => (k === i ? line.ref[k] * 2 : v)), line.ref, changed, line.zero), false)
  assert.equal(bandsOutOfRange(line.cont, line.ref, changed, line.zero), false, 'значение шкалы — не правка')
  const z = seriesOf('Common Crypt 25', { ...DEFAULT_SETTINGS, mix: {} })
  const j = BANDS.indexOf(450)
  assert.equal(bandsOutOfRange(z.cont.map((v, k) => (k === j ? 40 : v)), z.ref, BANDS.map((_, k) => k === j), z.zero), false, 'на нулевом уровне 40 очков — в границах')
  assert.equal(bandsOutOfRange(z.cont.map((v, k) => (k === j ? 0 : v)), z.ref, BANDS.map((_, k) => k === j), z.zero), false, 'на нулевом уровне 0 — это шкала')
})
