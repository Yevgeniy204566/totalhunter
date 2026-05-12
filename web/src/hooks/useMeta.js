import { useEffect } from 'react'

const DEFAULT_TITLE = 'Total Hunter — бот для Total Battle | Биржи и склепы на автомате'
const DEFAULT_DESC  = 'Автоматический поиск бирж наёмников и сбор склепов в Total Battle. Нейросеть + имитация игрока. 100 алмазов бесплатно при регистрации.'

function setMeta(selector, attr, value) {
  const el = document.querySelector(selector)
  if (el) el.setAttribute(attr, value)
}

export function useMeta({ title, description }) {
  useEffect(() => {
    document.title = title
    setMeta('meta[name="description"]',          'content', description)
    setMeta('meta[property="og:title"]',         'content', title)
    setMeta('meta[property="og:description"]',   'content', description)
    setMeta('meta[name="twitter:title"]',        'content', title)
    setMeta('meta[name="twitter:description"]',  'content', description)
    return () => {
      document.title = DEFAULT_TITLE
      setMeta('meta[name="description"]',          'content', DEFAULT_DESC)
      setMeta('meta[property="og:title"]',         'content', 'Total Hunter — бот для Total Battle')
      setMeta('meta[property="og:description"]',   'content', DEFAULT_DESC)
      setMeta('meta[name="twitter:title"]',        'content', 'Total Hunter — бот для Total Battle')
      setMeta('meta[name="twitter:description"]',  'content', DEFAULT_DESC)
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
