// Автоперевод Chrome ломает короткие подписи: без контекста «Сундуки» → «грудль», «Реферальный баланс» →
// «направление». Поэтому названия разделов, вкладок, кнопок, заголовков и шапок таблиц помечаются translate="no"
// и остаются на языке сайта (RU/EN). Абзацы и длинные тексты переводятся как раньше.
// Атрибут ставится по DOM после отрисовки: React чужие атрибуты не трогает, на гидратацию это не влияет.
const SELECTOR = [
  'a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'th', 'label', 'summary', 'legend', 'option', '[role="tab"]',
  '[class*="tab"]', '[class*="nav"]', '[class*="label"]', '[class*="title"]', '[class*="badge"]',
  '[class*="stat"]', '[class*="chip"]', '[class*="btn"]', '[class*="head"]', '[class*="name"]',
].join(',')

const MAX_LEN = 48

function isShortLabel(el) {
  const text = (el.textContent || '').trim()
  return text.length > 0 && text.length <= MAX_LEN && !/[.!?]\s*\S/.test(text)
}

function mark(root) {
  const list = root.nodeType === 1 ? [root, ...root.querySelectorAll(SELECTOR)] : []
  for (const el of list) {
    if (!el.matches(SELECTOR) || el.hasAttribute('translate')) continue
    if (isShortLabel(el)) el.setAttribute('translate', 'no')
  }
}

export function startProtectLabels() {
  if (typeof document === 'undefined' || typeof MutationObserver === 'undefined') return
  let queued = false
  const pending = new Set()
  const flush = () => {
    queued = false
    pending.forEach(n => { if (n.isConnected) mark(n) })
    pending.clear()
  }
  const schedule = n => {
    pending.add(n)
    if (!queued) { queued = true; setTimeout(flush, 50) }
  }
  new MutationObserver(muts => {
    for (const m of muts) {
      if (m.type === 'childList') m.addedNodes.forEach(n => n.nodeType === 1 && schedule(n))
      // текст подписи сменился (например, переключили язык) — перепроверить ближайший элемент
      else if (m.type === 'characterData' && m.target.parentElement) schedule(m.target.parentElement)
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true })
  schedule(document.body)
}
