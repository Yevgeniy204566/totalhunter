/**
 * Prerender script — per-route meta injection for static HTML.
 * Runs postbuild: node prerender.mjs
 * Generates both EN (default) and RU (/ru prefix) versions with hreflang.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DIST = resolve(__dirname, 'dist')
const BASE = 'https://total-hunter.com'

const ROUTES = [
  // ── EN routes (default, no prefix) ──────────────────────────────
  {
    path: '/',
    lang: 'en',
    title:       'Total Hunter — Total Battle Automation | Exchanges & Crypts',
    description: 'Automatic mercenary exchange and crypt finder for Total Battle. Neural network + player simulation. 100 free diamonds on registration.',
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
    description: 'Download Total Hunter for free. Mercenary exchange finder and crypt collector for Total Battle. 100 free diamonds on registration.',
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
    title:       'Total Hunter — автоматизация Total Battle | Биржи и склепы',
    description: 'Автоматический поиск бирж наёмников и сбор склепов в Total Battle. Нейросеть + имитация игрока. 100 алмазов бесплатно при регистрации.',
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
    description: 'Скачать Total Hunter бесплатно. Поиск бирж наёмников и сбор склепов в Total Battle. 100 алмазов бесплатно при регистрации.',
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

// FAQ JSON-LD (EN)
const FAQ_EN = JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    { '@type': 'Question', name: 'What is Total Hunter?',
      acceptedAnswer: { '@type': 'Answer', text: 'Total Hunter is a desktop bot for automating Total Battle. It automatically searches for mercenary exchanges and collects crypts, simulating real player actions.' } },
    { '@type': 'Question', name: 'How much does Total Hunter cost?',
      acceptedAnswer: { '@type': 'Answer', text: 'First 100 diamonds are free on registration — no credit card needed. Diamonds are spent only for successful actions: −10 for a found exchange, −1 for a collected crypt.' } },
    { '@type': 'Question', name: 'Does the bot work with the browser and Total Battle client?',
      acceptedAnswer: { '@type': 'Answer', text: 'Yes. Total Hunter supports browser version (Chrome, Firefox) and the official Total Battle client. Settings are saved in profiles.' } },
    { '@type': 'Question', name: 'Can I get banned for using the bot?',
      acceptedAnswer: { '@type': 'Answer', text: 'The bot fully simulates human actions: random pauses 0.4–0.9 sec, random click offset ±5–8 pixels. Risk is minimal.' } },
    { '@type': 'Question', name: 'Does the bot need my game password?',
      acceptedAnswer: { '@type': 'Answer', text: 'No. The bot works on top of an already running game via screen screenshots. Your credentials are not needed.' } },
    { '@type': 'Question', name: 'What systems does Total Hunter support?',
      acceptedAnswer: { '@type': 'Answer', text: 'Windows 10 and Windows 11 (64-bit). Installer includes all required components (VC++ Runtime).' } },
  ],
})

// FAQ JSON-LD (RU)
const FAQ_RU = JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    { '@type': 'Question', name: 'Что такое Total Hunter?',
      acceptedAnswer: { '@type': 'Answer', text: 'Total Hunter — десктопный бот для автоматизации Total Battle. Автоматически ищет биржи наёмников и собирает склепы, имитируя действия реального игрока.' } },
    { '@type': 'Question', name: 'Сколько стоит Total Hunter?',
      acceptedAnswer: { '@type': 'Answer', text: 'Первые 100 алмазов бесплатно при регистрации — без кредитной карты. Алмазы списываются только за успешные действия: −10 за найденную биржу, −1 за собранный склеп.' } },
    { '@type': 'Question', name: 'Работает ли бот с браузером и клиентом Total Battle?',
      acceptedAnswer: { '@type': 'Answer', text: 'Да. Total Hunter поддерживает браузерную версию (Chrome, Firefox) и официальный клиент Total Battle. Настройки сохраняются в профилях.' } },
    { '@type': 'Question', name: 'Могут ли меня забанить за использование бота?',
      acceptedAnswer: { '@type': 'Answer', text: 'Бот полностью имитирует действия человека: случайные паузы 0.4–0.9 сек, случайное отклонение кликов ±5–8 пикселей. Риск минимален.' } },
    { '@type': 'Question', name: 'Нужен ли боту мой игровой пароль?',
      acceptedAnswer: { '@type': 'Answer', text: 'Нет. Бот работает поверх уже запущенной игры через скриншоты экрана. Ваши учётные данные нам не нужны.' } },
    { '@type': 'Question', name: 'На каких системах работает Total Hunter?',
      acceptedAnswer: { '@type': 'Answer', text: 'Windows 10 и Windows 11 (64-bit). Установщик включает все необходимые компоненты (VC++ Runtime).' } },
  ],
})

const template = readFileSync(resolve(DIST, 'index.html'), 'utf-8')

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
