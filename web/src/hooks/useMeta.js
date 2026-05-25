import { useEffect } from 'react'

const BASE = 'https://total-hunter.com'
const DEFAULT_TITLE = 'Total Hunter — Total Battle Automation | Exchanges & Crypts'
const DEFAULT_DESC  = 'Automatic mercenary exchange and crypt finder for Total Battle. Neural network + player simulation. 100 free diamonds on registration.'

function setMeta(selector, attr, value) {
  const el = document.querySelector(selector)
  if (el) el.setAttribute(attr, value)
}

function syncHreflang(pathname) {
  document.querySelectorAll('link[rel="alternate"][hreflang]').forEach(el => el.remove())
  if (pathname.startsWith('/dashboard')) return

  const isRu   = pathname.startsWith('/ru')
  const enPath = isRu ? (pathname.slice(3) || '/') : pathname
  const ruPath = isRu ? pathname : '/ru' + (pathname === '/' ? '' : pathname)

  ;[
    { hreflang: 'x-default', href: BASE + enPath },
    { hreflang: 'en',        href: BASE + enPath },
    { hreflang: 'ru',        href: BASE + ruPath },
  ].forEach(({ hreflang, href }) => {
    const link = document.createElement('link')
    link.rel = 'alternate'
    link.setAttribute('hreflang', hreflang)
    link.href = href
    document.head.appendChild(link)
  })
}

export function useMeta({ title, description }) {
  useEffect(() => {
    const path = window.location.pathname
    document.title = title
    setMeta('meta[name="description"]',         'content', description)
    setMeta('meta[property="og:title"]',        'content', title)
    setMeta('meta[property="og:description"]',  'content', description)
    setMeta('meta[property="og:url"]',          'content', window.location.href)
    setMeta('meta[name="twitter:title"]',       'content', title)
    setMeta('meta[name="twitter:description"]', 'content', description)
    syncHreflang(path)

    return () => {
      document.title = DEFAULT_TITLE
      setMeta('meta[name="description"]',         'content', DEFAULT_DESC)
      setMeta('meta[property="og:title"]',        'content', 'Total Hunter — Total Battle Automation')
      setMeta('meta[property="og:description"]',  'content', DEFAULT_DESC)
      setMeta('meta[property="og:url"]',          'content', BASE)
      setMeta('meta[name="twitter:title"]',       'content', 'Total Hunter — Total Battle Automation')
      setMeta('meta[name="twitter:description"]', 'content', DEFAULT_DESC)
      document.querySelectorAll('link[rel="alternate"][hreflang]').forEach(el => el.remove())
    }
  }, [title, description])
}

export function useFaqSchema(items) {
  useEffect(() => {
    const schema = {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: items.map(({ q, a }) => ({
        '@type': 'Question',
        name: q,
        acceptedAnswer: { '@type': 'Answer', text: a },
      })),
    }
    const script = document.createElement('script')
    script.type = 'application/ld+json'
    script.id   = 'faq-schema'
    script.text = JSON.stringify(schema)
    document.head.appendChild(script)
    return () => {
      const el = document.getElementById('faq-schema')
      if (el) el.remove()
    }
  }, [])
}
