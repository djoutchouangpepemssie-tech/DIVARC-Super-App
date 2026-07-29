'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import {
  Heart, MessageCircle, Bookmark, Share2, Volume2, VolumeX, Plus, X, ArrowLeft,
  ShoppingBag, Info, BadgeCheck, Sparkles, Check, UserPlus, UserCheck, EyeOff, Send as SendIcon, Gift, Cpu, ChevronRight
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const eur = (c) => (c / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const kf = (n) => n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace('.0', '') + 'k' : String(n)
const Glass = ({ className, children, ...p }) => <div className={cx('glass', className)} {...p}>{children}</div>
const Avatar = ({ c, size = 44 }) => (
  <div className="grid place-items-center rounded-full text-white font-semibold shrink-0"
    style={{ width: size, height: size, background: c?.avatarColor || '#4353F0', fontSize: size * 0.36 }}>{c?.initials}</div>
)

const LIBRARY = [
  { label: 'Joyrides', url: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4' },
  { label: 'Fun', url: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4' },
  { label: 'Blazes', url: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4' },
  { label: 'Escapes', url: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4' },
  { label: 'Sintel', url: 'https://storage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4' },
]

export default function Social({ me, onBack }) {
  const [mode, setMode] = useState('foryou') // foryou | following | chrono
  const [feed, setFeed] = useState([])
  const [muted, setMuted] = useState(true)
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [commentsFor, setCommentsFor] = useState(null)
  const [tipFor, setTipFor] = useState(null)
  const [toast, setToast] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    const scope = mode === 'following' ? 'following' : 'all'
    const m = mode === 'chrono' ? 'chrono' : 'foryou'
    const r = await api(`/social/feed?mode=${m}&scope=${scope}`)
    if (Array.isArray(r)) setFeed(r)
    setLoading(false)
  }, [mode])
  useEffect(() => { load() }, [load])

  const showToast = (t) => { setToast(t); setTimeout(() => setToast(null), 2200) }

  const onLike = async (p) => {
    setFeed((f) => f.map((x) => x.id === p.id ? { ...x, liked: !x.liked, likes: x.likes + (x.liked ? -1 : 1) } : x))
    await api(`/social/posts/${p.id}/like`, { method: 'POST' })
  }
  const onSave = async (p) => {
    setFeed((f) => f.map((x) => x.id === p.id ? { ...x, saved: !x.saved, saves: x.saves + (x.saved ? -1 : 1) } : x))
    await api(`/social/posts/${p.id}/save`, { method: 'POST' })
    showToast(p.saved ? 'Retiré des enregistrements' : 'Enregistré ✓')
  }
  const onFollow = async (p) => {
    setFeed((f) => f.map((x) => x.author?.id === p.author?.id ? { ...x, following: !x.following } : x))
    await api(`/social/follow/${p.author.id}`, { method: 'POST' })
  }
  const onNotInterested = async (p) => {
    await api(`/social/posts/${p.id}/notinterested`, { method: 'POST' })
    setFeed((f) => f.filter((x) => x.id !== p.id)); showToast('Merci, moins de contenu comme ça')
  }
  const onBuy = async (p) => {
    const r = await api(`/social/posts/${p.id}/buy`, { method: 'POST' })
    if (r.error) return showToast('⚠️ ' + r.error)
    showToast(`Acheté ✓ ${p.product.title} · ${eur(r.amountCents)} €`)
  }
  const onTip = async (p, amountCents) => {
    const r = await api(`/social/posts/${p.id}/tip`, { method: 'POST', body: JSON.stringify({ amountCents }) })
    setTipFor(null)
    if (r.error) return showToast('⚠️ ' + r.error)
    showToast(`Pourboire envoyé 💛 ${eur(amountCents)} €`)
  }

  return (
    <div className="fixed inset-0 z-40 bg-black">
      {/* feed */}
      <div className="h-full w-full overflow-y-scroll snap-y snap-mandatory no-scrollbar">
        {loading && <div className="h-full grid place-items-center text-white/70">Chargement du flux…</div>}
        {!loading && feed.length === 0 && (
          <div className="h-full grid place-items-center text-center text-white/70 px-8">
            <div>
              <Sparkles className="mx-auto mb-3" />
              {mode === 'following' ? 'Suis des créateurs pour remplir ce flux.' : 'Aucune vidéo pour le moment.'}
            </div>
          </div>
        )}
        {feed.map((p, i) => (
          <PostCard key={p.id} p={p} muted={muted} setMuted={setMuted}
            onLike={onLike} onSave={onSave} onFollow={onFollow} onComments={() => setCommentsFor(p)}
            onTip={() => setTipFor(p)} onBuy={onBuy} onNotInterested={onNotInterested} showToast={showToast} />
        ))}
        {!loading && feed.length > 0 && <WellnessCard />}
      </div>

      {/* top bar */}
      <div className="absolute top-0 inset-x-0 pt-[max(env(safe-area-inset-top),14px)] px-4 flex items-center gap-3 z-20">
        <button onClick={onBack} aria-label="Retour" className="press w-9 h-9 rounded-full grid place-items-center bg-black/30 text-white backdrop-blur"><ArrowLeft size={18} /></button>
        <div className="flex-1 flex items-center justify-center gap-4">
          {[['following', 'Abonnements'], ['foryou', 'Pour toi'], ['chrono', 'Chrono']].map(([id, label]) => (
            <button key={id} onClick={() => setMode(id)}
              className={cx('press text-sm font-semibold relative pb-1', mode === id ? 'text-white' : 'text-white/55')}>
              {label}
              {mode === id && <motion.div layoutId="soctab" className="absolute -bottom-0 left-0 right-0 h-0.5 bg-white rounded-full" />}
            </button>
          ))}
        </div>
        <button onClick={() => setCreateOpen(true)} aria-label="Créer" className="press w-9 h-9 rounded-full grid place-items-center bg-white text-black"><Plus size={20} /></button>
      </div>

      {/* toast */}
      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="absolute bottom-28 left-1/2 -translate-x-1/2 z-30 bg-white text-ink text-sm font-medium px-4 py-2.5 rounded-full shadow-xl">{toast}</motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {createOpen && <CreatePost me={me} onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); setMode('chrono'); load(); showToast('Publié ✓') }} />}
        {commentsFor && <CommentsSheet post={commentsFor} me={me} onClose={() => setCommentsFor(null)} onAdded={() => setFeed((f) => f.map((x) => x.id === commentsFor.id ? { ...x, comments: x.comments + 1 } : x))} />}
        {tipFor && <TipSheet post={tipFor} onClose={() => setTipFor(null)} onTip={(amt) => onTip(tipFor, amt)} />}
      </AnimatePresence>
    </div>
  )
}

function PostCard({ p, muted, setMuted, onLike, onSave, onFollow, onComments, onTip, onBuy, onNotInterested, showToast }) {
  const vidRef = useRef()
  const cardRef = useRef()
  const [showWhy, setShowWhy] = useState(false)
  const [hearts, setHearts] = useState([])
  const viewed = useRef(false)

  useEffect(() => {
    const el = cardRef.current
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        const active = e.isIntersecting && e.intersectionRatio > 0.7
        const v = vidRef.current
        if (v) { active ? v.play().catch(() => {}) : v.pause() }
        if (active && !viewed.current) {
          viewed.current = true
          if (p.sponsored) api(`/ads/campaigns/${p.campaignId}/track`, { method: 'POST', body: JSON.stringify({ type: 'impression' }) })
          else api(`/social/posts/${p.id}/view`, { method: 'POST' })
        }
      })
    }, { threshold: [0, 0.7, 1] })
    if (el) obs.observe(el)
    return () => obs.disconnect()
  }, [p.id])

  const dblLike = () => {
    if (!p.liked) onLike(p)
    const id = Date.now()
    setHearts((h) => [...h, id])
    setTimeout(() => setHearts((h) => h.filter((x) => x !== id)), 1000)
  }

  return (
    <div ref={cardRef} className="relative h-full w-full snap-start snap-always overflow-hidden bg-black">
      <video ref={vidRef} src={p.mediaUrl} muted={muted} loop playsInline preload="metadata"
        className={cx('absolute inset-0 w-full h-full object-cover', p.sponsored && 'hidden')} onClick={dblLike} onDoubleClick={dblLike} />
      {p.sponsored && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-10 text-center" style={{ background: `linear-gradient(160deg, ${p.color}, #14162B)` }}>
          <div className="text-7xl mb-5 float-slow">{p.emoji}</div>
          <div className="font-display text-3xl leading-tight">{(p.caption || '').split('\n')[0]}</div>
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30 pointer-events-none" />

      {/* floating hearts */}
      <AnimatePresence>
        {hearts.map((id) => (
          <motion.div key={id} initial={{ opacity: 1, scale: 0.5, y: 0, x: 0 }}
            animate={{ opacity: 0, scale: 1.4, y: -180, x: (Math.random() - 0.5) * 80 }} transition={{ duration: 1 }}
            className="absolute left-1/2 top-1/2 text-5xl pointer-events-none">❤️</motion.div>
        ))}
      </AnimatePresence>

      {/* AI + sound */}
      <div className="absolute top-16 right-3 flex flex-col gap-2 z-10">
        <button onClick={() => setMuted((m) => !m)} className="press w-9 h-9 rounded-full grid place-items-center bg-black/35 text-white backdrop-blur">
          {muted ? <VolumeX size={17} /> : <Volume2 size={17} />}
        </button>
        {p.aiGenerated && <span className="text-[9px] bg-black/40 text-white px-2 py-1 rounded-full backdrop-blur flex items-center gap-1"><Cpu size={10} /> IA</span>}
      </div>

      {/* right action rail */}
      <div className="absolute right-3 bottom-32 flex flex-col items-center gap-5 z-10 text-white">
        <button onClick={() => onFollow(p)} className="press relative">
          <Avatar c={p.author} size={48} />
          <span className={cx('absolute -bottom-2 left-1/2 -translate-x-1/2 w-5 h-5 rounded-full grid place-items-center text-white', p.following ? 'bg-green-500' : 'bg-primary')}>
            {p.following ? <Check size={12} /> : <Plus size={12} />}
          </span>
        </button>
        <RailBtn onClick={() => onLike(p)} active={p.liked} icon={<Heart size={30} fill={p.liked ? '#F15BB5' : 'none'} color={p.liked ? '#F15BB5' : '#fff'} />} label={kf(p.likes)} />
        <RailBtn onClick={onComments} icon={<MessageCircle size={30} />} label={kf(p.comments)} />
        <RailBtn onClick={() => onSave(p)} active={p.saved} icon={<Bookmark size={28} fill={p.saved ? '#E2AA2B' : 'none'} color={p.saved ? '#E2AA2B' : '#fff'} />} label={kf(p.saves)} />
        <RailBtn onClick={() => onTip(p)} icon={<Gift size={28} color="#F0CE7E" />} label="Pourboire" />
        <RailBtn onClick={() => showToast('Lien copié · partage dans le Chat')} icon={<Share2 size={28} />} label="Partager" />
        <RailBtn onClick={() => onNotInterested(p)} icon={<EyeOff size={24} />} label="Moins" />
      </div>

      {/* bottom info */}
      <div className="absolute left-3 right-16 bottom-28 z-10 text-white">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-semibold">{p.author?.handle}</span>
          {p.author?.verified && <BadgeCheck size={15} className="text-sky-300" />}
          {p.sponsored && <span className="text-[10px] uppercase tracking-wide bg-white/25 px-2 py-0.5 rounded-full">Sponsorisé</span>}
        </div>
        <p className="text-sm mb-2 leading-snug drop-shadow">{p.caption}</p>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {p.hashtags?.map((h) => <span key={h} className="text-xs text-white/85 font-medium">{h}</span>)}
        </div>
        {p.sponsored && (
          <button onClick={() => api(`/ads/campaigns/${p.campaignId}/track`, { method: 'POST', body: JSON.stringify({ type: 'click' }) }).then(() => showToast('Merci de ton intérêt ! 🙌'))}
            className="press mb-2 inline-flex items-center gap-2 bg-white text-ink rounded-2xl px-4 py-2 font-semibold text-sm shadow-lg">
            {p.cta} <ChevronRight size={16} />
          </button>
        )}

        {/* Why this video */}
        <button onClick={() => setShowWhy((s) => !s)} className="press inline-flex items-center gap-1.5 text-xs bg-white/15 backdrop-blur px-2.5 py-1 rounded-full mb-2">
          <Info size={12} /> Pourquoi cette vidéo ?
        </button>
        <AnimatePresence>
          {showWhy && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden">
              <div className="text-xs bg-black/50 backdrop-blur rounded-2xl p-3 mb-2 max-w-xs">
                <b className="text-gold">{p.reason}</b>
                <div className="text-white/70 mt-1">Algorithme transparent (DSA). Tu peux régler tes intérêts ou passer en Chrono à tout moment.</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* shoppable */}
        {p.product && (
          <motion.button onClick={() => onBuy(p)} initial={{ y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
            className="press flex items-center gap-2 bg-white text-ink rounded-2xl pl-2 pr-3 py-2 shadow-lg max-w-xs">
            <span className="w-9 h-9 rounded-xl grid place-items-center bg-gold/20 text-lg">{p.product.emoji}</span>
            <div className="text-left leading-tight">
              <div className="text-xs font-semibold truncate">{p.product.title}</div>
              <div className="text-[11px] text-muted-foreground">Acheter en 1 tap</div>
            </div>
            <span className="ml-1 font-display text-sm">{eur(p.product.priceCents)} €</span>
            <ShoppingBag size={16} />
          </motion.button>
        )}
      </div>
    </div>
  )
}
const RailBtn = ({ onClick, icon, label, active }) => (
  <button onClick={onClick} className="press flex flex-col items-center gap-1">
    <span className={cx('drop-shadow', active && 'scale-110')}>{icon}</span>
    <span className="text-[11px] font-medium drop-shadow">{label}</span>
  </button>
)

function WellnessCard() {
  return (
    <div className="h-full w-full snap-start grid place-items-center bg-gradient-to-b from-black to-[#0E1020] text-white text-center px-8">
      <div className="card-hero p-8 max-w-sm w-full glow-primary">
        <div className="relative">
          <div className="w-20 h-20 rounded-3xl grid place-items-center mx-auto mb-5 bg-white/15 backdrop-blur hairline float-slow text-4xl">✨</div>
          <div className="font-display text-3xl mb-2">Tu es à jour</div>
          <p className="text-white/80 text-sm max-w-xs mx-auto leading-relaxed">DIVARC ne force pas le scroll infini — tu as vu toutes les nouveautés. Reviens quand tu veux. 💛</p>
        </div>
      </div>
    </div>
  )
}

function BottomSheet({ children, onClose, title }) {
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end justify-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass className="glass-sheen glass-strong p-5 pt-3 rounded-b-none max-h-[80dvh] overflow-y-auto no-scrollbar">
          <div className="w-10 h-1.5 rounded-full bg-foreground/15 mx-auto mb-4" />
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-2xl">{title}</h3>
            <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button>
          </div>
          {children}
        </Glass>
      </motion.div>
    </motion.div>
  )
}

function CommentsSheet({ post, me, onClose, onAdded }) {
  const [list, setList] = useState([])
  const [text, setText] = useState('')
  const load = useCallback(async () => { const r = await api(`/social/posts/${post.id}/comments`); if (Array.isArray(r)) setList(r) }, [post.id])
  useEffect(() => { load() }, [load])
  const add = async () => {
    if (!text.trim()) return
    const r = await api(`/social/posts/${post.id}/comments`, { method: 'POST', body: JSON.stringify({ text }) })
    if (!r.error) { setList((l) => [r, ...l]); setText(''); onAdded() }
  }
  return (
    <BottomSheet onClose={onClose} title={`${post.comments} commentaires`}>
      <div className="space-y-3 mb-4">
        {list.length === 0 && <div className="text-center text-sm text-muted-foreground py-6">Sois le premier à commenter.</div>}
        {list.map((c) => (
          <div key={c.id} className="flex gap-2.5">
            <Avatar c={c} size={36} />
            <div><div className="text-xs font-semibold">{c.name}</div><div className="text-sm">{c.text}</div></div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 sticky bottom-0">
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder="Ajoute un commentaire…" className="flex-1 rounded-full border border-border bg-card/60 px-4 py-2.5 text-sm" />
        <button onClick={add} className="press w-10 h-10 rounded-full grid place-items-center text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><SendIcon size={17} /></button>
      </div>
    </BottomSheet>
  )
}

function TipSheet({ post, onClose, onTip }) {
  const [custom, setCustom] = useState('')
  return (
    <BottomSheet onClose={onClose} title="Pourboire au créateur">
      <div className="text-center mb-4">
        <Avatar c={post.author} size={56} />
        <div className="mt-2 font-semibold">{post.author?.name}</div>
        <div className="text-xs text-muted-foreground">Ton pourboire est crédité direct dans son wallet 💛</div>
      </div>
      <div className="grid grid-cols-3 gap-2 mb-3">
        {[100, 200, 500].map((a) => (
          <button key={a} onClick={() => onTip(a)} className="press py-4 rounded-2xl border border-gold/40 bg-gold/10 hairline hover:glow-gold transition-shadow"><span className="gold-text font-display text-xl">{eur(a)} €</span></button>
        ))}
      </div>
      <div className="flex gap-2">
        <input value={custom} onChange={(e) => setCustom(e.target.value.replace(/\D/g, ''))} placeholder="Autre montant (€)"
          className="flex-1 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
        <button onClick={() => custom && onTip(Number(custom) * 100)} className="press px-5 rounded-2xl font-semibold text-ink" style={{ background: 'linear-gradient(135deg,#F0CE7E,#E2AA2B,#B98514)' }}>Envoyer</button>
      </div>
    </BottomSheet>
  )
}

function CreatePost({ me, onClose, onCreated }) {
  const [caption, setCaption] = useState('')
  const [tags, setTags] = useState('')
  const [media, setMedia] = useState(LIBRARY[0].url)
  const [shop, setShop] = useState(false)
  const [pTitle, setPTitle] = useState('')
  const [pPrice, setPPrice] = useState('')
  const [busy, setBusy] = useState(false)
  const [aiIdea, setAiIdea] = useState(false)

  const suggest = () => {
    setAiIdea(true)
    setCaption('POV : tu découvres ta nouvelle app préférée 🤩')
    setTags('divarc, lifestyle, tech')
    setTimeout(() => setAiIdea(false), 400)
  }
  const publish = async () => {
    setBusy(true)
    const body = {
      caption, mediaUrl: media, mediaType: 'video',
      hashtags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      product: shop && pTitle ? { title: pTitle, priceCents: Math.round(Number(pPrice || 0) * 100), emoji: '🛍️' } : null,
    }
    const r = await api('/social/posts', { method: 'POST', body: JSON.stringify(body) })
    setBusy(false)
    if (!r.error) onCreated()
  }
  return (
    <BottomSheet onClose={onClose} title="Studio — nouvelle vidéo">
      <label className="text-xs text-muted-foreground">Choisis un clip</label>
      <div className="flex gap-2 overflow-x-auto no-scrollbar my-2 pb-1">
        {LIBRARY.map((v) => (
          <button key={v.url} onClick={() => setMedia(v.url)} className={cx('press shrink-0 w-20 h-28 rounded-xl overflow-hidden relative border-2', media === v.url ? 'border-primary' : 'border-transparent')}>
            <video src={v.url} muted className="w-full h-full object-cover" />
            <span className="absolute bottom-1 left-1 text-[9px] text-white bg-black/40 px-1 rounded">{v.label}</span>
          </button>
        ))}
      </div>
      <div className="flex items-center justify-between mt-3 mb-1">
        <label className="text-xs text-muted-foreground">Légende</label>
        <button onClick={suggest} className="press text-xs text-primary font-medium flex items-center gap-1"><Sparkles size={12} /> Idée IA</button>
      </div>
      <textarea value={caption} onChange={(e) => setCaption(e.target.value)} rows={2} placeholder="Raconte ton histoire…"
        className={cx('w-full rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm transition', aiIdea && 'ring-2 ring-primary')} />
      <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="Hashtags (séparés par des virgules)"
        className="w-full mt-3 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
      <button onClick={() => setShop((s) => !s)} className="press w-full mt-3 flex items-center justify-between rounded-2xl border border-border bg-card/60 px-4 py-3">
        <span className="text-sm font-medium flex items-center gap-2"><ShoppingBag size={16} /> Vidéo achetable</span>
        <div className={cx('w-11 h-6 rounded-full p-0.5 transition-colors', shop ? 'bg-primary' : 'bg-muted')}><motion.div className="w-5 h-5 rounded-full bg-white" animate={{ x: shop ? 20 : 0 }} /></div>
      </button>
      {shop && (
        <div className="grid grid-cols-3 gap-2 mt-2">
          <input value={pTitle} onChange={(e) => setPTitle(e.target.value)} placeholder="Produit" className="col-span-2 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
          <input value={pPrice} onChange={(e) => setPPrice(e.target.value)} placeholder="€" className="rounded-2xl border border-border bg-card/60 px-3 py-3 text-sm" />
        </div>
      )}
      <button onClick={publish} disabled={busy} className="press w-full mt-5 rounded-2xl py-3.5 font-semibold text-white disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
        {busy ? 'Publication…' : 'Publier'}
      </button>
    </BottomSheet>
  )
}
