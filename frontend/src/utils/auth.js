const TOKEN_KEY = 'fa_access_token'
const USER_KEY = 'fa_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token || '')
  localStorage.setItem(USER_KEY, JSON.stringify(user || null))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn() {
  return Boolean(getToken())
}

export function logoutAndRedirect(router) {
  clearAuth()
  if (router) {
    router.replace({ path: '/login' })
  } else {
    window.location.href = '/login'
  }
}
