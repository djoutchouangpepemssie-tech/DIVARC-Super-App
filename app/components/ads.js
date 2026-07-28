'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { Plus, X, Megaphone, Eye, MousePointerClick, TrendingUp, Pause, Play, RotateCcw, Target, Users, Wallet, ChevronRight, Sparkles, Check } from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const eur = (c) => (c / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const Glass = ({ className, sheen, children, ...p }) => <div className={cx('glass', sheen && 'glass-sheen', className)} {...p}>{children}</div>

const OBJECTIVES = [
  { id: 'Notoriété', emoji: '📣', d: 'Maximiser les impressions' },
  { id: 'Trafic', emoji: '🔗', d: 'Clics vers ta page' },
  { id: 'Ventes', emoji: '🛍️', d: 'Conversions & achats' },
  { id: 'Abonnés', emoji: '➕', d: 'Gagner des abonnés' },
]
const INTERESTS = ['#tech', '#mode', '#food', '#voyage', '#sport', '#musique', '#deco', '#lifestyle']
const COLORS = ['#4353F0', '#E2AA2B', '#3FB68B', '#9B5DE5', '#F15BB5', '#00BBF9']
const EMOJIS = ['📣', '🛍️', '🚀', '🔥', '💡', '🎉', '👟', '🍔', '✈️', '🎧']

export default function AdsManager({ me, onWalletRefresh }) {
  const [camps, setCamps] = useState([])
  const [open, setOpen] = useState(false)
  const [toast, setToast] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => { setLoading(true); const r = await api('/ads/campaigns'); if (Array.isArray(r)) setCamps(r); setLoading(false) }, [])
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t) }, [load])
  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2600) }

  const setStatus = async (c, status) => {
    await api(`/ads/campaigns/${c.id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
    load(); if (status === 'ended') { showToast('Campagne terminée · budget restant remboursé ↩️'); onWalletRefresh && onWalletRefresh() }
  }
  const totals = camps.reduce((a, c) => ({ imp: a.imp + (c.impressions || 0), clk: a.clk + (c.clicks || 0), spend: a.spend + (c.spentCents || 0) }), { imp: 0, clk: 0, spend: 0 })

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-4xl px-4 pt-6 pb-28">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-display text-3xl">Ads Manager</h1>
          <button onClick={() => setOpen(true)} className="press inline-flex items-center gap-2 rounded-full px-4 py-2.5 font-semibold text-white shadow-lg" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Plus size={18} /> Campagne</button>
        </div>

        {/* overview */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          <Stat icon={<Eye size={16} />} label="Impressions" value={totals.imp.toLocaleString('fr-FR')} />
          <Stat icon={<MousePointerClick size={16} />} label="Clics" value={totals.clk.toLocaleString('fr-FR')} />
          <Stat icon={<Wallet size={16} />} label="Dépensé" value={`${eur(totals.spend)} €`} />
        </div>

        {loading && camps.length === 0 ? (
          <Glass className="p-10 text-center text-muted-foreground">Chargement…</Glass>
        ) : camps.length === 0 ? (
          <Glass sheen className="p-10 text-center">
            <Megaphone className="mx-auto mb-3 text-primary" size={32} />
            <div className="font-semibold mb-1">Aucune campagne</div>
            <p className="text-sm text-muted-foreground mb-4">Lance ta première pub — elle apparaîtra en post sponsorisé dans DIVARC Social.</p>
            <button onClick={() => setOpen(true)} className="press rounded-2xl px-5 py-3 font-semibold text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Créer une campagne</button>
          </Glass>
        ) : (
          <div className="space-y-3">
            {camps.map((c) => {
              const pct = Math.min(100, Math.round((c.spentCents / c.budgetCents) * 100))
              return (
                <Glass key={c.id} className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-11 h-11 rounded-2xl grid place-items-center text-xl text-white" style={{ background: c.color }}>{c.creative?.emoji || '📣'}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm truncate">{c.name}</div>
                      <div className="text-xs text-muted-foreground">{c.objective} · {c.audience?.locations?.join(', ') || 'France'}</div>
                    </div>
                    <span className={cx('text-[11px] font-semibold px-2.5 py-1 rounded-full',
                      c.status === 'active' ? 'bg-green-500/12 text-green-600 dark:text-green-400' : c.status === 'paused' ? 'bg-amber-500/12 text-amber-600' : 'bg-muted text-muted-foreground')}>
                      {c.status === 'active' ? 'En cours' : c.status === 'paused' ? 'En pause' : 'Terminée'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-3 text-center">
                    <MiniStat label="Impressions" value={c.impressions} />
                    <MiniStat label="Clics" value={c.clicks} />
                    <MiniStat label="CTR" value={`${c.ctr || 0}%`} />
                  </div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Budget</span>
                    <span className="font-medium">{eur(c.spentCents)} / {eur(c.budgetCents)} €</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ background: c.color }} initial={{ width: 0 }} animate={{ width: `${pct}%` }} />
                  </div>
                  {c.status !== 'ended' && (
                    <div className="flex gap-2 mt-3">
                      {c.status === 'active'
                        ? <button onClick={() => setStatus(c, 'paused')} className="press flex-1 py-2 rounded-xl border border-border bg-card/60 text-sm font-medium flex items-center justify-center gap-1.5"><Pause size={14} /> Pause</button>
                        : <button onClick={() => setStatus(c, 'active')} className="press flex-1 py-2 rounded-xl border border-border bg-card/60 text-sm font-medium flex items-center justify-center gap-1.5"><Play size={14} /> Reprendre</button>}
                      <button onClick={() => setStatus(c, 'ended')} className="press flex-1 py-2 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-sm font-medium flex items-center justify-center gap-1.5"><RotateCcw size={14} /> Terminer</button>
                    </div>
                  )}
                </Glass>
              )
            })}
          </div>
        )}
      </div>

      <AnimatePresence>
        {open && <CreateCampaign me={me} onClose={() => setOpen(false)} onCreated={() => { setOpen(false); load(); onWalletRefresh && onWalletRefresh(); showToast('Campagne lancée 🚀 elle passe dans le feed Social !') }} />}
        {toast && <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="fixed bottom-28 left-1/2 -translate-x-1/2 z-[60] bg-ink text-white text-sm font-medium px-4 py-2.5 rounded-full shadow-xl">{toast}</motion.div>}
      </AnimatePresence>
    </div>
  )
}
const Stat = ({ icon, label, value }) => (
  <Glass className="p-3 text-center"><div className="flex items-center justify-center gap-1 text-muted-foreground text-xs mb-1">{icon}{label}</div><div className="font-display text-xl">{value}</div></Glass>
)
const MiniStat = ({ label, value }) => (
  <div><div className="font-display text-lg">{value}</div><div className="text-[10px] text-muted-foreground">{label}</div></div>
)

function CreateCampaign({ me, onClose, onCreated }) {
  const [step, setStep] = useState(0)
  const [objective, setObjective] = useState('Notoriété')
  const [interests, setInterests] = useState(['#tech'])
  const [age, setAge] = useState('18-34')
  const [budget, setBudget] = useState(1000) // €
  const [headline, setHeadline] = useState('')
  const [bodyTxt, setBodyTxt] = useState('')
  const [cta, setCta] = useState('En savoir plus')
  const [emoji, setEmoji] = useState('📣')
  const [color, setColor] = useState('#4353F0')
  const [busy, setBusy] = useState(false)
  const budgetCents = budget * 100
  const estImp = Math.round(budgetCents / 3)

  const toggleInt = (i) => setInterests((s) => s.includes(i) ? s.filter((x) => x !== i) : [...s, i])
  const suggest = () => { setHeadline('L\u2019offre qui change tout ✨'); setBodyTxt('Rejoins des milliers d\u2019utilisateurs sur DIVARC.'); setCta('Découvrir') }

  const launch = async () => {
    setBusy(true)
    const r = await api('/ads/campaigns', { method: 'POST', body: JSON.stringify({
      name: headline || 'Ma campagne', objective, audience: { interests, age, locations: ['France'] },
      budgetCents, color, creative: { headline: headline || 'Découvre DIVARC', body: bodyTxt, cta, emoji },
    }) })
    setBusy(false)
    if (r.error) return alert(r.error)
    onCreated()
  }

  const steps = ['Objectif', 'Audience', 'Budget', 'Créatif', 'Aperçu']
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass className="glass-strong p-5 rounded-b-none sm:rounded-b-[var(--radius)] max-h-[92dvh] overflow-y-auto no-scrollbar">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-2xl">Nouvelle campagne</h3>
            <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button>
          </div>
          <div className="flex gap-1.5 mb-5">
            {steps.map((_, i) => <div key={i} className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden"><motion.div className="h-full bg-primary" animate={{ width: i <= step ? '100%' : '0%' }} /></div>)}
          </div>

          {step === 0 && (
            <div>
              <StepH icon={<Target size={20} />} title="Quel est ton objectif ?" />
              <div className="grid grid-cols-2 gap-2">
                {OBJECTIVES.map((o) => (
                  <button key={o.id} onClick={() => setObjective(o.id)} className={cx('press p-3 rounded-2xl border text-left', objective === o.id ? 'border-primary bg-primary/10' : 'border-border bg-card/60')}>
                    <div className="text-2xl mb-1">{o.emoji}</div><div className="font-semibold text-sm">{o.id}</div><div className="text-[11px] text-muted-foreground">{o.d}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {step === 1 && (
            <div>
              <StepH icon={<Users size={20} />} title="Cible ton audience" />
              <label className="text-xs text-muted-foreground">Centres d'intérêt</label>
              <div className="flex flex-wrap gap-2 my-2">
                {INTERESTS.map((i) => <button key={i} onClick={() => toggleInt(i)} className={cx('press px-3 py-1.5 rounded-full text-sm border', interests.includes(i) ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border')}>{i}</button>)}
              </div>
              <label className="text-xs text-muted-foreground">Âge</label>
              <div className="flex gap-2 mt-2">
                {['13-17', '18-34', '35-54', '55+', 'Tous'].map((a) => <button key={a} onClick={() => setAge(a)} className={cx('press flex-1 py-2 rounded-xl text-sm border', age === a ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border')}>{a}</button>)}
              </div>
            </div>
          )}
          {step === 2 && (
            <div>
              <StepH icon={<Wallet size={20} />} title="Ton budget" />
              <div className="text-center my-3"><span className="font-display text-5xl tabular">{budget}</span> <span className="gold-text font-display text-3xl">€</span></div>
              <input type="range" min="5" max="200" step="5" value={budget} onChange={(e) => setBudget(Number(e.target.value))} className="w-full accent-[#4353F0]" />
              <Glass className="p-3 mt-4 text-sm flex items-center justify-between"><span className="text-muted-foreground">Impressions estimées</span><span className="font-semibold">~{estImp.toLocaleString('fr-FR')}</span></Glass>
              <p className="text-[11px] text-muted-foreground mt-2">Budget prépayé depuis ton wallet. Le reste non dépensé est remboursé si tu termines la campagne.</p>
            </div>
          )}
          {step === 3 && (
            <div>
              <StepH icon={<Sparkles size={20} />} title="Ton visuel" action={<button onClick={suggest} className="text-xs text-primary font-medium flex items-center gap-1"><Sparkles size={12} /> Idée IA</button>} />
              <div className="flex gap-2 overflow-x-auto no-scrollbar mb-2">{EMOJIS.map((e) => <button key={e} onClick={() => setEmoji(e)} className={cx('press shrink-0 w-11 h-11 rounded-2xl grid place-items-center text-xl border-2', emoji === e ? 'border-primary bg-primary/10' : 'border-border bg-card/60')}>{e}</button>)}</div>
              <div className="flex gap-2 mb-3">{COLORS.map((c) => <button key={c} onClick={() => setColor(c)} className={cx('press w-8 h-8 rounded-full border-2', color === c ? 'border-foreground' : 'border-transparent')} style={{ background: c }} />)}</div>
              <input value={headline} onChange={(e) => setHeadline(e.target.value)} placeholder="Titre accrocheur" className="w-full rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm mb-2" />
              <textarea value={bodyTxt} onChange={(e) => setBodyTxt(e.target.value)} rows={2} placeholder="Message…" className="w-full rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm mb-2" />
              <input value={cta} onChange={(e) => setCta(e.target.value)} placeholder="Bouton (CTA)" className="w-full rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
            </div>
          )}
          {step === 4 && (
            <div>
              <StepH icon={<Eye size={20} />} title="Aperçu sponsorisé" />
              <div className="rounded-[22px] overflow-hidden mb-4 h-64 flex flex-col items-center justify-center text-white text-center p-6" style={{ background: `linear-gradient(160deg, ${color}, #14162B)` }}>
                <span className="text-[10px] uppercase tracking-wide bg-white/25 px-2 py-0.5 rounded-full mb-3">Sponsorisé</span>
                <div className="text-5xl mb-3">{emoji}</div>
                <div className="font-display text-2xl leading-tight">{headline || 'Découvre DIVARC'}</div>
                <div className="text-sm text-white/80 mt-1">{bodyTxt}</div>
                <div className="mt-4 bg-white text-ink rounded-2xl px-4 py-2 font-semibold text-sm">{cta} →</div>
              </div>
              <Glass className="p-3 flex items-center justify-between text-sm"><span className="text-muted-foreground">À débiter du wallet</span><span className="font-display text-lg">{eur(budgetCents)} €</span></Glass>
            </div>
          )}

          <div className="flex gap-2 mt-5">
            {step > 0 && <button onClick={() => setStep((s) => s - 1)} className="press px-5 py-3 rounded-2xl border border-border bg-card/60 font-medium">Retour</button>}
            {step < 4
              ? <button onClick={() => setStep((s) => s + 1)} className="press flex-1 py-3 rounded-2xl font-semibold text-white flex items-center justify-center gap-1" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Continuer <ChevronRight size={18} /></button>
              : <button onClick={launch} disabled={busy} className="press flex-1 py-3 rounded-2xl font-semibold text-white disabled:opacity-40 flex items-center justify-center gap-2" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>{busy ? 'Lancement…' : <><Check size={18} /> Lancer & payer</>}</button>}
          </div>
        </Glass>
      </motion.div>
    </motion.div>
  )
}
const StepH = ({ icon, title, action }) => (
  <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-2"><div className="w-9 h-9 rounded-xl grid place-items-center bg-primary/10 text-primary">{icon}</div><h4 className="font-semibold">{title}</h4></div>{action}</div>
)
