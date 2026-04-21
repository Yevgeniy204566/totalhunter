const TOKEN_KEY = 'th_jwt'

export function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function isLoggedIn() {
  const token = getToken()
  if (!token) return false
  try {
    // JWT uses base64url (- and _ instead of + and /); atob() needs standard base64
    const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(b64))
    return payload.exp * 1000 > Date.now()
  } catch {
    return false
  }
}
