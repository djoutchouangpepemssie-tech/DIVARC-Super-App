// Notifications push Web DIVARC : enregistrement du Service Worker + abonnement VAPID.
// Le navigateur s'abonne auprès de son propre service de push ; le backend envoie via VAPID.
import { api } from './api'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const out = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

export function pushSupported() {
  return typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
}

// Enregistre le Service Worker (idempotent). À appeler au démarrage.
export async function registerServiceWorker() {
  if (!pushSupported()) return null
  try {
    return await navigator.serviceWorker.register('/sw.js', { scope: '/' })
  } catch (e) {
    return null
  }
}

// État courant : { supported, permission, subscribed }
export async function getPushStatus() {
  if (!pushSupported()) return { supported: false, permission: 'unsupported', subscribed: false }
  let subscribed = false
  try {
    const reg = await navigator.serviceWorker.getRegistration()
    if (reg) subscribed = !!(await reg.pushManager.getSubscription())
  } catch (e) {}
  return { supported: true, permission: Notification.permission, subscribed }
}

// Active le push : demande la permission, s'abonne, enregistre côté serveur.
// Retourne { ok, reason? }. À appeler DEPUIS un geste utilisateur (clic).
export async function enablePush() {
  if (!pushSupported()) return { ok: false, reason: 'unsupported' }

  const perm = await Notification.requestPermission()
  if (perm !== 'granted') return { ok: false, reason: perm === 'denied' ? 'denied' : 'dismissed' }

  const reg = (await navigator.serviceWorker.getRegistration()) || (await registerServiceWorker())
  if (!reg) return { ok: false, reason: 'no-sw' }
  await navigator.serviceWorker.ready

  // Clé publique VAPID fournie par le backend
  const v = await api('/push/vapid')
  if (!v || !v.publicKey) return { ok: false, reason: 'no-vapid' }

  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(v.publicKey),
    })
  }

  const r = await api('/push/subscribe', { method: 'POST', body: JSON.stringify({ subscription: sub.toJSON() }) })
  if (r && r.error) return { ok: false, reason: 'server' }
  return { ok: true }
}

// Désactive le push : désabonne le navigateur + supprime côté serveur.
export async function disablePush() {
  if (!pushSupported()) return { ok: true }
  try {
    const reg = await navigator.serviceWorker.getRegistration()
    const sub = reg && (await reg.pushManager.getSubscription())
    if (sub) {
      const endpoint = sub.endpoint
      await sub.unsubscribe()
      await api('/push/unsubscribe', { method: 'POST', body: JSON.stringify({ endpoint }) })
    }
  } catch (e) {}
  return { ok: true }
}
