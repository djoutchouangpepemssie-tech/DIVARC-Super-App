// Détection de la plateforme d'exécution (web vs app native iOS/Android).
// Sert à : (1) router les appels API vers le backend en natif (pas de proxy same-origin),
// (2) masquer sur iOS les fonctions non conformes App Store V1 (wallet €, abonnement,
//     achat d'Éclats) — décisions produit validées.

let _cap = null
function cap() {
  if (_cap !== null) return _cap
  if (typeof window !== 'undefined' && window.Capacitor) _cap = window.Capacitor
  else _cap = false
  return _cap
}

export function isNative() {
  const c = cap()
  return !!(c && (c.isNativePlatform ? c.isNativePlatform() : c.isNative))
}

export function getPlatform() {
  const c = cap()
  if (c && c.getPlatform) return c.getPlatform()
  return 'web'
}

export const isIOS = () => getPlatform() === 'ios'
export const isAndroid = () => getPlatform() === 'android'

// L'app iOS publiée sur l'App Store est une version « allégée » (conforme aux règles Apple) :
// pas de vente de numérique hors achats intégrés (abo DIVARC+, achat d'Éclats) ni de
// wallet en argent réel. On garde les Éclats GAGNÉS gratuitement.
export function isAppStoreBuild() {
  return isNative() && isIOS()
}

// Ces helpers pilotent l'affichage conditionnel côté UI.
export const showMoneyWallet = () => !isAppStoreBuild()   // wallet €, envoi d'argent, SEPA
export const showPaidPlans = () => !isAppStoreBuild()      // abonnement DIVARC+ payant
export const showBuyEclats = () => !isAppStoreBuild()      // acheter/recharger des Éclats

// Base des appels API. En web : proxy same-origin `/api`. En natif : URL absolue du backend
// (configurable via NEXT_PUBLIC_API_BASE au build ; défaut = domaine public DIVARC).
export function apiBase() {
  if (!isNative()) return ''
  const base = (process.env.NEXT_PUBLIC_API_BASE || 'https://www.divarc.fr').replace(/\/$/, '')
  return base
}
