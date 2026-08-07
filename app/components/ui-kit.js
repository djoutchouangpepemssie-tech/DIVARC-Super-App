'use client'

/* =====================================================================
   DIVARC — Kit UI canonique (Design System v2)
   UN toast · UN avatar · UN toggle · UNE confirmation stylée · UN Éclat
   Remplace : les 3 toasts concurrents, les 4 avatars dupliqués,
   les 3 toggles, les alert()/confirm()/prompt() natifs, le « ⚡ » texte.
   ===================================================================== */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, Info, AlertTriangle, Zap, X } from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')

/* ---------------------------------------------------------------------
   TOAST — pilule encre, bas centré (2,6 s), icône selon le sens.
   Usage : toast('Annonce publiée') · toast('Impossible', 'error')
   <ToastHost /> est monté une seule fois dans page.js.
--------------------------------------------------------------------- */
const toastListeners = new Set()
let toastSeq = 0

export function toast(msg, kind = 'success') {
  toastListeners.forEach((l) => l({ id: ++toastSeq, msg, kind }))
}

const TOAST_ICON = {
  success: Check,
  info: Info,
  error: AlertTriangle,
  eclat: Zap,
}

export function ToastHost() {
  const [items, setItems] = useState([])
  useEffect(() => {
    const on = (t) => {
      setItems((xs) => [...xs.slice(-2), t])
      setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== t.id)), 2600)
    }
    toastListeners.add(on)
    return () => toastListeners.delete(on)
  }, [])
  return (
    <div className="fixed left-0 right-0 bottom-28 z-[95] flex flex-col items-center gap-2 pointer-events-none px-4">
      <AnimatePresence>
        {items.map((t) => {
          const Icon = TOAST_ICON[t.kind] || Info
          return (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 14, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              className="flex items-center gap-2 rounded-full bg-ink text-white text-xs font-semibold px-4 py-2.5 shadow-xl max-w-full"
            >
              <Icon
                size={13}
                className={cx(
                  t.kind === 'error' && 'text-danger',
                  t.kind === 'eclat' && 'text-gold',
                  t.kind === 'success' && 'text-success'
                )}
              />
              <span className="truncate">{t.msg}</span>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

/* ---------------------------------------------------------------------
   CONFIRMATION STYLÉE — remplace confirm()/prompt() natifs.
   Usage : const ok = await askConfirm({ title: 'Supprimer ?', message: '…',
            confirmLabel: 'Supprimer', danger: true })
   <ConfirmHost /> est monté une seule fois dans page.js.
--------------------------------------------------------------------- */
const confirmListeners = new Set()

export function askConfirm(opts) {
  return new Promise((resolve) => {
    confirmListeners.forEach((l) => l({ ...opts, resolve }))
  })
}

export function ConfirmHost() {
  const [req, setReq] = useState(null)
  useEffect(() => {
    const on = (r) => setReq(r)
    confirmListeners.add(on)
    return () => confirmListeners.delete(on)
  }, [])
  const close = (val) => {
    req?.resolve(val)
    setReq(null)
  }
  return (
    <AnimatePresence>
      {req && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[96] bg-ink/40 backdrop-blur-sm flex items-end sm:items-center justify-center"
          onClick={() => close(false)}
        >
          <motion.div
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 30, opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 340 }}
            onClick={(e) => e.stopPropagation()}
            className="glass glass-strong w-full max-w-sm m-0 sm:m-4 p-5 pb-[max(env(safe-area-inset-bottom),20px)] rounded-b-none sm:rounded-b-lg"
          >
            <div className="mx-auto w-10 h-1.5 rounded-full bg-muted mb-4 sm:hidden" />
            <div className="flex items-start gap-3">
              <div
                className={cx(
                  'w-10 h-10 rounded-inner flex items-center justify-center shrink-0',
                  req.danger ? 'bg-danger/10 text-danger' : 'bg-primary/10 text-primary'
                )}
              >
                {req.danger ? <AlertTriangle size={18} /> : <Info size={18} />}
              </div>
              <div className="min-w-0">
                <div className="font-display text-2xl leading-tight">{req.title}</div>
                {req.message && (
                  <p className="text-sm text-muted-foreground mt-1.5">{req.message}</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-5">
              <button
                onClick={() => close(false)}
                className="rounded-inner border border-border bg-card/60 px-4 py-3 text-sm font-semibold press"
              >
                {req.cancelLabel || 'Annuler'}
              </button>
              <button
                onClick={() => close(true)}
                className={cx(
                  'rounded-inner px-4 py-3 text-sm font-bold text-white press',
                  req.danger ? 'bg-danger' : 'grad-primary'
                )}
              >
                {req.confirmLabel || 'Confirmer'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/* ---------------------------------------------------------------------
   AVATAR — LE composant unique (fallback : dégradé primaire canonique).
   Props : c {name, color?, avatarColor?, photo?} · size · ring (couleur)
--------------------------------------------------------------------- */
export function Avatar({ c, size = 44, ring, className, children }) {
  const name = c?.name || c?.displayName || c?.title || ''
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
  const solid = c?.color || c?.avatarColor
  return (
    <div
      className={cx(
        'relative grid place-items-center rounded-full text-white font-body font-bold shrink-0 overflow-hidden',
        !solid && 'grad-primary',
        className
      )}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        background: solid || undefined,
        boxShadow: ring ? `0 0 0 2px hsl(var(--background)), 0 0 0 4px ${ring}` : undefined,
      }}
    >
      {c?.photo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={c.photo} alt={name} className="w-full h-full object-cover" />
      ) : (
        initials || '•'
      )}
      {children}
    </div>
  )
}

/* ---------------------------------------------------------------------
   TOGGLE — LE toggle unique (48×28, pastille 21, ressort).
--------------------------------------------------------------------- */
export function Toggle({ on, onClick, busy, 'aria-label': ariaLabel }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={!!on}
      aria-label={ariaLabel}
      disabled={busy}
      onClick={onClick}
      className={cx(
        'relative w-12 h-7 rounded-full border transition-colors duration-200 shrink-0',
        on ? 'bg-primary border-primary' : 'bg-muted border-border',
        busy && 'opacity-60'
      )}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className="absolute top-[2.5px] w-[21px] h-[21px] rounded-full bg-white shadow"
        style={{ left: on ? 22 : 3 }}
      />
    </button>
  )
}

/* ---------------------------------------------------------------------
   ÉCLAT — le glyphe or unique. Remplace le « ⚡ » texte partout.
   Usage : <Eclats n={240} /> · <EclatIcon size={14} />
--------------------------------------------------------------------- */
export function EclatIcon({ size = 13, className }) {
  return <Zap size={size} className={cx('inline-block text-gold shrink-0', className)} fill="currentColor" strokeWidth={0} aria-label="Éclats" />
}

export function Eclats({ n, size = 13, className }) {
  return (
    <span className={cx('inline-flex items-center gap-1 tabular', className)}>
      {typeof n === 'number' ? n.toLocaleString('fr-FR') : n}
      <EclatIcon size={size} />
    </span>
  )
}

/* ---------------------------------------------------------------------
   PILL — étiquette canonique.
--------------------------------------------------------------------- */
export function Pill({ tone = 'neutral', className, children }) {
  const tones = {
    neutral: 'bg-muted text-muted-foreground',
    indigo: 'bg-primary/10 text-primary',
    gold: 'bg-gold/15 text-gold-deep border border-gold/35',
    success: 'bg-success/10 text-success',
    danger: 'bg-danger/10 text-danger',
    glass: 'bg-white/15 text-white border border-white/25',
  }
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold',
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  )
}
