import { next, rewrite } from '@vercel/functions'

// Нейтральный домен публичных страниц кланов. Белый список: всё, чего нет в списке, — 404,
// чтобы на этом адресе нельзя было открыть лендинг, кабинет, гайд и прочие страницы сервиса.
const CLAN_HOSTS = new Set(['clbx.date', 'www.clbx.date'])

const PAGE_PREFIXES = ['/c/', '/chests/', '/ancients/']
// браузер ходит на /api/<путь>, vercel.json пересылает на бэкенд без префикса /api
const API_PREFIXES = ['/api/api/v1/chests/', '/api/api/v1/ancients/public/']
const STATIC_PREFIXES = ['/icons/']

export const config = {
  // assets/ не трогаем: хешированные файлы сборки не должны тратить вызовы middleware
  matcher: ['/((?!assets/).*)'],
}

export default function middleware(request) {
  const host = (request.headers.get('host') || '').toLowerCase().split(':')[0]
  if (!CLAN_HOSTS.has(host)) return next()

  const url = new URL(request.url)
  const path = url.pathname

  if (PAGE_PREFIXES.some(p => path.startsWith(p))) {
    url.pathname = '/clan.html'
    return rewrite(url)
  }
  if (API_PREFIXES.some(p => path.startsWith(p)) || STATIC_PREFIXES.some(p => path.startsWith(p))) {
    return next()
  }
  if (path === '/robots.txt') {
    return new Response('User-agent: *\nDisallow: /\n', { headers: { 'content-type': 'text/plain' } })
  }
  return new Response('Not found', { status: 404, headers: { 'content-type': 'text/plain' } })
}
