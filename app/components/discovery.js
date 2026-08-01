'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import {
  Search, X, UserPlus, MessageCircle, Check, Clock, Users, MapPin, Link2, Copy,
  ContactRound, Sparkles, ShieldCheck, RefreshCw, ChevronRight,
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')

/* ---------- hachage client (RGPD : jamais de numéro/e-mail en clair envoyé) ---------- */
const normEmail = (e) => (e || '').trim().toLowerCase()
const normPhone = (p) => { const d = (p || '').replace(/\D/g, ''); return d.length >= 9 ? d.slice(-9) : '' }
async function sha256(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str))
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

const Avatar = ({ u, size = 44 }) => (
  <div className="rounded-full grid place-items-center text-white font-semibold shrink-0"
    style={{ width: size, height: size, background: u?.avatarColor || 'linear-gradient(135deg,#4353F0,#2C39C7)', fontSize: size * 0.36 }}>
    {u?.initials || (u?.name || '?').slice(0, 1)}
  </div>
)

function UserRow({ u, onMessage, onAdd, busy }) {
  const rel = u.relation
  return (
    <div className="flex items-center gap-3 p-3 rounded-2xl border border-border bg-card/60">
      <Avatar u={u} />
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm flex items-center gap-1 truncate">
          {u.name} {u.verified && <ShieldCheck size={13} className="text-primary shrink-0" />}
        </div>
        <div className="text-xs text-muted-foreground truncate">{u.handle}{u.distanceM != null && ` · ${u.distanceM < 1000 ? u.distanceM + ' m' : (u.distanceM / 1000).toFixed(1) + ' km'}`}</div>
      </div>
      {rel === 'contact' || rel === 'pending_in' ? (
        <button onClick={() => onMessage(u)} disabled={busy} className="press px-3 py-2 rounded-full bg-primary text-white text-xs font-medium flex items-center gap-1"><MessageCircle size={14} /> Message</button>
      ) : rel === 'pending_out' ? (
        <span className="px-3 py-2 rounded-full bg-muted text-muted-foreground text-xs flex items-center gap-1"><Clock size={14} /> Envoyée</span>
      ) : (
        <button onClick={() => onAdd(u)} disabled={busy} className="press px-3 py-2 rounded-full bg-primary/10 text-primary text-xs font-medium flex items-center gap-1"><UserPlus size={14} /> Ajouter</button>
      )}
    </div>
  )
}

export default function Discovery({ onClose, onOpenConversation }) {
  const [tab, setTab] = useState('search') // search | contacts | nearby | invite
  const [busy, setBusy] = useState(false)
  const [requests, setRequests] = useState([])

  const loadRequests = useCallback(async () => {
    const r = await api('/discover/requests'); if (Array.isArray(r)) setRequests(r)
  }, [])
  useEffect(() => { loadRequests() }, [loadRequests])

  const addContact = async (u) => { setBusy(true); const r = await api(`/discover/request/${u.id}`, { method: 'POST' }); setBusy(false); return r }
  const message = async (u) => {
    setBusy(true)
    const r = await api('/conversations', { method: 'POST', body: JSON.stringify({ type: 'dm', memberHandles: [u.handle] }) })
    setBusy(false)
    if (r.id) { onOpenConversation?.(r.id); onClose?.() }
  }
  const respond = async (req, action) => {
    await api(`/discover/request/${req.id}/respond`, { method: 'POST', body: JSON.stringify({ action }) })
    loadRequests()
  }

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 border-b border-border/60">
        <button onClick={onClose} className="press"><X size={22} /></button>
        <h1 className="font-display text-2xl">Ajouter des contacts</h1>
      </div>

      {requests.length > 0 && (
        <div className="px-4 pt-3">
          <div className="text-xs font-medium text-muted-foreground mb-2">Demandes reçues ({requests.length})</div>
          <div className="space-y-2">
            {requests.map((r) => (
              <div key={r.requestId} className="flex items-center gap-3 p-3 rounded-2xl border border-primary/20 bg-primary/5">
                <Avatar u={r} size={40} />
                <div className="flex-1 min-w-0"><div className="font-medium text-sm truncate">{r.name}</div><div className="text-xs text-muted-foreground">{r.handle}</div></div>
                <button onClick={() => respond(r, 'accept')} className="press px-3 py-1.5 rounded-full bg-primary text-white text-xs font-medium">Accepter</button>
                <button onClick={() => respond(r, 'reject')} className="press w-8 h-8 rounded-full grid place-items-center bg-muted"><X size={15} /></button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1 p-1 m-4 rounded-2xl bg-muted/60">
        {[['search', 'Rechercher', Search], ['contacts', 'Contacts', ContactRound], ['nearby', 'Proximité', MapPin], ['invite', 'Inviter', Link2]].map(([id, label, Icon]) => (
          <button key={id} onClick={() => setTab(id)}
            className={cx('press flex-1 py-2 rounded-xl text-xs font-medium flex items-center justify-center gap-1', tab === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-8">
        {tab === 'search' && <SearchTab onMessage={message} onAdd={addContact} busy={busy} />}
        {tab === 'contacts' && <ContactsTab onMessage={message} onAdd={addContact} busy={busy} />}
        {tab === 'nearby' && <NearbyTab onMessage={message} onAdd={addContact} busy={busy} />}
        {tab === 'invite' && <InviteTab />}
      </div>
    </motion.div>
  )
}

function SearchTab({ onMessage, onAdd, busy }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); return }
    setLoading(true)
    const t = setTimeout(async () => { const r = await api(`/discover/search?q=${encodeURIComponent(q)}`); setResults(Array.isArray(r) ? r : []); setLoading(false) }, 300)
    return () => clearTimeout(t)
  }, [q])
  const doAdd = async (u) => { const r = await onAdd(u); if (r?.status) setResults((xs) => xs.map((x) => x.id === u.id ? { ...x, relation: r.status } : x)) }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-2.5">
        <Search size={18} className="text-muted-foreground" />
        <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus placeholder="Nom ou @handle…" className="flex-1 bg-transparent text-sm outline-none" />
      </div>
      {loading && <div className="text-center text-sm text-muted-foreground py-4"><RefreshCw className="animate-spin mx-auto" size={18} /></div>}
      {!loading && q.trim().length >= 2 && results.length === 0 && <div className="text-center text-sm text-muted-foreground py-8">Aucun résultat pour « {q} »</div>}
      {results.map((u) => <UserRow key={u.id} u={u} onMessage={onMessage} onAdd={doAdd} busy={busy} />)}
    </div>
  )
}

function ContactsTab({ onMessage, onAdd, busy }) {
  const [matches, setMatches] = useState(null)
  const [loading, setLoading] = useState(false)
  const [manual, setManual] = useState('')

  const runMatch = async (phones, emails) => {
    setLoading(true)
    const phoneHashes = (await Promise.all(phones.map(normPhone).filter(Boolean).map(sha256)))
    const emailHashes = (await Promise.all(emails.map(normEmail).filter(Boolean).map(sha256)))
    const r = await api('/discover/contacts/match', { method: 'POST', body: JSON.stringify({ phoneHashes, emailHashes }) })
    setMatches(Array.isArray(r) ? r : [])
    setLoading(false)
  }
  const importDevice = async () => {
    try {
      if (navigator.contacts && navigator.contacts.select) {
        const picked = await navigator.contacts.select(['tel', 'email'], { multiple: true })
        const phones = picked.flatMap((c) => c.tel || []); const emails = picked.flatMap((c) => c.email || [])
        await runMatch(phones, emails)
      } else {
        alert("L'import direct du carnet n'est pas disponible sur ce navigateur. Colle des numéros ou e-mails ci-dessous.")
      }
    } catch (e) { /* annulé */ }
  }
  const runManual = async () => {
    const tokens = manual.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean)
    const emails = tokens.filter((t) => t.includes('@')); const phones = tokens.filter((t) => !t.includes('@'))
    await runMatch(phones, emails)
  }
  const doAdd = async (u) => { const r = await onAdd(u); if (r?.status) setMatches((xs) => xs.map((x) => x.id === u.id ? { ...x, relation: r.status } : x)) }

  return (
    <div className="space-y-4">
      <div className="p-4 rounded-2xl border border-border bg-card/60">
        <div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck size={16} className="text-emerald-500" /> Confidentialité</div>
        <p className="text-xs text-muted-foreground mt-1">Tes contacts sont <b>hachés sur ton appareil</b> avant l'envoi. Aucun numéro ni e-mail n'est stocké en clair.</p>
      </div>
      <button onClick={importDevice} className="press w-full py-3 rounded-2xl bg-primary text-white font-medium flex items-center justify-center gap-2"><ContactRound size={18} /> Importer mes contacts</button>
      <div>
        <label className="text-xs text-muted-foreground">Ou colle des numéros / e-mails (un par ligne)</label>
        <textarea value={manual} onChange={(e) => setManual(e.target.value)} rows={3} placeholder="0612345678&#10;ami@exemple.fr" className="w-full mt-1 rounded-xl border border-border bg-card/60 px-3 py-2 text-sm" />
        <button onClick={runManual} disabled={!manual.trim()} className="press mt-2 w-full py-2.5 rounded-xl bg-primary/10 text-primary text-sm font-medium disabled:opacity-40">Chercher sur DIVARC</button>
      </div>
      {loading && <div className="text-center py-4"><RefreshCw className="animate-spin mx-auto text-primary" size={20} /></div>}
      {matches && !loading && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground">{matches.length} contact(s) sur DIVARC</div>
          {matches.length === 0 && <div className="text-center text-sm text-muted-foreground py-6">Aucun de tes contacts n'est encore sur DIVARC.<br />Invite-les depuis l'onglet « Inviter » 🎁</div>}
          {matches.map((u) => <UserRow key={u.id} u={u} onMessage={onMessage} onAdd={doAdd} busy={busy} />)}
        </div>
      )}
    </div>
  )
}

function NearbyTab({ onMessage, onAdd, busy }) {
  const [list, setList] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const activate = () => {
    setErr(''); setLoading(true)
    if (!navigator.geolocation) { setErr('Géolocalisation indisponible'); setLoading(false); return }
    navigator.geolocation.getCurrentPosition(async (pos) => {
      await api('/discover/nearby/ping', { method: 'POST', body: JSON.stringify({ lat: pos.coords.latitude, lon: pos.coords.longitude }) })
      const r = await api('/discover/nearby')
      setList(Array.isArray(r) ? r : []); setLoading(false)
    }, () => { setErr('Autorise la localisation pour découvrir les personnes à proximité.'); setLoading(false) }, { enableHighAccuracy: true, timeout: 10000 })
  }
  const doAdd = async (u) => { const r = await onAdd(u); if (r?.status) setList((xs) => xs.map((x) => x.id === u.id ? { ...x, relation: r.status } : x)) }
  return (
    <div className="space-y-4">
      <div className="p-4 rounded-2xl border border-border bg-card/60 text-xs text-muted-foreground">
        <MapPin size={16} className="text-primary inline mr-1" /> Découverte <b>ponctuelle</b> : ta position n'est partagée que 5 minutes, jamais en continu.
      </div>
      <button onClick={activate} disabled={loading} className="press w-full py-3 rounded-2xl bg-primary text-white font-medium flex items-center justify-center gap-2">
        {loading ? <RefreshCw className="animate-spin" size={18} /> : <><MapPin size={18} /> Activer ma position</>}
      </button>
      {err && <div className="text-sm text-rose-500 text-center">{err}</div>}
      {list && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground">{list.length} personne(s) à proximité</div>
          {list.length === 0 && <div className="text-center text-sm text-muted-foreground py-6">Personne autour de toi pour le moment.</div>}
          {list.map((u) => <UserRow key={u.id} u={u} onMessage={onMessage} onAdd={doAdd} busy={busy} />)}
        </div>
      )}
    </div>
  )
}

function InviteTab() {
  const [inv, setInv] = useState(null)
  const [copied, setCopied] = useState(false)
  useEffect(() => { api('/discover/invite', { method: 'POST' }).then((r) => { if (r.link) setInv(r) }) }, [])
  const copy = () => { try { navigator.clipboard.writeText(inv.link); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch (e) {} }
  const share = async () => { try { await navigator.share({ title: 'Rejoins-moi sur DIVARC', text: 'Rejoins-moi sur DIVARC 🎉', url: inv.link }) } catch (e) {} }
  if (!inv) return <div className="text-center py-8"><RefreshCw className="animate-spin mx-auto text-primary" size={20} /></div>
  return (
    <div className="space-y-4 text-center">
      <div className="w-16 h-16 mx-auto rounded-2xl grid place-items-center text-white" style={{ background: 'linear-gradient(135deg,#E2AA2B,#F0CE7E)' }}><Sparkles size={28} /></div>
      <div className="font-display text-2xl">Invite tes amis</div>
      <p className="text-sm text-muted-foreground">Quand un ami rejoint DIVARC avec ton lien, tu gagnes <b className="text-foreground">+5,00 €</b> 🎁</p>
      <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 p-3">
        <Link2 size={16} className="text-muted-foreground shrink-0" />
        <span className="flex-1 text-sm truncate text-left">{inv.link}</span>
        <button onClick={copy} className="press w-9 h-9 rounded-full grid place-items-center bg-primary/10 text-primary">{copied ? <Check size={16} /> : <Copy size={16} />}</button>
      </div>
      {typeof navigator !== 'undefined' && navigator.share && (
        <button onClick={share} className="press w-full py-3 rounded-2xl bg-primary text-white font-medium">Partager le lien</button>
      )}
      {inv.count > 0 && <div className="text-xs text-muted-foreground">{inv.count} personne(s) ont rejoint grâce à toi 🎉</div>}
    </div>
  )
}
