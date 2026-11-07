// Цветовые группы сундуков (владелец 2026-11-07): цвет = принадлежность к группе, а не тип сундука.
// Один источник для публичной страницы и для «Сундуки → Общие нормы клана»: цвета одинаковы на всех языках.
//   squad     — «Рагнарек»: Эпический отряд Фенрира / Ёрмунганда — тёмно-синий
//   tartaros  — «Олимп»: склепы Тартароса, отряд Бриарея, Химера, Василиск — золотой
//   epicCrypt — эпические склепы                            — фиолетовый
//   rare      — редкие склепы                               — светло-синий
//   common    — обычные склепы                              — зелёный
//   emc       — остальные эпические монстры                 — неоновый
// Цитадели и нестандартные типы вне групп: group = null, без цвета и без полоски.
// Палитры в стиле имён таблицы лидерства (владелец 2026-11-07): у каждой группы градиент в своей гамме
// [светлый, средний, глубокий] — синий от голубого до синего, золото от бледного до тёмного и т.д.
// Сплошной заливки нет: градиент — в линии над столбцами и в тексте названия группы.
export const GROUP_PALETTE = {
  squad:     ['#8fb4ff', '#4f7be8', '#2646b4'],   // Рагнарек — сапфир: от васильково-голубого к синему
  tartaros:  ['#f6e3a1', '#d9a73a', '#9a6a16'],   // Олимп — золото: бледное → тёмное
  epicCrypt: ['#d2c0ff', '#9a78e6', '#5a3fb8'],   // эпические склепы — аметист → индиго
  rare:      ['#d8f0ff', '#8fd0ff', '#4aa3e8'],   // редкие склепы — от почти белого к небесно-голубому
  common:    ['#a8f0c8', '#5fc790', '#2a8f5c'],   // обычные склепы — изумруд
  citadel:   ['#a6ece6', '#4fc4b8', '#1a8a7e'],   // цитадели — бирюза
  emc:       ['#ffb09a', '#e8604a', '#a8261c'],   // остальные эпические монстры — от коралла к рубину
}
export const GROUP_COLOR = Object.fromEntries(Object.entries(GROUP_PALETTE).map(([g, p]) => [g, p[1]]))
export const paletteCss = group => {
  const p = GROUP_PALETTE[group]
  return p ? { '--g1': p[0], '--g2': p[1], '--g3': p[2] } : {}
}

export const GROUP_TITLE = {
  ru: { squad: 'Рагнарек', tartaros: 'Олимп', epicCrypt: 'Эпические склепы',
        rare: 'Редкие склепы', common: 'Обычные склепы', citadel: 'Цитадели', emc: 'Эпические монстры' },
  en: { squad: 'Ragnarok', tartaros: 'Olympus', epicCrypt: 'Epic crypts',
        rare: 'Rare crypts', common: 'Common crypts', citadel: 'Citadels', emc: 'Epic monsters' },
}

// Короткие названия — для группы из одного столбца, где полное не поместится (читается целиком, без подсказок)
export const GROUP_SHORT = {
  ru: { squad: 'Рагнарек', tartaros: 'Олимп', epicCrypt: 'Эпик', rare: 'Редкие', common: 'Обычные', citadel: 'Цитадели', emc: 'Монстры' },
  en: { squad: 'Ragnarok', tartaros: 'Olympus', epicCrypt: 'Epic', rare: 'Rare', common: 'Common', citadel: 'Citadels', emc: 'Monsters' },
}

export const isEpicCryptId = id => /^Epic Crypt\s+\d+$/.test(String(id || ''))

const SQUAD_IDS = new Set(['Epic Fenrir', 'Epic Jormungander'])
const TARTAROS_IDS = new Set(['Epic Briareus', 'Epic Chimera', 'Epic Basilisk'])

// Эпический монстр / событие EMC по каталожному id (склепы сюда не входят)
export const isEmcId = id => {
  const s = String(id || '')
  return !isEpicCryptId(s) && (/^Epic /.test(s) || s === 'Dark Omens Chest' || s === 'Yogwai')
}

// slot === 2 — сундук из квоты EMC: всё, что в EMC, но не в Олимпе/Рагнареке, — «Эпические монстры» (владелец 2026-11-07)
export function chestGroup(id, slot = null) {
  const s = String(id || '')
  if (SQUAD_IDS.has(s)) return 'squad'
  if (TARTAROS_IDS.has(s) || /^Tartaros Crypt\b/.test(s)) return 'tartaros'
  if (isEpicCryptId(s)) return 'epicCrypt'
  if (/^Rare Crypt\b/.test(s)) return 'rare'
  if (/^Common Crypt\b/.test(s)) return 'common'
  if (/Citadel/.test(s)) return 'citadel'
  if (isEmcId(s) || slot === 2) return 'emc'
  return null
}

export const groupColor = (id, slot = null) => GROUP_COLOR[chestGroup(id, slot)] || null
export const groupTitle = (group, lang, short = false) => ((short ? GROUP_SHORT : GROUP_TITLE)[lang] || (short ? GROUP_SHORT : GROUP_TITLE).en)[group]
