// Язык подписей интерфейса: выбор игрока (запоминается) → язык браузера, если он не ru/en → не задан.
// «Не задан» = подписи остаются на языке самого сайта (ru/en), его выбирает кнопка RU/EN.
// Без React и роутера: модуль нужен и публичным страницам кланов, и кабинету.
import { LABEL_ORDER } from './labelDict.js'

export const ALL_CODES = ['ru', 'en', ...LABEL_ORDER]
const STORE_KEY = 'th_label_lang'
const listeners = new Set()

export function detectBrowserLang() {
  const raw = (typeof navigator !== 'undefined' ? navigator.language || '' : '').toLowerCase().replace('-', '_')
  if (/^zh_(tw|hk|mo|hant)/.test(raw)) return 'zh_tw'
  const base = raw.split('_')[0]
  if (base === 'nb' || base === 'nn') return 'no'
  return LABEL_ORDER.includes(base) ? base : undefined
}

function readStored() {
  try { const v = localStorage.getItem(STORE_KEY); return ALL_CODES.includes(v) ? v : undefined } catch { return undefined }
}

let chosen = readStored()
let auto = detectBrowserLang()

export const getChosen = () => chosen
export const getLabelCode = () => chosen || auto

export function chooseLabelLang(code) {
  chosen = code
  try { localStorage.setItem(STORE_KEY, code) } catch { /* без хранилища выбор живёт до перезагрузки */ }
  listeners.forEach(fn => fn())
}

export function subscribeLabelLang(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
