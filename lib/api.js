// Centralized DIVARC client API with session token + offline queue
export function getToken() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('divarc_token')
}
export function setToken(t) { try { localStorage.setItem('divarc_token', t) } catch (e) {} }
export function clearToken() { try { localStorage.removeItem('divarc_token') } catch (e) {} }

/* ---------------- Offline queue (mutations) ---------------- */
const QUEUE_KEY = 'divarc_offline_queue'
function readQueue() { try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]') } catch (e) { return [] } }
function writeQueue(q) { try { localStorage.setItem(QUEUE_KEY, JSON.stringify(q)) } catch (e) {} }
function emit() { try { window.dispatchEvent(new Event('divarc:queue')) } catch (e) {} }

export function pendingCount() {
  if (typeof window === 'undefined') return 0
  return readQueue().length
}

function buildHeaders(extra = {}) {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

export async function api(path, opts = {}) {
  const method = (opts.method || 'GET').toUpperCase()
  const isMutation = method !== 'GET'
  try {
    const res = await fetch(`/api${path}`, {
      ...opts,
      headers: buildHeaders(opts.headers || {}),
    })
    try { return await res.json() } catch (e) { return { error: 'bad_response' } }
  } catch (e) {
    // Network failure (offline / server unreachable)
    if (isMutation) {
      const q = readQueue()
      q.push({ path, method, body: opts.body || null, headers: opts.headers || null, ts: Date.now() })
      writeQueue(q)
      emit()
      return { queued: true, offline: true }
    }
    return { error: 'offline', offline: true }
  }
}

// Replay queued mutations; returns number successfully flushed
export async function flushQueue() {
  if (typeof window === 'undefined') return 0
  let q = readQueue()
  if (!q.length) return 0
  const remaining = []
  let flushed = 0
  for (const item of q) {
    try {
      await fetch(`/api${item.path}`, {
        method: item.method,
        body: item.body || undefined,
        headers: buildHeaders(item.headers || {}),
      })
      flushed++
    } catch (e) {
      remaining.push(item)
    }
  }
  writeQueue(remaining)
  emit()
  return flushed
}
