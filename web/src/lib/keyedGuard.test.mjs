import test from 'node:test'
import assert from 'node:assert/strict'
import { createKeyedGuard } from './keyedGuard.js'

const sleep = ms => new Promise(r => setTimeout(r, ms))

test('повторный запуск того же ключа, пока идёт первый, игнорируется', async () => {
  const g = createKeyedGuard()
  let calls = 0
  const job = async () => { calls += 1; await sleep(30); return 'ok' }
  const results = await Promise.all([g.run('clan', job), g.run('clan', job), g.run('clan', job)])
  assert.equal(calls, 1)
  assert.deepEqual(results, ['ok', undefined, undefined])
})

test('после завершения можно запустить снова', async () => {
  const g = createKeyedGuard()
  let calls = 0
  await g.run('clan', async () => { calls += 1 })
  await g.run('clan', async () => { calls += 1 })
  assert.equal(calls, 2)
  assert.equal(g.isRunning('clan'), false)
})

test('разные ключи не мешают друг другу', async () => {
  const g = createKeyedGuard()
  let calls = 0
  const job = async () => { calls += 1; await sleep(20) }
  await Promise.all([g.run('a', job), g.run('b', job)])
  assert.equal(calls, 2)
})

test('ошибка внутри не оставляет ключ занятым', async () => {
  const g = createKeyedGuard()
  await assert.rejects(g.run('clan', async () => { throw new Error('boom') }))
  assert.equal(g.isRunning('clan'), false)
  assert.equal(await g.run('clan', async () => 5), 5)
})
