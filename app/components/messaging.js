'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { onRealtime, sendRealtime, isOnline } from '@/lib/realtime'
import Discovery from './discovery'
import { startCall } from './call'
import {
  Plus, Search, ArrowLeft, Send as SendIcon, X, Lock, BadgeCheck, Users, Hash,
  Smile, Flame, Check, Sparkles, Globe, MessageCircle, UserPlus, Crown, Paperclip, RefreshCw,
  Phone, Video
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const Glass = ({ className, strong, children, ...p }) => (
  <div className={cx('glass', strong && 'glass-strong', className)} {...p}>{children}</div>
)
const Avatar = ({ c, size = 44, ring }) => (
  <div className="grid place-items-center rounded-full text-white font-semibold shrink-0"
    style={{ width: size, height: size, background: c?.avatarColor || c?.color || '#4353F0', fontSize: size * 0.36, boxShadow: ring ? `0 0 0 3px ${ring}` : 'none' }}>
    {c?.initials}
  </div>
)
const timeShort = (d) => {
  if (!d) return ''
  const diff = (Date.now() - new Date(d).getTime()) / 60000
  if (diff < 1) return 'maintenant'
  if (diff < 60) return `${Math.floor(diff)} min`
  if (diff < 1440) return `${Math.floor(diff / 60)} h`
  return `${Math.floor(diff / 1440)} j`
}
const LEVEL_COLORS = ['#8BA0B4', '#6E7BF5', '#E2AA2B', '#F97C4E', '#F15BB5']
const REACTIONS = ['❤️', '🔥', '😂', '👍', '😮', '🙏']

/* ---------- Living flame (unique) ---------- */
function LivingFlame({ streak, size = 20 }) {
  if (!streak) return null
  const scale = Math.min(1.6, 1 + streak * 0.03)
  return (
    <span className="inline-flex items-center gap-0.5 font-grotesk" title={`${streak} jours de flamme`}>
      <motion.span style={{ display: 'inline-block', fontSize: size }}
        animate={{ scale: [scale, scale * 1.12, scale], rotate: [-4, 4, -4] }}
        transition={{ duration: 0.9, repeat: Infinity, ease: 'easeInOut' }}>🔥</motion.span>
      <span className="text-[11px] font-bold" style={{ color: '#F97C4E' }}>{streak}</span>
    </span>
  )
}

/* ---------- Friendship progression panel (unique) ---------- */
function FriendshipPanel({ f, levelUp }) {
  if (!f) return null
  const color = LEVEL_COLORS[f.level] || '#6E7BF5'
  return (
    <div className="px-4 py-3 border-b border-border/60 relative overflow-hidden">
      {levelUp && (
        <motion.div className="absolute inset-0 pointer-events-none"
          initial={{ opacity: 0.9 }} animate={{ opacity: 0 }} transition={{ duration: 1.2 }}
          style={{ background: `radial-gradient(circle at 50% 0%, ${color}55, transparent 70%)` }} />
      )}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{f.emoji}</span>
          <span className="text-sm font-semibold" style={{ color }}>{f.name}</span>
          {f.streak > 0 && <LivingFlame streak={f.streak} size={16} />}
        </div>
        <span className="font-grotesk text-[11px] text-muted-foreground">{f.xp} XP</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden relative">
        <motion.div className="h-full rounded-full relative overflow-hidden"
          style={{ background: `linear-gradient(90deg, ${color}, ${color}cc)` }}
          initial={{ width: 0 }} animate={{ width: `${f.pct}%` }} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}>
          <motion.div className="absolute inset-y-0 w-1/3"
            style={{ background: 'linear-gradient(90deg,transparent,rgba(255,255,255,.6),transparent)' }}
            animate={{ x: ['-100%', '400%'] }} transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }} />
        </motion.div>
      </div>
      {f.next && <div className="text-[10px] text-muted-foreground mt-1">Prochain palier : {f.next.name} · {f.next.at - f.xp} XP restants</div>}
    </div>
  )
}

/* ---------- Message bubble with physical reactions ---------- */
function Bubble({ m, me, onReact, isGroup }) {
  const mine = m.senderId === me?.id
  const [showReacts, setShowReacts] = useState(false)
  return (
    <div className={cx('flex flex-col', mine ? 'items-end' : 'items-start')}>
      {isGroup && !mine && <span className="text-[10px] text-muted-foreground ml-3 mb-0.5">{m.senderName}</span>}
      <div className={cx('group relative flex items-end gap-1', mine && 'flex-row-reverse')}>
        <div onDoubleClick={() => onReact(m.id, '❤️')} className={cx('max-w-[78%] flex flex-col gap-1', mine ? 'items-end' : 'items-start')}>
          {m.mediaUrl && m.mediaType === 'image' && (
            <a href={m.mediaUrl} target="_blank" rel="noreferrer" className="block">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={m.mediaUrl} alt="Photo" loading="lazy" className="rounded-2xl max-h-72 w-auto object-cover border border-border" />
            </a>
          )}
          {m.mediaUrl && m.mediaType === 'video' && (
            <video src={m.mediaUrl} controls playsInline className="rounded-2xl max-h-72 w-auto border border-border bg-black" />
          )}
          {m.mediaUrl && m.mediaType === 'audio' && (
            <audio src={m.mediaUrl} controls className="w-56 max-w-full" />
          )}
          {m.text && (
            <div onClick={() => setShowReacts((s) => !s)}
              className={cx('px-4 py-2.5 rounded-2xl text-sm cursor-pointer select-none break-words',
                mine ? 'bg-primary text-white rounded-br-md' : 'bg-card border border-border rounded-bl-md')}>
              {m.text}
            </div>
          )}
        </div>
        <button onClick={() => setShowReacts((s) => !s)} aria-label="Réagir"
          className="opacity-0 group-hover:opacity-100 transition-opacity w-7 h-7 grid place-items-center rounded-full text-muted-foreground">
          <Smile size={15} />
        </button>
      </div>

      {/* reaction chips */}
      {m.reactions?.length > 0 && (
        <div className={cx('flex gap-1 mt-1', mine ? 'mr-1' : 'ml-1')}>
          {Object.entries(m.reactions.reduce((a, r) => ((a[r.emoji] = (a[r.emoji] || 0) + 1), a), {})).map(([e, n]) => (
            <motion.span key={e} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 500, damping: 18 }}
              className="text-xs bg-card border border-border rounded-full px-1.5 py-0.5">{e} {n > 1 ? n : ''}</motion.span>
          ))}
        </div>
      )}

      <AnimatePresence>
        {showReacts && (
          <motion.div initial={{ opacity: 0, y: 6, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
            className={cx('flex gap-1 mt-1 p-1 rounded-full glass', mine ? 'self-end' : 'self-start')}>
            {REACTIONS.map((e) => (
              <button key={e} onClick={() => { onReact(m.id, e); setShowReacts(false) }}
                className="w-8 h-8 grid place-items-center rounded-full hover:bg-muted press text-lg">{e}</button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ============================= MAIN ============================= */
export default function Messaging({ me, openConvId, onConsumed }) {
  const [tab, setTab] = useState('dm') // dm | communities
  const [convos, setConvos] = useState([])
  const [communities, setCommunities] = useState([])
  const [active, setActive] = useState(null) // conversation id
  const [detail, setDetail] = useState(null) // {conversation, messages}
  const [input, setInput] = useState('')
  const [newOpen, setNewOpen] = useState(false)
  const [levelUp, setLevelUp] = useState(false)
  const prevLevel = useRef(null)
  const scrollRef = useRef()
  const [sending, setSending] = useState(false)
  const [pendingMedia, setPendingMedia] = useState(null) // { kind, dataUrl, preview, name }
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)
  const activeRef = useRef(null)
  useEffect(() => { activeRef.current = active }, [active])
  const [, setPresenceTick] = useState(0) // force le re-rendu quand la présence change
  const [typingConvo, setTypingConvo] = useState(null) // conv où "l'autre" écrit
  const typingTimer = useRef(null)
  const lastTypingSent = useRef(0)

  const loadConvos = useCallback(async () => {
    const c = await api('/conversations'); if (Array.isArray(c)) setConvos(c)
  }, [])
  const loadCommunities = useCallback(async () => {
    const c = await api('/communities'); if (Array.isArray(c)) setCommunities(c)
  }, [])
  const loadDetail = useCallback(async (id) => {
    const d = await api(`/conversations/${id}/messages`)
    if (!d.error) {
      setDetail(d)
      const f = d.conversation?.friendship
      if (f) {
        if (prevLevel.current !== null && f.level > prevLevel.current) { setLevelUp(true); setTimeout(() => setLevelUp(false), 1400) }
        prevLevel.current = f.level
      }
    }
  }, [])

  useEffect(() => { loadConvos(); loadCommunities() }, [loadConvos, loadCommunities])
  // Temps réel : messages instantanés, présence, "en train d'écrire"
  useEffect(() => {
    const offMsg = onRealtime('message', (m) => {
      loadConvos()
      if (m.conversationId === activeRef.current) { loadDetail(activeRef.current); setTypingConvo(null) }
    })
    const offReact = onRealtime('reaction', (m) => {
      if (m.conversationId === activeRef.current) loadDetail(activeRef.current)
    })
    const offPres = onRealtime('presence', () => setPresenceTick((v) => v + 1))
    const offPresState = onRealtime('presence_state', () => setPresenceTick((v) => v + 1))
    const offTyping = onRealtime('typing', (m) => {
      if (m.conversationId === activeRef.current) {
        setTypingConvo(m.conversationId)
        if (typingTimer.current) clearTimeout(typingTimer.current)
        typingTimer.current = setTimeout(() => setTypingConvo(null), 3000)
      }
    })
    return () => { offMsg(); offReact(); offPres(); offPresState(); offTyping() }
  }, [loadConvos, loadDetail])
  // Fallback lent si le WebSocket est indisponible
  useEffect(() => { const t = setInterval(loadConvos, 15000); return () => clearInterval(t) }, [loadConvos])
  useEffect(() => {
    if (!active) return
    loadDetail(active)
    const t = setInterval(() => loadDetail(active), 10000)
    return () => clearInterval(t)
  }, [active, loadDetail])
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [detail?.messages?.length])

  const openConv = (id) => { prevLevel.current = null; setActive(id) }

  // Ouverture d'une conversation demandée de l'extérieur (clic sur une notification)
  useEffect(() => {
    if (!openConvId) return
    setTab('dm'); openConv(openConvId); loadConvos()
    onConsumed?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openConvId])

  // Sélection d'une photo/vidéo/audio -> aperçu (converti en data-URL, uploadé à l'envoi)
  const onPickFile = (e) => {
    const file = e.target.files?.[0]
    e.target.value = '' // permet de re-choisir le même fichier
    if (!file) return
    if (file.size > 6.5 * 1024 * 1024) { alert('Fichier trop lourd (max ~6 Mo).'); return }
    const kind = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio'
    const reader = new FileReader()
    reader.onload = () => setPendingMedia({ kind, dataUrl: reader.result, preview: reader.result, name: file.name })
    reader.readAsDataURL(file)
  }

  const send = async () => {
    const text = input.trim()
    if ((!text && !pendingMedia) || sending) return
    setSending(true)
    let media = null
    // 1) upload du média s'il y en a un
    if (pendingMedia) {
      setUploading(true)
      const up = await api('/chat/upload', { method: 'POST', body: JSON.stringify({ data: pendingMedia.dataUrl }) })
      setUploading(false)
      if (up.error) { alert(up.error); setSending(false); return }
      media = { mediaUrl: up.url, mediaType: up.kind }
    }
    const payload = { text, ...(media || {}), kind: media ? media.mediaType : 'text' }
    setInput(''); setPendingMedia(null)
    // optimistic
    setDetail((d) => d ? { ...d, messages: [...d.messages, { id: 'tmp' + Date.now(), senderId: me.id, senderName: me.name, text, mediaUrl: media?.mediaUrl, mediaType: media?.mediaType, reactions: [], createdAt: new Date() }] } : d)
    const r = await api(`/conversations/${active}/messages`, { method: 'POST', body: JSON.stringify(payload) })
    if (r.friendship) {
      if (prevLevel.current !== null && r.friendship.level > prevLevel.current) { setLevelUp(true); setTimeout(() => setLevelUp(false), 1400) }
      prevLevel.current = r.friendship.level
    }
    setSending(false)
    loadDetail(active); loadConvos()
  }

  const react = async (mid, emoji) => {
    setDetail((d) => d ? { ...d, messages: d.messages.map((m) => m.id === mid ? { ...m, reactions: [...(m.reactions || []).filter((r) => r.userId !== me.id), { userId: me.id, emoji }] } : m) } : d)
    await api(`/messages/${mid}/react`, { method: 'POST', body: JSON.stringify({ emoji }) })
  }

  const conv = detail?.conversation
  const isGroup = conv && conv.type !== 'dm'

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-6xl px-3 sm:px-4 pt-5 pb-28 grid md:grid-cols-[340px_1fr] gap-4">
        {/* ============ LEFT: list ============ */}
        <div className={cx(active && 'hidden md:block')}>
          <div className="flex items-center justify-between mb-4">
            <h1 className="font-display text-3xl">Messages</h1>
            <button onClick={() => setNewOpen(true)} aria-label="Nouvelle discussion"
              className="press w-10 h-10 rounded-full grid place-items-center text-white shadow-lg" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
              <Plus size={20} />
            </button>
          </div>

          <div className="flex gap-2 p-1 rounded-2xl bg-muted/60 mb-4">
            {[['dm', 'Discussions', MessageCircle], ['communities', 'Communautés', Globe]].map(([id, label, Icon]) => (
              <button key={id} onClick={() => setTab(id)}
                className={cx('press flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-1.5', tab === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>
                <Icon size={15} /> {label}
              </button>
            ))}
          </div>

          {tab === 'dm' ? (
            <Glass className="p-2 space-y-1 max-h-[calc(100dvh-220px)] overflow-y-auto no-scrollbar">
              {convos.length === 0 && <Empty text="Aucune discussion. Touche + pour commencer." />}
              {convos.map((c) => (
                <button key={c.id} onClick={() => openConv(c.id)}
                  className={cx('press w-full flex items-center gap-3 p-2.5 rounded-2xl text-left', active === c.id && 'bg-primary/10')}>
                  <div className="relative">
                    <Avatar c={c.type === 'dm' ? c.other : { initials: c.title?.[0] || '#', avatarColor: c.avatarColor }} size={48} />
                    {c.type !== 'dm' && <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-card border border-border grid place-items-center"><Users size={11} /></span>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-sm truncate">{c.title || 'Groupe'}</span>
                      {c.other?.verified && <BadgeCheck size={13} className="text-primary shrink-0" />}
                      {c.friendship?.streak > 0 && <LivingFlame streak={c.friendship.streak} size={13} />}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{c.lastText || 'Nouvelle conversation'}</div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-[10px] text-muted-foreground">{timeShort(c.lastMessageAt)}</div>
                    {c.unread > 0 && <div className="mt-1 inline-grid place-items-center min-w-[20px] h-5 px-1 rounded-full bg-primary text-white text-[10px]">{c.unread}</div>}
                    {c.friendship?.level >= 2 && c.unread === 0 && <span className="text-sm">{c.friendship.emoji}</span>}
                  </div>
                </button>
              ))}
            </Glass>
          ) : (
            <Glass className="p-2 space-y-1">
              {communities.map((c) => (
                <div key={c.id} className="flex items-center gap-3 p-2.5 rounded-2xl">
                  <Avatar c={{ initials: c.name?.[0] || '#', avatarColor: c.avatarColor }} size={48} />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm flex items-center gap-1"><Hash size={13} />{c.name}</div>
                    <div className="text-xs text-muted-foreground truncate">{c.topic} · {c.memberCount} membres</div>
                  </div>
                  {c.joined ? (
                    <button onClick={() => { setTab('dm'); openConv(c.id) }} className="press text-xs font-semibold px-3 py-1.5 rounded-full bg-primary/10 text-primary">Ouvrir</button>
                  ) : (
                    <button onClick={async () => { await api(`/conversations/${c.id}/join`, { method: 'POST' }); loadCommunities(); loadConvos() }}
                      className="press text-xs font-semibold px-3 py-1.5 rounded-full text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>Rejoindre</button>
                  )}
                </div>
              ))}
            </Glass>
          )}
        </div>

        {/* ============ RIGHT: chat ============ */}
        <div className={cx(!active && 'hidden md:block')}>
          {!active ? (
            <Glass className="h-[calc(100dvh-150px)] md:h-[calc(100dvh-120px)] grid place-items-center text-center">
              <div className="text-muted-foreground">
                <MessageCircle size={40} className="mx-auto mb-3 opacity-40" />
                <div className="font-medium">Ta messagerie DIVARC</div>
                <div className="text-sm">Choisis une discussion ou démarre-en une.</div>
              </div>
            </Glass>
          ) : (
            <Glass className="flex flex-col h-[calc(var(--vvh)-var(--chat-offset))] md:h-[calc(100dvh-120px)]">
              {/* header */}
              <div className="flex items-center gap-3 p-4 border-b border-border/60">
                <button onClick={() => setActive(null)} className="md:hidden press"><ArrowLeft size={20} /></button>
                <Avatar c={conv?.type === 'dm' ? conv.other : { initials: conv?.name?.[0] || '#', avatarColor: '#4353F0' }} size={40}
                  ring={conv?.friendship ? LEVEL_COLORS[conv.friendship.level] : null} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm flex items-center gap-1 truncate">
                    {conv?.type === 'dm' ? conv.other?.name : (conv?.name || 'Groupe')}
                    {conv?.other?.verified && <BadgeCheck size={13} className="text-primary" />}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {conv?.type === 'dm'
                      ? (isOnline(conv?.other?.id)
                          ? <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />en ligne</span>
                          : 'hors ligne')
                      : `${conv?.memberCount} membres`}
                  </div>
                </div>
                {conv?.type === 'dm' && conv.other && (
                  <>
                    <button onClick={() => startCall(conv.other.id, conv.other.name, conv.other.avatarColor, false)}
                      aria-label="Appel audio" className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60 text-foreground">
                      <Phone size={17} />
                    </button>
                    <button onClick={() => startCall(conv.other.id, conv.other.name, conv.other.avatarColor, true)}
                      aria-label="Appel vidéo" className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60 text-foreground">
                      <Video size={17} />
                    </button>
                  </>
                )}
                <Lock size={16} className="text-muted-foreground shrink-0" title="Chiffré de bout en bout" />
              </div>

              {conv?.type === 'dm' && <FriendshipPanel f={conv.friendship} levelUp={levelUp} />}

              {/* messages */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-2.5 no-scrollbar">
                {detail?.messages?.map((m) => <Bubble key={m.id} m={m} me={me} onReact={react} isGroup={isGroup} />)}
              </div>

              {/* en train d'écrire — au pied du chat, juste au-dessus du champ */}
              <AnimatePresence>
                {typingConvo === active && (
                  <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}
                    className="px-4 pb-1 flex items-center gap-2 text-xs text-primary">
                    <span className="flex gap-0.5">
                      <motion.span className="w-1.5 h-1.5 rounded-full bg-primary" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1, repeat: Infinity, delay: 0 }} />
                      <motion.span className="w-1.5 h-1.5 rounded-full bg-primary" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1, repeat: Infinity, delay: 0.2 }} />
                      <motion.span className="w-1.5 h-1.5 rounded-full bg-primary" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1, repeat: Infinity, delay: 0.4 }} />
                    </span>
                    {conv?.type === 'dm' ? (conv.other?.name?.split(' ')[0] + ' écrit…') : 'Quelqu’un écrit…'}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* aperçu du média sélectionné avant envoi */}
              {pendingMedia && (
                <div className="px-3 pt-2 flex items-center gap-2">
                  <div className="relative">
                    {pendingMedia.kind === 'image'
                      ? <img src={pendingMedia.preview} alt="" className="w-16 h-16 rounded-xl object-cover border border-border" />
                      : <div className="w-16 h-16 rounded-xl border border-border grid place-items-center bg-muted/60 text-xs text-muted-foreground text-center px-1">{pendingMedia.kind === 'video' ? '🎥 Vidéo' : '🎤 Audio'}</div>}
                    <button onClick={() => setPendingMedia(null)} aria-label="Retirer" className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-ink text-white grid place-items-center"><X size={12} /></button>
                  </div>
                  <span className="text-xs text-muted-foreground truncate">{pendingMedia.name}</span>
                </div>
              )}

              {/* input */}
              <div className="p-3 pb-safe border-t border-border/60 flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*,video/*,audio/*" className="hidden" onChange={onPickFile} />
                <button onClick={() => fileRef.current?.click()} disabled={uploading} aria-label="Joindre une photo ou vidéo"
                  className="press w-10 h-10 rounded-full grid place-items-center bg-muted/60 text-muted-foreground shrink-0 disabled:opacity-50">
                  {uploading ? <RefreshCw size={18} className="animate-spin" /> : <Paperclip size={18} />}
                </button>
                <input value={input} onChange={(e) => { setInput(e.target.value); const t = Date.now(); if (active && t - lastTypingSent.current > 1500) { lastTypingSent.current = t; sendRealtime({ type: 'typing', conversationId: active }) } }} onKeyDown={(e) => e.key === 'Enter' && send()}
                  placeholder="Message…" className="flex-1 rounded-full border border-border bg-card/60 px-4 py-2.5 text-sm" />
                <button onClick={send} disabled={(!input.trim() && !pendingMedia) || sending} aria-label="Envoyer"
                  className="press w-10 h-10 rounded-full grid place-items-center text-white disabled:opacity-40 shrink-0" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
                  <SendIcon size={18} />
                </button>
              </div>
            </Glass>
          )}
        </div>
      </div>

      <AnimatePresence>
        <AnimatePresence>
          {newOpen && <Discovery onClose={() => setNewOpen(false)} onOpenConversation={(id) => { setNewOpen(false); setTab('dm'); loadConvos(); openConv(id) }} />}
        </AnimatePresence>
      </AnimatePresence>
    </div>
  )
}

const Empty = ({ text }) => <div className="text-center text-sm text-muted-foreground py-10 px-4">{text}</div>

/* ---------- New chat / group modal ---------- */
function NewChat({ me, onClose, onOpen }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [mode, setMode] = useState('dm') // dm | group
  const [selected, setSelected] = useState([])
  const [groupName, setGroupName] = useState('')

  useEffect(() => {
    const t = setTimeout(async () => { const r = await api(`/users?q=${encodeURIComponent(q)}`); if (Array.isArray(r)) setResults(r) }, 250)
    return () => clearTimeout(t)
  }, [q])

  const toggle = (u) => setSelected((s) => s.find((x) => x.id === u.id) ? s.filter((x) => x.id !== u.id) : [...s, u])

  const startDm = async (u) => {
    const r = await api('/conversations', { method: 'POST', body: JSON.stringify({ type: 'dm', memberHandles: [u.handle] }) })
    if (r.id) onOpen(r.id)
  }
  const createGroup = async () => {
    if (selected.length === 0) return
    const r = await api('/conversations', { method: 'POST', body: JSON.stringify({ type: 'group', name: groupName || 'Nouveau groupe', memberHandles: selected.map((s) => s.handle) }) })
    if (r.id) onOpen(r.id)
  }

  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass strong className="p-5 pb-safe rounded-b-none sm:rounded-b-[var(--radius)] max-h-[88dvh] overflow-y-auto overscroll-contain no-scrollbar">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-2xl">Nouvelle discussion</h3>
            <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button>
          </div>
          <div className="flex gap-2 p-1 rounded-2xl bg-muted/60 mb-4">
            {[['dm', 'Message', MessageCircle], ['group', 'Groupe', Users]].map(([id, label, Icon]) => (
              <button key={id} onClick={() => setMode(id)} className={cx('press flex-1 py-2 rounded-xl text-sm font-medium flex items-center justify-center gap-1.5', mode === id ? 'bg-card shadow' : 'text-muted-foreground')}><Icon size={15} />{label}</button>
            ))}
          </div>
          {mode === 'group' && (
            <input value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="Nom du groupe…"
              className="w-full mb-3 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
          )}
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-3 py-2.5 mb-3">
            <Search size={16} className="text-muted-foreground" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher par nom ou @handle…" className="flex-1 bg-transparent text-sm outline-none" />
          </div>
          {mode === 'group' && selected.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {selected.map((u) => (
                <span key={u.id} className="inline-flex items-center gap-1 text-xs bg-primary/10 text-primary rounded-full pl-1 pr-2 py-0.5">
                  <Avatar c={u} size={20} /> {u.name.split(' ')[0]} <button onClick={() => toggle(u)}><X size={12} /></button>
                </span>
              ))}
            </div>
          )}
          <div className="space-y-1 max-h-[40dvh] overflow-y-auto no-scrollbar">
            {results.map((u) => (
              <button key={u.id} onClick={() => mode === 'dm' ? startDm(u) : toggle(u)}
                className={cx('press w-full flex items-center gap-3 p-2.5 rounded-2xl text-left', selected.find((x) => x.id === u.id) && 'bg-primary/10')}>
                <Avatar c={u} size={44} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm flex items-center gap-1">{u.name} {u.verified && <BadgeCheck size={13} className="text-primary" />}</div>
                  <div className="text-xs text-muted-foreground">{u.handle}</div>
                </div>
                {mode === 'dm' ? <UserPlus size={18} className="text-muted-foreground" />
                  : <div className={cx('w-5 h-5 rounded-md grid place-items-center', selected.find((x) => x.id === u.id) ? 'bg-primary text-white' : 'bg-muted')}>{selected.find((x) => x.id === u.id) && <Check size={13} />}</div>}
              </button>
            ))}
            {results.length === 0 && <Empty text="Aucun utilisateur trouvé." />}
          </div>
          {mode === 'group' && (
            <button onClick={createGroup} disabled={selected.length === 0}
              className="press w-full mt-4 rounded-2xl py-3.5 font-semibold text-white disabled:opacity-40" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
              Créer le groupe ({selected.length})
            </button>
          )}
        </Glass>
      </motion.div>
    </motion.div>
  )
}
