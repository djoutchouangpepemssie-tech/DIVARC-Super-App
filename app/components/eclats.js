'use client'

// Éclats — monnaie interne DIVARC (sens unique, sans valeur monétaire).
import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, X, Gift, Flame, Check, RefreshCw, Info } from 'lucide-react'
import { api } from '@/lib/api'

const cx = (...a) => a.filter(Boolean).join(' ')
const fmt = (n) => new Intl.NumberFormat('fr-FR').format(n || 0)

function timeAgo(d) {
  const s = (Date.now() - new Date(d).getTime()) / 1000
  if (s < 60) return "à l'instant"
  if (s < 3600) return Math.floor(s / 60) + ' min'
  if (s < 86400) return Math.floor(s / 3600) + ' h'
  return Math.floor(s / 86400) + ' j'
}

// Petite carte à afficher dans le Hub
export function EclatsCard({ onOpen }) {
  const [balance, setBalance] = useState(null)
  const [canCheckin, setCanCheckin] = useState(false)
  useEffect(() => {
    let alive = true
    api('/eclats').then((r) => { if (alive && r && !r.error) { setBalance(r.balance); setCanCheckin(r.canCheckin) } })
    return () => { alive = false }
  }, [])
  return (
    <button onClick={onOpen} className="press w-full text-left rounded-[var(--radius)] p-4 relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg,#3a2f0e,#7a5b12 55%,#E2AA2B)' }}>
      <div className="flex items-center gap-3 text-white">
        <div className="w-11 h-11 rounded-2xl grid place-items-center bg-white/15 backdrop-blur"><Zap size={22} className="text-white" /></div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-white/75">Mes Éclats</div>
          <div className="font-display text-2xl leading-tight tabular">{balance == null ? '—' : fmt(balance)} ⚡</div>
        </div>
        {canCheckin && <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-white text-[#7a5b12] shrink-0">Check-in dispo</span>}
      </div>
    </button>
  )
}

export default function EclatsSheet({ onClose }) {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [giftOpen, setGiftOpen] = useState(false)
  const [giftHandle, setGiftHandle] = useState('')
  const [giftAmount, setGiftAmount] = useState('')

  const load = useCallback(async () => {
    const r = await api('/eclats')
    if (r && !r.error) setData(r)
  }, [])
  useEffect(() => { load() }, [load])

  const checkin = async () => {
    setBusy(true); setMsg('')
    const r = await api('/eclats/checkin', { method: 'POST' })
    setBusy(false)
    if (r.error) { setMsg(r.error); return }
    setMsg(`+${r.reward} ⚡ · série de ${r.streak} jour${r.streak > 1 ? 's' : ''} 🔥`)
    load()
  }

  const gift = async () => {
    const amount = parseInt(giftAmount, 10)
    if (!giftHandle.trim() || !amount || amount <= 0) { setMsg('Renseigne un contact et un montant'); return }
    setBusy(true); setMsg('')
    const r = await api('/eclats/gift', { method: 'POST', body: JSON.stringify({ toHandle: giftHandle.trim(), amount }) })
    setBusy(false)
    if (r.error) { setMsg(r.error); return }
    setMsg(`${amount} ⚡ offerts à ${r.to} 🎁`)
    setGiftOpen(false); setGiftHandle(''); setGiftAmount(''); load()
  }

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={onClose} className="press" aria-label="Fermer"><X size={22} /></button>
        <h1 className="font-display text-2xl">Éclats</h1>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
        {/* Solde */}
        <div className="rounded-[var(--radius)] p-6 my-4 text-white relative overflow-hidden" style={{ background: 'linear-gradient(135deg,#3a2f0e,#7a5b12 55%,#E2AA2B)' }}>
          <div className="text-sm text-white/75 flex items-center gap-1.5"><Zap size={15} /> Mon solde</div>
          <div className="font-display text-5xl mt-1 tabular">{data == null ? '—' : fmt(data.balance)} ⚡</div>
          {data?.streak > 0 && <div className="mt-2 inline-flex items-center gap-1 text-sm bg-white/15 backdrop-blur px-2.5 py-1 rounded-full"><Flame size={14} /> Série de {data.streak} jour{data.streak > 1 ? 's' : ''}</div>}
        </div>

        {msg && <div className="mb-3 rounded-2xl bg-gold/12 border border-gold/30 px-4 py-2.5 text-sm text-center">{msg}</div>}

        {/* Actions */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <button onClick={checkin} disabled={busy || !data?.canCheckin}
            className={cx('press rounded-2xl px-4 py-3.5 font-semibold flex items-center justify-center gap-2 text-white disabled:opacity-50', 'bg-gradient-to-br')}
            style={{ backgroundImage: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
            {busy ? <RefreshCw size={18} className="animate-spin" /> : <><Check size={18} /> {data?.canCheckin ? `Check-in +${data?.rates?.daily}` : 'Check-in fait ✓'}</>}
          </button>
          <button onClick={() => setGiftOpen((v) => !v)} className="press rounded-2xl px-4 py-3.5 font-semibold flex items-center justify-center gap-2 border border-border bg-card/60">
            <Gift size={18} /> Offrir
          </button>
        </div>

        {/* Formulaire cadeau */}
        <AnimatePresence>
          {giftOpen && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden mb-4">
              <div className="rounded-2xl border border-border bg-card/60 p-4 space-y-3">
                <div>
                  <label className="text-xs text-muted-foreground">Contact (@identifiant)</label>
                  <input value={giftHandle} onChange={(e) => setGiftHandle(e.target.value)} placeholder="@son_nom"
                    autoCapitalize="none" className="w-full mt-1 rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none focus:border-primary" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Nombre d'Éclats</label>
                  <input value={giftAmount} onChange={(e) => setGiftAmount(e.target.value.replace(/\D/g, ''))} inputMode="numeric" placeholder="30"
                    className="w-full mt-1 rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none focus:border-primary" />
                </div>
                <button onClick={gift} disabled={busy} className="press w-full rounded-xl py-3 font-semibold text-white disabled:opacity-50" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
                  Offrir les Éclats
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Comment en gagner */}
        <div className="rounded-2xl border border-border bg-card/40 p-4 mb-4 text-sm">
          <div className="font-semibold mb-2 flex items-center gap-1.5"><Zap size={15} className="text-gold" /> Comment gagner des Éclats</div>
          <ul className="space-y-1 text-muted-foreground text-[13px]">
            <li>• Check-in quotidien (+{data?.rates?.daily || 10}, bonus de série)</li>
            <li>• Parrainer un ami (+{data?.rates?.referral || 50} pour vous deux)</li>
            <li>• Cashback sur tes vrais achats ({((data?.rates?.cashbackBps || 200) / 100).toFixed(0)}%)</li>
          </ul>
        </div>

        {/* Historique */}
        <div className="mb-4">
          <div className="text-xs font-medium text-muted-foreground mb-2 px-1">Historique</div>
          <div className="rounded-2xl border border-border bg-card/40 divide-y divide-border/60">
            {(!data?.history || data.history.length === 0) ? (
              <div className="p-5 text-center text-sm text-muted-foreground">Aucun mouvement pour l'instant</div>
            ) : data.history.map((h) => (
              <div key={h.id} className="flex items-center gap-3 p-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{h.meta?.label || h.reason}</div>
                  <div className="text-[11px] text-muted-foreground">{timeAgo(h.createdAt)}</div>
                </div>
                <div className={cx('font-display tabular text-sm', h.delta >= 0 ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground')}>
                  {h.delta >= 0 ? '+' : ''}{fmt(h.delta)} ⚡
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Mention légale */}
        <div className="flex items-start gap-2 text-[11px] text-muted-foreground px-1 pb-4">
          <Info size={13} className="shrink-0 mt-0.5" />
          <span>{data?.disclaimer || "Les Éclats sont une monnaie interne à DIVARC, sans valeur monétaire. Ils ne sont ni retirables, ni remboursables, ni convertibles en argent."}</span>
        </div>
      </div>
    </motion.div>
  )
}
