// Sons de notification DIVARC — bip synthétisé via WebAudio (aucun asset, marche hors-ligne)
// + vibration haptique. Respecte une préférence utilisateur (localStorage) et la politique
// d'autoplay des navigateurs (le contexte audio est « débloqué » au 1er geste utilisateur).

let ctx = null
let unlocked = false

const PREF_KEY = 'divarc_sound'

export function soundEnabled() {
  if (typeof window === 'undefined') return true
  return localStorage.getItem(PREF_KEY) !== 'off'
}

export function setSoundEnabled(on) {
  if (typeof window === 'undefined') return
  localStorage.setItem(PREF_KEY, on ? 'on' : 'off')
  if (on) unlockAudio() // profiter du geste courant pour débloquer
}

function getCtx() {
  if (typeof window === 'undefined') return null
  const AC = window.AudioContext || window.webkitAudioContext
  if (!AC) return null
  if (!ctx) ctx = new AC()
  return ctx
}

// Débloque l'audio au premier geste (requis par iOS/Android).
export function unlockAudio() {
  const c = getCtx()
  if (!c) return
  if (c.state === 'suspended') c.resume().catch(() => {})
  unlocked = true
}

// Installe l'écouteur de déblocage une seule fois.
export function installAudioUnlock() {
  if (typeof window === 'undefined' || unlocked) return
  const handler = () => { unlockAudio() }
  ;['pointerdown', 'keydown', 'touchstart'].forEach((e) =>
    window.addEventListener(e, handler, { once: true, passive: true })
  )
}

// Joue un « ding » à deux notes, doux et court.
export function playPing() {
  if (!soundEnabled()) return
  // vibration légère (Android surtout)
  try { navigator.vibrate?.([12, 40, 12]) } catch {}
  const c = getCtx()
  if (!c) return
  if (c.state === 'suspended') { c.resume().catch(() => {}); }
  try {
    const now = c.currentTime
    const master = c.createGain()
    master.gain.value = 0.0001
    master.connect(c.destination)
    // enveloppe globale
    master.gain.setValueAtTime(0.0001, now)
    master.gain.exponentialRampToValueAtTime(0.22, now + 0.015)
    master.gain.exponentialRampToValueAtTime(0.0001, now + 0.5)

    const notes = [
      { f: 880, t: 0.0 },   // La5
      { f: 1174.66, t: 0.11 }, // Ré6
    ]
    for (const n of notes) {
      const osc = c.createOscillator()
      const g = c.createGain()
      osc.type = 'sine'
      osc.frequency.value = n.f
      g.gain.value = 1
      osc.connect(g); g.connect(master)
      osc.start(now + n.t)
      osc.stop(now + n.t + 0.28)
    }
  } catch {}
}
