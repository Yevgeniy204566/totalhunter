// Защита от повторного запуска одного и того же действия, пока оно ещё идёт (например «Сохранить имена»):
// второй и третий клик, пока первый запрос в пути, игнорируются. Вчера (2026-11-13 22:10 UTC) три быстрых
// клика ушли на сервер тремя одновременными запросами, и последний получил 500.
export function createKeyedGuard() {
  const running = new Set()
  return {
    isRunning: key => running.has(key),
    // Возвращает результат fn или undefined, если действие с таким key уже идёт.
    async run(key, fn) {
      if (running.has(key)) return undefined
      running.add(key)
      try { return await fn() } finally { running.delete(key) }
    },
  }
}
