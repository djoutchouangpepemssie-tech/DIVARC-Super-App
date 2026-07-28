'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import {
  Search, Plus, X, Heart, BadgeCheck, MapPin, ShoppingBag, Check, ArrowUpDown, Tag, Store, RefreshCw, ChevronRight
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const eur = (c) => (c / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const Glass = ({ className, sheen, children, ...p }) => <div className={cx('glass', sheen && 'glass-sheen', className)} {...p}>{children}</div>
const Avatar = ({ c, size = 32 }) => (
  <div className="grid place-items-center rounded-full text-white font-semibold shrink-0"
    style={{ width: size, height: size, background: c?.avatarColor || '#4353F0', fontSize: size * 0.38 }}>{c?.initials}</div>
)
const CATS = ['Tout', 'Mode', 'Chaussures', 'Maison', 'Tech', 'Vélo', 'Jardin', 'Autre']
const EMOJIS = ['📦', '👕', '👟', '🪑', '📱', '🚲', '🪴', '🎮', '📚', '⌚', '🎸', '🧸']

const Card = ({ children, className }) => (
  <div className={cx('rounded-[22px] overflow-hidden', className)}>{children}</div>
)

export default function Marketplace({ me, onWalletRefresh }) {
  const [tab, setTab] = useState('explore') // explore | mine
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('Tout')
  const [sort, setSort] = useState('recent')
  const [detail, setDetail] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [mine, setMine] = useState({ selling: [], purchases: [] })
  const [toast, setToast] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    const r = await api(`/market/listings?q=${encodeURIComponent(q)}&cat=${encodeURIComponent(cat)}&sort=${sort}`)
    if (Array.isArray(r)) setItems(r)
    setLoading(false)
  }, [q, cat, sort])
  const loadMine = useCallback(async () => { const r = await api('/market/mine'); if (!r.error) setMine(r) }, [])
  useEffect(() => { load() }, [load])
  useEffect(() => { if (tab === 'mine') loadMine() }, [tab, loadMine])

  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2400) }

  const toggleFav = async (l) => {
    setItems((it) => it.map((x) => x.id === l.id ? { ...x, favorited: !x.favorited } : x))
    if (detail?.id === l.id) setDetail((d) => ({ ...d, favorited: !d.favorited }))
    await api(`/market/listings/${l.id}/favorite`, { method: 'POST' })
  }
  const buy = async (l) => {
    const r = await api(`/market/listings/${l.id}/buy`, { method: 'POST' })
    if (r.error) return showToast('⚠️ ' + r.error)
    setDetail(null); showToast(`Acheté ✓ ${l.title} · ${eur(l.priceCents)} €`)
    load(); onWalletRefresh && onWalletRefresh()
  }

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-5xl px-4 pt-6 pb-28">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-display text-3xl">Marketplace</h1>
          <button onClick={() => setCreateOpen(true)} className="press inline-flex items-center gap-2 rounded-full px-4 py-2.5 font-semibold text-white shadow-lg" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
            <Plus size={18} /> Vendre
          </button>
        </div>

        <div className="flex gap-2 p-1 rounded-2xl bg-muted/60 mb-4 max-w-xs">
          {[['explore', 'Explorer', Store], ['mine', 'Mes annonces', Tag]].map(([id, label, Icon]) => (
            <button key={id} onClick={() => setTab(id)} className={cx('press flex-1 py-2 rounded-xl text-sm font-medium flex items-center justify-center gap-1.5', tab === id ? 'bg-card shadow' : 'text-muted-foreground')}><Icon size={15} />{label}</button>
          ))}
        </div>

        {tab === 'explore' ? (
          <>
            <div className="flex gap-2 mb-3">
              <div className="flex-1 flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5">
                <Search size={16} className="text-muted-foreground" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher un article…" className="flex-1 bg-transparent text-sm outline-none" />
              </div>
              <button onClick={() => setSort((s) => s === 'recent' ? 'price_asc' : s === 'price_asc' ? 'price_desc' : 'recent')}
                className="press rounded-2xl border border-border bg-card/60 px-3 grid place-items-center" title="Trier">
                <ArrowUpDown size={16} />
              </button>
            </div>
            <div className="flex gap-2 overflow-x-auto no-scrollbar mb-4">
              {CATS.map((c) => (
                <button key={c} onClick={() => setCat(c)} className={cx('press whitespace-nowrap px-3.5 py-1.5 rounded-full text-sm font-medium border', cat === c ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{c}</button>
              ))}
            </div>
            <div className="text-xs text-muted-foreground mb-3">{sort === 'recent' ? 'Plus récents' : sort === 'price_asc' ? 'Prix croissant' : 'Prix décroissant'}</div>

            {loading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Array.from({ length: 6 }).map((_, i) => <Glass key={i} className="aspect-[3/4] animate-pulse" />)}
              </div>
            ) : items.length === 0 ? (
              <Glass className="p-10 text-center text-muted-foreground">Aucune annonce. Sois le premier à vendre !</Glass>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 cascade">
                {items.map((l) => <ListingCard key={l.id} l={l} onOpen={() => setDetail(l)} onFav={() => toggleFav(l)} />)}
              </div>
            )}
          </>
        ) : (
          <MineView mine={mine} onOpen={(l) => setDetail(l)} />
        )}
      </div>

      <AnimatePresence>
        {detail && <DetailSheet l={detail} me={me} onClose={() => setDetail(null)} onFav={() => toggleFav(detail)} onBuy={() => buy(detail)} />}
        {createOpen && <CreateSheet onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); setTab('explore'); load(); showToast('Annonce publiée ✓') }} />}
        {toast && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="fixed bottom-28 left-1/2 -translate-x-1/2 z-[60] bg-ink text-white text-sm font-medium px-4 py-2.5 rounded-full shadow-xl">{toast}</motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ListingCard({ l, onOpen, onFav }) {
  return (
    <div className="press">
      <Card className="glass">
        <button onClick={onOpen} className="block w-full text-left">
          <div className="aspect-square relative overflow-hidden bg-muted">
            {l.images?.length ? (
              <img src={l.images[0]} alt={l.title} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full grid place-items-center text-5xl" style={{ background: `${l.color || '#4353F0'}22` }}>{l.emoji || '📦'}</div>
            )}
            {l.type === 'ad' && <span className="absolute top-2 left-2 text-[10px] bg-ink/70 text-white px-2 py-0.5 rounded-full">Annonce</span>}
          </div>
        </button>
        <button onClick={onFav} aria-label="Favori" className="absolute top-2 right-2 w-8 h-8 rounded-full grid place-items-center bg-white/80 backdrop-blur">
          <Heart size={16} fill={l.favorited ? '#F15BB5' : 'none'} color={l.favorited ? '#F15BB5' : '#14162B'} />
        </button>
        <div className="p-3">
          <div className="font-display text-lg">{eur(l.priceCents)} <span className="text-gold text-sm">€</span></div>
          <div className="text-sm font-medium truncate">{l.title}</div>
          <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5"><MapPin size={11} /> {l.location} · {l.condition}</div>
        </div>
      </Card>
    </div>
  )
}

function DetailSheet({ l, me, onClose, onFav, onBuy }) {
  const own = l.seller?.id === me?.id
  return (
    <Sheet onClose={onClose}>
      <div className="aspect-square rounded-2xl overflow-hidden bg-muted mb-4">
        {l.images?.length ? <img src={l.images[0]} alt={l.title} className="w-full h-full object-cover" />
          : <div className="w-full h-full grid place-items-center text-7xl" style={{ background: `${l.color || '#4353F0'}22` }}>{l.emoji || '📦'}</div>}
      </div>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-display text-3xl">{eur(l.priceCents)} <span className="text-gold text-xl">€</span></div>
          <div className="font-semibold">{l.title}</div>
          <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1"><MapPin size={12} /> {l.location} · {l.condition} · {l.category}</div>
        </div>
        <button onClick={onFav} className="press w-11 h-11 rounded-full grid place-items-center border border-border bg-card/60">
          <Heart size={20} fill={l.favorited ? '#F15BB5' : 'none'} color={l.favorited ? '#F15BB5' : 'currentColor'} />
        </button>
      </div>
      <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{l.description}</p>
      {l.seller && (
        <div className="flex items-center gap-2.5 mt-4 p-3 rounded-2xl bg-card/60 border border-border">
          <Avatar c={l.seller} size={40} />
          <div className="flex-1"><div className="text-sm font-medium flex items-center gap-1">{l.seller.name} {l.seller.verified && <BadgeCheck size={13} className="text-primary" />}</div><div className="text-xs text-muted-foreground">{l.seller.handle}</div></div>
        </div>
      )}
      <div className="mt-5">
        {own ? (
          <div className="text-center text-sm text-muted-foreground py-2">C'est ton annonce.</div>
        ) : (
          <button onClick={onBuy} className="press w-full rounded-2xl py-3.5 font-semibold text-white flex items-center justify-center gap-2" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
            <ShoppingBag size={18} /> Acheter · {eur(l.priceCents)} € · payé au wallet
          </button>
        )}
        <div className="text-center text-[11px] text-muted-foreground mt-2">Paiement protégé · SEPA Instant ⚡</div>
      </div>
    </Sheet>
  )
}

function MineView({ mine, onOpen }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-[15px] mb-2">Mes ventes</h2>
        {mine.selling.length === 0 ? <Glass className="p-6 text-center text-sm text-muted-foreground">Tu n'as pas encore d'annonce.</Glass> : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {mine.selling.map((l) => (
              <button key={l.id} onClick={() => onOpen(l)} className="press text-left">
                <Glass>
                  <div className="aspect-square overflow-hidden bg-muted relative">
                    {l.images?.length ? <img src={l.images[0]} className="w-full h-full object-cover" /> : <div className="w-full h-full grid place-items-center text-4xl">{l.emoji || '📦'}</div>}
                    {l.status === 'sold' && <span className="absolute inset-0 bg-ink/50 grid place-items-center text-white font-semibold">Vendu ✓</span>}
                  </div>
                  <div className="p-2.5"><div className="font-display">{eur(l.priceCents)} €</div><div className="text-xs truncate">{l.title}</div></div>
                </Glass>
              </button>
            ))}
          </div>
        )}
      </div>
      <div>
        <h2 className="font-semibold text-[15px] mb-2">Mes achats</h2>
        {mine.purchases.length === 0 ? <Glass className="p-6 text-center text-sm text-muted-foreground">Aucun achat pour l'instant.</Glass> : (
          <Glass className="divide-y divide-border/60">
            {mine.purchases.map((o) => (
              <div key={o.id} className="flex items-center justify-between p-3.5">
                <div><div className="text-sm font-medium">{o.title}</div><div className="text-xs text-muted-foreground">Commande confirmée</div></div>
                <div className="font-display">{eur(o.priceCents)} €</div>
              </div>
            ))}
          </Glass>
        )}
      </div>
    </div>
  )
}

function CreateSheet({ onClose, onCreated }) {
  const [title, setTitle] = useState('')
  const [price, setPrice] = useState('')
  const [desc, setDesc] = useState('')
  const [category, setCategory] = useState('Mode')
  const [condition, setCondition] = useState('Bon état')
  const [type, setType] = useState('item')
  const [emoji, setEmoji] = useState('📦')
  const [location, setLocation] = useState('Paris')
  const [busy, setBusy] = useState(false)

  const publish = async () => {
    if (!title || !price) return
    setBusy(true)
    const r = await api('/market/listings', { method: 'POST', body: JSON.stringify({
      title, description: desc, priceCents: Math.round(Number(price) * 100), category, condition, type, emoji, location,
    }) })
    setBusy(false)
    if (!r.error) onCreated()
  }
  return (
    <Sheet onClose={onClose} title="Vendre un article">
      <div className="flex gap-2 overflow-x-auto no-scrollbar mb-3">
        {EMOJIS.map((e) => (
          <button key={e} onClick={() => setEmoji(e)} className={cx('press shrink-0 w-12 h-12 rounded-2xl grid place-items-center text-2xl border-2', emoji === e ? 'border-primary bg-primary/10' : 'border-border bg-card/60')}>{e}</button>
        ))}
      </div>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre de l'annonce" className="w-full rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm mb-3" />
      <div className="flex gap-2 mb-3">
        <input value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9.]/g, ''))} placeholder="Prix (€)" className="flex-1 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
        <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Ville" className="flex-1 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
      </div>
      <textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={2} placeholder="Description…" className="w-full rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm mb-3" />
      <div className="grid grid-cols-2 gap-2 mb-3">
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-2xl border border-border bg-card/60 px-3 py-3 text-sm">
          {CATS.filter((c) => c !== 'Tout').map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={condition} onChange={(e) => setCondition(e.target.value)} className="rounded-2xl border border-border bg-card/60 px-3 py-3 text-sm">
          {['Neuf', 'Très bon état', 'Bon état', 'Correct'].map((c) => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div className="flex gap-2 p-1 rounded-2xl bg-muted/60 mb-4">
        {[['item', 'Article à vendre'], ['ad', 'Annonce']].map(([id, label]) => (
          <button key={id} onClick={() => setType(id)} className={cx('press flex-1 py-2 rounded-xl text-sm font-medium', type === id ? 'bg-card shadow' : 'text-muted-foreground')}>{label}</button>
        ))}
      </div>
      <button onClick={publish} disabled={busy || !title || !price} className="press w-full rounded-2xl py-3.5 font-semibold text-white disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
        {busy ? 'Publication…' : 'Publier l\u2019annonce'}
      </button>
    </Sheet>
  )
}

function Sheet({ children, onClose, title }) {
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass className="glass-strong p-5 rounded-b-none sm:rounded-b-[var(--radius)] max-h-[92dvh] overflow-y-auto no-scrollbar">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-2xl">{title || 'Détail'}</h3>
            <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button>
          </div>
          {children}
        </Glass>
      </motion.div>
    </motion.div>
  )
}
