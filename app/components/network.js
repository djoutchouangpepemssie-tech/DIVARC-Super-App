'use client'

// Réseau DIVARC (type Facebook) — Couche 2 : composer + fil (curseur) + suppression.
// Appelle le nouveau contexte social /api/net/* (PostgreSQL). Réactions/commentaires = Couche 3.
import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Image as ImageIcon, Globe, Users, Lock, RefreshCw, Trash2, MoreHorizontal, ShieldCheck } from 'lucide-react'
import { api } from '@/lib/api'

const cx = (...a) => a.filter(Boolean).join(' ')
const VIS = [['public', 'Public', Globe], ['friends', 'Amis', Users], ['only_me', 'Moi', Lock]]

function timeAgo(d) {
  const s = (Date.now() - new Date(d).getTime()) / 1000
  if (s < 60) return "à l'instant"
  if (s < 3600) return Math.floor(s / 60) + ' min'
  if (s < 86400) return Math.floor(s / 3600) + ' h'
  return Math.floor(s / 86400) + ' j'
}
const fileToDataUrl = (f) => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(f) })

export default function NetworkModule({ me, onClose }) {
  const [items, setItems] = useState(null)
  const [cursor, setCursor] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [unavailable, setUnavailable] = useState(false)

  const load = useCallback(async (cur) => {
    const r = await api(`/net/feed${cur ? `?cursor=${encodeURIComponent(cur)}` : ''}`)
    if (r?.error) { setUnavailable(true); setItems([]); return }
    setUnavailable(false)
    setItems((prev) => (cur && prev ? [...prev, ...r.items] : r.items))
    setCursor(r.nextCursor || null)
  }, [])
  useEffect(() => { load() }, [load])

  const onPublished = (post) => setItems((prev) => [post, ...(prev || [])])
  const onDeleted = (id) => setItems((prev) => (prev || []).filter((p) => p.id !== id))

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={onClose} className="press" aria-label="Fermer"><X size={22} /></button>
        <h1 className="font-display text-2xl">Réseau <span className="text-xs align-top text-muted-foreground">bêta</span></h1>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
        {unavailable ? (
          <div className="text-center py-20 text-muted-foreground">
            <ShieldCheck size={36} className="mx-auto mb-3 opacity-50" />
            <div className="font-medium text-foreground">Réseau en cours d'activation</div>
            <div className="text-sm mt-1">La base PostgreSQL doit être branchée (Railway). Revenez bientôt.</div>
          </div>
        ) : (
          <>
            <Composer me={me} onPublished={onPublished} />
            {items === null ? (
              <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
            ) : items.length === 0 ? (
              <div className="text-center py-14 text-sm text-muted-foreground">Ton fil est vide. Publie ou suis des gens pour le remplir.</div>
            ) : (
              <div className="space-y-3 pb-4">
                {items.map((p) => <PostCard key={p.id} p={p} onDeleted={onDeleted} />)}
                {cursor && (
                  <button onClick={async () => { setLoadingMore(true); await load(cursor); setLoadingMore(false) }}
                    className="press w-full py-3 rounded-2xl border border-border bg-card/60 text-sm font-medium">
                    {loadingMore ? <RefreshCw size={16} className="animate-spin mx-auto" /> : 'Voir plus'}
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}

function Composer({ me, onPublished }) {
  const [body, setBody] = useState('')
  const [image, setImage] = useState(null)   // { url, alt }
  const [vis, setVis] = useState('public')
  const [busy, setBusy] = useState(false)
  const fileRef = useRef(null)

  const pick = async (e) => {
    const f = e.target.files?.[0]; e.target.value = ''
    if (!f) return
    if (f.size > 6.5 * 1024 * 1024) return alert('Image trop lourde (max ~6 Mo)')
    const dataUrl = await fileToDataUrl(f)
    const r = await api('/chat/upload', { method: 'POST', body: JSON.stringify({ data: dataUrl }) })
    if (r.url) setImage({ url: r.url, alt: '' })
  }
  const publish = async () => {
    if (!body.trim() && !image) return
    setBusy(true)
    const payload = { body, visibility: vis, media: image ? [{ url: image.url, alt: image.alt || 'image', kind: 'image' }] : [] }
    const r = await api('/net/posts', { method: 'POST', body: JSON.stringify(payload) })
    setBusy(false)
    if (r.error) return alert(r.error)
    onPublished(r); setBody(''); setImage(null); setVis('public')
  }

  return (
    <div className="rounded-2xl border border-border bg-card/60 p-4 my-4">
      <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={3} placeholder="Quoi de neuf ?"
        className="w-full bg-transparent outline-none resize-none text-sm" />
      {image && (
        <div className="relative mt-2">
          <img src={image.url} alt="" className="rounded-xl max-h-56 w-auto border border-border" />
          <button onClick={() => setImage(null)} className="absolute top-2 right-2 w-7 h-7 rounded-full bg-ink text-white grid place-items-center"><X size={14} /></button>
          <input value={image.alt} onChange={(e) => setImage({ ...image, alt: e.target.value })} placeholder="Texte alternatif (accessibilité)"
            className="w-full mt-1.5 text-xs rounded-lg border border-border bg-background/60 px-2.5 py-1.5 outline-none" />
        </div>
      )}
      <div className="flex items-center gap-2 mt-3">
        <button onClick={() => fileRef.current?.click()} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60 text-muted-foreground"><ImageIcon size={18} /></button>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={pick} />
        <div className="flex gap-1">
          {VIS.map(([v, l, Icon]) => (
            <button key={v} onClick={() => setVis(v)} className={cx('press flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-full border', vis === v ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>
              <Icon size={12} /> {l}
            </button>
          ))}
        </div>
        <button onClick={publish} disabled={busy || (!body.trim() && !image)} className="press ml-auto px-4 py-2 rounded-full font-semibold text-white text-sm disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
          {busy ? <RefreshCw size={16} className="animate-spin" /> : 'Publier'}
        </button>
      </div>
    </div>
  )
}

function PostCard({ p, onDeleted }) {
  const [menu, setMenu] = useState(false)
  const del = async () => { setMenu(false); if (confirm('Supprimer cette publication ?')) { await api(`/net/posts/${p.id}`, { method: 'DELETE' }); onDeleted(p.id) } }
  const VisIcon = (VIS.find((v) => v[0] === p.visibility) || VIS[0])[2]
  return (
    <div className="rounded-2xl border border-border bg-card/60 p-4">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-full grid place-items-center text-white font-semibold" style={{ background: p.author?.avatarColor || '#4353F0' }}>{p.author?.initials}</div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm flex items-center gap-1">{p.author?.name || 'Utilisateur'} {p.author?.verified && <ShieldCheck size={13} className="text-primary" />}</div>
          <div className="text-[11px] text-muted-foreground flex items-center gap-1">{timeAgo(p.createdAt)} · <VisIcon size={10} /> {p.editedAt && '· modifié'}</div>
        </div>
        {p.mine && (
          <div className="relative">
            <button onClick={() => setMenu((m) => !m)} className="press w-8 h-8 rounded-full grid place-items-center text-muted-foreground"><MoreHorizontal size={18} /></button>
            {menu && (
              <div className="absolute right-0 top-9 z-10 rounded-xl border border-border bg-card shadow-lg overflow-hidden">
                <button onClick={del} className="press flex items-center gap-2 px-4 py-2.5 text-sm text-destructive"><Trash2 size={15} /> Supprimer</button>
              </div>
            )}
          </div>
        )}
      </div>
      {p.body && <p className="text-sm mt-3 whitespace-pre-line break-words">{p.body}</p>}
      {p.media?.[0] && <img src={p.media[0].url} alt={p.media[0].alt || ''} loading="lazy" className="rounded-xl mt-3 max-h-96 w-auto border border-border" />}
      <div className="text-[11px] text-muted-foreground mt-3">Réactions & commentaires — bientôt (Couche 3)</div>
    </div>
  )
}
