// Цветовые группы сундуков (владелец 2026-11-07): цвет = принадлежность к группе, а не тип сундука.
// Один источник для публичной страницы и для «Сундуки → Общие нормы клана»: цвета одинаковы на всех языках.
//   squad     — Эпический отряд Фенрира / Ёрмунганда        — тёмно-синий
//   tartaros  — склепы Тартароса, отряд Бриарея, Химера, Василиск — золотой
//   epicCrypt — эпические склепы                            — фиолетовый
//   rare      — редкие склепы                               — светло-синий
//   common    — обычные склепы                              — зелёный
//   emc       — остальные эпические монстры                 — неоновый
// Цитадели и нестандартные типы вне групп: group = null, без цвета и без полоски.
export const GROUP_COLOR = {
  squad:     '#3a5ff0',
  tartaros:  '#f5c518',
  epicCrypt: '#a855f7',
  rare:      '#7dd3fc',
  common:    '#4ade80',
  emc:       '#ff2bd6',
}

export const GROUP_TITLE = {
  ru: { squad: 'Эпические отряды', tartaros: 'Тартарос и Бриарей', epicCrypt: 'Эпические склепы',
        rare: 'Редкие склепы', common: 'Обычные склепы', emc: 'Эпические монстры' },
  en: { squad: 'Epic squads', tartaros: 'Tartaros & Briareus', epicCrypt: 'Epic crypts',
        rare: 'Rare crypts', common: 'Common crypts', emc: 'Epic monsters' },
}

export const isEpicCryptId = id => /^Epic Crypt\s+\d+$/.test(String(id || ''))

const SQUAD_IDS = new Set(['Epic Fenrir', 'Epic Jormungander'])
const TARTAROS_IDS = new Set(['Epic Briareus', 'Epic Chimera', 'Epic Basilisk'])

// Эпический монстр / событие EMC по каталожному id (склепы сюда не входят)
export const isEmcId = id => {
  const s = String(id || '')
  return !isEpicCryptId(s) && (/^Epic /.test(s) || s === 'Dark Omens Chest' || s === 'Yogwai')
}

export function chestGroup(id) {
  const s = String(id || '')
  if (SQUAD_IDS.has(s)) return 'squad'
  if (TARTAROS_IDS.has(s) || /^Tartaros Crypt\b/.test(s)) return 'tartaros'
  if (isEpicCryptId(s)) return 'epicCrypt'
  if (/^Rare Crypt\b/.test(s)) return 'rare'
  if (/^Common Crypt\b/.test(s)) return 'common'
  if (isEmcId(s)) return 'emc'
  return null
}

export const groupColor = id => GROUP_COLOR[chestGroup(id)] || null
export const groupTitle = (group, lang) => (GROUP_TITLE[lang] || GROUP_TITLE.en)[group]
