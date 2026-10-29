// Автоперевод Chrome ломает короткие подписи: без контекста «Сундуки» → «грудль», «Реферальный баланс» →
// «направление». Поэтому:
//  1) подпись из общего словаря (i18n/labelDict.js) подставляется на язык игрока и помечается translate="no";
//  2) подпись с игровым термином, которой в словаре нет, тоже защищается от автоперевода (остаётся на языке сайта);
//  3) все остальные подписи и все длинные тексты Chrome переводит как обычно.
// Подмена идёт только в текстовом узле подписи — структуру, которой владеет React, не трогаем.
import { LABEL_INDEX } from '../i18n/labelDict.js'
import { getLabelCode, subscribeLabelLang } from '../i18n/labelStore.js'

const MAX_LEN = 48
// Название бренда и игры (никогда не переводятся) + игровые и платёжные термины, которые Chrome без контекста переводит неверно
const TERM_RE = /total ?hunter|total ?battle|сундук|склеп|бирж|реферал|баланс|недел|алмаз|кредит|герой|героя|героев|древн|квот|сезон|цитадел|ростер|chest|crypt|exchange|referral|balance|week\b|diamond|credit|hero|ancient|quota|season|citadel|roster/i
const SELECTOR = [
  'a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'th', 'label', 'summary', 'legend', 'option', '[role="tab"]',
  '[class*="tab"]', '[class*="nav"]', '[class*="label"]', '[class*="title"]', '[class*="badge"]',
  '[class*="stat"]', '[class*="chip"]', '[class*="btn"]', '[class*="head"]', '[class*="name"]',
].join(',')

const textState = new WeakMap()   // текстовый узел → { src: исходный текст, shown: что показано }
const protectedByUs = new WeakSet() // элементы, которым translate="no" поставили мы

const isShort = s => s.length > 0 && s.length <= MAX_LEN && !/[.!?]\s*\S/.test(s)

function localizeTextNode(node) {
  const el = node.parentElement
  if (!el || el.childNodes.length !== 1) return false
  const value = node.nodeValue || ''
  const core = value.trim()
  if (!core || core.length > MAX_LEN) return false
  // Логотип «Total» + «Hunter» — название бренда: не подменять и не отдавать автопереводу («Total» → «Усього»)
  if (/^(Total|Hunter)$/.test(core)) {
    const sib = el.nextElementSibling || el.previousElementSibling
    if (sib && /^(Total|Hunter)$/.test(sib.textContent.trim())) {
      if (!el.hasAttribute('translate')) el.setAttribute('translate', 'no')
      return true
    }
  }
  const st = textState.get(node)
  const full = st && core === st.shown ? st.src : core   // значение изменил React — это новый источник
  // значки и стрелки по краям («⬇ Скачать», «Войти →») в поиск не входят, но остаются на месте
  const [, pre, body, post] = full.match(/^([^\p{L}\p{N}]*)(.*?)([^\p{L}\p{N}]*)$/su)
  const row = LABEL_INDEX.get(body) || LABEL_INDEX.get(body.toLowerCase())
  if (!row) { textState.delete(node); return false }
  const code = getLabelCode()
  const word = code ? row[code] : undefined
  if (word) {
    const target = pre + word + post
    // уже на нужном языке (отличается лишь регистром, например «Referral Program») — текст не трогаем
    if (target.toLowerCase() !== core.toLowerCase()) {
      const lead = value.match(/^\s*/)[0], trail = value.match(/\s*$/)[0]
      node.nodeValue = lead + target + trail
      textState.set(node, { src: full, shown: target })
    }
  } else if (st && st.src !== core) {
    node.nodeValue = value.replace(core, st.src)   // язык не задан — вернуть исходный текст
    textState.delete(node)
  }
  if (!el.hasAttribute('translate')) { el.setAttribute('translate', 'no'); protectedByUs.add(el) }
  return true
}

function protectTerm(el) {
  const text = (el.textContent || '').trim()
  const need = isShort(text) && TERM_RE.test(text)
  if (need && !el.hasAttribute('translate')) { el.setAttribute('translate', 'no'); protectedByUs.add(el) }
  else if (!need && protectedByUs.has(el) && !LABEL_INDEX.has(text.toLowerCase())) { el.removeAttribute('translate'); protectedByUs.delete(el) }
}

function process(root) {
  if (root.nodeType === 3) { if (root.parentElement) process(root.parentElement); return }
  if (root.nodeType !== 1) return
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const dictEls = new Set()
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (localizeTextNode(n)) dictEls.add(n.parentElement)
  }
  const els = [root, ...root.querySelectorAll(SELECTOR)]
  for (const el of els) if (el.matches?.(SELECTOR) && !dictEls.has(el)) protectTerm(el)
}

export function startProtectLabels() {
  if (typeof document === 'undefined' || typeof MutationObserver === 'undefined') return
  let queued = false
  const pending = new Set()
  const flush = () => {
    queued = false
    pending.forEach(n => { if (n.isConnected) process(n) })
    pending.clear()
  }
  const schedule = n => {
    pending.add(n)
    if (!queued) { queued = true; setTimeout(flush, 50) }
  }
  new MutationObserver(muts => {
    for (const m of muts) {
      if (m.type === 'childList') m.addedNodes.forEach(n => (n.nodeType === 1 || n.nodeType === 3) && schedule(n))
      else if (m.type === 'characterData') schedule(m.target)
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true })
  subscribeLabelLang(() => schedule(document.body))   // язык подписей сменили — пройти по всей странице
  schedule(document.body)
}
