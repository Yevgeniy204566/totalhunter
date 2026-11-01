// Название квоты («Склепы») задаёт клан и хранится как текст. Фрагмент в шапке публичной таблицы помечен
// translate="no", поэтому ни Chrome, ни protectLabels его не трогают — слово оставалось русским при любом языке
// (владелец 2026-11-01). Решение владельца: русский язык — как задано; любой другой — английское слово из словаря.
// Название, которого нет в словаре («EMC», свои слова клана), остаётся как есть.
import { useSyncExternalStore } from 'react'
import { LABEL_INDEX } from '../i18n/labelDict.js'
import { getLabelCode, subscribeLabelLang } from '../i18n/labelStore.js'

export function quotaLabel(name, effectiveLang) {
  if (!name || effectiveLang === 'ru') return name
  return LABEL_INDEX.get(name.trim())?.en ?? LABEL_INDEX.get(name.trim().toLowerCase())?.en ?? name
}

// effectiveLang: выбор подписей игрока (или язык браузера, если не ru/en) важнее кнопки RU/EN страницы
export function useQuotaLabel(pageLang) {
  const code = useSyncExternalStore(subscribeLabelLang, getLabelCode, getLabelCode)
  const eff = code || pageLang
  return name => quotaLabel(name, eff)
}
