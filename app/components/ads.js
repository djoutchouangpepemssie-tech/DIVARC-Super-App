'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import {
  ArrowLeft, Plus, X, Check, TrendingUp, MousePointerClick, Eye, Target, DollarSign,
  Play, Pause, Trash2, ChevronRight, Sparkles, Search, Loader2, BarChart3, Users,
  Megaphone, Zap, Wallet as WalletIcon, Gauge, MapPin, Percent,
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const Glass = ({ className, sheen, strong, children, ...p }) => <div className={cx('glass', sheen && 'glass-sheen', strong && 'glass-strong', className)} {...p}>{children}</div>
const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const eur0 = (c) => Math.round((c || 0) / 100).toLocaleString('fr-FR')
const kf = (n) => n >= 1000000 ? (n / 1000000).toFixed(1).replace('.0', '') + 'M' : n >= 1000 ? (n / 1000).toFixed(1).replace('.0', '') + 'k' : String(n || 0)

export default function AdsManager({ me, onWalletRefresh, onImmersive }) {
  const [view, setView] = useState('dashboard') // dashboard | create | detail
  const [config, setConfig] = useState(null)
  const [campaigns, setCampaigns] = useState([])
  const [insights, setInsights] = useState(null)
  const [detailId, setDetailId] = useState(null)
  const [toast, setToast] = useState(null)
  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2600) }

  useEffect(() => { onImmersive?.(view !== 'dashboard') }, [view, onImmersive])

  const load = useCallback(async () => {
    const [c, i] = await Promise.all([api('/ads/campaigns'), api('/ads/insights')])
    if (Array.isArray(c)) setCampaigns(c)
    if (i && !i.error) setInsights(i)
  }, [])
  useEffect(() => { api('/ads/config').then((r) => { if (!r.error) setConfig(r) }); load() }, [load])

  if (view === 'create' && config) return <CreateWizard config={config} onCancel={() => setView('dashboard')} onDone={() => { showToast('Campagne lancée 🚀'); onWalletRefresh?.(); setView('dashboard'); load() }} showToast={showToast} />
  if (view === 'detail' && detailId) return <CampaignDetail id={detailId} config={config} onBack={() => { setView('dashboard'); load() }} onWalletRefresh={onWalletRefresh} showToast={showToast} />

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-5xl px-4 pt-6 pb-28">
        <div className="flex items-center justify-between mb-4">
          <div><h1 className="font-display text-3xl leading-none">Ads Manager</h1><p className="text-sm text-muted-foreground mt-1">Crée, cible et pilote tes campagnes — comme les pros.</p></div>
          <button onClick={() => setView('create')} className="press h-11 px-4 rounded-full grid place-items-center text-white font-semibold text-sm gap-1.5 flex" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Plus size={18} /> Nouvelle campagne</button>
        </div>

        {/* KPIs globaux */}
        {insights && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mb-5">
            <Kpi icon={Eye} label="Impressions" value={kf(insights.totals.impressions)} color="#4353F0" />
            <Kpi icon={MousePointerClick} label="Clics" value={kf(insights.totals.clicks)} sub={`CTR ${insights.totals.ctr}%`} color="#9B5DE5" />
            <Kpi icon={Target} label="Conversions" value={kf(insights.totals.conversions)} sub={`${insights.totals.convRate}%`} color="#3FB68B" />
            <Kpi icon={DollarSign} label="Dépensé" value={`${eur0(insights.totals.spentCents)} €`} sub={`CPC ${eur(insights.totals.cpcCents)} €`} gold />
          </div>
        )}

        {/* graphe perf agrégée */}
        {insights?.daily?.length > 0 && (
          <Glass className="p-4 mb-5">
            <div className="flex items-center justify-between mb-3"><div className="font-semibold text-sm flex items-center gap-1.5"><BarChart3 size={15} className="text-primary" /> Performance (14 j)</div><span className="text-xs text-muted-foreground">Impressions / jour</span></div>
            <BarChart data={insights.daily} field="impressions" />
          </Glass>
        )}

        {/* liste campagnes */}
        <div className="flex items-center justify-between mb-2"><div className="font-semibold">Campagnes {insights && <span className="text-muted-foreground font-normal">· {insights.counts.active} active{insights.counts.active > 1 ? 's' : ''}</span>}</div></div>
        {campaigns.length === 0 ? (
          <Glass className="p-12 text-center"><Megaphone size={34} className="mx-auto mb-3 text-muted-foreground" /><div className="font-semibold mb-1">Aucune campagne</div><div className="text-sm text-muted-foreground mb-4">Lance ta première campagne en 3 étapes.</div><button onClick={() => setView('create')} className="press px-5 py-2.5 rounded-full text-white font-semibold text-sm" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Créer une campagne</button></Glass>
        ) : (
          <div className="space-y-2.5">{campaigns.map((c) => <CampaignRow key={c.id} c={c} config={config} onOpen={() => { setDetailId(c.id); setView('detail') }} />)}</div>
        )}
      </div>
      <AnimatePresence>{toast && <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="fixed bottom-28 left-1/2 -translate-x-1/2 z-[70] bg-ink text-white text-sm font-medium px-4 py-2.5 rounded-full shadow-xl">{toast}</motion.div>}</AnimatePresence>
    </div>
  )
}

const Kpi = ({ icon: Icon, label, value, sub, color, gold }) => (
  <Glass className="p-3.5">
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><Icon size={13} style={{ color: gold ? '#E2AA2B' : color }} /> {label}</div>
    <div className={cx('font-display tabular text-2xl leading-none', gold && 'text-gold')} style={!gold ? { color } : {}}>{value}</div>
    {sub && <div className="text-[11px] text-muted-foreground mt-1">{sub}</div>}
  </Glass>
)

function BarChart({ data, field = 'impressions' }) {
  const max = Math.max(1, ...data.map((d) => d[field] || 0))
  return (
    <div className="flex items-end gap-1 h-28">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
          <div className="w-full rounded-t-md transition-all" style={{ height: `${Math.max(4, (d[field] || 0) / max * 100)}%`, background: 'linear-gradient(180deg,#4353F0,#6E7BF5)' }} title={`${d.date} : ${d[field]}`} />
          <span className="text-[8px] text-muted-foreground">{d.date.slice(8)}</span>
        </div>
      ))}
    </div>
  )
}

function CampaignRow({ c, config, onOpen }) {
  const typeDef = config?.types?.find((t) => t.id === c.type)
  const statusColor = c.status === 'active' ? 'text-green-600 dark:text-green-400 bg-green-500/12' : c.status === 'paused' ? 'text-gold bg-gold/12' : 'text-muted-foreground bg-muted/60'
  const statusLabel = c.status === 'active' ? 'Active' : c.status === 'paused' ? 'En pause' : 'Terminée'
  const pct = c.budgetCents ? Math.min(100, Math.round((c.spentCents || 0) / c.budgetCents * 100)) : 0
  return (
    <button onClick={onOpen} className="press w-full text-left"><Glass className="p-3.5">
      <div className="flex items-center gap-3 mb-2.5">
        <div className="w-10 h-10 rounded-2xl grid place-items-center text-white text-lg shrink-0" style={{ background: typeDef?.color || c.color || '#4353F0' }}>{typeDef?.emoji || '📣'}</div>
        <div className="flex-1 min-w-0"><div className="font-semibold text-sm truncate">{c.name}</div><div className="text-[11px] text-muted-foreground">{typeDef?.name || c.type} · {c.objective}</div></div>
        <span className={cx('text-[11px] font-semibold px-2.5 py-1 rounded-full shrink-0', statusColor)}>{statusLabel}</span>
      </div>
      <div className="grid grid-cols-4 gap-2 text-center mb-2.5">
        <Mini label="Impr." value={kf(c.impressions)} /><Mini label="Clics" value={kf(c.clicks)} /><Mini label="CTR" value={`${c.ctr}%`} /><Mini label="CPC" value={`${eur(c.cpcCents)}€`} gold />
      </div>
      <div className="flex items-center gap-2"><div className="flex-1 h-1.5 rounded-full bg-muted/60 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'linear-gradient(90deg,#E2AA2B,#F0CE7E)' }} /></div><span className="text-[11px] text-muted-foreground tabular">{eur0(c.spentCents)} / {eur0(c.budgetCents)} €</span></div>
    </Glass></button>
  )
}
const Mini = ({ label, value, gold }) => <div><div className={cx('font-display tabular text-sm', gold && 'text-gold')}>{value}</div><div className="text-[10px] text-muted-foreground">{label}</div></div>

/* ============================ ASSISTANT DE CRÉATION ============================ */
function CreateWizard({ config, onCancel, onDone, showToast }) {
  const [step, setStep] = useState(0) // 0 type+obj, 1 ciblage+budget, 2 créa/mots-clés
  const [type, setType] = useState('search')
  const [objective, setObjective] = useState('traffic')
  const [name, setName] = useState('')
  const [budgetType, setBudgetType] = useState('daily')
  const [dailyBudget, setDailyBudget] = useState('20')
  const [totalBudget, setTotalBudget] = useState('300')
  const [bidStrategy, setBidStrategy] = useState('cpc')
  const [maxBid, setMaxBid] = useState('0.45')
  const [interests, setInterests] = useState([])
  const [ageRange, setAgeRange] = useState([])
  const [genders, setGenders] = useState(['Tous'])
  const [devices, setDevices] = useState([...config.devices])
  const [headline, setHeadline] = useState('')
  const [bodyTxt, setBodyTxt] = useState('')
  const [ctaTxt, setCtaTxt] = useState('En savoir plus')
  const [keywords, setKeywords] = useState([])
  const [kwSeed, setKwSeed] = useState('')
  const [kwSug, setKwSug] = useState([])
  const [estimate, setEstimate] = useState(null)
  const [busy, setBusy] = useState(false)

  const typeDef = config.types.find((t) => t.id === type)
  useEffect(() => { setBidStrategy(typeDef?.defaultBid || 'cpc') }, [type])

  const dailyCents = () => Math.round((budgetType === 'daily' ? +dailyBudget : +totalBudget / 30) * 100)
  const totalCents = () => Math.round((budgetType === 'daily' ? +dailyBudget * 30 : +totalBudget) * 100)

  const runEstimate = useCallback(async () => {
    const r = await api('/ads/estimate', { method: 'POST', body: JSON.stringify({ dailyBudgetCents: dailyCents(), bidStrategy, maxBidCents: Math.round(+maxBid * 100), targeting: { interests, ageRange } }) })
    if (!r.error) setEstimate(r)
  }, [dailyBudget, totalBudget, budgetType, bidStrategy, maxBid, interests, ageRange])
  useEffect(() => { if (step === 1) runEstimate() }, [step, runEstimate])

  const suggestKw = async () => { const r = await api(`/ads/keywords?q=${encodeURIComponent(kwSeed || name)}`); if (Array.isArray(r)) setKwSug(r) }
  const toggle = (arr, set, v) => set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v])

  const launch = async () => {
    if (!name.trim()) { setStep(0); return showToast('Nomme ta campagne') }
    setBusy(true)
    const r = await api('/ads/campaigns', { method: 'POST', body: JSON.stringify({
      name: name.trim(), type, objective, budgetType, budgetCents: totalCents(), dailyBudgetCents: dailyCents(),
      bidStrategy, maxBidCents: Math.round(+maxBid * 100),
      targeting: { interests, ageRange, genders, devices, locations: [] },
      keywords: keywords.map((k) => ({ text: k, matchType: 'broad', bidCents: Math.round(+maxBid * 100) })),
      creative: { headline: headline || name, body: bodyTxt, cta: ctaTxt },
    }) })
    setBusy(false)
    if (r.error) return showToast('⚠️ ' + r.error)
    onDone()
  }

  return (
    <div className="min-h-[100dvh] bg-app-gradient"><div className="mx-auto max-w-2xl px-4 pt-6 pb-28">
      <div className="flex items-center gap-3 mb-5"><button onClick={() => step === 0 ? onCancel() : setStep(step - 1)} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button><h1 className="font-display text-2xl">Nouvelle campagne</h1></div>
      <div className="flex gap-1.5 mb-6">{['Objectif', 'Budget & ciblage', 'Création'].map((l, s) => <div key={s} className="flex-1"><div className={cx('h-1.5 rounded-full', s <= step ? 'bg-primary' : 'bg-muted/60')} /><div className={cx('text-[10px] mt-1', s === step ? 'text-primary font-medium' : 'text-muted-foreground')}>{l}</div></div>)}</div>

      {step === 0 && (
        <div className="cascade space-y-5">
          <div>
            <div className="font-semibold text-sm mb-2">Type de campagne</div>
            <div className="grid grid-cols-2 gap-2.5">{config.types.map((t) => <button key={t.id} onClick={() => setType(t.id)} className="press text-left"><Glass className={cx('p-3.5 h-full border-2', type === t.id ? 'border-primary' : 'border-transparent')}><div className="w-9 h-9 rounded-xl grid place-items-center text-white text-lg mb-2" style={{ background: t.color }}>{t.emoji}</div><div className="font-semibold text-sm">{t.name}</div><div className="text-[11px] text-muted-foreground leading-tight mt-0.5">{t.desc}</div></Glass></button>)}</div>
          </div>
          <div>
            <div className="font-semibold text-sm mb-2">Objectif</div>
            <div className="flex flex-wrap gap-2">{config.objectives.map((o) => <button key={o.id} onClick={() => setObjective(o.id)} className={cx('press px-3.5 py-2 rounded-full text-sm font-medium border', objective === o.id ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{o.emoji} {o.name}</button>)}</div>
          </div>
          <div>
            <div className="font-semibold text-sm mb-2">Nom de la campagne</div>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex. Soldes d'été — Paris" className="w-full rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary" />
          </div>
          <button onClick={() => setStep(1)} className="press w-full py-3.5 rounded-2xl font-semibold text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Continuer</button>
        </div>
      )}

      {step === 1 && (
        <div className="cascade space-y-5">
          <div>
            <div className="font-semibold text-sm mb-2">Budget</div>
            <div className="flex gap-2 mb-2">{[['daily', 'Quotidien'], ['total', 'Total']].map(([v, l]) => <button key={v} onClick={() => setBudgetType(v)} className={cx('press flex-1 py-2 rounded-xl text-sm font-medium border', budgetType === v ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{l}</button>)}</div>
            <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3.5 py-3"><WalletIcon size={16} className="text-gold" /><input type="number" value={budgetType === 'daily' ? dailyBudget : totalBudget} onChange={(e) => budgetType === 'daily' ? setDailyBudget(e.target.value) : setTotalBudget(e.target.value)} className="flex-1 bg-transparent text-sm outline-none tabular" /><span className="text-sm text-muted-foreground">€ {budgetType === 'daily' ? '/ jour' : 'total'}</span></div>
            <p className="text-[11px] text-muted-foreground mt-1">Débité de ton wallet : <b className="text-gold">{eur0(totalCents())} €</b></p>
          </div>
          <div>
            <div className="font-semibold text-sm mb-2">Enchère</div>
            <div className="flex flex-wrap gap-2 mb-2">{config.bidStrategies.map((b) => <button key={b.id} onClick={() => setBidStrategy(b.id)} className={cx('press px-3 py-1.5 rounded-full text-xs font-medium border', bidStrategy === b.id ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{b.name}</button>)}</div>
            {(bidStrategy === 'cpc' || bidStrategy === 'cpm') && <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3.5 py-2.5"><Gauge size={15} className="text-primary" /><span className="text-sm text-muted-foreground">Enchère max</span><input type="number" step="0.05" value={maxBid} onChange={(e) => setMaxBid(e.target.value)} className="flex-1 bg-transparent text-sm outline-none tabular text-right" /><span className="text-sm text-muted-foreground">€ / {bidStrategy === 'cpc' ? 'clic' : '1000 impr.'}</span></div>}
          </div>
          <div>
            <div className="font-semibold text-sm mb-2">Ciblage · centres d'intérêt</div>
            <div className="flex flex-wrap gap-2">{config.interests.map((i) => <button key={i} onClick={() => toggle(interests, setInterests, i)} className={cx('press px-3 py-1.5 rounded-full text-xs font-medium border', interests.includes(i) ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{i}</button>)}</div>
          </div>
          <div>
            <div className="font-semibold text-sm mb-2">Âge</div>
            <div className="flex flex-wrap gap-2">{config.ageRanges.map((a) => <button key={a} onClick={() => toggle(ageRange, setAgeRange, a)} className={cx('press px-3 py-1.5 rounded-full text-xs font-medium border', ageRange.includes(a) ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{a}</button>)}</div>
          </div>
          {estimate && (
            <Glass sheen className="p-4 !bg-primary/6">
              <div className="font-semibold text-sm mb-3 flex items-center gap-1.5"><Sparkles size={15} className="text-primary" /> Estimation quotidienne</div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div><div className="font-display tabular text-lg text-primary">{kf(estimate.impressionsPerDay[0])}–{kf(estimate.impressionsPerDay[1])}</div><div className="text-[10px] text-muted-foreground">Impressions</div></div>
                <div><div className="font-display tabular text-lg text-primary">{kf(estimate.clicksPerDay[0])}–{kf(estimate.clicksPerDay[1])}</div><div className="text-[10px] text-muted-foreground">Clics</div></div>
                <div><div className="font-display tabular text-lg text-gold">{kf(estimate.reachPerDay[0])}–{kf(estimate.reachPerDay[1])}</div><div className="text-[10px] text-muted-foreground">Portée</div></div>
              </div>
              <div className="text-[11px] text-muted-foreground text-center mt-3">Audience potentielle : <b>{kf(estimate.audience)}</b> · CTR estimé {estimate.estCtr}%</div>
            </Glass>
          )}
          <button onClick={() => setStep(2)} className="press w-full py-3.5 rounded-2xl font-semibold text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Continuer</button>
        </div>
      )}

      {step === 2 && (
        <div className="cascade space-y-5">
          <div>
            <div className="font-semibold text-sm mb-2">Annonce</div>
            <input value={headline} onChange={(e) => setHeadline(e.target.value)} placeholder="Titre accrocheur (max 30)" maxLength={40} className="w-full mb-2 rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary" />
            <textarea value={bodyTxt} onChange={(e) => setBodyTxt(e.target.value)} placeholder="Description de ton offre…" rows={3} className="w-full mb-2 rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary resize-none" />
            <div className="flex flex-wrap gap-2">{['En savoir plus', 'Acheter', 'S\u2019inscrire', 'Télécharger', 'Contacter'].map((c) => <button key={c} onClick={() => setCtaTxt(c)} className={cx('press px-3 py-1.5 rounded-full text-xs font-medium border', ctaTxt === c ? 'bg-gold/15 border-gold/40 text-gold' : 'bg-card/60 border-border text-muted-foreground')}>{c}</button>)}</div>
          </div>

          {/* aperçu */}
          <div>
            <div className="font-semibold text-sm mb-2">Aperçu</div>
            <Glass className="p-3.5"><div className="flex items-center gap-2 mb-2"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-muted/70 text-muted-foreground">Annonce</span><span className="text-xs font-medium">{me?.name || 'Ton entreprise'}</span></div><div className="font-semibold text-primary text-[15px] leading-tight">{headline || name || 'Titre de ton annonce'}</div><div className="text-sm text-muted-foreground mt-1">{bodyTxt || 'La description de ton offre apparaîtra ici.'}</div><span className="inline-block mt-2.5 px-3 py-1.5 rounded-full text-xs font-semibold text-white" style={{ background: typeDef?.color || '#4353F0' }}>{ctaTxt}</span></Glass>
          </div>

          {type === 'search' && (
            <div>
              <div className="font-semibold text-sm mb-2">Mots-clés</div>
              <div className="flex gap-2 mb-2"><div className="flex-1 flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5"><Search size={15} className="text-muted-foreground" /><input value={kwSeed} onChange={(e) => setKwSeed(e.target.value)} placeholder="Thème (ex. chaussures)" className="flex-1 bg-transparent text-sm outline-none" /></div><button onClick={suggestKw} className="press px-3 rounded-2xl bg-primary/10 text-primary text-sm font-semibold flex items-center gap-1"><Sparkles size={14} /> Suggérer</button></div>
              {keywords.length > 0 && <div className="flex flex-wrap gap-2 mb-2">{keywords.map((k) => <span key={k} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary text-white text-xs">{k}<button onClick={() => setKeywords((x) => x.filter((y) => y !== k))}><X size={12} /></button></span>)}</div>}
              {kwSug.length > 0 && <Glass className="divide-y divide-border max-h-56 overflow-y-auto">{kwSug.filter((s) => !keywords.includes(s.text)).map((s) => <button key={s.text} onClick={() => setKeywords((k) => [...k, s.text])} className="press w-full text-left px-3.5 py-2.5 flex items-center gap-2"><Plus size={14} className="text-primary shrink-0" /><span className="flex-1 text-sm truncate">{s.text}</span><span className="text-[10px] text-muted-foreground">{kf(s.volume)}/mois · {s.competition}</span></button>)}</Glass>}
            </div>
          )}

          <button onClick={launch} disabled={busy} className="press w-full py-3.5 rounded-2xl font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>{busy ? <Loader2 className="animate-spin" size={18} /> : <><Zap size={18} /> Lancer · {eur0(totalCents())} €</>}</button>
        </div>
      )}
    </div></div>
  )
}

/* ============================ DÉTAIL CAMPAGNE ============================ */
function CampaignDetail({ id, config, onBack, onWalletRefresh, showToast }) {
  const [c, setC] = useState(null)
  const [metric, setMetric] = useState('impressions')
  const load = useCallback(async () => { const r = await api(`/ads/campaigns/${id}`); if (!r.error) setC(r) }, [id])
  useEffect(() => { load() }, [load])

  const setStatus = async (status) => { const r = await api(`/ads/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); if (r.error) return showToast('⚠️ ' + r.error); if (status === 'ended') onWalletRefresh?.(); setC(r); showToast(status === 'active' ? 'Reprise' : status === 'paused' ? 'Mise en pause' : 'Terminée · budget remboursé') }
  const remove = async () => { await api(`/ads/campaigns/${id}`, { method: 'DELETE' }); onWalletRefresh?.(); onBack() }
  const simulate = async (type) => { await api(`/ads/campaigns/${id}/track`, { method: 'POST', body: JSON.stringify({ type }) }); load() }

  if (!c) return <div className="min-h-[60dvh] grid place-items-center"><Loader2 className="animate-spin text-primary" /></div>
  const typeDef = config?.types?.find((t) => t.id === c.type)
  const metrics = [['impressions', 'Impressions'], ['clicks', 'Clics'], ['spentCents', 'Dépense'], ['conversions', 'Conv.']]

  return (
    <div className="min-h-[100dvh] bg-app-gradient"><div className="mx-auto max-w-2xl px-4 pt-6 pb-28">
      <div className="flex items-center gap-3 mb-4"><button onClick={onBack} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button><div className="flex-1"><h1 className="font-display text-xl leading-none truncate">{c.name}</h1><div className="text-xs text-muted-foreground mt-1">{typeDef?.name} · {c.objective}</div></div>
        <div className="w-10 h-10 rounded-2xl grid place-items-center text-white text-lg" style={{ background: typeDef?.color || '#4353F0' }}>{typeDef?.emoji || '📣'}</div></div>

      {/* contrôles */}
      <div className="flex gap-2 mb-5">
        {c.status === 'active' && <button onClick={() => setStatus('paused')} className="press flex-1 py-2.5 rounded-2xl border border-gold/40 bg-gold/12 text-gold font-medium text-sm flex items-center justify-center gap-1.5"><Pause size={15} /> Pause</button>}
        {c.status === 'paused' && <button onClick={() => setStatus('active')} className="press flex-1 py-2.5 rounded-2xl border border-green-500/40 bg-green-500/12 text-green-600 dark:text-green-400 font-medium text-sm flex items-center justify-center gap-1.5"><Play size={15} /> Reprendre</button>}
        {c.status !== 'ended' && <button onClick={() => setStatus('ended')} className="press flex-1 py-2.5 rounded-2xl border border-border bg-card/70 font-medium text-sm">Terminer</button>}
        <button onClick={remove} className="press px-4 py-2.5 rounded-2xl border border-destructive/30 bg-destructive/10 text-destructive flex items-center justify-center"><Trash2 size={16} /></button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mb-5">
        <Kpi icon={Eye} label="Impressions" value={kf(c.impressions)} color="#4353F0" />
        <Kpi icon={MousePointerClick} label="Clics" value={kf(c.clicks)} sub={`CTR ${c.ctr}%`} color="#9B5DE5" />
        <Kpi icon={Target} label="Conversions" value={kf(c.conversions)} sub={`${c.convRate}%`} color="#3FB68B" />
        <Kpi icon={DollarSign} label="CPC moyen" value={`${eur(c.cpcCents)} €`} sub={`CPM ${eur(c.cpmCents)}€`} gold />
      </div>

      {/* budget */}
      <Glass className="p-4 mb-5"><div className="flex justify-between text-sm mb-2"><span className="font-medium">Budget consommé</span><span className="tabular"><b className="text-gold">{eur(c.spentCents)} €</b> / {eur(c.budgetCents)} €</span></div><div className="h-2.5 rounded-full bg-muted/60 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${c.budgetCents ? Math.min(100, c.spentCents / c.budgetCents * 100) : 0}%`, background: 'linear-gradient(90deg,#E2AA2B,#F0CE7E)' }} /></div><div className="text-[11px] text-muted-foreground mt-1.5">Reste {eur(c.remainingCents)} € · {c.bidStrategy?.toUpperCase()} · enchère max {eur(c.maxBidCents)} €</div></Glass>

      {/* graphe */}
      {c.daily?.length > 0 && (
        <Glass className="p-4 mb-5">
          <div className="flex items-center gap-2 mb-3 overflow-x-auto no-scrollbar">{metrics.map(([m, l]) => <button key={m} onClick={() => setMetric(m)} className={cx('press whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium border', metric === m ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{l}</button>)}</div>
          <BarChart data={c.daily} field={metric} />
        </Glass>
      )}

      {/* ciblage */}
      <Glass className="p-4 mb-5"><div className="font-semibold text-sm mb-3 flex items-center gap-1.5"><Users size={15} className="text-primary" /> Ciblage</div>
        {c.targeting?.interests?.length > 0 && <div className="mb-2"><div className="text-xs text-muted-foreground mb-1">Centres d'intérêt</div><div className="flex flex-wrap gap-1.5">{c.targeting.interests.map((i) => <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">{i}</span>)}</div></div>}
        {c.targeting?.ageRange?.length > 0 && <div className="mb-2"><div className="text-xs text-muted-foreground mb-1">Âge</div><div className="flex flex-wrap gap-1.5">{c.targeting.ageRange.map((a) => <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-muted/60">{a}</span>)}</div></div>}
        <div className="text-xs text-muted-foreground">Appareils : {(c.targeting?.devices || []).join(', ') || 'Tous'}</div>
      </Glass>

      {c.keywords?.length > 0 && <Glass className="p-4 mb-5"><div className="font-semibold text-sm mb-2">Mots-clés ({c.keywords.length})</div><div className="flex flex-wrap gap-1.5">{c.keywords.map((k, i) => <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-card/70 border border-border">{k.text}</span>)}</div></Glass>}

      {/* simulateur (démo) */}
      {c.status === 'active' && (
        <Glass className="p-4"><div className="font-semibold text-sm mb-2 flex items-center gap-1.5"><Zap size={15} className="text-gold" /> Simuler du trafic (démo)</div><div className="flex gap-2"><button onClick={() => simulate('impression')} className="press flex-1 py-2 rounded-xl border border-border bg-card/70 text-sm">+ Impression</button><button onClick={() => simulate('click')} className="press flex-1 py-2 rounded-xl border border-border bg-card/70 text-sm">+ Clic</button><button onClick={() => simulate('conversion')} className="press flex-1 py-2 rounded-xl border border-border bg-card/70 text-sm">+ Conversion</button></div></Glass>
      )}
    </div></div>
  )
}
