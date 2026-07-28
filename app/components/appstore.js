'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { Search, X, Star, Check, Shield, Link2, Unlink, ExternalLink, Sparkles, Users } from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const Glass = ({ className, sheen, children, ...p }) => <div className={cx('glass', sheen && 'glass-sheen', className)} {...p}>{children}</div>
const Icon = ({ a, size = 56 }) => (
  <div className="rounded-2xl grid place-items-center text-white shadow" style={{ width: size, height: size, background: `linear-gradient(150deg, ${a.color}, ${a.color}bb)`, fontSize: size * 0.44 }}>{a.emoji}</div>
)
const CATS = ['Tout', 'Finance', 'Musique', 'Streaming', 'Transport', 'Santé', 'Shopping', 'Productivité', 'Jeux', 'Repas']
const kf = (n) => n >= 1000000 ? (n / 1000000).toFixed(1).replace('.0', '') + 'M' : n >= 1000 ? Math.round(n / 1000) + 'k' : n

export default function AppStore({ me }) {
  const [apps, setApps] = useState([])
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('Tout')
  const [detail, setDetail] = useState(null)
  const [toast, setToast] = useState(null)

  const load = useCallback(async () => { const r = await api(`/store/apps?q=${encodeURIComponent(q)}&cat=${encodeURIComponent(cat)}`); if (Array.isArray(r)) setApps(r) }, [q, cat])
  useEffect(() => { load() }, [load])
  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2600) }

  const connect = async (a) => {
    const r = await api(`/store/apps/${a.id}/connect`, { method: 'POST' })
    if (r.error) return showToast('⚠️ ' + r.error)
    setDetail((d) => d ? { ...d, connected: true, pseudonym: r.connection.pseudonym } : d)
    load(); showToast(`${a.name} connectée · pseudonyme ${r.connection.pseudonym}`)
  }
  const disconnect = async (a) => {
    await api(`/store/apps/${a.id}/disconnect`, { method: 'POST' })
    setDetail((d) => d ? { ...d, connected: false } : d)
    load(); showToast(`${a.name} déconnectée`)
  }

  const connected = apps.filter((a) => a.connected)

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-4xl px-4 pt-6 pb-28">
        <h1 className="font-display text-3xl mb-1">App Store</h1>
        <p className="text-sm text-muted-foreground mb-4">Connecte tes apps préférées — accès facile, identité cloisonnée par app.</p>

        <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5 mb-3">
          <Search size={16} className="text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher une app…" className="flex-1 bg-transparent text-sm outline-none" />
        </div>
        <div className="flex gap-2 overflow-x-auto no-scrollbar mb-5">
          {CATS.map((c) => <button key={c} onClick={() => setCat(c)} className={cx('press whitespace-nowrap px-3.5 py-1.5 rounded-full text-sm font-medium border', cat === c ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{c}</button>)}
        </div>

        {connected.length > 0 && cat === 'Tout' && !q && (
          <div className="mb-6">
            <h2 className="font-semibold text-[15px] mb-2 flex items-center gap-1.5"><Link2 size={15} className="text-primary" /> Connectées</h2>
            <div className="flex gap-4 overflow-x-auto no-scrollbar pb-1">
              {connected.map((a) => (
                <button key={a.id} onClick={() => setDetail(a)} className="press flex flex-col items-center gap-1.5 min-w-[64px]">
                  <div className="relative"><Icon a={a} size={56} /><span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-green-500 grid place-items-center text-white"><Check size={12} /></span></div>
                  <span className="text-[11px] font-medium truncate w-16 text-center">{a.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2.5">
          {apps.map((a) => (
            <button key={a.id} onClick={() => setDetail(a)} className="press w-full text-left">
              <Glass className="p-3 flex items-center gap-3">
                <Icon a={a} size={52} />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm flex items-center gap-1.5">{a.name} <span className="text-[10px] text-muted-foreground font-normal">· {a.cat}</span></div>
                  <div className="text-xs text-muted-foreground truncate">{a.desc}</div>
                  <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted-foreground"><span className="flex items-center gap-0.5"><Star size={11} className="text-gold" fill="#E2AA2B" /> {a.rating}</span><span className="flex items-center gap-0.5"><Users size={11} /> {kf(a.users)}</span></div>
                </div>
                <span className={cx('shrink-0 text-xs font-semibold px-3 py-1.5 rounded-full', a.connected ? 'bg-green-500/12 text-green-600 dark:text-green-400' : 'bg-primary/10 text-primary')}>{a.connected ? 'Connectée' : 'Connecter'}</span>
              </Glass>
            </button>
          ))}
          {apps.length === 0 && <Glass className="p-10 text-center text-muted-foreground">Aucune app trouvée.</Glass>}
        </div>
      </div>

      <AnimatePresence>
        {detail && <AppDetail a={detail} onClose={() => setDetail(null)} onConnect={() => connect(detail)} onDisconnect={() => disconnect(detail)} onOpen={() => showToast(`Ouverture de ${detail.name}…`)} />}
        {toast && <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="fixed bottom-28 left-1/2 -translate-x-1/2 z-[60] bg-ink text-white text-sm font-medium px-4 py-2.5 rounded-full shadow-xl max-w-[92vw] text-center">{toast}</motion.div>}
      </AnimatePresence>
    </div>
  )
}

function AppDetail({ a, onClose, onConnect, onDisconnect, onOpen }) {
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass sheen className="glass-strong p-5 rounded-b-none sm:rounded-b-[var(--radius)] max-h-[92dvh] overflow-y-auto no-scrollbar">
          <div className="flex justify-end mb-2"><button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button></div>
          <div className="flex items-center gap-4 mb-4">
            <Icon a={a} size={72} />
            <div>
              <div className="font-display text-2xl">{a.name}</div>
              <div className="text-sm text-muted-foreground">{a.cat}</div>
              <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground"><span className="flex items-center gap-0.5"><Star size={12} className="text-gold" fill="#E2AA2B" /> {a.rating}</span><span className="flex items-center gap-0.5"><Users size={12} /> {kf(a.users)} utilisateurs</span></div>
            </div>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed mb-4">{a.desc}</p>

          <div className="mb-4">
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5"><Shield size={15} className="text-primary" /> Données demandées</h3>
            <div className="space-y-1.5">
              {a.perms?.map((p) => (
                <div key={p} className="flex items-center gap-2 text-sm rounded-xl bg-card/60 border border-border px-3 py-2"><Check size={14} className="text-primary" /> {p}</div>
              ))}
            </div>
          </div>

          {a.connected ? (
            <>
              <Glass className="p-3 mb-3 text-sm flex items-center gap-2 !bg-green-500/10"><Shield size={16} className="text-green-600 dark:text-green-400" /> Connectée sous le pseudonyme <b className="font-grotesk">{a.pseudonym || 'divarc-••••'}</b></Glass>
              <div className="flex gap-2">
                <button onClick={onOpen} className="press flex-1 py-3 rounded-2xl font-semibold text-white flex items-center justify-center gap-2" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><ExternalLink size={16} /> Ouvrir</button>
                <button onClick={onDisconnect} className="press px-5 py-3 rounded-2xl border border-destructive/30 bg-destructive/10 text-destructive font-medium flex items-center gap-1.5"><Unlink size={16} /> Déconnecter</button>
              </div>
            </>
          ) : (
            <button onClick={onConnect} className="press w-full py-3.5 rounded-2xl font-semibold text-white flex items-center justify-center gap-2" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
              <Link2 size={18} /> Connecter · identité cloisonnée
            </button>
          )}
          <p className="text-[11px] text-muted-foreground text-center mt-3">Tu peux révoquer l'accès à tout moment depuis Profil › Qui voit quoi.</p>
        </Glass>
      </motion.div>
    </motion.div>
  )
}
