// Нужно ли колесу удачи (страница «Заработать») реагировать на нажатую клавишу.
// Поля ввода колесо не трогает: раньше его обработчик глотал Space и Enter на всём окне и после захода
// на «Заработать» в форме обратной связи не печатались пробелы и переводы строк.
export function wheelKeyShouldSpin(e, spinBtn) {
  if (e.code !== 'Space' && e.code !== 'Enter') return false
  const t = e.target
  const tag = t && t.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return false
  return !!spinBtn && !spinBtn.disabled
}
