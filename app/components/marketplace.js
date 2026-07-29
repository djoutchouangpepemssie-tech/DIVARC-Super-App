'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import {
  Search, X, Heart, MapPin, SlidersHorizontal, Plus, ChevronRight, ChevronLeft, Camera,
  MessageCircle, Store, Compass, Check, Crosshair, Loader2, Send, Tag, Trash2, ShieldCheck,
  ArrowLeft, Eye, Sparkles, Home, Car, Building2, HandCoins,
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const Glass = ({ className, sheen, strong, children, ...p }) => <div className={cx('glass', sheen && 'glass-sheen', strong && 'glass-strong', className)} {...p}>{children}</div>
const euro = (cents) => Math.round((cents || 0) / 100).toLocaleString('fr-FR')
const priceLabel = (l) => `${euro(l.priceCents)} €${l.transactionType === 'rent' ? '/mois' : ''}`
const imgSrc = (u) => u ? (u.startsWith('/api') ? u : u) : null

/* ---------- resize + upload d'image ---------- */
function fileToResizedDataUrl(file, max = 1280, quality = 0.82) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        let { width, height } = img
        if (width > height && width > max) { height = Math.round(height * max / width); width = max }
        else if (height >= width && height > max) { width = Math.round(width * max / height); height = max }
        const canvas = document.createElement('canvas')
        canvas.width = width; canvas.height = height
        canvas.getContext('2d').drawImage(img, 0, 0, width, height)
        resolve(canvas.toDataURL('image/jpeg', quality))
      }
      img.onerror = reject
      img.src = e.target.result
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function Marketplace({ me, onWalletRefresh, onImmersive }) {
  const [view, setView] = useState('browse') // browse | detail | sell | threads | thread
  const [cats, setCats] = useState([])
  const [conditions, setConditions] = useState([])
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const [activeThread, setActiveThread] = useState(null)
  const [toast, setToast] = useState(null)

  // filtres
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('Tout')
  const [subcat, setSubcat] = useState('')
  const [txType, setTxType] = useState('')
  const [cond, setCond] = useState('')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [sort, setSort] = useState('recent')
  const [showFilters, setShowFilters] = useState(false)
  const [geo, setGeo] = useState(null) // {city, lat, lon}
  const [radius, setRadius] = useState(0)
  const [showLoc, setShowLoc] = useState(false)

  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2600) }

  useEffect(() => { onImmersive?.(view !== 'browse') }, [view, onImmersive])

  useEffect(() => {
    try { const g = JSON.parse(localStorage.getItem('divarc_geo') || 'null'); if (g) { setGeo(g); setRadius(g.radius || 0) } } catch (e) {}
    api('/market/categories').then((r) => { if (r.categories) { setCats(r.categories); setConditions(r.conditions || []) } })
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    const p = new URLSearchParams()
    if (q) p.set('q', q)
    if (cat && cat !== 'Tout') p.set('cat', cat)
    if (subcat) p.set('subcat', subcat)
    if (txType) p.set('type', txType)
    if (cond) p.set('condition', cond)
    if (minPrice) p.set('minPrice', String(Math.round(+minPrice * 100)))
    if (maxPrice) p.set('maxPrice', String(Math.round(+maxPrice * 100)))
    p.set('sort', sort)
    if (geo?.lat != null) { p.set('lat', geo.lat); p.set('lon', geo.lon); if (radius) p.set('radiusKm', String(radius)) }
    const r = await api(`/market/listings?${p.toString()}`)
    if (Array.isArray(r)) setListings(r)
    setLoading(false)
  }, [q, cat, subcat, txType, cond, minPrice, maxPrice, sort, geo, radius])
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t) }, [load])

  const catDef = cats.find((c) => c.id === cat)

  const openDetail = async (id) => {
    const r = await api(`/market/listings/${id}`)
    if (r.error) return showToast('⚠️ ' + r.error)
    setDetail(r); setView('detail')
  }
  const toggleFav = async (id) => {
    const r = await api(`/market/listings/${id}/favorite`, { method: 'POST' })
    if (!r.error) { setListings((ls) => ls.map((l) => l.id === id ? { ...l, favorited: r.favorited, favorites: r.favorites } : l)); setDetail((d) => d && d.id === id ? { ...d, favorited: r.favorited, favorites: r.favorites } : d) }
  }
  const openChat = async (listing, text) => {
    const r = await api(`/market/listings/${listing.id}/chat`, { method: 'POST', body: JSON.stringify({ text }) })
    if (r.error) return showToast('⚠️ ' + r.error)
    setActiveThread(r.thread.id); setView('thread')
  }
  const applyGeo = (g) => { const ng = { ...g, radius }; setGeo(g); try { localStorage.setItem('divarc_geo', JSON.stringify(ng)) } catch (e) {}; setShowLoc(false) }
  const clearGeo = () => { setGeo(null); setRadius(0); try { localStorage.removeItem('divarc_geo') } catch (e) {}; setShowLoc(false) }

  const activeFilters = [subcat, txType, cond, minPrice, maxPrice].filter(Boolean).length + (radius ? 1 : 0)

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      {view === 'browse' && (
        <div className="mx-auto max-w-5xl px-4 pt-6 pb-28">
          <div className="flex items-center justify-between mb-3">
            <h1 className="font-display text-3xl">Marketplace</h1>
            <div className="flex gap-2">
              <button onClick={() => setView('threads')} className="press w-10 h-10 rounded-full grid place-items-center bg-card/60 border border-border relative"><MessageCircle size={18} /></button>
              <button onClick={() => setView('sell')} className="press h-10 px-4 rounded-full grid place-items-center text-white font-semibold text-sm gap-1.5 flex" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Plus size={17} /> Vendre</button>
            </div>
          </div>

          {/* recherche + localisation */}
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5 mb-2">
            <Search size={16} className="text-muted-foreground" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Que recherches-tu ?" className="flex-1 bg-transparent text-sm outline-none" />
            {q && <button onClick={() => setQ('')}><X size={15} className="text-muted-foreground" /></button>}
          </div>
          <div className="flex gap-2 mb-3">
            <button onClick={() => setShowLoc(true)} className="press flex-1 flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5 text-sm">
              <MapPin size={16} className="text-primary" />
              <span className="truncate flex-1 text-left">{geo?.city ? `${geo.city}${radius ? ` · ${radius} km` : ''}` : 'Toute l\u2019Europe'}</span>
            </button>
            <button onClick={() => setShowFilters(true)} className="press flex items-center gap-1.5 rounded-2xl border border-border bg-card/60 px-3.5 py-2.5 text-sm font-medium relative">
              <SlidersHorizontal size={16} /> Filtres
              {activeFilters > 0 && <span className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-primary text-white text-[10px] grid place-items-center font-bold">{activeFilters}</span>}
            </button>
          </div>

          {/* catégories */}
          <div className="flex gap-2 overflow-x-auto no-scrollbar mb-4 pb-1">
            <button onClick={() => { setCat('Tout'); setSubcat(''); setTxType('') }} className={cx('press whitespace-nowrap px-3.5 py-1.5 rounded-full text-sm font-medium border', cat === 'Tout' ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>Tout</button>
            {cats.map((c) => <button key={c.id} onClick={() => { setCat(c.id); setSubcat(''); setTxType('') }} className={cx('press whitespace-nowrap px-3.5 py-1.5 rounded-full text-sm font-medium border flex items-center gap-1.5', cat === c.id ? 'text-white border-transparent' : 'bg-card/60 border-border text-muted-foreground')} style={cat === c.id ? { background: c.color } : {}}>{c.emoji} {c.name}</button>)}
          </div>

          {/* sous-catégories + type sale/rent */}
          {catDef && (
            <div className="flex gap-2 overflow-x-auto no-scrollbar mb-4">
              {catDef.types?.length > 1 && catDef.types.map((t) => (
                <button key={t} onClick={() => setTxType(txType === t ? '' : t)} className={cx('press whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-semibold border', txType === t ? 'bg-gold/15 border-gold/40 text-gold' : 'bg-card/60 border-border text-muted-foreground')}>{t === 'sale' ? 'Vente' : t === 'rent' ? 'Location' : 'Service'}</button>
              ))}
              {catDef.subcats?.map((s) => <button key={s} onClick={() => setSubcat(subcat === s ? '' : s)} className={cx('press whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium border', subcat === s ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{s}</button>)}
            </div>
          )}

          {/* résultats */}
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">{[...Array(6)].map((_, i) => <div key={i} className="glass rounded-2xl overflow-hidden animate-pulse"><div className="aspect-[4/3] bg-muted/60" /><div className="p-2.5 space-y-2"><div className="h-3 bg-muted/60 rounded w-3/4" /><div className="h-4 bg-muted/60 rounded w-1/2" /></div></div>)}</div>
          ) : listings.length === 0 ? (
            <Glass className="p-12 text-center"><Store size={34} className="mx-auto mb-3 text-muted-foreground" /><div className="font-semibold mb-1">Aucune annonce</div><div className="text-sm text-muted-foreground">Élargis ta zone ou modifie tes filtres.</div></Glass>
          ) : (
            <>
              <div className="text-xs text-muted-foreground mb-2">{listings.length} annonce{listings.length > 1 ? 's' : ''}</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {listings.map((l) => <ListingCard key={l.id} l={l} onOpen={() => openDetail(l.id)} onFav={() => toggleFav(l.id)} />)}
              </div>
            </>
          )}
        </div>
      )}

      {view === 'detail' && detail && <DetailView l={detail} me={me} onBack={() => { setView('browse'); load() }} onFav={() => toggleFav(detail.id)} onOpenListing={openDetail} onChat={openChat} onBought={() => { onWalletRefresh?.(); showToast('Achat effectué ✅'); setView('browse'); load() }} showToast={showToast} />}

      {view === 'sell' && <SellView cats={cats} conditions={conditions} onCancel={() => setView('browse')} onPublished={() => { showToast('Annonce publiée 🎉'); setView('browse'); load() }} showToast={showToast} />}

      {view === 'threads' && <ThreadsView onBack={() => setView('browse')} onOpen={(id) => { setActiveThread(id); setView('thread') }} />}

      {view === 'thread' && activeThread && <ThreadView me={me} threadId={activeThread} onBack={() => setView('threads')} onBought={() => { onWalletRefresh?.(); showToast('Achat effectué ✅') }} showToast={showToast} />}

      <AnimatePresence>
        {showLoc && <LocationSheet current={geo} radius={radius} setRadius={setRadius} onApply={applyGeo} onClear={clearGeo} onClose={() => setShowLoc(false)} showToast={showToast} />}
        {showFilters && <FiltersSheet {...{ conditions, cond, setCond, minPrice, setMinPrice, maxPrice, setMaxPrice, sort, setSort, geo }} onClose={() => setShowFilters(false)} onReset={() => { setCond(''); setMinPrice(''); setMaxPrice(''); setSort('recent') }} />}
        {toast && <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="fixed bottom-28 left-1/2 -translate-x-1/2 z-[70] bg-ink text-white text-sm font-medium px-4 py-2.5 rounded-full shadow-xl max-w-[92vw] text-center">{toast}</motion.div>}
      </AnimatePresence>
    </div>
  )
}

/* ============================ CARTE ANNONCE ============================ */
function ListingCard({ l, onOpen, onFav }) {
  return (
    <div className="press cursor-pointer" onClick={onOpen}>
      <Glass className="rounded-2xl overflow-hidden">
        <div className="relative aspect-[4/3] bg-muted/60">
          {l.images?.[0] ? <img src={imgSrc(l.images[0])} alt={l.title} className="w-full h-full object-cover" loading="lazy" /> : <div className="w-full h-full grid place-items-center text-3xl">📦</div>}
          <button onClick={(e) => { e.stopPropagation(); onFav() }} className="absolute top-2 right-2 w-8 h-8 rounded-full grid place-items-center bg-white/85 backdrop-blur shadow"><Heart size={16} className={l.favorited ? 'text-destructive' : 'text-ink'} fill={l.favorited ? '#EF476F' : 'none'} /></button>
          {l.transactionType === 'rent' && <span className="absolute top-2 left-2 text-[10px] font-bold px-2 py-0.5 rounded-full bg-gold text-white">LOCATION</span>}
          {l.distanceKm != null && <span className="absolute bottom-2 left-2 text-[10px] font-medium px-2 py-0.5 rounded-full bg-ink/70 text-white flex items-center gap-1"><MapPin size={9} /> {l.distanceKm} km</span>}
        </div>
        <div className="p-2.5">
          <div className="font-display tabular text-gold text-[15px] leading-none mb-1">{priceLabel(l)}</div>
          <div className="text-sm font-medium truncate">{l.title}</div>
          <div className="text-[11px] text-muted-foreground truncate">{l.city || 'France'} · {l.condition}</div>
        </div>
      </Glass>
    </div>
  )
}

/* ============================ DÉTAIL ============================ */
function DetailView({ l, me, onBack, onFav, onOpenListing, onChat, onBought, showToast }) {
  const [idx, setIdx] = useState(0)
  const [msg, setMsg] = useState('')
  const cat = null
  const buy = async () => {
    const r = await api(`/market/listings/${l.id}/buy`, { method: 'POST' })
    if (r.error) return showToast('⚠️ ' + r.error)
    onBought()
  }
  const attrs = Object.entries(l.attributes || {}).filter(([, v]) => v !== '' && v != null && v !== false)
  return (
    <div className="mx-auto max-w-3xl pb-28">
      <div className="sticky top-0 z-20 flex items-center gap-3 px-4 py-3 bg-app-gradient/90 backdrop-blur">
        <button onClick={onBack} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button>
        <div className="flex-1 font-semibold truncate">{l.title}</div>
        <button onClick={onFav} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><Heart size={17} className={l.favorited ? 'text-destructive' : ''} fill={l.favorited ? '#EF476F' : 'none'} /></button>
      </div>

      {/* galerie */}
      <div className="relative aspect-[4/3] md:aspect-[16/9] bg-muted/60 md:rounded-2xl overflow-hidden mx-0 md:mx-4">
        {l.images?.length ? <img src={imgSrc(l.images[idx])} alt={l.title} className="w-full h-full object-cover" /> : <div className="w-full h-full grid place-items-center text-5xl">📦</div>}
        {l.images?.length > 1 && <>
          <button onClick={() => setIdx((i) => (i - 1 + l.images.length) % l.images.length)} className="absolute left-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/85 grid place-items-center shadow"><ChevronLeft size={18} /></button>
          <button onClick={() => setIdx((i) => (i + 1) % l.images.length)} className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/85 grid place-items-center shadow"><ChevronRight size={18} /></button>
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">{l.images.map((_, i) => <span key={i} className={cx('w-1.5 h-1.5 rounded-full', i === idx ? 'bg-white' : 'bg-white/50')} />)}</div>
        </>}
      </div>

      <div className="px-4">
        <div className="flex items-center justify-between mt-4 mb-1">
          <div className="font-display tabular text-gold text-3xl">{priceLabel(l)}</div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground"><span className="flex items-center gap-1"><Eye size={13} /> {l.views}</span><span className="flex items-center gap-1"><Heart size={13} /> {l.favorites}</span></div>
        </div>
        <h1 className="font-display text-2xl leading-tight mb-1">{l.title}</h1>
        <div className="text-sm text-muted-foreground flex items-center gap-1.5 mb-4"><MapPin size={14} className="text-primary" /> {l.city || 'France'}{l.postcode ? ` (${l.postcode})` : ''}{l.distanceKm != null ? ` · à ${l.distanceKm} km` : ''}</div>

        {attrs.length > 0 && (
          <Glass className="p-4 mb-4">
            <div className="font-semibold text-sm mb-3">Caractéristiques</div>
            <div className="grid grid-cols-2 gap-y-2.5 gap-x-4 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">État</span><span className="font-medium">{l.condition}</span></div>
              {attrs.map(([k, v]) => <div key={k} className="flex justify-between"><span className="text-muted-foreground capitalize">{k}</span><span className="font-medium">{v === true ? 'Oui' : String(v)}</span></div>)}
            </div>
          </Glass>
        )}

        <Glass className="p-4 mb-4">
          <div className="font-semibold text-sm mb-2">Description</div>
          <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">{l.description || 'Aucune description.'}</p>
        </Glass>

        {l.seller && (
          <Glass className="p-4 mb-4 flex items-center gap-3">
            <div className="grid place-items-center rounded-full text-white font-semibold shrink-0" style={{ width: 44, height: 44, background: l.seller.avatarColor || '#4353F0' }}>{l.seller.initials}</div>
            <div className="flex-1"><div className="font-semibold text-sm flex items-center gap-1">{l.seller.name} {l.seller.verified && <ShieldCheck size={14} className="text-primary" />}</div><div className="text-xs text-muted-foreground">{l.seller.handle}</div></div>
          </Glass>
        )}

        {l.similar?.length > 0 && (
          <div className="mb-4">
            <div className="font-semibold text-sm mb-2">Annonces similaires</div>
            <div className="flex gap-3 overflow-x-auto no-scrollbar">
              {l.similar.map((s) => (
                <button key={s.id} onClick={() => { setIdx(0); onOpenListing(s.id) }} className="press min-w-[140px] text-left">
                  <Glass className="rounded-2xl overflow-hidden"><div className="aspect-[4/3] bg-muted/60">{s.images?.[0] && <img src={imgSrc(s.images[0])} className="w-full h-full object-cover" alt="" />}</div><div className="p-2"><div className="font-display tabular text-gold text-sm">{priceLabel(s)}</div><div className="text-xs truncate">{s.title}</div></div></Glass>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* barre d'action */}
      {!l.isMine ? (
        <div className="fixed bottom-0 inset-x-0 z-30 p-3 bg-app-gradient/95 backdrop-blur border-t border-border">
          <div className="mx-auto max-w-3xl flex gap-2">
            <button onClick={() => onChat(l, `Bonjour, votre annonce « ${l.title} » est-elle toujours disponible ?`)} className="press flex-1 py-3 rounded-2xl border border-border bg-card/70 font-semibold flex items-center justify-center gap-1.5"><MessageCircle size={17} /> Message</button>
            <button onClick={() => onChat(l, null)} className="press px-4 py-3 rounded-2xl border border-gold/40 bg-gold/12 text-gold font-semibold flex items-center justify-center gap-1.5"><HandCoins size={17} /> Offre</button>
            <button onClick={buy} className="press flex-[1.2] py-3 rounded-2xl font-semibold text-white flex items-center justify-center gap-1.5" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>{l.transactionType === 'rent' ? 'Réserver' : 'Acheter'}</button>
          </div>
        </div>
      ) : (
        <div className="fixed bottom-0 inset-x-0 z-30 p-3 bg-app-gradient/95 backdrop-blur border-t border-border"><div className="mx-auto max-w-3xl text-center text-sm text-muted-foreground py-1">C'est ton annonce</div></div>
      )}
    </div>
  )
}

/* ============================ VENDRE ============================ */
function SellView({ cats, conditions, onCancel, onPublished, showToast }) {
  const [step, setStep] = useState(0) // 0 cat, 1 infos, 2 photos+loc
  const [cat, setCat] = useState(null)
  const [subcat, setSubcat] = useState('')
  const [txType, setTxType] = useState('sale')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [condition, setCondition] = useState('Bon état')
  const [attrs, setAttrs] = useState({})
  const [images, setImages] = useState([])
  const [uploading, setUploading] = useState(false)
  const [loc, setLoc] = useState(null)
  const [publishing, setPublishing] = useState(false)
  const fileRef = useRef(null)

  const pickCat = (c) => { setCat(c); setSubcat(c.subcats?.[0] || ''); setTxType(c.types?.[0] || 'sale'); setStep(1) }

  const onFiles = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, 8 - images.length)
    if (!files.length) return
    setUploading(true)
    for (const f of files) {
      try { const dataUrl = await fileToResizedDataUrl(f); const r = await api('/market/upload', { method: 'POST', body: JSON.stringify({ data: dataUrl }) }); if (r.url) setImages((im) => [...im, r.url]) } catch (err) { showToast('⚠️ Échec upload image') }
    }
    setUploading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  const publish = async () => {
    if (!title.trim()) return showToast('Ajoute un titre')
    if (!price || +price <= 0) return showToast('Ajoute un prix')
    setPublishing(true)
    const r = await api('/market/listings', { method: 'POST', body: JSON.stringify({
      title: title.trim(), description: description.trim(), priceCents: Math.round(+price * 100),
      category: cat.id, subcategory: subcat, transactionType: txType, condition, attributes: attrs, images,
      city: loc?.city || '', postcode: loc?.postcode || '', country: loc?.country || 'FR', lat: loc?.lat, lon: loc?.lon,
    }) })
    setPublishing(false)
    if (r.error) return showToast('⚠️ ' + r.error)
    onPublished()
  }

  return (
    <div className="mx-auto max-w-2xl px-4 pt-6 pb-28">
      <div className="flex items-center gap-3 mb-5">
        <button onClick={() => step === 0 ? onCancel() : setStep(step - 1)} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button>
        <h1 className="font-display text-2xl">Déposer une annonce</h1>
      </div>
      <div className="flex gap-1.5 mb-6">{[0, 1, 2].map((s) => <div key={s} className={cx('h-1.5 flex-1 rounded-full', s <= step ? 'bg-primary' : 'bg-muted/60')} />)}</div>

      {step === 0 && (
        <div className="cascade">
          <div className="font-semibold mb-3">Choisis une catégorie</div>
          <div className="grid grid-cols-2 gap-3">
            {cats.map((c) => <button key={c.id} onClick={() => pickCat(c)} className="press text-left"><Glass className="p-4 flex items-center gap-3"><div className="w-11 h-11 rounded-2xl grid place-items-center text-2xl text-white" style={{ background: c.color }}>{c.emoji}</div><div className="flex-1 min-w-0"><div className="font-semibold text-sm">{c.name}</div><div className="text-[11px] text-muted-foreground truncate">{c.subcats?.slice(0, 2).join(', ')}…</div></div></Glass></button>)}
          </div>
        </div>
      )}

      {step === 1 && cat && (
        <div className="cascade space-y-3">
          <div className="flex gap-2">
            <select value={subcat} onChange={(e) => setSubcat(e.target.value)} className="flex-1 rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none">{cat.subcats?.map((s) => <option key={s} value={s}>{s}</option>)}</select>
            {cat.types?.length > 1 && <select value={txType} onChange={(e) => setTxType(e.target.value)} className="rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none">{cat.types.map((t) => <option key={t} value={t}>{t === 'sale' ? 'Vente' : t === 'rent' ? 'Location' : 'Service'}</option>)}</select>}
          </div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre de l'annonce" className="w-full rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary" />
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Décris ton bien (état, détails, remise en main propre…)" rows={4} className="w-full rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary resize-none" />
          <div className="flex gap-2">
            <div className="flex-1 flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3.5 py-3">
              <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Prix" className="flex-1 bg-transparent text-sm outline-none tabular" />
              <span className="text-sm text-muted-foreground">€{txType === 'rent' ? '/mois' : ''}</span>
            </div>
            <select value={condition} onChange={(e) => setCondition(e.target.value)} className="rounded-2xl border border-border bg-card/60 px-3.5 py-3 text-sm outline-none">{conditions.map((c) => <option key={c} value={c}>{c}</option>)}</select>
          </div>
          {cat.fields?.length > 0 && (
            <Glass className="p-4 space-y-3">
              <div className="font-semibold text-sm">Caractéristiques</div>
              {cat.fields.map((f) => (
                <div key={f.key} className="flex items-center gap-3">
                  <label className="text-sm text-muted-foreground w-28 shrink-0">{f.label}</label>
                  {f.type === 'bool' ? (
                    <button onClick={() => setAttrs((a) => ({ ...a, [f.key]: !a[f.key] }))} className={cx('press px-3 py-1.5 rounded-full text-sm font-medium border', attrs[f.key] ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{attrs[f.key] ? 'Oui' : 'Non'}</button>
                  ) : f.type === 'select' ? (
                    <select value={attrs[f.key] || ''} onChange={(e) => setAttrs((a) => ({ ...a, [f.key]: e.target.value }))} className="flex-1 rounded-xl border border-border bg-card/60 px-3 py-2 text-sm outline-none"><option value="">—</option>{f.options.map((o) => <option key={o} value={o}>{o}</option>)}</select>
                  ) : (
                    <div className="flex-1 flex items-center gap-1"><input type={f.type === 'number' ? 'number' : 'text'} value={attrs[f.key] || ''} onChange={(e) => setAttrs((a) => ({ ...a, [f.key]: f.type === 'number' ? (e.target.value === '' ? '' : +e.target.value) : e.target.value }))} className="flex-1 rounded-xl border border-border bg-card/60 px-3 py-2 text-sm outline-none" />{f.unit && <span className="text-xs text-muted-foreground">{f.unit}</span>}</div>
                  )}
                </div>
              ))}
            </Glass>
          )}
          <button onClick={() => setStep(2)} className="press w-full py-3.5 rounded-2xl font-semibold text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Continuer</button>
        </div>
      )}

      {step === 2 && (
        <div className="cascade space-y-4">
          <div>
            <div className="font-semibold text-sm mb-2">Photos ({images.length}/8)</div>
            <div className="grid grid-cols-3 gap-2">
              {images.map((im, i) => <div key={i} className="relative aspect-square rounded-xl overflow-hidden"><img src={imgSrc(im)} className="w-full h-full object-cover" alt="" /><button onClick={() => setImages((x) => x.filter((_, j) => j !== i))} className="absolute top-1 right-1 w-6 h-6 rounded-full bg-ink/70 grid place-items-center text-white"><X size={13} /></button></div>)}
              {images.length < 8 && <button onClick={() => fileRef.current?.click()} className="press aspect-square rounded-xl border-2 border-dashed border-border grid place-items-center text-muted-foreground">{uploading ? <Loader2 className="animate-spin" size={22} /> : <Camera size={22} />}</button>}
            </div>
            <input ref={fileRef} type="file" accept="image/*" multiple capture="environment" onChange={onFiles} className="hidden" />
            <p className="text-[11px] text-muted-foreground mt-1.5">Depuis ton téléphone ou ordinateur · redimensionnées automatiquement.</p>
          </div>
          <div>
            <div className="font-semibold text-sm mb-2">Localisation</div>
            <SellLocation loc={loc} setLoc={setLoc} showToast={showToast} />
          </div>
          <button onClick={publish} disabled={publishing} className="press w-full py-3.5 rounded-2xl font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>{publishing ? <Loader2 className="animate-spin" size={18} /> : <><Check size={18} /> Publier l'annonce</>}</button>
        </div>
      )}
    </div>
  )
}

function SellLocation({ loc, setLoc, showToast }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [busy, setBusy] = useState(false)
  useEffect(() => { const t = setTimeout(async () => { if (q.trim().length < 3) return setResults([]); const r = await api(`/geo/autocomplete?q=${encodeURIComponent(q)}`); if (Array.isArray(r)) setResults(r) }, 300); return () => clearTimeout(t) }, [q])
  const useGPS = () => {
    if (!navigator.geolocation) return showToast('GPS indisponible')
    setBusy(true)
    navigator.geolocation.getCurrentPosition(async ({ coords }) => { const r = await api(`/geo/reverse?lat=${coords.latitude}&lon=${coords.longitude}`); setLoc({ city: r.city, postcode: r.postcode, country: r.country, lat: r.lat, lon: r.lon }); setBusy(false) }, () => { showToast('Autorise la localisation'); setBusy(false) }, { enableHighAccuracy: true, timeout: 10000 })
  }
  return (
    <div>
      {loc?.city && <Glass className="p-3 mb-2 flex items-center gap-2 text-sm !bg-primary/8"><MapPin size={15} className="text-primary" /> {loc.city}{loc.postcode ? ` (${loc.postcode})` : ''}<button onClick={() => setLoc(null)} className="ml-auto"><X size={15} className="text-muted-foreground" /></button></Glass>}
      <div className="flex gap-2">
        <div className="flex-1 flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5"><Search size={15} className="text-muted-foreground" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ville, code postal…" className="flex-1 bg-transparent text-sm outline-none" /></div>
        <button onClick={useGPS} className="press px-3 rounded-2xl border border-border bg-card/60 grid place-items-center">{busy ? <Loader2 className="animate-spin" size={17} /> : <Crosshair size={17} className="text-primary" />}</button>
      </div>
      {results.length > 0 && <Glass className="mt-2 divide-y divide-border max-h-52 overflow-y-auto">{results.map((r, i) => <button key={i} onClick={() => { setLoc({ city: r.city, postcode: r.postcode, country: r.country, lat: r.lat, lon: r.lon }); setQ(''); setResults([]) }} className="press w-full text-left px-3.5 py-2.5 text-sm flex items-center gap-2"><MapPin size={14} className="text-muted-foreground shrink-0" /> <span className="truncate">{r.label}</span></button>)}</Glass>}
    </div>
  )
}

/* ============================ SHEET LOCALISATION (filtre) ============================ */
function LocationSheet({ current, radius, setRadius, onApply, onClear, onClose, showToast }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [picked, setPicked] = useState(current)
  const [busy, setBusy] = useState(false)
  useEffect(() => { const t = setTimeout(async () => { if (q.trim().length < 3) return setResults([]); const r = await api(`/geo/autocomplete?q=${encodeURIComponent(q)}`); if (Array.isArray(r)) setResults(r) }, 300); return () => clearTimeout(t) }, [q])
  const useGPS = () => {
    if (!navigator.geolocation) return showToast('GPS indisponible')
    setBusy(true)
    navigator.geolocation.getCurrentPosition(async ({ coords }) => { const r = await api(`/geo/reverse?lat=${coords.latitude}&lon=${coords.longitude}`); setPicked({ city: r.city, lat: r.lat, lon: r.lon }); setBusy(false) }, () => { showToast('Autorise la localisation'); setBusy(false) }, { enableHighAccuracy: true, timeout: 10000 })
  }
  return (
    <Sheet onClose={onClose} title="Où cherches-tu ?">
      <div className="flex gap-2 mb-3">
        <div className="flex-1 flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5"><Search size={15} className="text-muted-foreground" /><input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ville, code postal, région…" className="flex-1 bg-transparent text-sm outline-none" /></div>
        <button onClick={useGPS} className="press px-3 rounded-2xl border border-border bg-card/60 grid place-items-center gap-1 text-primary">{busy ? <Loader2 className="animate-spin" size={17} /> : <Crosshair size={17} />}</button>
      </div>
      {results.length > 0 && <Glass className="mb-3 divide-y divide-border max-h-48 overflow-y-auto">{results.map((r, i) => <button key={i} onClick={() => { setPicked({ city: r.city, lat: r.lat, lon: r.lon }); setQ(''); setResults([]) }} className="press w-full text-left px-3.5 py-2.5 text-sm flex items-center gap-2"><MapPin size={14} className="text-muted-foreground shrink-0" /><span className="truncate">{r.label}</span></button>)}</Glass>}
      {picked?.city && (
        <>
          <Glass className="p-3 mb-4 flex items-center gap-2 text-sm !bg-primary/8"><MapPin size={15} className="text-primary" /> <b>{picked.city}</b></Glass>
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-2"><span className="font-medium">Rayon</span><span className="text-primary font-semibold">{radius === 0 ? 'Toute distance' : `${radius} km`}</span></div>
            <input type="range" min="0" max="200" step="5" value={radius} onChange={(e) => setRadius(+e.target.value)} className="w-full accent-[#4353F0]" />
          </div>
        </>
      )}
      <div className="flex gap-2">
        <button onClick={onClear} className="press flex-1 py-3 rounded-2xl border border-border bg-card/70 font-medium">Toute l'Europe</button>
        <button onClick={() => picked?.city ? onApply(picked) : showToast('Choisis une ville')} className="press flex-[1.5] py-3 rounded-2xl font-semibold text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Appliquer</button>
      </div>
    </Sheet>
  )
}

/* ============================ SHEET FILTRES ============================ */
function FiltersSheet({ conditions, cond, setCond, minPrice, setMinPrice, maxPrice, setMaxPrice, sort, setSort, onClose, onReset }) {
  const sorts = [['recent', 'Plus récentes'], ['price_asc', 'Prix croissant'], ['price_desc', 'Prix décroissant'], ['distance', 'Plus proches']]
  return (
    <Sheet onClose={onClose} title="Filtres">
      <div className="space-y-5">
        <div>
          <div className="font-semibold text-sm mb-2">Prix (€)</div>
          <div className="flex items-center gap-2"><input type="number" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} placeholder="Min" className="flex-1 rounded-xl border border-border bg-card/60 px-3 py-2.5 text-sm outline-none tabular" /><span className="text-muted-foreground">—</span><input type="number" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} placeholder="Max" className="flex-1 rounded-xl border border-border bg-card/60 px-3 py-2.5 text-sm outline-none tabular" /></div>
        </div>
        <div>
          <div className="font-semibold text-sm mb-2">État</div>
          <div className="flex flex-wrap gap-2">{conditions.map((c) => <button key={c} onClick={() => setCond(cond === c ? '' : c)} className={cx('press px-3 py-1.5 rounded-full text-sm border', cond === c ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{c}</button>)}</div>
        </div>
        <div>
          <div className="font-semibold text-sm mb-2">Trier par</div>
          <div className="flex flex-wrap gap-2">{sorts.map(([v, l]) => <button key={v} onClick={() => setSort(v)} className={cx('press px-3 py-1.5 rounded-full text-sm border', sort === v ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{l}</button>)}</div>
        </div>
        <div className="flex gap-2 pt-2">
          <button onClick={onReset} className="press flex-1 py-3 rounded-2xl border border-border bg-card/70 font-medium">Réinitialiser</button>
          <button onClick={onClose} className="press flex-[1.5] py-3 rounded-2xl font-semibold text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Voir les résultats</button>
        </div>
      </div>
    </Sheet>
  )
}

/* ============================ MESSAGES (threads) ============================ */
function ThreadsView({ onBack, onOpen }) {
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => { api('/market/threads').then((r) => { if (Array.isArray(r)) setThreads(r); setLoading(false) }) }, [])
  return (
    <div className="mx-auto max-w-2xl px-4 pt-6 pb-28">
      <div className="flex items-center gap-3 mb-5"><button onClick={onBack} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button><h1 className="font-display text-2xl">Messages</h1></div>
      {loading ? <Glass className="p-8 text-center text-muted-foreground"><Loader2 className="animate-spin mx-auto" /></Glass> : threads.length === 0 ? <Glass className="p-12 text-center"><MessageCircle size={32} className="mx-auto mb-3 text-muted-foreground" /><div className="font-semibold mb-1">Aucune conversation</div><div className="text-sm text-muted-foreground">Contacte un vendeur depuis une annonce.</div></Glass> : (
        <div className="space-y-2">
          {threads.map((t) => (
            <button key={t.id} onClick={() => onOpen(t.id)} className="press w-full text-left"><Glass className="p-3 flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-muted/60 overflow-hidden shrink-0">{t.listingImage && <img src={imgSrc(t.listingImage)} className="w-full h-full object-cover" alt="" />}</div>
              <div className="flex-1 min-w-0"><div className="font-semibold text-sm truncate">{t.listingTitle}</div><div className="text-xs text-muted-foreground truncate">{t.other?.name} · {t.lastMessage ? (t.lastMessage.type === 'offer' ? `💰 Offre ${euro(t.lastMessage.amountCents)} €` : t.lastMessage.text) : 'Nouvelle conversation'}</div></div>
              <span className={cx('text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0', t.role === 'seller' ? 'bg-gold/15 text-gold' : 'bg-primary/10 text-primary')}>{t.role === 'seller' ? 'Vends' : 'Achat'}</span>
            </Glass></button>
          ))}
        </div>
      )}
    </div>
  )
}

/* ============================ CONVERSATION ============================ */
function ThreadView({ me, threadId, onBack, onBought, showToast }) {
  const [data, setData] = useState(null)
  const [text, setText] = useState('')
  const [showOffer, setShowOffer] = useState(false)
  const [offerAmt, setOfferAmt] = useState('')
  const scrollRef = useRef(null)
  const load = useCallback(async () => { const r = await api(`/market/threads/${threadId}/messages`); if (!r.error) setData(r) }, [threadId])
  useEffect(() => { load() }, [load])
  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [data])

  const send = async () => { if (!text.trim()) return; const r = await api(`/market/threads/${threadId}/messages`, { method: 'POST', body: JSON.stringify({ text }) }); if (!r.error) { setText(''); load() } }
  const makeOffer = async () => { if (!offerAmt || +offerAmt <= 0) return; const r = await api(`/market/threads/${threadId}/offer`, { method: 'POST', body: JSON.stringify({ amountCents: Math.round(+offerAmt * 100) }) }); if (r.error) return showToast('⚠️ ' + r.error); setShowOffer(false); setOfferAmt(''); load() }
  const respond = async (offerId, action) => { const r = await api(`/market/threads/${threadId}/offer/${offerId}/respond`, { method: 'POST', body: JSON.stringify({ action }) }); if (r.error) return showToast('⚠️ ' + r.error); load() }
  const buyAt = async (amountCents) => { const r = await api(`/market/listings/${data.listing.id}/buy`, { method: 'POST', body: JSON.stringify({ priceCents: amountCents }) }); if (r.error) return showToast('⚠️ ' + r.error); onBought(); load() }

  if (!data) return <div className="min-h-[60dvh] grid place-items-center"><Loader2 className="animate-spin text-primary" /></div>
  const isSeller = data.thread.role === 'seller'

  return (
    <div className="mx-auto max-w-2xl flex flex-col h-[100dvh]">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-app-gradient/90 backdrop-blur">
        <button onClick={onBack} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button>
        <div className="w-10 h-10 rounded-xl bg-muted/60 overflow-hidden shrink-0">{data.listing?.images?.[0] && <img src={imgSrc(data.listing.images[0])} className="w-full h-full object-cover" alt="" />}</div>
        <div className="flex-1 min-w-0"><div className="font-semibold text-sm truncate">{data.thread.listingTitle}</div><div className="text-xs text-muted-foreground">{data.other?.name} · <span className="text-gold font-medium tabular">{euro(data.thread.listingPriceCents)} €</span></div></div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        {data.messages.map((m) => {
          const mine = m.senderId === me.id
          if (m.type === 'system') return <div key={m.id} className="text-center text-xs text-muted-foreground py-1">{m.text}</div>
          if (m.type === 'offer') return (
            <div key={m.id} className={cx('flex', mine ? 'justify-end' : 'justify-start')}>
              <Glass className={cx('p-3 max-w-[80%] rounded-2xl', m.offerStatus === 'accepted' ? '!bg-green-500/10' : m.offerStatus === 'rejected' ? '!bg-destructive/8' : '!bg-gold/10')}>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><HandCoins size={13} className="text-gold" /> Offre {mine ? 'envoyée' : 'reçue'}</div>
                <div className="font-display tabular text-gold text-2xl">{euro(m.amountCents)} €</div>
                {m.offerStatus === 'pending' && !mine && <div className="flex gap-2 mt-2"><button onClick={() => respond(m.offerId, 'reject')} className="press flex-1 py-1.5 rounded-xl border border-border text-sm">Refuser</button><button onClick={() => respond(m.offerId, 'accept')} className="press flex-1 py-1.5 rounded-xl bg-green-500 text-white text-sm font-semibold">Accepter</button></div>}
                {m.offerStatus === 'accepted' && <div className="mt-2 text-xs font-medium text-green-600 dark:text-green-400 flex items-center gap-1"><Check size={13} /> Acceptée{!isSeller && <button onClick={() => buyAt(m.amountCents)} className="ml-auto press px-3 py-1 rounded-lg bg-primary text-white">Payer</button>}</div>}
                {m.offerStatus === 'rejected' && <div className="mt-1 text-xs text-destructive">Refusée</div>}
                {m.offerStatus === 'pending' && mine && <div className="mt-1 text-xs text-muted-foreground">En attente…</div>}
              </Glass>
            </div>
          )
          return <div key={m.id} className={cx('flex', mine ? 'justify-end' : 'justify-start')}><div className={cx('px-3.5 py-2 rounded-2xl max-w-[80%] text-sm', mine ? 'bg-primary text-white' : 'glass')}>{m.text}</div></div>
        })}
      </div>

      <div className="p-3 border-t border-border bg-app-gradient/95 backdrop-blur">
        <div className="flex items-center gap-2">
          <button onClick={() => setShowOffer((s) => !s)} className="press w-10 h-10 rounded-full grid place-items-center border border-gold/40 bg-gold/12 text-gold shrink-0"><HandCoins size={18} /></button>
          <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Écris un message…" className="flex-1 rounded-full border border-border bg-card/60 px-4 py-2.5 text-sm outline-none" />
          <button onClick={send} className="press w-10 h-10 rounded-full grid place-items-center text-white shrink-0" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Send size={17} /></button>
        </div>
        <AnimatePresence>{showOffer && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="flex items-center gap-2 mt-2"><div className="flex-1 flex items-center gap-2 rounded-full border border-gold/40 bg-gold/8 px-4 py-2.5"><span className="text-sm text-muted-foreground">Ton offre :</span><input type="number" autoFocus value={offerAmt} onChange={(e) => setOfferAmt(e.target.value)} placeholder="0" className="flex-1 bg-transparent text-sm outline-none tabular" /><span className="text-sm text-gold font-semibold">€</span></div><button onClick={makeOffer} className="press px-4 py-2.5 rounded-full bg-gold text-white text-sm font-semibold">Envoyer</button></div>
          </motion.div>
        )}</AnimatePresence>
      </div>
    </div>
  )
}

/* ============================ SHEET générique ============================ */
function Sheet({ onClose, title, children }) {
  return (
    <motion.div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass sheen strong className="p-5 rounded-b-none sm:rounded-b-[var(--radius)] max-h-[90dvh] overflow-y-auto no-scrollbar">
          <div className="flex items-center justify-between mb-4"><h3 className="font-display text-xl">{title}</h3><button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button></div>
          {children}
        </Glass>
      </motion.div>
    </motion.div>
  )
}
