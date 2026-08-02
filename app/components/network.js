'use client'

// Réseau DIVARC (type Facebook) — Couche 2 : composer + fil (curseur) + suppression.
// Appelle le nouveau contexte social /api/net/* (PostgreSQL). Réactions/commentaires = Couche 3.
import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Image as ImageIcon, Globe, Users, Lock, RefreshCw, Trash2, MoreHorizontal, ShieldCheck, MessageCircle, Share2, Bookmark, Send, CornerDownRight, UserPlus, UserCheck, Check, Clock, UserX, EyeOff, Info, Search, Bell, Flag, Download, ShieldAlert, Leaf } from 'lucide-react'

const REPORT_REASONS = [['spam', 'Spam / publicité'], ['harcelement', 'Harcèlement'], ['haine', 'Discours haineux'], ['violence', 'Violence'], ['nudite', 'Nudité / contenu sexuel'], ['arnaque', 'Arnaque'], ['autre', 'Autre']]
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
  const [tab, setTab] = useState('feed') // feed | friends
  const [profileId, setProfileId] = useState(null)
  const [mode, setMode] = useState('ranked') // ranked | recent
  const [items, setItems] = useState(null)
  const [cursor, setCursor] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [unavailable, setUnavailable] = useState(false)
  const [showPrefs, setShowPrefs] = useState(false)
  const [isMod, setIsMod] = useState(false)
  const [showMod, setShowMod] = useState(false)
  const [calm, setCalm] = useState(false)
  const [caughtUp, setCaughtUp] = useState(false)
  const [toast, setToast] = useState(null)

  useEffect(() => { (async () => { const c = await api('/net/moderation/config'); if (!c.error) setIsMod(!!c.isModerator) })() }, [])

  const load = useCallback(async (cur) => {
    const r = await api(`/net/feed?mode=${mode}${cur ? `&cursor=${encodeURIComponent(cur)}` : ''}`)
    if (r?.error) { setUnavailable(true); setItems([]); return }
    setUnavailable(false)
    setItems((prev) => (cur && prev ? [...prev, ...r.items] : r.items))
    setCursor(r.nextCursor || null)
    setCalm(!!r.calm); setCaughtUp(!!r.caughtUp)
  }, [mode])
  useEffect(() => { setItems(null); load() }, [load])

  const onPublished = (post) => {
    setItems((prev) => [post, ...(prev || [])])
    if (post?.eclatsEarned) { setToast(`+${post.eclatsEarned} ⚡ Éclats — première publication du jour !`); setTimeout(() => setToast(null), 3500) }
  }
  const onDeleted = (id) => setItems((prev) => (prev || []).filter((p) => p.id !== id))

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={onClose} className="press" aria-label="Fermer"><X size={22} /></button>
        <h1 className="font-display text-2xl">Réseau <span className="text-xs align-top text-muted-foreground">bêta</span></h1>
        {!unavailable && (
          <div className="ml-auto flex items-center gap-2">
            {isMod && (
              <button onClick={() => setShowMod(true)} className="press w-9 h-9 rounded-full grid place-items-center bg-primary/10 text-primary" aria-label="Modération"><ShieldAlert size={18} /></button>
            )}
            <button onClick={() => setShowPrefs(true)} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60 text-muted-foreground" aria-label="Réglages"><Bell size={18} /></button>
          </div>
        )}
      </div>

      {!unavailable && (
        <div className="flex gap-1 p-1 mx-4 mt-3 rounded-2xl bg-muted/60">
          {[['feed', 'Fil'], ['friends', 'Amis'], ['espaces', 'Espaces']].map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} className={cx('press flex-1 py-2 rounded-xl text-sm font-medium', tab === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>{label}</button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
        {unavailable ? (
          <div className="text-center py-20 text-muted-foreground">
            <ShieldCheck size={36} className="mx-auto mb-3 opacity-50" />
            <div className="font-medium text-foreground">Réseau en cours d'activation</div>
            <div className="text-sm mt-1">La base PostgreSQL doit être branchée (Railway). Revenez bientôt.</div>
          </div>
        ) : tab === 'friends' ? (
          <FriendsPanel onOpenProfile={setProfileId} />
        ) : tab === 'espaces' ? (
          <EspacesPanel me={me} onOpenProfile={setProfileId} />
        ) : (
          <>
            <StoriesBar me={me} />
            <Composer me={me} onPublished={onPublished} />
            {calm ? (
              <div className="flex items-center gap-2 mb-3 text-xs text-primary bg-primary/5 border border-primary/20 rounded-full px-3 py-1.5">
                <Leaf size={13} /> Fil apaisé activé — chronologique, sans chiffres. <button onClick={() => setShowPrefs(true)} className="underline ml-auto">Régler</button>
              </div>
            ) : (
              <div className="flex items-center gap-2 mb-3 text-xs">
                <span className="text-muted-foreground">Fil :</span>
                {[['ranked', 'Classé'], ['recent', 'Récent']].map(([id, label]) => (
                  <button key={id} onClick={() => setMode(id)} className={cx('press px-3 py-1 rounded-full border', mode === id ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{label}</button>
                ))}
              </div>
            )}
            {items === null ? (
              <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
            ) : items.length === 0 ? (
              caughtUp ? (
                <div className="text-center py-14 text-sm text-muted-foreground">
                  <div className="w-11 h-11 rounded-full bg-primary/10 grid place-items-center mx-auto mb-2"><Check size={20} className="text-primary" /></div>
                  Tu es à jour ✨<div className="text-xs mt-1">Tu as vu toutes les nouveautés. Reviens plus tard, ou passe en « Récent ».</div>
                </div>
              ) : (
                <div className="text-center py-14 text-sm text-muted-foreground">Ton fil est vide. Publie ou suis des gens pour le remplir.</div>
              )
            ) : (
              <div className="space-y-3 pb-4">
                {items.map((p) => <PostCard key={p.id} p={p} onDeleted={onDeleted} onOpenProfile={setProfileId} />)}
                {cursor ? (
                  <button onClick={async () => { setLoadingMore(true); await load(cursor); setLoadingMore(false) }}
                    className="press w-full py-3 rounded-2xl border border-border bg-card/60 text-sm font-medium">
                    {loadingMore ? <RefreshCw size={16} className="animate-spin mx-auto" /> : 'Voir plus'}
                  </button>
                ) : caughtUp && (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    <div className="w-11 h-11 rounded-full bg-primary/10 grid place-items-center mx-auto mb-2"><Check size={20} className="text-primary" /></div>
                    Tu es à jour ✨<div className="text-xs mt-1">Prends une pause si tu veux — le Réseau t'attendra.</div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <AnimatePresence>
        {toast && (
          <motion.div key="toast" className="fixed left-1/2 -translate-x-1/2 bottom-24 z-[90] px-4 py-2.5 rounded-full bg-ink text-white text-sm font-medium shadow-lg"
            initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 20, opacity: 0 }}>{toast}</motion.div>
        )}
        {profileId && <ProfileSheet userId={profileId} meId={me?.id} onClose={() => setProfileId(null)} />}
        {showPrefs && <NotifPrefsSheet onClose={() => setShowPrefs(false)} />}
        {showMod && <ModerationPanel onClose={() => setShowMod(false)} />}
      </AnimatePresence>
    </motion.div>
  )
}

const NOTIF_LABELS = {
  reaction: 'Réactions à mes publications',
  comment: 'Commentaires sur mes publications',
  reply: 'Réponses à mes commentaires',
  friend_accept: 'Demandes d\'ami acceptées',
  group_approved: 'Admission dans un groupe',
  mention: 'Mentions',
}

function NotifPrefsSheet({ onClose }) {
  const [kinds, setKinds] = useState(null)
  const [disabled, setDisabled] = useState([])
  const [saving, setSaving] = useState(false)
  const [wb, setWb] = useState({ calmMode: false, hideCounts: false })
  useEffect(() => {
    (async () => {
      const r = await api('/net/notifications/prefs')
      if (!r.error) { setKinds(r.kinds || Object.keys(NOTIF_LABELS)); setDisabled(r.disabled || []) }
      const w = await api('/net/wellbeing/prefs')
      if (!w.error) setWb({ calmMode: !!w.calmMode, hideCounts: !!w.hideCounts })
    })()
  }, [])
  const toggleWb = async (key) => {
    const next = { ...wb, [key]: !wb[key] }
    setWb(next); setSaving(true)
    await api('/net/wellbeing/prefs', { method: 'PUT', body: JSON.stringify(next) })
    setSaving(false)
  }
  const toggle = async (k) => {
    const next = disabled.includes(k) ? disabled.filter((x) => x !== k) : [...disabled, k]
    setDisabled(next); setSaving(true)
    await api('/net/notifications/prefs', { method: 'PUT', body: JSON.stringify({ disabled: next }) })
    setSaving(false)
  }
  const exportData = async () => {
    const d = await api('/net/me/export')
    if (d.error) return alert(d.error)
    const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'mes-donnees-divarc-reseau.json'; a.click()
    URL.revokeObjectURL(url)
  }
  const eraseData = async () => {
    const t = prompt('Cette action est IRRÉVERSIBLE : elle efface tes publications, commentaires, réactions et relations du Réseau (ton compte DIVARC n\'est pas supprimé).\n\nÉcris SUPPRIMER pour confirmer :')
    if (t !== 'SUPPRIMER') return
    const r = await api('/net/me/erase', { method: 'POST', body: JSON.stringify({ confirm: 'SUPPRIMER' }) })
    if (r.error) return alert(r.error)
    alert(`Effacé : ${r.posts} publication(s), ${r.comments} commentaire(s). Recharge le Réseau.`)
    onClose()
  }
  return (
    <motion.div className="fixed inset-0 z-[80] bg-black/40 flex items-end sm:items-center sm:justify-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div className="w-full sm:max-w-md bg-card rounded-t-3xl sm:rounded-3xl border border-border p-5 pb-safe" initial={{ y: 40 }} animate={{ y: 0 }} exit={{ y: 40 }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-4">
          <Bell size={20} className="text-primary" />
          <h2 className="font-display text-xl flex-1">Notifications</h2>
          {saving && <RefreshCw size={16} className="animate-spin text-muted-foreground" />}
          <button onClick={onClose} className="press" aria-label="Fermer"><X size={20} /></button>
        </div>
        <p className="text-xs text-muted-foreground mb-3">Choisis ce que tu veux recevoir. Les autres continueront d'apparaître dans le fil.</p>
        {kinds === null ? (
          <div className="grid place-items-center py-10"><RefreshCw className="animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="space-y-1">
            {kinds.map((k) => {
              const on = !disabled.includes(k)
              return (
                <button key={k} onClick={() => toggle(k)} className="press w-full flex items-center gap-3 py-3 px-1 text-left">
                  <span className="flex-1 text-sm">{NOTIF_LABELS[k] || k}</span>
                  <span className={cx('w-11 h-6 rounded-full p-0.5 transition-colors', on ? 'bg-primary' : 'bg-muted')}>
                    <span className={cx('block w-5 h-5 rounded-full bg-white transition-transform', on && 'translate-x-5')} />
                  </span>
                </button>
              )
            })}
          </div>
        )}
        {/* Bien-être / fil apaisé (Couche 10) */}
        <div className="mt-5 pt-4 border-t border-border">
          <div className="flex items-center gap-2 text-sm font-medium mb-1"><Leaf size={15} className="text-primary" /> Bien-être</div>
          <p className="text-xs text-muted-foreground mb-2">Un réseau qui te respecte, pas qui te capte.</p>
          {[['calmMode', 'Fil apaisé', 'Chronologique, sans « boost viral », chiffres masqués'],
            ['hideCounts', 'Masquer les compteurs', 'Moins de comparaison sociale (j\'aime & commentaires)']].map(([k, label, desc]) => (
            <button key={k} onClick={() => toggleWb(k)} className="press w-full flex items-center gap-3 py-2.5 text-left">
              <div className="flex-1">
                <div className="text-sm">{label}</div>
                <div className="text-[11px] text-muted-foreground">{desc}</div>
              </div>
              <span className={cx('w-11 h-6 rounded-full p-0.5 transition-colors shrink-0', wb[k] ? 'bg-primary' : 'bg-muted')}>
                <span className={cx('block w-5 h-5 rounded-full bg-white transition-transform', wb[k] && 'translate-x-5')} />
              </span>
            </button>
          ))}
        </div>
        {/* RGPD — Mes données (Couche 9) */}
        <div className="mt-5 pt-4 border-t border-border">
          <div className="text-sm font-medium mb-1">Mes données (RGPD)</div>
          <p className="text-xs text-muted-foreground mb-3">Conforme RGPD · hébergé dans l'UE. Tu contrôles tes données.</p>
          <button onClick={exportData} className="press w-full flex items-center gap-2 py-2.5 px-3 rounded-xl border border-border text-sm mb-2"><Download size={15} /> Exporter mes données (JSON)</button>
          <button onClick={eraseData} className="press w-full flex items-center gap-2 py-2.5 px-3 rounded-xl border border-destructive/40 text-destructive text-sm"><Trash2 size={15} /> Effacer mes données du Réseau</button>
        </div>
      </motion.div>
    </motion.div>
  )
}

function ModerationPanel({ onClose }) {
  const [items, setItems] = useState(null)
  const load = useCallback(async () => {
    const r = await api('/net/moderation/queue')
    if (!r.error) setItems(r.items)
  }, [])
  useEffect(() => { load() }, [load])
  const resolve = async (id, action) => {
    await api(`/net/moderation/reports/${id}/resolve`, { method: 'POST', body: JSON.stringify({ action }) })
    setItems((prev) => (prev || []).filter((x) => x.id !== id))
  }
  const RLABEL = Object.fromEntries(REPORT_REASONS)
  return (
    <motion.div className="fixed inset-0 z-[80] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={onClose} className="press" aria-label="Fermer"><X size={22} /></button>
        <ShieldAlert size={20} className="text-primary" />
        <h1 className="font-display text-xl flex-1">Modération</h1>
        <button onClick={load} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60 text-muted-foreground" aria-label="Rafraîchir"><RefreshCw size={16} /></button>
      </div>
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        {items === null ? (
          <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
        ) : items.length === 0 ? (
          <div className="text-center py-16 text-sm text-muted-foreground">
            <ShieldCheck size={36} className="mx-auto mb-3 opacity-50" />
            Aucun signalement en attente. Tout est propre. ✨
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((r) => (
              <div key={r.id} className="rounded-2xl border border-border bg-card/60 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-destructive/10 text-destructive">{RLABEL[r.reason] || r.reason}</span>
                  <span className="text-[11px] text-muted-foreground">{r.subjectType}</span>
                  <span className="text-[11px] text-muted-foreground ml-auto">{timeAgo(r.createdAt)}</span>
                </div>
                {r.excerpt && <p className="text-sm bg-muted/40 rounded-lg px-3 py-2 mb-2 break-words">« {r.excerpt} »</p>}
                <div className="text-[11px] text-muted-foreground mb-3">
                  {r.author?.name && <>Auteur : <b>{r.author.name}</b> · </>}Signalé par {r.reporter?.name || 'un utilisateur'}
                  {r.details && <div className="mt-1 italic">Détail : {r.details}</div>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => resolve(r.id, 'remove')} className="press flex-1 py-2 rounded-full bg-destructive/10 text-destructive text-sm font-medium">Retirer le contenu</button>
                  <button onClick={() => resolve(r.id, 'warn')} className="press flex-1 py-2 rounded-full border border-border text-sm font-medium">Avertir</button>
                  <button onClick={() => resolve(r.id, 'dismiss')} className="press flex-1 py-2 rounded-full border border-border text-sm font-medium text-muted-foreground">Rejeter</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

function FriendsPanel({ onOpenProfile }) {
  const [reqs, setReqs] = useState(null)
  const [friends, setFriends] = useState(null)
  const [sugg, setSugg] = useState([])
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const load = useCallback(async () => {
    const r = await api('/net/friends/requests'); if (!r.error) setReqs(r)
    const f = await api('/net/friends'); if (!f.error) setFriends(f.items)
    const s = await api('/net/suggestions'); if (!s.error) setSugg(s.items)
  }, [])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (q.trim().length < 2) { setResults(null); return }
    let alive = true
    const t = setTimeout(async () => { const r = await api(`/net/search?q=${encodeURIComponent(q)}`); if (alive && !r.error) setResults(r) }, 350)
    return () => { alive = false; clearTimeout(t) }
  }, [q])
  const respond = async (id, action) => { await api(`/net/friends/${action}/${id}`, { method: 'POST' }); load() }
  const addFriend = async (id) => { await api(`/net/friends/request/${id}`, { method: 'POST' }); setSugg((s) => s.filter((u) => u.id !== id)) }
  if (!reqs) return <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  return (
    <div className="py-4 space-y-5">
      {/* Recherche */}
      <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3">
        <Search size={16} className="text-muted-foreground" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher personnes, publications…"
          className="flex-1 bg-transparent py-2.5 text-sm outline-none" autoCapitalize="none" />
        {q && <button onClick={() => setQ('')} className="press"><X size={15} className="text-muted-foreground" /></button>}
      </div>
      {results && (
        <div className="space-y-3">
          {results.people?.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">Personnes</div>
              <div className="space-y-2">
                {results.people.map((u) => (
                  <button key={u.id} onClick={() => onOpenProfile(u.id)} className="press w-full flex items-center gap-3 p-2.5 rounded-2xl border border-border bg-card/60 text-left">
                    <div className="w-9 h-9 rounded-full grid place-items-center text-white text-sm font-semibold" style={{ background: u.avatarColor || '#4353F0' }}>{u.initials}</div>
                    <div className="flex-1 min-w-0"><div className="text-sm font-medium truncate">{u.name}</div>{u.handle && <div className="text-[11px] text-muted-foreground">@{u.handle}</div>}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {results.posts?.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">Publications</div>
              <div className="space-y-3">{results.posts.map((p) => <PostCard key={p.id} p={p} onDeleted={() => {}} onOpenProfile={onOpenProfile} />)}</div>
            </div>
          )}
          {(!results.people?.length && !results.posts?.length) && <div className="text-sm text-muted-foreground text-center py-6">Aucun résultat.</div>}
        </div>
      )}

      {!results && sugg.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-2">Suggestions</div>
          <div className="flex gap-3 overflow-x-auto no-scrollbar pb-1">
            {sugg.map((u) => (
              <div key={u.id} className="min-w-[130px] rounded-2xl border border-border bg-card/60 p-3 text-center">
                <button onClick={() => onOpenProfile(u.id)} className="w-14 h-14 rounded-full grid place-items-center text-white text-lg font-semibold mx-auto mb-2" style={{ background: u.avatarColor || '#4353F0' }}>{u.initials}</button>
                <div className="text-sm font-medium truncate">{u.name}</div>
                <div className="text-[10px] text-muted-foreground mb-2">{u.reason}</div>
                <button onClick={() => addFriend(u.id)} className="press w-full py-1.5 rounded-full bg-primary/10 text-primary text-xs font-medium flex items-center justify-center gap-1"><UserPlus size={12} /> Ajouter</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {reqs.incoming?.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-2">Demandes reçues ({reqs.incoming.length})</div>
          <div className="space-y-2">
            {reqs.incoming.map((u) => (
              <div key={u.id} className="flex items-center gap-3 p-3 rounded-2xl border border-primary/20 bg-primary/5">
                <button onClick={() => onOpenProfile(u.id)} className="w-10 h-10 rounded-full grid place-items-center text-white font-semibold shrink-0" style={{ background: u.avatarColor || '#4353F0' }}>{u.initials}</button>
                <div className="flex-1 min-w-0 font-medium text-sm truncate">{u.name}</div>
                <button onClick={() => respond(u.id, 'accept')} className="press px-3 py-1.5 rounded-full bg-primary text-white text-xs font-medium">Accepter</button>
                <button onClick={() => respond(u.id, 'decline')} className="press w-8 h-8 rounded-full grid place-items-center bg-muted"><X size={15} /></button>
              </div>
            ))}
          </div>
        </div>
      )}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-2">Mes amis ({friends?.length || 0})</div>
        {!friends || friends.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-8">Aucun ami pour l'instant. Ajoute des gens depuis leur profil.</div>
        ) : (
          <div className="space-y-2">
            {friends.map((u) => (
              <button key={u.id} onClick={() => onOpenProfile(u.id)} className="press w-full flex items-center gap-3 p-3 rounded-2xl border border-border bg-card/60 text-left">
                <div className="w-10 h-10 rounded-full grid place-items-center text-white font-semibold" style={{ background: u.avatarColor || '#4353F0' }}>{u.initials}</div>
                <div className="flex-1 font-medium text-sm">{u.name}</div>
                {u.relationship?.following && <UserCheck size={16} className="text-muted-foreground" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ProfileSheet({ userId, meId, onClose }) {
  const [p, setP] = useState(null)
  const load = useCallback(async () => { const r = await api(`/net/profile/${userId}`); if (!r.error) setP(r) }, [userId])
  useEffect(() => { load() }, [load])
  const act = async (method, path) => { await api(path, { method }); load() }
  const rel = p?.relationship || {}
  const isMe = userId === meId
  return (
    <motion.div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <div className="glass glass-strong p-5 pb-safe rounded-t-[var(--radius)] sm:rounded-[var(--radius)]">
          {!p ? <div className="grid place-items-center py-10"><RefreshCw className="animate-spin text-muted-foreground" /></div> : (
            <>
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 rounded-full grid place-items-center text-white text-xl font-semibold" style={{ background: p.avatarColor || '#4353F0' }}>{p.initials}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-display text-xl flex items-center gap-1">{p.name} {p.verified && <ShieldCheck size={16} className="text-primary" />}</div>
                  {p.handle && <div className="text-sm text-muted-foreground">@{p.handle}</div>}
                </div>
                <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button>
              </div>
              {p.bio && <p className="text-sm text-muted-foreground mb-4">{p.bio}</p>}
              {!isMe && (
                <div className="grid grid-cols-2 gap-2">
                  {rel.friend ? (
                    <button onClick={() => act('DELETE', `/net/friends/${userId}`)} className="press py-3 rounded-2xl border border-border bg-card/60 text-sm font-medium flex items-center justify-center gap-1.5"><UserCheck size={16} /> Amis</button>
                  ) : rel.requestReceived ? (
                    <button onClick={() => act('POST', `/net/friends/accept/${userId}`)} className="press py-3 rounded-2xl text-white text-sm font-semibold flex items-center justify-center gap-1.5" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Check size={16} /> Accepter</button>
                  ) : rel.requestSent ? (
                    <button onClick={() => act('DELETE', `/net/friends/request/${userId}`)} className="press py-3 rounded-2xl border border-border bg-card/60 text-sm font-medium flex items-center justify-center gap-1.5"><Clock size={16} /> Demande envoyée</button>
                  ) : (
                    <button onClick={() => act('POST', `/net/friends/request/${userId}`)} className="press py-3 rounded-2xl text-white text-sm font-semibold flex items-center justify-center gap-1.5" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><UserPlus size={16} /> Ajouter</button>
                  )}
                  {rel.following ? (
                    <button onClick={() => act('DELETE', `/net/follow/${userId}`)} className="press py-3 rounded-2xl border border-border bg-card/60 text-sm font-medium">Suivi ✓</button>
                  ) : (
                    <button onClick={() => act('POST', `/net/follow/${userId}`)} className="press py-3 rounded-2xl border border-border bg-card/60 text-sm font-medium">Suivre</button>
                  )}
                  {rel.blocked ? (
                    <button onClick={() => act('DELETE', `/net/block/${userId}`)} className="press col-span-2 py-2.5 rounded-2xl text-sm text-muted-foreground">Débloquer</button>
                  ) : (
                    <button onClick={() => act('POST', `/net/block/${userId}`)} className="press col-span-2 py-2.5 rounded-2xl text-sm text-destructive flex items-center justify-center gap-1.5"><UserX size={15} /> Bloquer</button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

function Composer({ me, onPublished }) {
  const [body, setBody] = useState('')
  const [media, setMedia] = useState(null)   // { url, alt, kind }
  const [vis, setVis] = useState('public')
  const [busy, setBusy] = useState(false)
  const [upBusy, setUpBusy] = useState(false)
  const fileRef = useRef(null)

  const pick = async (e) => {
    const f = e.target.files?.[0]; e.target.value = ''
    if (!f) return
    const isVideo = (f.type || '').startsWith('video/')
    const cap = isVideo ? 12 : 6.5
    if (f.size > cap * 1024 * 1024) return alert(`Fichier trop lourd (max ~${cap} Mo)`)
    setUpBusy(true)
    const dataUrl = await fileToDataUrl(f)
    const r = await api('/chat/upload', { method: 'POST', body: JSON.stringify({ data: dataUrl }) })
    setUpBusy(false)
    if (r.url) setMedia({ url: r.url, alt: '', kind: isVideo ? 'video' : 'image' })
  }
  const publish = async () => {
    if (!body.trim() && !media) return
    setBusy(true)
    const payload = { body, visibility: vis, media: media ? [{ url: media.url, alt: media.alt || (media.kind === 'video' ? 'vidéo' : 'image'), kind: media.kind }] : [] }
    const r = await api('/net/posts', { method: 'POST', body: JSON.stringify(payload) })
    setBusy(false)
    if (r.error) return alert(r.error)
    onPublished(r); setBody(''); setMedia(null); setVis('public')
  }

  return (
    <div className="rounded-2xl border border-border bg-card/60 p-4 my-4">
      <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={3} placeholder="Quoi de neuf ?"
        className="w-full bg-transparent outline-none resize-none text-sm" />
      {media && (
        <div className="relative mt-2">
          {media.kind === 'video'
            ? <video src={media.url} controls playsInline className="rounded-xl max-h-56 w-auto border border-border" />
            : <img src={media.url} alt="" className="rounded-xl max-h-56 w-auto border border-border" />}
          <button onClick={() => setMedia(null)} className="absolute top-2 right-2 w-7 h-7 rounded-full bg-ink text-white grid place-items-center"><X size={14} /></button>
          <input value={media.alt} onChange={(e) => setMedia({ ...media, alt: e.target.value })} placeholder="Texte alternatif (accessibilité)"
            className="w-full mt-1.5 text-xs rounded-lg border border-border bg-background/60 px-2.5 py-1.5 outline-none" />
        </div>
      )}
      <div className="flex items-center gap-2 mt-3">
        <button onClick={() => fileRef.current?.click()} disabled={upBusy} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60 text-muted-foreground disabled:opacity-40">{upBusy ? <RefreshCw size={16} className="animate-spin" /> : <ImageIcon size={18} />}</button>
        <input ref={fileRef} type="file" accept="image/*,video/*" className="hidden" onChange={pick} />
        <div className="flex gap-1">
          {VIS.map(([v, l, Icon]) => (
            <button key={v} onClick={() => setVis(v)} className={cx('press flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-full border', vis === v ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>
              <Icon size={12} /> {l}
            </button>
          ))}
        </div>
        <button onClick={publish} disabled={busy || (!body.trim() && !media)} className="press ml-auto px-4 py-2 rounded-full font-semibold text-white text-sm disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
          {busy ? <RefreshCw size={16} className="animate-spin" /> : 'Publier'}
        </button>
      </div>
    </div>
  )
}

const RX = { like: '👍', love: '❤️', bravo: '👏', support: '🫶', haha: '😂', wow: '😮', sad: '😢', grr: '😡' }

function PostBody({ p }) {
  return (
    <>
      {p.body && <p className="text-sm mt-3 whitespace-pre-line break-words">{p.body}</p>}
      {p.media?.[0] && (p.media[0].kind === 'video'
        ? <video src={p.media[0].url} controls playsInline preload="metadata" aria-label={p.media[0].alt || 'vidéo'} className="rounded-xl mt-3 max-h-96 w-full border border-border bg-black" />
        : <img src={p.media[0].url} alt={p.media[0].alt || ''} loading="lazy" className="rounded-xl mt-3 max-h-96 w-auto border border-border" />)}
    </>
  )
}

function ReportSheet({ subjectType, subjectId, onClose }) {
  const [reason, setReason] = useState(null)
  const [details, setDetails] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    if (!reason) return
    setBusy(true)
    const r = await api('/net/report', { method: 'POST', body: JSON.stringify({ subjectType, subjectId, reason, details }) })
    setBusy(false)
    if (r.error) return alert(r.error)
    setDone(true)
  }
  return (
    <motion.div className="fixed inset-0 z-[80] bg-black/40 flex items-end sm:items-center sm:justify-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div className="w-full sm:max-w-md bg-card rounded-t-3xl sm:rounded-3xl border border-border p-5 pb-safe" initial={{ y: 40 }} animate={{ y: 0 }} exit={{ y: 40 }} onClick={(e) => e.stopPropagation()}>
        {done ? (
          <div className="text-center py-6">
            <div className="w-12 h-12 rounded-full bg-primary/10 grid place-items-center mx-auto mb-3"><Check size={22} className="text-primary" /></div>
            <div className="font-medium">Merci, c'est signalé.</div>
            <div className="text-sm text-muted-foreground mt-1">Notre équipe va l'examiner. Tu peux aussi masquer ce contenu.</div>
            <button onClick={onClose} className="press mt-4 px-5 py-2.5 rounded-full bg-primary text-white text-sm font-semibold">Fermer</button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 mb-1">
              <Flag size={20} className="text-primary" />
              <h2 className="font-display text-xl flex-1">Signaler</h2>
              <button onClick={onClose} className="press" aria-label="Fermer"><X size={20} /></button>
            </div>
            <p className="text-xs text-muted-foreground mb-3">Pourquoi signales-tu ce contenu ? Un humain de l'équipe examinera.</p>
            <div className="space-y-1">
              {REPORT_REASONS.map(([v, l]) => (
                <button key={v} onClick={() => setReason(v)} className={cx('press w-full flex items-center gap-3 py-2.5 px-3 rounded-xl text-sm text-left border', reason === v ? 'border-primary bg-primary/5' : 'border-transparent')}>
                  <span className={cx('w-4 h-4 rounded-full border-2 shrink-0', reason === v ? 'border-primary bg-primary' : 'border-muted-foreground/40')} />
                  {l}
                </button>
              ))}
            </div>
            <textarea value={details} onChange={(e) => setDetails(e.target.value)} rows={2} placeholder="Détails (optionnel)"
              className="w-full mt-3 text-sm rounded-xl border border-border bg-background/60 px-3 py-2 outline-none resize-none" />
            <button onClick={submit} disabled={!reason || busy} className="press w-full mt-3 py-3 rounded-full font-semibold text-white text-sm disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
              {busy ? <RefreshCw size={16} className="animate-spin mx-auto" /> : 'Envoyer le signalement'}
            </button>
          </>
        )}
      </motion.div>
    </motion.div>
  )
}

function PostCard({ p, onDeleted, onOpenProfile }) {
  const [menu, setMenu] = useState(false)
  const [report, setReport] = useState(false)
  const [rxTotal, setRxTotal] = useState(p.reactions?.total || 0)
  const [byType, setByType] = useState(p.reactions?.byType || {})
  const [mine, setMine] = useState(p.myReaction || null)
  const [palette, setPalette] = useState(false)
  const [bookmarked, setBookmarked] = useState(!!p.bookmarked)
  const [comments, setComments] = useState(null)   // null = fermé
  const [cCount, setCCount] = useState(p.commentCount || 0)
  const VisIcon = (VIS.find((v) => v[0] === p.visibility) || VIS[0])[2]

  const del = async () => { setMenu(false); if (confirm('Supprimer cette publication ?')) { await api(`/net/posts/${p.id}`, { method: 'DELETE' }); onDeleted(p.id) } }
  const hide = async () => { setMenu(false); await api(`/net/posts/${p.id}/hide`, { method: 'POST' }); onDeleted(p.id) }
  const react = async (type) => {
    setPalette(false)
    if (mine === type) {
      const r = await api(`/net/posts/${p.id}/reactions`, { method: 'DELETE' })
      setMine(null); setRxTotal(r.total ?? Math.max(0, rxTotal - 1)); setByType((b) => ({ ...b, [type]: Math.max(0, (b[type] || 1) - 1) }))
    } else {
      const r = await api(`/net/posts/${p.id}/reactions`, { method: 'PUT', body: JSON.stringify({ type }) })
      setByType((b) => { const nb = { ...b }; if (mine) nb[mine] = Math.max(0, (nb[mine] || 1) - 1); nb[type] = (nb[type] || 0) + 1; return nb })
      setMine(type); setRxTotal(r.total ?? rxTotal + (mine ? 0 : 1))
    }
  }
  const share = async () => {
    setMenu(false)
    const text = prompt('Ajouter un mot au partage (optionnel) :') || ''
    const r = await api(`/net/posts/${p.id}/share`, { method: 'POST', body: JSON.stringify({ body: text }) })
    if (r.error) alert(r.error)
  }
  const toggleBk = async () => { const r = await api(`/net/posts/${p.id}/bookmark`, { method: 'PUT' }); if (!r.error) setBookmarked(r.bookmarked) }
  const openComments = async () => {
    if (comments !== null) { setComments(null); return }
    const r = await api(`/net/posts/${p.id}/comments`); setComments(r.items || [])
  }
  const emojis = Object.keys(byType).filter((t) => byType[t] > 0).slice(0, 3)

  return (
    <div className="rounded-2xl border border-border bg-card/60 p-4">
      <div className="flex items-center gap-3">
        <button onClick={() => onOpenProfile?.(p.author?.id)} className="w-11 h-11 rounded-full grid place-items-center text-white font-semibold shrink-0" style={{ background: p.author?.avatarColor || '#4353F0' }}>{p.author?.initials}</button>
        <div className="flex-1 min-w-0">
          <button onClick={() => onOpenProfile?.(p.author?.id)} className="font-medium text-sm flex items-center gap-1 text-left">{p.author?.name || 'Utilisateur'} {p.author?.verified && <ShieldCheck size={13} className="text-primary" />}</button>
          <div className="text-[11px] text-muted-foreground flex items-center gap-1">{timeAgo(p.createdAt)} · <VisIcon size={10} />{p.editedAt ? ' · modifié' : ''}</div>
        </div>
        <div className="relative">
          <button onClick={() => setMenu((m) => !m)} className="press w-8 h-8 rounded-full grid place-items-center text-muted-foreground"><MoreHorizontal size={18} /></button>
          {menu && (
            <div className="absolute right-0 top-9 z-10 rounded-xl border border-border bg-card shadow-lg overflow-hidden min-w-[160px]">
              <button onClick={share} className="press w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm"><Share2 size={15} /> Partager</button>
              {!p.mine && <button onClick={hide} className="press w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm"><EyeOff size={15} /> Voir moins</button>}
              {!p.mine && <button onClick={() => { setMenu(false); setReport(true) }} className="press w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm"><Flag size={15} /> Signaler</button>}
              {p.mine && <button onClick={del} className="press w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm text-destructive"><Trash2 size={15} /> Supprimer</button>}
            </div>
          )}
        </div>
      </div>
      <AnimatePresence>
        {report && <ReportSheet subjectType="post" subjectId={p.id} onClose={() => setReport(false)} />}
      </AnimatePresence>

      {p.reason && (
        <div className="mt-2 inline-flex items-center gap-1 text-[10px] text-muted-foreground bg-muted/40 px-2 py-0.5 rounded-full" title="Transparence : pourquoi ce post t'est montré">
          <Info size={10} /> {p.reason}
        </div>
      )}

      <PostBody p={p} />

      {/* post partagé */}
      {p.sharedPost && (
        <div className="mt-3 rounded-xl border border-border p-3 bg-background/40">
          <div className="text-xs font-medium flex items-center gap-1 text-muted-foreground"><Share2 size={12} /> {p.sharedPost.author?.name}</div>
          <PostBody p={p.sharedPost} />
        </div>
      )}

      {/* compteurs — masqués en mode apaisé (countsHidden) : on garde juste les emojis */}
      {p.countsHidden ? (
        emojis.length > 0 && <div className="text-[11px] text-muted-foreground mt-3">{emojis.map((e) => RX[e]).join('')}</div>
      ) : (rxTotal > 0 || cCount > 0) && (
        <div className="flex items-center justify-between text-[11px] text-muted-foreground mt-3">
          <span>{emojis.map((e) => RX[e]).join('')} {rxTotal > 0 ? rxTotal : ''}</span>
          <span>{cCount > 0 ? `${cCount} commentaire${cCount > 1 ? 's' : ''}` : ''}</span>
        </div>
      )}

      {/* barre d'actions */}
      <div className="grid grid-cols-4 gap-1 mt-2 pt-2 border-t border-border/60 relative">
        <button onClick={() => setPalette((v) => !v)} className={cx('press flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-medium', mine ? 'text-primary' : 'text-muted-foreground')}>
          <span className="text-base">{mine ? RX[mine] : '👍'}</span> J'aime
        </button>
        <button onClick={openComments} className="press flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-medium text-muted-foreground"><MessageCircle size={17} /> Comm.</button>
        <button onClick={share} className="press flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-medium text-muted-foreground"><Share2 size={17} /> Partager</button>
        <button onClick={toggleBk} className={cx('press flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-medium', bookmarked ? 'text-gold' : 'text-muted-foreground')}><Bookmark size={17} fill={bookmarked ? '#E2AA2B' : 'none'} /> Enreg.</button>

        {palette && (
          <div className="absolute -top-11 left-0 flex gap-1 p-1.5 rounded-full glass shadow-lg z-20">
            {Object.entries(RX).map(([t, e]) => (
              <button key={t} onClick={() => react(t)} className="press w-8 h-8 grid place-items-center rounded-full hover:bg-muted text-lg">{e}</button>
            ))}
          </div>
        )}
      </div>

      {comments !== null && <CommentsSection postId={p.id} comments={comments} setComments={setComments} setCCount={setCCount} postOwner={p.mine} />}
    </div>
  )
}

function CommentsSection({ postId, comments, setComments, setCCount, postOwner }) {
  const [text, setText] = useState('')
  const [replyTo, setReplyTo] = useState(null)
  const send = async () => {
    if (!text.trim()) return
    const r = await api(`/net/posts/${postId}/comments`, { method: 'POST', body: JSON.stringify({ body: text, parentId: replyTo?.id || null }) })
    if (r.error) return alert(r.error)
    setComments((c) => [...c, r]); setCCount((n) => n + 1); setText(''); setReplyTo(null)
  }
  const del = async (id) => { await api(`/net/comments/${id}`, { method: 'DELETE' }); setComments((c) => c.map((x) => x.id === id ? { ...x, deleted: true, body: '' } : x)); setCCount((n) => Math.max(0, n - 1)) }
  return (
    <div className="mt-3 pt-3 border-t border-border/60">
      <div className="space-y-2 mb-3">
        {comments.length === 0 && <div className="text-xs text-muted-foreground text-center py-2">Aucun commentaire — sois le premier.</div>}
        {comments.map((c) => (
          <div key={c.id} style={{ marginLeft: Math.min(c.depth, 4) * 16 }} className="flex items-start gap-2">
            {c.depth > 0 && <CornerDownRight size={13} className="text-muted-foreground mt-2 shrink-0" />}
            <div className="w-7 h-7 rounded-full grid place-items-center text-white text-[10px] font-semibold shrink-0" style={{ background: c.author?.avatarColor || '#4353F0' }}>{c.author?.initials}</div>
            <div className="flex-1 min-w-0">
              <div className="rounded-2xl bg-background/60 px-3 py-1.5">
                <div className="text-[11px] font-medium">{c.author?.name}</div>
                {c.deleted ? <div className="text-xs italic text-muted-foreground">Commentaire supprimé</div> : <div className="text-sm break-words">{c.body}</div>}
              </div>
              {!c.deleted && (
                <div className="flex items-center gap-3 mt-0.5 ml-2 text-[10px] text-muted-foreground">
                  <button onClick={() => setReplyTo(c)} className="press">Répondre</button>
                  {(c.mine || postOwner) && <button onClick={() => del(c.id)} className="press text-destructive">Supprimer</button>}
                  <span>{timeAgo(c.createdAt)}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {replyTo && <div className="text-[11px] text-muted-foreground mb-1 flex items-center gap-1">Réponse à {replyTo.author?.name} <button onClick={() => setReplyTo(null)} className="press"><X size={11} /></button></div>}
      <div className="flex items-center gap-2">
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Écrire un commentaire…"
          className="flex-1 rounded-full border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary" />
        <button onClick={send} disabled={!text.trim()} className="press w-9 h-9 rounded-full grid place-items-center text-white disabled:opacity-40 shrink-0" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Send size={16} /></button>
      </div>
    </div>
  )
}

/* ---------------- Stories ---------------- */
function StoriesBar({ me }) {
  const [groups, setGroups] = useState([])
  const [viewer, setViewer] = useState(null)
  const fileRef = useRef(null)
  const load = useCallback(async () => { const r = await api('/net/stories'); if (!r.error) setGroups(r.items) }, [])
  useEffect(() => { load() }, [load])
  const addStory = async (e) => {
    const f = e.target.files?.[0]; e.target.value = ''
    if (!f) return
    if (f.size > 6.5 * 1024 * 1024) return alert('Trop lourd (max ~6 Mo)')
    const dataUrl = await fileToDataUrl(f)
    const up = await api('/chat/upload', { method: 'POST', body: JSON.stringify({ data: dataUrl }) })
    if (up.url) { await api('/net/stories', { method: 'POST', body: JSON.stringify({ mediaUrl: up.url }) }); load() }
  }
  return (
    <div className="flex gap-3 overflow-x-auto no-scrollbar mb-4 pb-1">
      <button onClick={() => fileRef.current?.click()} className="press flex flex-col items-center gap-1 shrink-0">
        <div className="w-16 h-16 rounded-full border-2 border-dashed border-primary grid place-items-center text-primary"><span className="text-2xl">+</span></div>
        <span className="text-[10px] text-muted-foreground">Ta story</span>
      </button>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={addStory} />
      {groups.map((g) => (
        <button key={g.author.id} onClick={() => setViewer({ ...g, index: 0 })} className="press flex flex-col items-center gap-1 shrink-0">
          <div className="w-16 h-16 rounded-full p-0.5" style={{ background: 'linear-gradient(135deg,#EF476F,#9B5DE5,#4353F0)' }}>
            <div className="w-full h-full rounded-full grid place-items-center text-white font-semibold border-2 border-background" style={{ background: g.author.avatarColor || '#4353F0' }}>{g.author.initials}</div>
          </div>
          <span className="text-[10px] truncate max-w-[64px]">{g.mine ? 'Toi' : (g.author.name || '').split(' ')[0]}</span>
        </button>
      ))}
      <AnimatePresence>{viewer && <StoryViewer group={viewer} onClose={() => setViewer(null)} />}</AnimatePresence>
    </div>
  )
}

function StoryViewer({ group, onClose }) {
  const [i, setI] = useState(group.index || 0)
  const story = group.items[i]
  useEffect(() => { if (story) api(`/net/stories/${story.id}/view`, { method: 'POST' }) }, [story])
  const next = () => { if (i + 1 < group.items.length) setI(i + 1); else onClose() }
  const prev = () => { if (i > 0) setI(i - 1) }
  if (!story) return null
  return (
    <motion.div className="fixed inset-0 z-[85] bg-ink flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex gap-1 p-2 pt-safe">
        {group.items.map((_, k) => <div key={k} className={cx('flex-1 h-0.5 rounded-full', k <= i ? 'bg-white' : 'bg-white/30')} />)}
      </div>
      <div className="flex items-center gap-2 px-3 pb-2 text-white">
        <div className="w-8 h-8 rounded-full grid place-items-center text-xs font-semibold" style={{ background: group.author.avatarColor || '#4353F0' }}>{group.author.initials}</div>
        <span className="text-sm font-medium flex-1">{group.author.name}</span>
        <button onClick={onClose} className="press"><X size={22} /></button>
      </div>
      <div className="flex-1 relative grid place-items-center">
        <img src={story.mediaUrl} alt="" className="max-h-full max-w-full object-contain" />
        {story.caption && <div className="absolute bottom-10 inset-x-0 text-center text-white px-6 text-sm drop-shadow">{story.caption}</div>}
        <button onClick={prev} className="absolute left-0 top-0 h-full w-1/3" aria-label="Précédent" />
        <button onClick={next} className="absolute right-0 top-0 h-full w-2/3" aria-label="Suivant" />
      </div>
    </motion.div>
  )
}

/* ---------------- Groupes ---------------- */
function GroupsPanel({ me, onOpenProfile }) {
  const [data, setData] = useState(null)
  const [active, setActive] = useState(null)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [privacy, setPrivacy] = useState('public')
  const load = useCallback(async () => { const r = await api('/net/groups'); if (!r.error) setData(r) }, [])
  useEffect(() => { load() }, [load])
  const create = async () => {
    if (!name.trim()) return
    const r = await api('/net/groups', { method: 'POST', body: JSON.stringify({ name, privacy }) })
    if (!r.error) { setCreating(false); setName(''); load() }
  }
  if (active) return <GroupView me={me} groupId={active} onBack={() => { setActive(null); load() }} onOpenProfile={onOpenProfile} />
  if (!data) return <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  return (
    <div className="py-4 space-y-5">
      <button onClick={() => setCreating((v) => !v)} className="press w-full py-3 rounded-2xl text-white font-semibold text-sm" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>+ Créer un groupe</button>
      {creating && (
        <div className="rounded-2xl border border-border bg-card/60 p-4 space-y-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nom du groupe" className="w-full rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none" />
          <div className="flex gap-2">
            {[['public', 'Public'], ['private', 'Privé'], ['secret', 'Secret']].map(([v, l]) => (
              <button key={v} onClick={() => setPrivacy(v)} className={cx('press flex-1 py-2 rounded-xl text-xs font-medium border', privacy === v ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border')}>{l}</button>
            ))}
          </div>
          <button onClick={create} className="press w-full py-2.5 rounded-xl bg-primary text-white text-sm font-semibold">Créer</button>
        </div>
      )}
      <GroupList title="Mes groupes" groups={data.mine} empty="Tu n'es dans aucun groupe." onOpen={setActive} />
      <GroupList title="À découvrir" groups={data.discover} empty="Aucun groupe public à découvrir." onOpen={setActive} />
    </div>
  )
}

function GroupList({ title, groups, empty, onOpen }) {
  return (
    <div>
      <div className="text-xs font-medium text-muted-foreground mb-2">{title}</div>
      {!groups?.length ? <div className="text-sm text-muted-foreground text-center py-4">{empty}</div> : (
        <div className="space-y-2">
          {groups.map((g) => (
            <button key={g.id} onClick={() => onOpen(g.id)} className="press w-full flex items-center gap-3 p-3 rounded-2xl border border-border bg-card/60 text-left">
              <div className="w-11 h-11 rounded-2xl grid place-items-center text-white font-semibold" style={{ background: g.avatarColor || '#4353F0' }}><Users size={20} /></div>
              <div className="flex-1 min-w-0"><div className="font-medium text-sm truncate">{g.name}</div><div className="text-[11px] text-muted-foreground">{g.memberCount} membre{g.memberCount > 1 ? 's' : ''} · {g.privacy}</div></div>
              {g.myRole && <UserCheck size={16} className="text-muted-foreground" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function GroupView({ me, groupId, onBack, onOpenProfile }) {
  const [g, setG] = useState(null)
  const [feed, setFeed] = useState(null)
  const [body, setBody] = useState('')
  const load = useCallback(async () => {
    const d = await api(`/net/groups/${groupId}`); if (!d.error) setG(d)
    const f = await api(`/net/groups/${groupId}/feed`); setFeed(f.error ? [] : f.items)
  }, [groupId])
  useEffect(() => { load() }, [load])
  const join = async () => { await api(`/net/groups/${groupId}/join`, { method: 'POST' }); load() }
  const leave = async () => { await api(`/net/groups/${groupId}/leave`, { method: 'POST' }); load() }
  const post = async () => { if (!body.trim()) return; const r = await api(`/net/groups/${groupId}/posts`, { method: 'POST', body: JSON.stringify({ body }) }); if (!r.error) { setBody(''); load() } }
  if (!g) return <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  const isMember = g.myStatus === 'active'
  return (
    <div className="py-4">
      <button onClick={onBack} className="press text-sm text-muted-foreground mb-3">‹ Retour</button>
      <div className="rounded-2xl p-5 text-white mb-4" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
        <div className="font-display text-2xl">{g.name}</div>
        <div className="text-sm text-white/80">{g.memberCount} membre{g.memberCount > 1 ? 's' : ''} · {g.privacy}</div>
        {g.description && <p className="text-sm text-white/90 mt-2">{g.description}</p>}
        <div className="mt-3">
          {isMember ? <button onClick={leave} className="press px-4 py-1.5 rounded-full bg-white/15 text-sm font-medium">Quitter</button>
            : g.myStatus === 'pending' ? <span className="px-4 py-1.5 rounded-full bg-white/15 text-sm">Demande envoyée</span>
            : <button onClick={join} className="press px-4 py-1.5 rounded-full bg-white text-primary text-sm font-semibold">Rejoindre</button>}
        </div>
      </div>
      {isMember && (
        <div className="rounded-2xl border border-border bg-card/60 p-3 mb-4 flex items-center gap-2">
          <input value={body} onChange={(e) => setBody(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && post()} placeholder="Publier dans le groupe…" className="flex-1 rounded-full border border-border bg-background/60 px-3 py-2 text-sm outline-none" />
          <button onClick={post} disabled={!body.trim()} className="press w-9 h-9 rounded-full grid place-items-center text-white disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><Send size={16} /></button>
        </div>
      )}
      {feed === null ? <div className="grid place-items-center py-10"><RefreshCw className="animate-spin text-muted-foreground" /></div>
        : feed.length === 0 ? <div className="text-sm text-muted-foreground text-center py-8">{isMember ? 'Aucune publication. Sois le premier !' : 'Rejoins le groupe pour voir les publications.'}</div>
        : <div className="space-y-3">{feed.map((p) => <PostCard key={p.id} p={p} onDeleted={() => load()} onOpenProfile={onOpenProfile} />)}</div>}
    </div>
  )
}

/* ---------------- Espaces (sous-nav) ---------------- */
function EspacesPanel({ me, onOpenProfile }) {
  const [sub, setSub] = useState('groups')
  return (
    <div className="py-3">
      <div className="flex gap-1 p-1 rounded-2xl bg-muted/60 mb-2">
        {[['groups', 'Groupes'], ['pages', 'Pages'], ['events', 'Événements']].map(([id, label]) => (
          <button key={id} onClick={() => setSub(id)} className={cx('press flex-1 py-1.5 rounded-xl text-xs font-medium', sub === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>{label}</button>
        ))}
      </div>
      {sub === 'groups' && <GroupsPanel me={me} onOpenProfile={onOpenProfile} />}
      {sub === 'pages' && <PagesPanel me={me} onOpenProfile={onOpenProfile} />}
      {sub === 'events' && <EventsPanel me={me} onOpenProfile={onOpenProfile} />}
    </div>
  )
}

/* ---------------- Pages ---------------- */
function PagesPanel({ me, onOpenProfile }) {
  const [data, setData] = useState(null)
  const [active, setActive] = useState(null)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const load = useCallback(async () => { const r = await api('/net/pages'); if (!r.error) setData(r) }, [])
  useEffect(() => { load() }, [load])
  const create = async () => { if (!name.trim()) return; const r = await api('/net/pages', { method: 'POST', body: JSON.stringify({ name }) }); if (!r.error) { setName(''); setCreating(false); load() } }
  if (active) return <PageView me={me} pageId={active} onBack={() => { setActive(null); load() }} onOpenProfile={onOpenProfile} />
  if (!data) return <div className="grid place-items-center py-12"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  return (
    <div className="space-y-4">
      <button onClick={() => setCreating((v) => !v)} className="press w-full py-3 rounded-2xl text-white font-semibold text-sm" style={{ background: 'linear-gradient(135deg,#9B5DE5,#4353F0)' }}>+ Créer une page</button>
      {creating && (
        <div className="rounded-2xl border border-border bg-card/60 p-4 space-y-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nom de la page" className="w-full rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none" />
          <button onClick={create} className="press w-full py-2.5 rounded-xl bg-primary text-white text-sm font-semibold">Créer</button>
        </div>
      )}
      <PageList title="Mes pages" pages={data.mine} empty="Tu ne gères aucune page." onOpen={setActive} />
      <PageList title="À découvrir" pages={data.discover} empty="Aucune page à découvrir." onOpen={setActive} />
    </div>
  )
}

function PageList({ title, pages, empty, onOpen }) {
  return (
    <div>
      <div className="text-xs font-medium text-muted-foreground mb-2">{title}</div>
      {!pages?.length ? <div className="text-sm text-muted-foreground text-center py-3">{empty}</div> : (
        <div className="space-y-2">{pages.map((p) => (
          <button key={p.id} onClick={() => onOpen(p.id)} className="press w-full flex items-center gap-3 p-3 rounded-2xl border border-border bg-card/60 text-left">
            <div className="w-11 h-11 rounded-full grid place-items-center text-white font-semibold" style={{ background: p.avatarColor || '#9B5DE5' }}>{(p.name || 'P').slice(0, 2).toUpperCase()}</div>
            <div className="flex-1 min-w-0"><div className="font-medium text-sm truncate flex items-center gap-1">{p.name}{p.verified && <ShieldCheck size={12} className="text-primary" />}</div><div className="text-[11px] text-muted-foreground">{p.followerCount} abonné{p.followerCount > 1 ? 's' : ''}{p.category ? ` · ${p.category}` : ''}</div></div>
            {p.following && <Check size={16} className="text-primary" />}
          </button>
        ))}</div>
      )}
    </div>
  )
}

function PageView({ me, pageId, onBack, onOpenProfile }) {
  const [p, setP] = useState(null)
  const [feed, setFeed] = useState(null)
  const [body, setBody] = useState('')
  const load = useCallback(async () => {
    const d = await api(`/net/pages/${pageId}`); if (!d.error) setP(d)
    const f = await api(`/net/pages/${pageId}/feed`); setFeed(f.error ? [] : f.items)
  }, [pageId])
  useEffect(() => { load() }, [load])
  const toggleFollow = async () => { await api(`/net/pages/${pageId}/follow`, { method: p?.following ? 'DELETE' : 'POST' }); load() }
  const publish = async () => { if (!body.trim()) return; const r = await api(`/net/pages/${pageId}/posts`, { method: 'POST', body: JSON.stringify({ body }) }); if (!r.error) { setBody(''); load() } }
  if (!p) return <div className="grid place-items-center py-12"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  const canPublish = p.myRole === 'admin' || p.myRole === 'editor'
  return (
    <div>
      <button onClick={onBack} className="press text-sm text-muted-foreground mb-3">‹ Retour</button>
      <div className="rounded-2xl p-5 text-white mb-4" style={{ background: 'linear-gradient(135deg,#9B5DE5,#4353F0)' }}>
        <div className="font-display text-2xl flex items-center gap-1">{p.name}{p.verified && <ShieldCheck size={16} />}</div>
        <div className="text-sm text-white/80">{p.followerCount} abonné{p.followerCount > 1 ? 's' : ''}{p.category ? ` · ${p.category}` : ''}</div>
        {p.bio && <p className="text-sm text-white/90 mt-2">{p.bio}</p>}
        {!canPublish && <button onClick={toggleFollow} className="press mt-3 px-4 py-1.5 rounded-full bg-white text-primary text-sm font-semibold">{p.following ? 'Abonné ✓' : "S'abonner"}</button>}
      </div>
      {canPublish && (
        <div className="rounded-2xl border border-border bg-card/60 p-3 mb-4 flex items-center gap-2">
          <input value={body} onChange={(e) => setBody(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && publish()} placeholder="Publier au nom de la page…" className="flex-1 rounded-full border border-border bg-background/60 px-3 py-2 text-sm outline-none" />
          <button onClick={publish} disabled={!body.trim()} className="press w-9 h-9 rounded-full grid place-items-center text-white disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#9B5DE5,#4353F0)' }}><Send size={16} /></button>
        </div>
      )}
      {feed === null ? <div className="grid place-items-center py-8"><RefreshCw className="animate-spin text-muted-foreground" /></div>
        : feed.length === 0 ? <div className="text-sm text-muted-foreground text-center py-6">Aucune publication.</div>
        : <div className="space-y-3">{feed.map((x) => <PostCard key={x.id} p={x} onDeleted={() => load()} onOpenProfile={onOpenProfile} />)}</div>}
    </div>
  )
}

/* ---------------- Événements ---------------- */
function EventsPanel({ me }) {
  const [data, setData] = useState(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ title: '', startsAt: '', location: '' })
  const load = useCallback(async () => { const r = await api('/net/events'); if (!r.error) setData(r) }, [])
  useEffect(() => { load() }, [load])
  const create = async () => {
    if (!form.title.trim() || !form.startsAt) return
    const r = await api('/net/events', { method: 'POST', body: JSON.stringify({ ...form, startsAt: new Date(form.startsAt).toISOString() }) })
    if (!r.error) { setForm({ title: '', startsAt: '', location: '' }); setCreating(false); load() }
  }
  const rsvp = async (id, status) => { await api(`/net/events/${id}/rsvp`, { method: 'POST', body: JSON.stringify({ status }) }); load() }
  if (!data) return <div className="grid place-items-center py-12"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  const card = (e) => (
    <div key={e.id} className="rounded-2xl border border-border bg-card/60 p-4">
      <div className="font-medium text-sm">{e.title}</div>
      <div className="text-[11px] text-muted-foreground mb-1">{new Date(e.startsAt).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })}{e.location ? ` · ${e.location}` : ''}{e.online ? ' · en ligne' : ''}</div>
      <div className="text-[11px] text-muted-foreground mb-2">{e.going} participant{e.going > 1 ? 's' : ''} · {e.interested} intéressé{e.interested > 1 ? 's' : ''}</div>
      <div className="flex gap-2">
        {[['going', 'Je participe'], ['interested', 'Intéressé']].map(([s, l]) => (
          <button key={s} onClick={() => rsvp(e.id, e.myRsvp === s ? 'none' : s)} className={cx('press flex-1 py-1.5 rounded-full text-xs font-medium border', e.myRsvp === s ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border')}>{l}</button>
        ))}
      </div>
    </div>
  )
  return (
    <div className="space-y-4">
      <button onClick={() => setCreating((v) => !v)} className="press w-full py-3 rounded-2xl text-white font-semibold text-sm" style={{ background: 'linear-gradient(135deg,#3FB68B,#4353F0)' }}>+ Créer un événement</button>
      {creating && (
        <div className="rounded-2xl border border-border bg-card/60 p-4 space-y-2">
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Titre" className="w-full rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none" />
          <input type="datetime-local" value={form.startsAt} onChange={(e) => setForm({ ...form, startsAt: e.target.value })} className="w-full rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none" />
          <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Lieu (optionnel)" className="w-full rounded-xl border border-border bg-background/60 px-3 py-2.5 text-sm outline-none" />
          <button onClick={create} className="press w-full py-2.5 rounded-xl bg-primary text-white text-sm font-semibold">Créer</button>
        </div>
      )}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-2">Mes événements</div>
        {!data.mine?.length ? <div className="text-sm text-muted-foreground text-center py-3">Aucun événement.</div> : <div className="space-y-3">{data.mine.map(card)}</div>}
      </div>
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-2">À venir</div>
        {!data.upcoming?.length ? <div className="text-sm text-muted-foreground text-center py-3">Rien à l'horizon.</div> : <div className="space-y-3">{data.upcoming.map(card)}</div>}
      </div>
    </div>
  )
}
