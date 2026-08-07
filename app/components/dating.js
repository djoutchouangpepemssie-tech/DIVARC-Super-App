'use client'

// DIVARC Rencontres — verticale intégrée, monétisée en Éclats. Trust & safety d'abord.
import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Heart, Star, MapPin, ShieldCheck, Zap, Flag, RefreshCw,
  Sparkles, Pause, Play, Trash2, Camera, Eye, MessageCircle,
} from 'lucide-react'
import { api } from '@/lib/api'
import { toast, askConfirm, Toggle, Eclats } from './ui-kit'

const cx = (...a) => a.filter(Boolean).join(' ')
const GENDERS = [['femme', 'Femme'], ['homme', 'Homme'], ['autre', 'Autre']]

function fileToDataUrl(file) {
  return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file) })
}

const Avatar = ({ c, size = 56 }) => (
  <div className={cx('rounded-full grid place-items-center text-white font-semibold shrink-0', !c?.avatarColor && 'grad-love')}
    style={{ width: size, height: size, background: c?.avatarColor || undefined, fontSize: size * 0.36 }}>
    {c?.initials || (c?.name || '?').slice(0, 1)}
  </div>
)

export default function DatingModule({ me, onClose, onOpenConversation }) {
  const [view, setView] = useState('loading') // loading | onboarding | main
  const [tab, setTab] = useState('discover')   // discover | likes | matches | settings
  const [profile, setProfile] = useState(null)

  const loadMe = useCallback(async () => {
    const r = await api('/dating/me')
    if (r && !r.error) { setProfile(r.profile); setView(r.hasProfile ? 'main' : 'onboarding') }
    else setView('onboarding')
  }, [])
  useEffect(() => { loadMe() }, [loadMe])

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={onClose} className="press" aria-label="Fermer"><X size={22} /></button>
        <h1 className="font-display text-2xl flex items-center gap-2"><Heart size={20} className="text-love" fill="currentColor" /> Rencontres</h1>
      </div>

      {view === 'loading' && <div className="flex-1 grid place-items-center"><RefreshCw className="animate-spin text-muted-foreground" /></div>}
      {view === 'onboarding' && <Onboarding onDone={loadMe} />}
      {view === 'main' && (
        <>
          <div className="flex gap-1 p-1 m-4 rounded-lg bg-muted/60">
            {[['discover', 'Découvrir'], ['likes', 'Likes'], ['matches', 'Matchs'], ['settings', 'Réglages']].map(([id, label]) => (
              <button key={id} onClick={() => setTab(id)}
                className={cx('press flex-1 py-2 rounded-inner text-xs font-medium', tab === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>{label}</button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
            {tab === 'discover' && <DiscoverTab onOpenConversation={onOpenConversation} />}
            {tab === 'likes' && <LikesTab />}
            {tab === 'matches' && <MatchesTab onOpenConversation={onOpenConversation} onClose={onClose} />}
            {tab === 'settings' && <SettingsTab profile={profile} onChanged={loadMe} onDeleted={() => setView('onboarding')} />}
          </div>
        </>
      )}
    </motion.div>
  )
}

/* ---------------- Onboarding ---------------- */
function Onboarding({ onDone }) {
  const [birthDate, setBirthDate] = useState('')
  const [gender, setGender] = useState('')
  const [seeking, setSeeking] = useState([])
  const [bio, setBio] = useState('')
  const [photos, setPhotos] = useState([])
  const [city, setCity] = useState('')
  const [geo, setGeo] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const toggleSeek = (g) => setSeeking((s) => s.includes(g) ? s.filter((x) => x !== g) : [...s, g])
  const addPhoto = async (e) => {
    const f = e.target.files?.[0]; e.target.value = ''
    if (!f) return
    if (f.size > 6.5 * 1024 * 1024) { setErr('Photo trop lourde (max ~6 Mo)'); return }
    const dataUrl = await fileToDataUrl(f)
    const r = await api('/chat/upload', { method: 'POST', body: JSON.stringify({ data: dataUrl }) })
    if (r.url) setPhotos((p) => [...p, r.url].slice(0, 6))
  }
  const locate = () => {
    if (!navigator.geolocation) return setErr('Localisation indisponible')
    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
      setGeo({ lat: coords.latitude, lon: coords.longitude })
      const r = await api(`/geo/reverse?lat=${coords.latitude}&lon=${coords.longitude}`)
      if (r?.city) setCity(r.city)
    }, () => setErr('Autorise la localisation'))
  }
  const submit = async () => {
    setErr('')
    if (!birthDate) return setErr('Indique ta date de naissance')
    if (!gender) return setErr('Indique ton genre')
    if (!seeking.length) return setErr('Indique qui tu cherches')
    setBusy(true)
    const r = await api('/dating/profile', { method: 'POST', body: JSON.stringify({
      birthDate, gender, seeking, bio, photos, city, lat: geo?.lat, lon: geo?.lon,
    }) })
    setBusy(false)
    if (r.error) return setErr(r.error)
    onDone()
  }

  return (
    <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
      <div className="rounded-lg bg-love/10 border border-love/20 p-4 my-4 text-sm flex items-start gap-2">
        <ShieldCheck size={18} className="text-love shrink-0 mt-0.5" />
        <span>Rencontres <b>vérifiées et sûres</b>. Réservé aux 18 ans et plus. Ta position reste <b>approximative</b> (jamais exacte).</span>
      </div>

      <label className="text-xs text-muted-foreground">Date de naissance (18+ obligatoire)</label>
      <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)}
        className="w-full mt-1 mb-4 rounded-inner border border-border bg-card/60 px-4 py-3 text-sm outline-none focus:border-primary" />

      <label className="text-xs text-muted-foreground">Je suis</label>
      <div className="flex gap-2 mt-1 mb-4">
        {GENDERS.map(([v, l]) => (
          <button key={v} onClick={() => setGender(v)} className={cx('press flex-1 py-2.5 rounded-inner text-sm font-medium border', gender === v ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border')}>{l}</button>
        ))}
      </div>

      <label className="text-xs text-muted-foreground">Je cherche</label>
      <div className="flex gap-2 mt-1 mb-4">
        {GENDERS.map(([v, l]) => (
          <button key={v} onClick={() => toggleSeek(v)} className={cx('press flex-1 py-2.5 rounded-inner text-sm font-medium border', seeking.includes(v) ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border')}>{l}</button>
        ))}
      </div>

      <label className="text-xs text-muted-foreground">Photos</label>
      <div className="flex gap-2 flex-wrap mt-1 mb-4">
        {photos.map((p, i) => (
          <div key={i} className="relative">
            <img src={p} alt="" className="w-20 h-24 rounded-inner object-cover border border-border" />
            <button onClick={() => setPhotos((ps) => ps.filter((_, j) => j !== i))} className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-ink text-white grid place-items-center"><X size={12} /></button>
          </div>
        ))}
        {photos.length < 6 && (
          <label className="w-20 h-24 rounded-inner border border-dashed border-border grid place-items-center cursor-pointer text-muted-foreground">
            <Camera size={20} />
            <input type="file" accept="image/*" className="hidden" onChange={addPhoto} />
          </label>
        )}
      </div>

      <label className="text-xs text-muted-foreground">Bio</label>
      <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={3} maxLength={500} placeholder="Parle un peu de toi…"
        className="w-full mt-1 mb-4 rounded-inner border border-border bg-card/60 px-4 py-3 text-sm outline-none focus:border-primary resize-none" />

      <button onClick={locate} className="press w-full mb-3 rounded-inner border border-border bg-card/60 px-4 py-3 text-sm flex items-center justify-center gap-2">
        <MapPin size={16} /> {city ? `Position : ${city} (approx.)` : 'Utiliser ma position (approximative)'}
      </button>

      {err && <p className="text-xs text-destructive mb-2">{err}</p>}
      <button onClick={submit} disabled={busy} className="press w-full rounded-lg py-3.5 font-semibold text-white disabled:opacity-50 mb-6 grad-love">
        {busy ? <RefreshCw size={18} className="animate-spin mx-auto" /> : 'Créer mon profil'}
      </button>
    </div>
  )
}

/* ---------------- Découverte (swipe par boutons) ---------------- */
function DiscoverTab({ onOpenConversation }) {
  const [cards, setCards] = useState(null)
  const [i, setI] = useState(0)
  const [match, setMatch] = useState(null)
  const [busy, setBusy] = useState(false)
  const [reporting, setReporting] = useState(false)

  const load = useCallback(async () => {
    const r = await api('/dating/discover')
    if (Array.isArray(r)) { setCards(r); setI(0) }
    else setCards([])
  }, [])
  useEffect(() => { load() }, [load])

  const current = cards?.[i]
  const swipe = async (action) => {
    if (!current || busy) return
    setBusy(true)
    const r = await api(`/dating/swipe/${current.userId}`, { method: 'POST', body: JSON.stringify({ action }) })
    setBusy(false)
    if (r.error) { toast(r.error, 'error'); return }
    if (r.match) setMatch({ ...current, conversationId: r.conversationId })
    setI((v) => v + 1)
  }
  const report = async () => {
    if (!current) return
    await api(`/dating/report/${current.userId}`, { method: 'POST', body: JSON.stringify({ reason: 'signalé depuis une carte' }) })
    setReporting(false); setI((v) => v + 1)
  }

  if (cards === null) return <div className="grid place-items-center py-20"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  if (!current) return (
    <div className="text-center py-16">
      <Sparkles size={36} className="mx-auto mb-3 text-muted-foreground opacity-50" />
      <div className="font-medium">Plus de profils pour l'instant</div>
      <div className="text-sm text-muted-foreground mt-1">Reviens plus tard — de nouveaux membres arrivent.</div>
      <button onClick={load} className="press mt-4 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">Actualiser</button>
    </div>
  )

  return (
    <div className="py-2">
      <div className="relative rounded-lg overflow-hidden border border-border shadow-xl bg-card">
        <div className="relative aspect-[3/4] bg-muted">
          {current.photos?.[0]
            ? <img src={current.photos[0]} alt={current.name} className="w-full h-full object-cover" />
            : <div className="w-full h-full grid place-items-center"><Avatar c={current} size={96} /></div>}
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
          {current.boosted && <span className="absolute top-3 left-3 text-[11px] font-bold px-2.5 py-1 rounded-full text-white flex items-center gap-1 grad-gold-deep"><Zap size={11} /> Boosté</span>}
          <button onClick={() => setReporting(true)} aria-label="Signaler" className="absolute top-3 right-3 w-9 h-9 rounded-full grid place-items-center bg-black/40 text-white backdrop-blur"><Flag size={16} /></button>
          <div className="absolute bottom-0 inset-x-0 p-4 text-white">
            <div className="flex items-center gap-2">
              <span className="font-display text-2xl">{current.name}{current.age ? `, ${current.age}` : ''}</span>
              {current.verified && <ShieldCheck size={18} className="text-sky-300" />}
            </div>
            <div className="text-sm text-white/80 flex items-center gap-2 mt-0.5">
              {current.distanceKm != null && <span className="flex items-center gap-1"><MapPin size={13} /> à ~{current.distanceKm} km</span>}
              {current.city && <span>· {current.city}</span>}
            </div>
            {current.bio && <p className="text-sm text-white/90 mt-2 line-clamp-3">{current.bio}</p>}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center gap-5 mt-5">
        <button onClick={() => swipe('pass')} disabled={busy} className="press w-14 h-14 rounded-full grid place-items-center bg-card border border-border shadow disabled:opacity-50"><X size={26} className="text-muted-foreground" /></button>
        <button onClick={() => swipe('superlike')} disabled={busy} className="press w-16 h-16 rounded-full grid place-items-center text-white shadow-xl disabled:opacity-50 grad-primary">
          <div className="flex flex-col items-center leading-none"><Star size={22} fill="#fff" /><span className="text-[9px] mt-0.5"><Eclats n={15} size={9} /></span></div>
        </button>
        <button onClick={() => swipe('like')} disabled={busy} className="press w-14 h-14 rounded-full grid place-items-center text-white shadow-lg disabled:opacity-50 grad-love"><Heart size={26} fill="#fff" /></button>
      </div>
      <p className="text-center text-[11px] text-muted-foreground mt-3">Super-like ⭐ = <Eclats n={15} size={10} /> · Like gratuit (limité/jour) · Position approximative</p>

      {/* Signalement */}
      <AnimatePresence>
        {reporting && (
          <motion.div className="fixed inset-0 z-[80] grid place-items-center p-6 bg-black/50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setReporting(false)}>
            <div className="rounded-lg bg-card border border-border p-5 max-w-sm w-full" onClick={(e) => e.stopPropagation()}>
              <div className="font-semibold mb-1">Signaler ce profil ?</div>
              <p className="text-sm text-muted-foreground mb-4">Notre équipe examinera ce signalement. Le profil ne te sera plus montré.</p>
              <div className="flex gap-2">
                <button onClick={() => setReporting(false)} className="press flex-1 py-2.5 rounded-inner border border-border text-sm">Annuler</button>
                <button onClick={report} className="press flex-1 py-2.5 rounded-inner bg-destructive/10 text-destructive font-medium text-sm">Signaler</button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Match */}
      <AnimatePresence>
        {match && (
          <motion.div className="fixed inset-0 z-[80] grid place-items-center p-6 grad-love" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="text-center text-white">
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 200, damping: 12 }}>
                <div className="text-6xl mb-3">💜</div>
                <div className="font-display text-4xl mb-1">C'est un match !</div>
                <div className="text-white/85 mb-6">Toi et {match.name} vous êtes plu</div>
              </motion.div>
              <button onClick={() => { const c = match.conversationId; setMatch(null); onOpenConversation?.(c) }} className="press w-full max-w-xs mx-auto rounded-lg py-3.5 font-semibold bg-white text-love flex items-center justify-center gap-2">
                <MessageCircle size={18} /> Envoyer un message
              </button>
              <button onClick={() => setMatch(null)} className="press mt-3 text-white/80 text-sm">Continuer à découvrir</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ---------------- Qui t'a liké ---------------- */
function LikesTab() {
  const [data, setData] = useState(null)
  const [revealed, setRevealed] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/dating/likes').then((r) => !r.error && setData(r)) }, [])
  const reveal = async () => {
    setBusy(true)
    const r = await api('/dating/likes/reveal', { method: 'POST' })
    setBusy(false)
    if (r.error) return toast(r.error, 'error')
    setRevealed(r.revealed)
  }
  if (!data) return <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  if (revealed) return (
    <div className="py-2 grid grid-cols-2 gap-3">
      {revealed.length === 0 && <div className="col-span-2 text-center text-sm text-muted-foreground py-10">Personne pour l'instant</div>}
      {revealed.map((u) => (
        <div key={u.userId} className="rounded-lg overflow-hidden border border-border">
          <div className="aspect-square bg-muted">{u.photos?.[0] ? <img src={u.photos[0]} alt="" className="w-full h-full object-cover" /> : <div className="w-full h-full grid place-items-center"><Avatar c={u} /></div>}</div>
          <div className="p-2"><div className="text-sm font-medium truncate">{u.name}{u.age ? `, ${u.age}` : ''} {u.superlike && <Star size={12} className="inline text-primary" fill="currentColor" />}</div></div>
        </div>
      ))}
    </div>
  )
  return (
    <div className="text-center py-14">
      <div className="w-20 h-20 rounded-full mx-auto grid place-items-center mb-4 grad-love"><Eye size={32} className="text-white" /></div>
      <div className="font-display text-3xl">{data.count}</div>
      <div className="text-sm text-muted-foreground mb-6">{data.count > 0 ? "personne(s) t'ont liké" : "Aucun like pour l'instant"}</div>
      {data.count > 0 && (
        <button onClick={reveal} disabled={busy} className="press px-6 py-3 rounded-lg font-semibold text-white disabled:opacity-50 grad-gold-deep">
          {busy ? <RefreshCw size={18} className="animate-spin" /> : <>Révéler · <Eclats n={data.revealCost} size={14} /></>}
        </button>
      )}
    </div>
  )
}

/* ---------------- Matchs ---------------- */
function MatchesTab({ onOpenConversation, onClose }) {
  const [ms, setMs] = useState(null)
  useEffect(() => { api('/dating/matches').then((r) => Array.isArray(r) ? setMs(r) : setMs([])) }, [])
  if (!ms) return <div className="grid place-items-center py-16"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  if (!ms.length) return <div className="text-center py-16 text-sm text-muted-foreground">Pas encore de match. Continue à découvrir !</div>
  return (
    <div className="py-2 space-y-2">
      {ms.map((m) => (
        <button key={m.userId} onClick={() => { onClose?.(); onOpenConversation?.(m.conversationId) }} className="press w-full flex items-center gap-3 p-3 rounded-lg border border-border bg-card/60 text-left">
          {m.photos?.[0] ? <img src={m.photos[0]} alt="" className="w-12 h-12 rounded-full object-cover" /> : <Avatar c={m} size={48} />}
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm flex items-center gap-1">{m.name}{m.age ? `, ${m.age}` : ''} {m.verified && <ShieldCheck size={13} className="text-primary" />}</div>
            <div className="text-xs text-muted-foreground">Touche pour discuter 💬</div>
          </div>
          <MessageCircle size={18} className="text-muted-foreground" />
        </button>
      ))}
    </div>
  )
}

/* ---------------- Réglages ---------------- */
function SettingsTab({ profile, onChanged, onDeleted }) {
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState('')
  const [incognito, setIncognito] = useState(!!profile?.incognito)
  const toggleIncognito = async () => {
    const v = !incognito; setIncognito(v)
    await api('/dating/profile', { method: 'POST', body: JSON.stringify({ incognito: v }) })
  }
  const boost = async () => {
    setBusy('boost'); setMsg('')
    const r = await api('/dating/boost', { method: 'POST' })
    setBusy('')
    setMsg(r.error ? r.error : `Profil boosté 🚀 · -${r.cost} Éclats`)
  }
  const togglePause = async () => {
    setBusy('pause')
    await api('/dating/pause', { method: 'POST', body: JSON.stringify({ paused: !profile?.paused }) })
    setBusy(''); onChanged()
  }
  const del = async () => {
    const ok = await askConfirm({ title: 'Supprimer ton profil Rencontres ?', message: 'Tes matchs et likes seront effacés.', confirmLabel: 'Supprimer', danger: true })
    if (!ok) return
    setBusy('del')
    await api('/dating/profile', { method: 'DELETE' })
    setBusy(''); onDeleted()
  }
  return (
    <div className="py-2 space-y-3">
      {msg && <div className="rounded-lg bg-gold/12 border border-gold/30 px-4 py-2.5 text-sm text-center">{msg}</div>}
      <button onClick={boost} disabled={busy === 'boost'} className="press w-full rounded-lg px-4 py-4 font-semibold text-white flex items-center justify-center gap-2 grad-gold-deep">
        {busy === 'boost' ? <RefreshCw size={18} className="animate-spin" /> : <><Zap size={18} /> Booster mon profil · <Eclats n={60} size={15} /></>}
      </button>
      <button onClick={togglePause} disabled={busy === 'pause'} className="press w-full rounded-lg px-4 py-4 font-medium border border-border bg-card/60 flex items-center justify-center gap-2">
        {profile?.paused ? <><Play size={18} /> Réactiver mon profil</> : <><Pause size={18} /> Mettre en pause</>}
      </button>
      <div className="flex items-center justify-between rounded-lg px-4 py-3.5 border border-border bg-card/60">
        <div className="flex items-center gap-3"><Eye size={18} className="text-muted-foreground" /><div><div className="font-medium text-sm">Mode incognito</div><div className="text-xs text-muted-foreground">Visible seulement des profils que tu likes · DIVARC+</div></div></div>
        <Toggle on={incognito} onClick={toggleIncognito} aria-label="Mode incognito" />
      </div>
      <div className="rounded-lg border border-border bg-card/40 p-4 text-xs text-muted-foreground">
        <div className="font-medium text-foreground mb-1 flex items-center gap-1.5"><ShieldCheck size={14} className="text-love" /> Sécurité & confidentialité</div>
        Âge déclaré 18+ · Position approximative (jamais exacte) · Blocage & signalement actifs · Données sensibles cloisonnées (RGPD).
      </div>
      <button onClick={del} disabled={busy === 'del'} className="press w-full rounded-lg px-4 py-3 font-medium border border-destructive/30 bg-destructive/10 text-destructive flex items-center justify-center gap-2">
        <Trash2 size={16} /> Supprimer mon profil
      </button>
    </div>
  )
}
