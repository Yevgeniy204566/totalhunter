import { getToken, clearToken } from './auth.js'

const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(method, path, body) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    return
  }

  let data
  try { data = await res.json() } catch { throw new Error('Server error') }
  if (!res.ok) throw new Error(data.detail?.message || data.detail || 'Request failed')
  return data
}

export const api = {
  authGoogle:       (id_token, ref_code = null) => request('POST', '/web/auth/google', { id_token, ref_code }),
  me:               ()         => request('GET',  '/web/me'),
  hunts:            ()         => request('GET',  '/web/hunts'),
  transactions:     ()         => request('GET',  '/web/transactions'),
  linkVerify:       (code)     => request('POST', '/web/link/verify', { code }),
  hwidReset:        ()         => request('POST', '/web/hwid/reset'),
  referralTransfer: ()         => request('POST', '/web/referral/transfer'),
  activateReferral: (code)     => request('POST', `/web/referral/activate?ref_code=${encodeURIComponent(code)}`),
  referralTree:     ()         => request('GET',  '/web/referral/tree'),
  globalStats:      ()         => request('GET',  '/web/stats/global'),
  sendFeedback:     (text)     => request('POST', '/web/feedback', { text }),
  paymentCreate:    (pkg)      => request('POST', '/web/payment/create', { package: pkg }),
  earnStatus:       ()         => request('GET',  '/web/earn/status'),
  earnReward:       ()         => request('POST', '/web/earn/reward'),
  dashboardChests:      ()              => request('GET',   '/web/dashboard/chests'),
  dashboardChestsSave:  (slug, rows)    => request('POST',  '/web/dashboard/chests/rows', { collector_slug: slug, rows }),
  dashboardChestsPlayerAliases: (slug, rows) => request('POST', '/web/dashboard/chests/player-aliases', { collector_slug: slug, rows }),
  dashboardChestsToken: (slug)          => request('POST',  '/web/dashboard/chests/management-token', { collector_slug: slug }),
  dashboardChestsClaim: (code)          => request('POST',  '/web/dashboard/chests/claim', { code }),
  dashboardChestsLang:  (slug, language) => request('PATCH', `/web/dashboard/chests/${slug}/language`, { language }),
  dashboardChestsSeason: (slug, payload) => request('PATCH', `/web/dashboard/chests/${slug}/season`, payload),
  dashboardChestsPresets: ()            => request('GET',   '/web/dashboard/chests/presets'),
  dashboardChestsHistory: (slug) => request('GET', `/web/dashboard/chests/${slug}/history`),
  dashboardChestsHistoryDetail: (slug, seasonId) => request('GET', `/web/dashboard/chests/${slug}/history/${seasonId}`),
  dashboardChestsCloseSeason:   (slug) => request('POST', `/web/dashboard/chests/${slug}/close-season`),
  dashboardChestsMyNames:       ()    => request('GET',  '/web/dashboard/chests/my-custom-names'),
  dashboardAncients:      ()              => request('GET',   '/web/dashboard/ancients'),
  dashboardAncientsTroopLevel: (slug, playerName, troopLevel) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/troop-level`,
            { player_name: playerName, troop_level: troopLevel }),
  dashboardAncientsCalculate: (slug, payload) =>
    request('POST', `/web/dashboard/ancients/${slug}/calculate`, payload),
}

export async function fetchChestSummary(slug) {
  const res = await fetch(`${BASE}/api/v1/chests/summary/${slug}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}

export async function fetchChestByKingdomSlug(kingdom, slug) {
  const res = await fetch(`${BASE}/api/v1/chests/by/${encodeURIComponent(kingdom)}/${encodeURIComponent(slug)}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}

export async function fetchChestHistory(slug) {
  const res = await fetch(`${BASE}/api/v1/chests/history/${slug}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}

export async function fetchChestHistorySeason(slug, seasonId) {
  const res = await fetch(`${BASE}/api/v1/chests/history/${slug}/${seasonId}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}
