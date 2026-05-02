import { createContext, useContext, useState, createElement } from 'react'

const LangContext = createContext(null)

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('th_lang') || 'ru')

  function toggle() {
    const next = lang === 'ru' ? 'en' : 'ru'
    localStorage.setItem('th_lang', next)
    setLang(next)
  }

  return createElement(LangContext.Provider, { value: { lang, toggle } }, children)
}

export function useLang() {
  return useContext(LangContext)
}
