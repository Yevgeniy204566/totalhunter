/**
 * Prerender script — per-route meta injection for static HTML.
 * Runs postbuild: node prerender.mjs
 * Generates both EN (default) and RU (/ru prefix) versions with hreflang.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath, pathToFileURL } from 'url'
import { FAQ_ITEMS_RU, FAQ_ITEMS_EN } from './src/faq.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DIST = resolve(__dirname, 'dist')
const BASE = 'https://total-hunter.com'

const ROUTES = [
  // ── EN routes (default, no prefix) ──────────────────────────────
  {
    path: '/',
    lang: 'en',
    title:       'Total Hunter — Bot for Total Battle | Exchanges, Crypts & Clan Chests',
    description: 'Automatic mercenary exchange search, crypt collection and clan chest accounting for Total Battle: public clan table, season goals and norms by Hero level. 300 free diamonds on registration.',
    canonical:   `${BASE}/`,
    enHref:      `${BASE}/`,
    ruHref:      `${BASE}/ru`,
    faqLang:     'en',
  },
  {
    path: '/guide',
    lang: 'en',
    title:       'Total Hunter Guide — Setup, Calibration & Launch | Total Battle',
    description: 'Step-by-step guide for installing and configuring Total Hunter for Total Battle. Calibration, profiles, launching exchange and crypt bots.',
    canonical:   `${BASE}/guide`,
    enHref:      `${BASE}/guide`,
    ruHref:      `${BASE}/ru/guide`,
  },
  {
    path: '/download',
    lang: 'en',
    title:       'Download Total Hunter — Total Battle Bot | Windows 10/11',
    description: 'Download Total Hunter for free. Mercenary exchange finder, crypt collector and clan chest accounting for Total Battle. 300 free diamonds on registration.',
    canonical:   `${BASE}/download`,
    enHref:      `${BASE}/download`,
    ruHref:      `${BASE}/ru/download`,
  },
  {
    path: '/contacts',
    lang: 'en',
    title:       'Total Hunter Support & Contacts',
    description: 'Total Hunter technical support. Discord, email, FAQ for common questions.',
    canonical:   `${BASE}/contacts`,
    enHref:      `${BASE}/contacts`,
    ruHref:      `${BASE}/ru/contacts`,
  },
  {
    path: '/legal',
    lang: 'en',
    title:       'Total Hunter Terms of Service',
    description: 'Terms and conditions for using the Total Hunter platform.',
    canonical:   `${BASE}/legal`,
    enHref:      `${BASE}/legal`,
    ruHref:      `${BASE}/ru/legal`,
  },

  // ── RU routes (/ru prefix) ───────────────────────────────────────
  {
    path: '/ru',
    lang: 'ru',
    title:       'Total Hunter — автоматизация Total Battle | Биржи, склепы, сундуки клана',
    description: 'Автоматический поиск бирж наёмников, сбор склепов и учёт сундуков клана в Total Battle: публичная таблица, цели сезона и нормы по уровню Героя. 300 алмазов бесплатно при регистрации.',
    canonical:   `${BASE}/ru`,
    enHref:      `${BASE}/`,
    ruHref:      `${BASE}/ru`,
    faqLang:     'ru',
  },
  {
    path: '/ru/guide',
    lang: 'ru',
    title:       'Гайд Total Hunter — установка, калибровка и запуск | Total Battle',
    description: 'Пошаговое руководство по установке и настройке Total Hunter для Total Battle. Калибровка, профили, запуск биржевого и склепного бота.',
    canonical:   `${BASE}/ru/guide`,
    enHref:      `${BASE}/guide`,
    ruHref:      `${BASE}/ru/guide`,
  },
  {
    path: '/ru/download',
    lang: 'ru',
    title:       'Скачать Total Hunter — бот для Total Battle | Windows 10/11',
    description: 'Скачать Total Hunter бесплатно. Поиск бирж наёмников, сбор склепов и учёт сундуков клана в Total Battle. 300 алмазов бесплатно при регистрации.',
    canonical:   `${BASE}/ru/download`,
    enHref:      `${BASE}/download`,
    ruHref:      `${BASE}/ru/download`,
  },
  {
    path: '/ru/contacts',
    lang: 'ru',
    title:       'Контакты Total Hunter — поддержка и связь',
    description: 'Техническая поддержка Total Hunter. Discord, email, FAQ по распространённым вопросам.',
    canonical:   `${BASE}/ru/contacts`,
    enHref:      `${BASE}/contacts`,
    ruHref:      `${BASE}/ru/contacts`,
  },
  {
    path: '/ru/legal',
    lang: 'ru',
    title:       'Пользовательское соглашение Total Hunter',
    description: 'Условия использования платформы Total Hunter.',
    canonical:   `${BASE}/ru/legal`,
    enHref:      `${BASE}/legal`,
    ruHref:      `${BASE}/ru/legal`,
  },
]

// FAQPage JSON-LD строится из того же списка, что и видимый FAQ на главной (src/faq.js)
const faqJson = items => JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: items.map(({ q, a }) => ({ '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: a } })),
})
const FAQ_EN = faqJson(FAQ_ITEMS_EN)
const FAQ_RU = faqJson(FAQ_ITEMS_RU)

const template = readFileSync(resolve(DIST, 'index.html'), 'utf-8')

// Серверная сборка React-приложения (vite build --ssr): текст страницы кладётся в HTML, а не рисуется скриптом
const { render } = await import(pathToFileURL(resolve(__dirname, 'dist-ssr', 'entry-server.js')).href)

for (const route of ROUTES) {
  let html = template

  // html[lang]
  html = html.replace(/(<html[^>]*\slang=")[^"]*(")/,  `$1${route.lang}$2`)

  // Title
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${route.title}</title>`)

  // Description
  html = html.replace(/(<meta name="description" content=")[^"]*(")/,       `$1${route.description}$2`)

  // OG
  html = html.replace(/(<meta property="og:title" content=")[^"]*(")/,       `$1${route.title}$2`)
  html = html.replace(/(<meta property="og:description" content=")[^"]*(")/,  `$1${route.description}$2`)
  html = html.replace(/(<meta property="og:url" content=")[^"]*(")/,          `$1${route.canonical}$2`)
  html = html.replace(/(<meta property="og:locale" content=")[^"]*(")/,
    `$1${route.lang === 'ru' ? 'ru_RU' : 'en_US'}$2`)

  // Canonical
  html = html.replace(/(<link rel="canonical" href=")[^"]*(")/,               `$1${route.canonical}$2`)

  // Twitter
  html = html.replace(/(<meta name="twitter:title" content=")[^"]*(")/,       `$1${route.title}$2`)
  html = html.replace(/(<meta name="twitter:description" content=")[^"]*(")/,  `$1${route.description}$2`)

  // Содержимое страницы: полный текст, заголовки и ссылки в исходном HTML (клиент гидрирует его из main.jsx)
  const body = render(route.path)
  if (!body || !template.includes('<div id="root"></div>')) throw new Error(`prerender: нет содержимого или корня для ${route.path}`)
  html = html.replace('<div id="root"></div>', () => `<div id="root">${body}</div>`)

  // hreflang tags (inject before </head>)
  const hreflangTags = [
    `    <link rel="alternate" hreflang="x-default" href="${route.enHref}" />`,
    `    <link rel="alternate" hreflang="en"        href="${route.enHref}" />`,
    `    <link rel="alternate" hreflang="ru"        href="${route.ruHref}" />`,
  ].join('\n')
  html = html.replace('</head>', `${hreflangTags}\n  </head>`)

  // FAQ JSON-LD (home pages only)
  if (route.faqLang) {
    const faqJson = route.faqLang === 'ru' ? FAQ_RU : FAQ_EN
    const faqTag = `\n    <script type="application/ld+json" id="faq-schema">\n    ${faqJson}\n    </script>`
    html = html.replace('</head>', `${faqTag}\n  </head>`)
  }

  // Write to dist
  const dir = route.path === '/' ? DIST : resolve(DIST, route.path.slice(1))
  mkdirSync(dir, { recursive: true })
  writeFileSync(resolve(dir, 'index.html'), html, 'utf-8')
  console.log(`  [prerender] ${route.path} (${route.lang})`)
}

console.log(`Prerender done — ${ROUTES.length} routes.`)
