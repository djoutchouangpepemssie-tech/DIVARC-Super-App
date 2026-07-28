// Centralized DIVARC client API with session token
export function getToken() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('divarc_token')
}
export function setToken(t) { try { localStorage.setItem('divarc_token', t) } catch (e) {} }
export function clearToken() { try { localStorage.removeItem('divarc_token') } catch (e) {} }

export async function api(path, opts = {}) {
  const token = getToken()
  const res = await fetch(`/api${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
    ...opts,
  })
  try { return await res.json() } catch (e) { return { error: 'bad_response' } }
}
