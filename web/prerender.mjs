/**
 * Prerender script — инжектирует per-route метатеги в статичный HTML.
 * Запускается postbuild: node prerender.mjs
 * Без puppeteer, без SSR — просто правильные meta/og/canonical для каждого маршрута.
 * Боты соцсетей (Discord, Telegram, Facebook) не выполняют JS и берут OG из статичного HTML.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DIST = resolve(__dirname, 'dist')
const BASE = 'https://total-hunter.com'

const ROUTES = {
  '/': {
    title:       'Total Hunter — автоматизация Total Battle | Биржи и склепы',
    description: 'Автоматический поиск бирж наёмников и сбор склепов в Total Battle. Нейросеть + имитация игрока. 100 алмазов бесплатно при регистрации.',
    canonical:   `${BASE}/`,
  },
  '/features': {
    title:       'Возможности Total Hunter — Рой, склепы, биржи | Total Battle автоматизация',
    description: 'Система РОЙ, автосбор склепов и поиск бирж наёмников в Total Battle. Как работает коллективный пул координат и нейросетевой поиск.',
    canonical:   `${BASE}/features`,
  },
  '/guide': {
    title:       'Гайд Total Hunter — установка, калибровка и запуск | Total Battle',
    description: 'Пошаговое руководство по установке и настройке Total Hunter для Total Battle. Калибровка, профили, запуск биржевого и склепного бота.',
    canonical:   `${BASE}/guide`,
  },
  '/download': {
    title:       'Скачать Total Hunter — бот для Total Battle | Windows 10/11',
    description: 'Скачать Total Hunter бесплатно. Поиск бирж наёмников и сбор склепов в Total Battle. 100 алмазов бесплатно при регистрации.',
    canonical:   `${BASE}/download`,
  },
  '/contacts': {
    title:       'Контакты Total Hunter — поддержка и связь',
    description: 'Техническая поддержка Total Hunter. Discord, email, FAQ по распространённым вопросам.',
    canonical:   `${BASE}/contacts`,
  },
  '/legal': {
    title:       'Пользовательское соглашение Total Hunter',
    description: 'Условия использования платформы Total Hunter.',
    canonical:   `${BASE}/legal`,
  },
}

const template = readFileSync(resolve(DIST, 'index.html'), 'utf-8')

for (const [route, meta] of Object.entries(ROUTES)) {
  let html = template

  // Title
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${meta.title}</title>`)

  // Description
  html = html.replace(
    /(<meta name="description" content=")[^"]*(")/,
    `$1${meta.description}$2`
  )

  // OG title
  html = html.replace(
    /(<meta property="og:title" content=")[^"]*(")/,
    `$1${meta.title}$2`
  )

  // OG description
  html = html.replace(
    /(<meta property="og:description" content=")[^"]*(")/,
    `$1${meta.description}$2`
  )

  // OG url
  html = html.replace(
    /(<meta property="og:url" content=")[^"]*(")/,
    `$1${meta.canonical}$2`
  )

  // Canonical
  html = html.replace(
    /(<link rel="canonical" href=")[^"]*(")/,
    `$1${meta.canonical}$2`
  )

  // Twitter title
  html = html.replace(
    /(<meta name="twitter:title" content=")[^"]*(")/,
    `$1${meta.title}$2`
  )

  // Twitter description
  html = html.replace(
    /(<meta name="twitter:description" content=")[^"]*(")/,
    `$1${meta.description}$2`
  )

  const dir = route === '/' ? DIST : resolve(DIST, route.slice(1))
  mkdirSync(dir, { recursive: true })
  writeFileSync(resolve(dir, 'index.html'), html, 'utf-8')
  console.log(`  [prerender] ${route}`)
}

console.log(`Prerender done — ${Object.keys(ROUTES).length} routes.`)
