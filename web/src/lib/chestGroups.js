// Цветовые группы сундуков (владелец 2026-11-07): цвет = принадлежность к группе, а не тип сундука.
// Один источник для публичной страницы и для «Сундуки → Общие нормы клана»: цвета одинаковы на всех языках.
//   squad     — «Рагнарек»: Эпический отряд Фенрира / Ёрмунганда — тёмно-синий
//   tartaros  — «Олимп»: склепы Тартароса, отряд Бриарея, Химера, Василиск — золотой
//   epicCrypt — эпические склепы                            — фиолетовый
//   rare      — редкие склепы                               — светло-синий
//   common    — обычные склепы                              — зелёный
//   emc       — остальные эпические монстры                 — неоновый
// Цитадели и нестандартные типы вне групп: group = null, без цвета и без полоски.
export const GROUP_COLOR = {
  squad:     '#5468b4',
  tartaros:  '#a8903f',
  epicCrypt: '#8566a8',
  rare:      '#6d9ab5',
  common:    '#5f9272',
  emc:       '#b0615f',
}

export const GROUP_TITLE = {
  ru: { squad: 'Рагнарек', tartaros: 'Олимп', epicCrypt: 'Эпические склепы',
        rare: 'Редкие склепы', common: 'Обычные склепы', emc: 'Эпические монстры' },
  en: { squad: 'Ragnarok', tartaros: 'Olympus', epicCrypt: 'Epic crypts',
        rare: 'Rare crypts', common: 'Common crypts', emc: 'Epic monsters' },
}

// Короткие названия — для группы из одного столбца, где полное не поместится (читается целиком, без подсказок)
export const GROUP_SHORT = {
  ru: { squad: 'Рагнарек', tartaros: 'Олимп', epicCrypt: 'Эпик', rare: 'Редкие', common: 'Обычные', emc: 'Монстры' },
  en: { squad: 'Ragnarok', tartaros: 'Olympus', epicCrypt: 'Epic', rare: 'Rare', common: 'Common', emc: 'Monsters' },
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
  if (isEmcId(s) || slot === 2) return 'emc'
  return null
}

export const groupColor = (id, slot = null) => GROUP_COLOR[chestGroup(id, slot)] || null
export const groupTitle = (group, lang, short = false) => ((short ? GROUP_SHORT : GROUP_TITLE)[lang] || (short ? GROUP_SHORT : GROUP_TITLE).en)[group]
