'use client'

// DIVARC+ — abonnement (avantages, essai gratuit, abonnement, résiliation en un tap).
import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { X, Star, Check, RefreshCw, Heart, Eye, Zap, ShieldOff, Sparkles, Infinity as InfinityIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { showPaidPlans } from '@/lib/platform'

const eur = (c) => (c / 100).toFixed(2).replace('.', ',')
const PERK_ICONS = [InfinityIcon, Eye, ShieldOff, Zap, Sparkles, Heart]

export function PlusBadge() {
  return <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#9B5DE5)' }}><Star size={10} fill="#fff" /> DIVARC+</span>
}

export default function PlusSheet({ onClose }) {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => { const r = await api('/plus'); if (r && !r.error) setData(r) }, [])
  useEffect(() => { load() }, [load])

  const act = async (path, key) => {
    setBusy(key); setMsg('')
    const r = await api(path, { method: 'POST' })
    setBusy('')
    if (r.error) { setMsg(r.error); return }
    setData(r); setMsg(key === 'cancel' ? 'Renouvellement désactivé — accès conservé jusqu\'à l\'échéance.' : 'DIVARC+ activé 🎉')
  }

  const until = data?.until ? new Date(data.until).toLocaleDateString('fr-FR') : null

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={onClose} className="press" aria-label="Fermer"><X size={22} /></button>
        <h1 className="font-display text-2xl flex items-center gap-2"><Star size={20} className="text-primary" fill="currentColor" /> DIVARC+</h1>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
        {/* Hero */}
        <div className="rounded-[var(--radius)] p-6 my-4 text-white relative overflow-hidden" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7 55%,#9B5DE5)' }}>
          <div className="font-display text-3xl leading-tight">Passe en illimité</div>
          <div className="text-white/80 text-sm mt-1">Tout DIVARC, sans limites ni publicité.</div>
          {data?.active && (
            <div className="mt-3 inline-flex items-center gap-1.5 text-sm bg-white/15 backdrop-blur px-3 py-1 rounded-full">
              <Check size={14} /> Actif{until ? ` jusqu'au ${until}` : ''}
            </div>
          )}
        </div>

        {msg && <div className="mb-3 rounded-2xl bg-gold/12 border border-gold/30 px-4 py-2.5 text-sm text-center">{msg}</div>}

        {/* Avantages */}
        <div className="rounded-2xl border border-border bg-card/40 divide-y divide-border/60 mb-4">
          {(data?.perks || []).map((p, i) => {
            const Icon = PERK_ICONS[i % PERK_ICONS.length]
            return (
              <div key={i} className="flex items-center gap-3 p-3.5">
                <div className="w-9 h-9 rounded-xl grid place-items-center text-primary bg-primary/10"><Icon size={18} /></div>
                <span className="text-sm font-medium">{p}</span>
                <Check size={16} className="text-green-500 ml-auto" />
              </div>
            )
          })}
        </div>

        {/* Actions */}
        {!data ? (
          <div className="grid place-items-center py-8"><RefreshCw className="animate-spin text-muted-foreground" /></div>
        ) : data.active ? (
          <>
            {data.autoRenew ? (
              <button onClick={() => act('/plus/cancel', 'cancel')} disabled={busy === 'cancel'} className="press w-full rounded-2xl py-3 font-medium border border-border bg-card/60 mb-3">
                Résilier (garder jusqu'à l'échéance)
              </button>
            ) : (
              <div className="text-center text-sm text-muted-foreground mb-3">Ne se renouvellera pas automatiquement.</div>
            )}
          </>
        ) : !showPaidPlans() ? (
          // iOS App Store V1 : pas de vente hors achats intégrés Apple -> on présente les
          // avantages sans CTA d'achat (conforme règle 3.1.1). Achat dispo sur divarc.fr.
          <div className="text-center text-sm text-muted-foreground mb-4 rounded-2xl border border-border bg-card/60 p-4">
            L'abonnement DIVARC+ n'est pas encore disponible à l'achat dans l'app.
            <br />Retrouve tous ces avantages prochainement.
          </div>
        ) : (
          <>
            {!data.trialUsed && (
              <button onClick={() => act('/plus/trial', 'trial')} disabled={busy === 'trial'} className="press w-full rounded-2xl py-3.5 font-semibold text-white mb-3" style={{ background: 'linear-gradient(135deg,#4353F0,#9B5DE5)' }}>
                {busy === 'trial' ? <RefreshCw size={18} className="animate-spin mx-auto" /> : `Essai gratuit ${data.trialDays} jours`}
              </button>
            )}
            <button onClick={() => act('/plus/subscribe', 'sub')} disabled={busy === 'sub'} className="press w-full rounded-2xl py-3.5 font-semibold border border-primary/40 bg-primary/10 text-primary mb-2">
              {busy === 'sub' ? <RefreshCw size={18} className="animate-spin mx-auto" /> : `S'abonner · ${eur(data.priceCents)} €/mois`}
            </button>
            <p className="text-center text-[11px] text-muted-foreground mb-4">
              Sans engagement · résiliable en un tap · +{data.monthlyEclats} Éclats chaque mois.
              <br />Paiement via ton wallet (rechargement carte/SEPA à venir).
            </p>
          </>
        )}
      </div>
    </motion.div>
  )
}
