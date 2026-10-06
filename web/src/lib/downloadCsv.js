import { quotaCsv } from './emcQuota.js'

// Скачивание таблицы квоты как CSV (открывается в Excel/Google Таблицах). Браузерные API могут
// быть недоступны — тогда молча ничего не делаем, страница остаётся рабочей.
export function downloadQuotaCsv(table, lang) {
  try {
    const blob = new Blob([quotaCsv(table, lang)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'emc_quota.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch { /* не критично */ }
}
