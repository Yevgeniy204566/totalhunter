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
  dashboardChestsPlayerProfiles: (slug, rows) =>
    request('POST', '/web/dashboard/chests/player-profiles', { collector_slug: slug, rows }),
  dashboardChestsToken: (slug)          => request('POST',  '/web/dashboard/chests/management-token', { collector_slug: slug }),
  dashboardChestsClaim: (code)          => request('POST',  '/web/dashboard/chests/claim', { code }),
  dashboardChestsLang:  (slug, language) => request('PATCH', `/web/dashboard/chests/${slug}/language`, { language }),
  dashboardChestsSeason: (slug, payload) => request('PATCH', `/web/dashboard/chests/${slug}/season`, payload),
  dashboardChestsLeader: (slug, payload) => request('PATCH', `/web/dashboard/chests/${slug}/leader`, payload),
  dashboardChestsPresets: ()            => request('GET',   '/web/dashboard/chests/presets'),
  dashboardChestsHistory: (slug) => request('GET', `/web/dashboard/chests/${slug}/history`),
  dashboardChestsHistoryDetail: (slug, seasonId) => request('GET', `/web/dashboard/chests/${slug}/history/${seasonId}`),
  dashboardChestsCloseSeason:   (slug) => request('POST', `/web/dashboard/chests/${slug}/close-season`),
  dashboardChestsMyNames:       ()    => request('GET',  '/web/dashboard/chests/my-custom-names'),
  dashboardChestsDelete:        (slug) => request('DELETE', `/web/dashboard/chests/${slug}`),
  dashboardAncients:      (fuzzyThreshold = 0.75) =>
    request('GET',   `/web/dashboard/ancients?fuzzy_threshold=${fuzzyThreshold}`),
  dashboardAncientsTroopLevel: (slug, playerName, troopLevel) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/troop-level`,
            { player_name: playerName, troop_level: troopLevel }),
  dashboardAncientsRank: (slug, playerName, rank) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/rank`,
            { player_name: playerName, rank }),
  dashboardAncientsQuotaThresholds: (slug, lightPct, mediumPct, criticalPct) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/quota-thresholds`,
            { light_pct: lightPct, medium_pct: mediumPct, critical_pct: criticalPct }),
  dashboardAncientsCalculate: (slug, payload) =>
    request('POST', `/web/dashboard/ancients/${slug}/calculate`, payload),
  dashboardAncientsNameMappings: (slug, mappings) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/name-mappings`, { mappings }),
  dashboardAncientsNameMappingDelete: (slug, rawOcrName) =>
    request('DELETE', `/web/dashboard/ancients/${slug}/name-mappings/${encodeURIComponent(rawOcrName)}`),
  dashboardAncientsInvite: (slug) =>
    request('POST', `/web/dashboard/ancients/${slug}/invite`),
  dashboardAncientsJoin: (code) =>
    request('POST', '/web/dashboard/ancients/join', { code }),
  dashboardAncientsSetHidden: (slug, hidden) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/ancient-visibility`, { hidden }),
  dashboardAncientsAddManual: async (slug, payload) => {
    const token = getToken()
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${BASE}/web/dashboard/ancients/${slug}/roster/manual`, {
      method: 'POST', headers, body: JSON.stringify(payload),
    })
    let data
    try { data = await res.json() } catch { data = {} }
    if (!res.ok) {
      const err = new Error(data.detail?.message || data.detail || 'Request failed')
      err.similarName = data.detail?.similar_name
      throw err
    }
    return data
  },
  dashboardAncientsDeleteRosterEntry: (slug, playerName) =>
    request('DELETE', `/web/dashboard/ancients/${slug}/roster/${encodeURIComponent(playerName)}`),
  dashboardAncientsClearOcrImport: (slug) =>
    request('DELETE', `/web/dashboard/ancients/${slug}/roster/ocr-import`),
  dashboardAncientsPopulateFromChests: (slug) =>
    request('POST', `/web/dashboard/ancients/${slug}/roster/populate-from-chests`),
  dashboardAncientsCreate: (kingdom, clan) =>
    request('POST', '/web/dashboard/ancients/create', { kingdom, clan }),
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

export async function fetchAncientsPublic(slug) {
  const res = await fetch(`${BASE}/api/v1/ancients/public/${encodeURIComponent(slug)}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}

export async function postPublicPlayerProfile(collector_slug, canonical_name, rank, troop_level) {
  const res = await fetch(`${BASE}/api/v1/chests/public/player-profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ collector_slug, canonical_name, rank, troop_level }),
  })
  if (!res.ok) {
    let msg = 'Save failed'
    try { const b = await res.json(); if (b.detail) msg = b.detail } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export async function postPublicAddSelf(slug, player_name, rank, troop_level) {
  const res = await fetch(`${BASE}/api/v1/ancients/public/${encodeURIComponent(slug)}/roster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_name, rank, troop_level }),
  })
  let data
  try { data = await res.json() } catch { data = {} }
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.detail || 'Save failed')
    err.similarName = data.detail?.similar_name
    throw err
  }
  return data
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
