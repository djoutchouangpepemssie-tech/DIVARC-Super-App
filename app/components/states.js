'use client'

import { motion } from 'framer-motion'
import { Loader2, WifiOff, RefreshCw, Inbox, AlertTriangle } from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')

/* ---------- Skeletons "glass" ---------- */
export function Skel({ className }) {
  return <div className={cx('skeleton rounded-inner', className)} />
}

export function ListingsSkeleton({ count = 6 }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass rounded-lg overflow-hidden">
          <Skel className="aspect-[4/3] rounded-none" />
          <div className="p-2.5 space-y-2">
            <Skel className="h-3 w-1/2" />
            <Skel className="h-4 w-3/4" />
            <Skel className="h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function RowsSkeleton({ count = 4 }) {
  return (
    <div className="space-y-2.5" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass rounded-lg p-3.5">
          <div className="flex items-center gap-3 mb-3">
            <Skel className="w-10 h-10" />
            <div className="flex-1 space-y-2"><Skel className="h-3 w-1/2" /><Skel className="h-2.5 w-1/3" /></div>
            <Skel className="h-5 w-16 rounded-full" />
          </div>
          <div className="grid grid-cols-4 gap-2 mb-2.5">{Array.from({ length: 4 }).map((_, j) => <Skel key={j} className="h-7" />)}</div>
          <Skel className="h-2 w-full rounded-full" />
        </div>
      ))}
    </div>
  )
}

export function KpiSkeleton({ count = 4 }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass rounded-lg p-3.5 space-y-2"><Skel className="h-3 w-1/2" /><Skel className="h-6 w-2/3" /></div>
      ))}
    </div>
  )
}

export function FeedSkeleton({ label = 'Chargement du flux…' }) {
  return (
    <div className="h-full w-full grid place-items-center bg-black" role="status" aria-live="polite">
      <div className="flex flex-col items-center gap-3 text-white/60">
        <Loader2 className="animate-spin" size={28} aria-hidden="true" />
        <span className="text-sm">{label}</span>
      </div>
    </div>
  )
}

/* ---------- États vides / erreur illustrés ---------- */
export function EmptyState({ icon: Icon = Inbox, title, desc, action, dark, emoji }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className={cx('grid place-items-center text-center px-8 py-14', dark && 'text-white')}>
      <div>
        <div className={cx('w-20 h-20 rounded-3xl grid place-items-center mx-auto mb-4 float-slow hairline', dark ? 'bg-white/10' : 'bg-primary/8')}>
          {emoji ? <span className="text-4xl" aria-hidden="true">{emoji}</span> : <Icon size={34} className={dark ? 'text-white/80' : 'text-primary'} aria-hidden="true" />}
        </div>
        <div className="font-display text-2xl mb-1.5">{title}</div>
        {desc && <p className={cx('text-sm max-w-xs mx-auto leading-relaxed', dark ? 'text-white/70' : 'text-muted-foreground')}>{desc}</p>}
        {action && <div className="mt-5 flex justify-center">{action}</div>}
      </div>
    </motion.div>
  )
}

export function ErrorState({ title = 'Oups, une erreur', desc = 'Impossible de charger le contenu. Vérifie ta connexion et réessaie.', onRetry, dark }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} role="alert"
      className={cx('grid place-items-center text-center px-8 py-14', dark && 'text-white')}>
      <div>
        <div className="w-20 h-20 rounded-3xl grid place-items-center mx-auto mb-4 bg-destructive/10 hairline"><AlertTriangle size={32} className="text-destructive" aria-hidden="true" /></div>
        <div className="font-display text-2xl mb-1.5">{title}</div>
        <p className={cx('text-sm max-w-xs mx-auto leading-relaxed', dark ? 'text-white/70' : 'text-muted-foreground')}>{desc}</p>
        {onRetry && <button onClick={onRetry} className="press mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-white font-semibold text-sm glow-primary grad-primary"><RefreshCw size={16} aria-hidden="true" /> Réessayer</button>}
      </div>
    </motion.div>
  )
}

/* ---------- Bandeau hors-ligne / synchronisation ---------- */
export function OfflineBanner({ online, syncing }) {
  if (online && !syncing) return null
  return (
    <motion.div initial={{ y: -44, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -44, opacity: 0 }}
      role="status" aria-live="polite"
      className={cx('fixed top-0 inset-x-0 z-[90] flex items-center justify-center gap-2 py-2 text-sm font-medium text-white shadow-lg',
        online ? 'grad-success' : 'grad-gold')}>
      {online
        ? <><RefreshCw size={14} className="animate-spin" aria-hidden="true" /> Reconnecté — synchronisation de tes actions…</>
        : <><WifiOff size={14} aria-hidden="true" /> Hors ligne — tes actions seront synchronisées au retour</>}
    </motion.div>
  )
}
