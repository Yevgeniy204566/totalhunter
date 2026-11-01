// Подсказки правильного имени для корявого прочтения. Только предлагаем — выбирает человек.
// Сходство считается по «упрощённому» виду: регистр, пробелы и знаки убраны, похожие кириллические
// и латинские буквы приведены к одной (OCR путает А/A, Е/E, О/O и т.п.).
const HOMOGLYPH = {
  а: 'a', в: 'b', е: 'e', к: 'k', м: 'm', н: 'h', о: 'o', р: 'p', с: 'c', т: 't', у: 'y', х: 'x',
  ё: 'e', з: '3', '0': 'o', '1': 'l', '|': 'l', і: 'i', ї: 'i', є: 'e',
}

export function simplify(name) {
  return [...String(name || '').toLowerCase()]
    .map(ch => HOMOGLYPH[ch] || ch)
    .filter(ch => /[\p{L}\p{N}]/u.test(ch))
    .join('')
}

function levenshtein(a, b) {
  const m = a.length, n = b.length
  if (!m) return n
  if (!n) return m
  let prev = Array.from({ length: n + 1 }, (_, j) => j)
  for (let i = 1; i <= m; i++) {
    const cur = [i]
    for (let j = 1; j <= n; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
    }
    prev = cur
  }
  return prev[n]
}

export function similarity(a, b) {
  const x = simplify(a), y = simplify(b)
  if (!x || !y) return 0
  if (x === y) return 1
  const base = 1 - levenshtein(x, y) / Math.max(x.length, y.length)
  // одно имя внутри другого («Крилата» / «Крилата W») — почти наверняка тот же игрок
  const inside = (x.includes(y) || y.includes(x)) ? 0.85 : 0
  return Math.max(base, inside)
}

// До `limit` самых похожих имён из пула; сам текущий вариант не предлагаем.
export function suggestNames(raw, pool, limit = 8, minScore = 0.4) {
  return (pool || [])
    .filter(n => n !== raw)
    .map(n => ({ n, s: similarity(raw, n) }))
    .filter(x => x.s >= minScore)
    .sort((p, q) => q.s - p.s || p.n.localeCompare(q.n))
    .slice(0, limit)
    .map(x => x.n)
}
