'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, X, ChevronRight, MessageCircle, HandCoins, ShoppingBag, Heart } from 'lucide-react'
import { api } from '@/lib/api'
import { onRealtime } from '@/lib/realtime'

const cx = (...a) => a.filter(Boolean).join(' ')
const ICONS = {
  message: { Icon: MessageCircle, cls: 'bg-primary/10 text-primary' },
  payment: { Icon: HandCoins, cls: 'bg-gold/15 text-gold-deep' },
  sale: { Icon: ShoppingBag, cls: 'bg-violet/10 text-violet' },
  offer: { Icon: HandCoins, cls: 'bg-gold/15 text-gold-deep' },
  social: { Icon: Heart, cls: 'bg-love/10 text-love' },
  system: { Icon: Bell, cls: 'bg-muted text-muted-foreground' },
}

function timeAgo(d) {
  const s = (Date.now() - new Date(d).getTime()) / 1000
  if (s < 60) return "à l'instant"
  if (s < 3600) return Math.floor(s / 60) + ' min'
  if (s < 86400) return Math.floor(s / 3600) + ' h'
  return Math.floor(s / 86400) + ' j'
}

export default function NotificationBell({ onOpen }) {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [unread, setUnread] = useState(0)

  const load = useCallback(async () => {
    const r = await api('/notifications')
    if (r && Array.isArray(r.items)) { setItems(r.items); setUnread(r.unread || 0) }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const off = onRealtime('notification', (m) => {
      if (m.notification) { setItems((x) => [m.notification, ...x].slice(0, 50)); setUnread((u) => u + 1) }
    })
    return off
  }, [])

  // Verrou du scroll de fond quand le panneau est ouvert
  useEffect(() => {
    if (typeof document === 'undefined') return
    document.body.classList.toggle('overlay-open', open)
    return () => document.body.classList.remove('overlay-open')
  }, [open])

  const openPanel = async () => {
    setOpen(true)
    if (unread > 0) {
      await api('/notifications/read', { method: 'POST' })
      setUnread(0)
      setItems((x) => x.map((n) => ({ ...n, read: true })))
    }
  }

  return (
    <>
      <button onClick={openPanel} aria-label="Notifications"
        className="relative w-10 h-10 rounded-full grid place-items-center press border border-border bg-card/60 backdrop-blur">
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-white text-[10px] font-bold grid place-items-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div className="fixed inset-0 z-[60]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
            <motion.div
              className="absolute right-0 top-0 h-full w-full max-w-sm border-l border-border p-4 pt-safe pb-safe overflow-y-auto overscroll-contain shadow-2xl"
              style={{ backgroundColor: 'hsl(var(--card))' }}
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 280 }}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-2xl">Notifications</h2>
                <button onClick={() => setOpen(false)} className="w-9 h-9 rounded-full grid place-items-center press" aria-label="Fermer">
                  <X size={18} />
                </button>
              </div>
              {items.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-20">
                  <Bell size={28} className="mx-auto mb-3 opacity-40" aria-hidden="true" />
                  Aucune notification pour le moment
                </div>
              ) : (
                <div className="space-y-2">
                  {items.map((n) => {
                    const { Icon, cls } = ICONS[n.kind] || ICONS.system
                    return (
                    <button key={n.id} onClick={() => { setOpen(false); onOpen?.(n) }}
                      className={cx('press w-full text-left flex gap-3 p-3 rounded-2xl border border-border hover:bg-muted/40 transition-colors', !n.read && 'bg-primary/5 border-primary/20')}>
                      <div className={cx('w-9 h-9 rounded-inner grid place-items-center shrink-0', cls)}><Icon size={17} /></div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium">{n.title}</div>
                        {n.body && <div className="text-xs text-muted-foreground truncate">{n.body}</div>}
                        <div className="text-[10px] text-muted-foreground mt-0.5">{timeAgo(n.createdAt)}</div>
                      </div>
                      <ChevronRight size={16} className="text-muted-foreground shrink-0 self-center" />
                    </button>
                    )
                  })}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
