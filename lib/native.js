// Intégration native (Capacitor) — ne s'active qu'en app iOS/Android. En web, tout est no-op.
// Fournit : démarrage natif (status bar, splash, bouton retour), haptique, partage natif,
// biométrie (Face ID / Touch ID), enregistrement des notifications push (APNs).
import { isNative, isIOS } from './platform'
import { api } from './api'

let _inited = false

export async function initNative() {
  if (_inited || !isNative()) return
  _inited = true
  try {
    const { StatusBar, Style } = await import('@capacitor/status-bar')
    await StatusBar.setStyle({ style: Style.Dark }).catch(() => {})
  } catch {}
  try {
    const { SplashScreen } = await import('@capacitor/splash-screen')
    await SplashScreen.hide().catch(() => {})
  } catch {}
  try {
    const { App } = await import('@capacitor/app')
    // Bouton retour Android : ne pas quitter brutalement l'app.
    App.addListener('backButton', ({ canGoBack }) => {
      if (canGoBack) window.history.back()
    })
  } catch {}
}

// ---------- Haptique ----------
export async function haptic(kind = 'light') {
  if (!isNative()) return
  try {
    const { Haptics, ImpactStyle, NotificationType } = await import('@capacitor/haptics')
    if (kind === 'success' || kind === 'error' || kind === 'warning') {
      const map = { success: NotificationType.Success, error: NotificationType.Error, warning: NotificationType.Warning }
      await Haptics.notification({ type: map[kind] })
    } else {
      const map = { light: ImpactStyle.Light, medium: ImpactStyle.Medium, heavy: ImpactStyle.Heavy }
      await Haptics.impact({ style: map[kind] || ImpactStyle.Light })
    }
  } catch {}
}

// ---------- Partage natif ----------
export async function nativeShare({ title, text, url }) {
  try {
    if (isNative()) {
      const { Share } = await import('@capacitor/share')
      await Share.share({ title, text, url })
      return true
    }
    if (typeof navigator !== 'undefined' && navigator.share) {
      await navigator.share({ title, text, url })
      return true
    }
  } catch {}
  return false
}

// ---------- Biométrie (Face ID / Touch ID) ----------
export async function biometricAvailable() {
  if (!isNative()) return false
  try {
    const { BiometricAuth } = await import('@aparajita/capacitor-biometric-auth')
    const info = await BiometricAuth.checkBiometry()
    return !!info.isAvailable
  } catch {
    return false
  }
}

export async function biometricVerify(reason = 'Déverrouille DIVARC') {
  if (!isNative()) return true
  try {
    const { BiometricAuth } = await import('@aparajita/capacitor-biometric-auth')
    await BiometricAuth.authenticate({
      reason,
      cancelTitle: 'Annuler',
      allowDeviceCredential: true,
      iosFallbackTitle: 'Utiliser le code',
    })
    return true
  } catch {
    return false
  }
}

// ---------- Notifications push (APNs) ----------
export async function registerPush() {
  if (!isNative()) return
  try {
    const { PushNotifications } = await import('@capacitor/push-notifications')
    let perm = await PushNotifications.checkPermissions()
    if (perm.receive === 'prompt') perm = await PushNotifications.requestPermissions()
    if (perm.receive !== 'granted') return
    PushNotifications.addListener('registration', (token) => {
      // Envoie le jeton APNs au backend (best-effort ; l'envoi réel APNs se configure côté serveur).
      api('/push/register-native', { method: 'POST', body: JSON.stringify({ platform: isIOS() ? 'ios' : 'android', token: token.value }) }).catch(() => {})
    })
    PushNotifications.addListener('registrationError', () => {})
    await PushNotifications.register()
  } catch {}
}
