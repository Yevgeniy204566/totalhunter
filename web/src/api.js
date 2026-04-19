import { getToken, clearToken } from './auth.js'

const BASE = import.meta.env.VITE_API_URL

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

  const data = await res.json()
  if (!res.ok) throw new Error(data.detail?.message || data.detail || 'Request failed')
  return data
}

export const api = {
  authGoogle:       (id_token) => request('POST', '/web/auth/google', { id_token }),
  me:               ()         => request('GET',  '/web/me'),
  hunts:            ()         => request('GET',  '/web/hunts'),
  transactions:     ()         => request('GET',  '/web/transactions'),
  linkVerify:       (code)     => request('POST', '/web/link/verify', { code }),
  hwidReset:        ()         => request('POST', '/web/hwid/reset'),
  referralTransfer: ()         => request('POST', '/web/referral/transfer'),
}
