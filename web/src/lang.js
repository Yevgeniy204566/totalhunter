import { createContext, useContext, useState, useEffect, createElement } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

const LangContext = createContext(null)

const TRANSLATABLE = ['/', '/features', '/guide', '/legal', '/contacts', '/download', '/login']

function getBasePath(pathname) {
  return pathname.startsWith('/ru') ? (pathname.slice(3) || '/') : pathname
}

function isTranslatable(pathname) {
  return TRANSLATABLE.includes(getBasePath(pathname))
}

export function LangProvider({ children }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  const onPublic = !pathname.startsWith('/dashboard')
  const urlLang  = pathname.startsWith('/ru') ? 'ru' : 'en'

  const [storedLang, setStoredLang] = useState(
    () => localStorage.getItem('th_lang') || 'en'
  )

  const lang = onPublic ? urlLang : storedLang

  useEffect(() => {
    document.documentElement.setAttribute('lang', lang)
  }, [lang])

  function toggle() {
    const next = lang === 'ru' ? 'en' : 'ru'
    localStorage.setItem('th_lang', next)
    setStoredLang(next)

    if (onPublic && isTranslatable(pathname)) {
      if (next === 'ru') {
        navigate('/ru' + (pathname === '/' ? '' : pathname))
      } else {
        navigate(pathname.slice(3) || '/')
      }
    }
  }

  return createElement(LangContext.Provider, { value: { lang, toggle } }, children)
}

export function useLang() {
  return useContext(LangContext)
}
