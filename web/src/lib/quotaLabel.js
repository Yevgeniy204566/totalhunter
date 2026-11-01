// Название квоты («Склепы») задаёт клан и хранится как текст. Фрагмент в шапке публичной таблицы помечен
// translate="no", поэтому ни Chrome, ни protectLabels его не трогали — слово оставалось русским при любом языке
// (владелец 2026-11-01). Решение владельца: название переводится на выбранный язык по словарю подписей
// (i18n/labelDict.js, 19 языков). Названия вне словаря («EMC», свои слова клана) остаются как есть.
import { useSyncExternalStore } from 'react'
import { LABEL_INDEX } from '../i18n/labelDict.js'
import { getLabelCode, subscribeLabelLang } from '../i18n/labelStore.js'

export function quotaLabel(name, lang) {
  if (!name || !lang) return name
  const row = LABEL_INDEX.get(name.trim()) || LABEL_INDEX.get(name.trim().toLowerCase())
  return row ? (row[lang] || row.en || name) : name
}

// effectiveLang: выбор подписей игрока (или язык браузера, если не ru/en) важнее кнопки RU/EN страницы
export function useQuotaLabel(pageLang) {
  const code = useSyncExternalStore(subscribeLabelLang, getLabelCode, getLabelCode)
  const eff = code || pageLang
  return name => quotaLabel(name, eff)
}
