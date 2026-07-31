// Client WebSocket temps réel DIVARC : présence, messages instantanés, "en train d'écrire".
import { getToken } from './api'

let ws = null
let reconnectTimer = null
let manualClose = false
const listeners = new Map() // type -> Set(cb)
const onlineUsers = new Set()

function wsBase() {
  // URL explicite en production (ex: wss://divarc-api.up.railway.app)
  const env = process.env.NEXT_PUBLIC_WS_URL
  if (env) return env.replace(/\/$/, '')
  if (typeof window === 'undefined') return ''
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  // Dev : le backend Python écoute sur :8000
  const host = window.location.hostname
  const port = window.location.port === '3000' ? '8000' : (window.location.port || '')
  return `${proto}://${host}${port ? ':' + port : ''}`
}

function emit(type, msg) {
  const set = listeners.get(type)
  if (set) set.forEach((cb) => { try { cb(msg) } catch (e) {} })
}

export function connectRealtime() {
  if (typeof window === 'undefined') return
  const token = getToken()
  if (!token) return
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  manualClose = false
  try {
    ws = new WebSocket(`${wsBase()}/api/ws?token=${encodeURIComponent(token)}`)
  } catch (e) { scheduleReconnect(); return }

  ws.onopen = () => emit('open', {})
  ws.onmessage = (e) => {
    let msg
    try { msg = JSON.parse(e.data) } catch (err) { return }
    if (msg.type === 'presence_state') {
      onlineUsers.clear();(msg.online || []).forEach((u) => onlineUsers.add(u))
    } else if (msg.type === 'presence') {
      if (msg.online) onlineUsers.add(msg.userId); else onlineUsers.delete(msg.userId)
    }
    emit(msg.type, msg)
    emit('*', msg)
  }
  ws.onclose = () => { ws = null; if (!manualClose) scheduleReconnect() }
  ws.onerror = () => { try { ws.close() } catch (e) {} }
}

function scheduleReconnect() {
  if (reconnectTimer || manualClose) return
  reconnectTimer = setTimeout(() => { reconnectTimer = null; connectRealtime() }, 2500)
}

export function disconnectRealtime() {
  manualClose = true
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  if (ws) { try { ws.close() } catch (e) {} ; ws = null }
  onlineUsers.clear()
}

export function sendRealtime(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    try { ws.send(JSON.stringify(obj)) } catch (e) {}
  }
}

// Abonnement à un type d'événement ('message' | 'presence' | 'presence_state' | 'typing' | 'reaction' | '*').
// Retourne une fonction de désabonnement.
export function onRealtime(type, cb) {
  if (!listeners.has(type)) listeners.set(type, new Set())
  listeners.get(type).add(cb)
  return () => { const s = listeners.get(type); if (s) s.delete(cb) }
}

export function isOnline(userId) { return onlineUsers.has(userId) }
