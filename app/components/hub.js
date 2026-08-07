'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { toast, Pill } from './ui-kit'
import {
  ArrowLeft, Shield, Lock, Link2, Unlink, Check, X, FileText, Plus, Share2,
  Trash2, Clock, ChevronRight, TrendingUp, TrendingDown, Landmark, Copy, AlertTriangle,
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const Glass = ({ className, sheen, strong, children, ...p }) => (
  <div className={cx('glass', sheen && 'glass-sheen', strong && 'glass-strong', className)} {...p}>{children}</div>
)
const eur = (cents) => (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const ConnIcon = ({ c, size = 48 }) => (
  <div className="rounded-2xl grid place-items-center text-white shadow shrink-0" style={{ width: size, height: size, background: `linear-gradient(150deg, ${c.color}, ${c.color}bb)`, fontSize: size * 0.44 }}>{c.emoji}</div>
)

export default function AdminHub({ me, onBack }) {
  const [tab, setTab] = useState('connectors') // connectors | vault | compta
  const [connectors, setConnectors] = useState([])
  const [docs, setDocs] = useState([])
  const [acc, setAcc] = useState(null)
  const [detail, setDetail] = useState(null)
  const [adding, setAdding] = useState(false)
  const [shareInfo, setShareInfo] = useState(null)

  const load = useCallback(async () => {
    const [c, d, a] = await Promise.all([api('/admin/connectors'), api('/admin/documents'), api('/admin/accounting')])
    if (Array.isArray(c)) setConnectors(c)
    if (Array.isArray(d)) setDocs(d)
    if (a && !a.error) setAcc(a)
  }, [])
  useEffect(() => { load() }, [load])

  const connect = async (c) => {
    const r = await api(`/admin/connectors/${c.id}/connect`, { method: 'POST' })
    if (r.error) return toast(r.error, 'error')
    await load()
    setDetail((prev) => prev ? { ...prev, connected: true, pseudonym: r.connection.pseudonym, data: r.connection.data } : prev)
    toast(`${c.name} connecté · pseudonyme ${r.connection.pseudonym}`)
  }
  const disconnect = async (c) => {
    await api(`/admin/connectors/${c.id}/disconnect`, { method: 'POST' })
    await load()
    setDetail((prev) => prev ? { ...prev, connected: false, data: [] } : prev)
    toast(`${c.name} déconnecté`, 'info')
  }
  const addDoc = async (form) => {
    const r = await api('/admin/documents', { method: 'POST', body: JSON.stringify(form) })
    if (r.error) return toast(r.error, 'error')
    setAdding(false); await load(); toast('Document chiffré ajouté au coffre-fort')
  }
  const shareDoc = async (d) => {
    const r = await api(`/admin/documents/${d.id}/share`, { method: 'POST', body: JSON.stringify({ hours: 24 }) })
    if (r.error) return toast(r.error, 'error')
    await load(); setShareInfo({ ...d, shareToken: r.shareToken, expiresAt: r.expiresAt })
  }
  const unshareDoc = async (d) => { await api(`/admin/documents/${d.id}/unshare`, { method: 'POST' }); await load(); toast('Partage révoqué', 'info') }
  const delDoc = async (d) => { await api(`/admin/documents/${d.id}`, { method: 'DELETE' }); await load(); toast('Document supprimé', 'info') }

  const connectedCount = connectors.filter((c) => c.connected).length

  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-2xl px-4 pt-6 pb-28">
        <div className="flex items-center gap-3 mb-1">
          {onBack && <button onClick={onBack} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button>}
          <div>
            <h1 className="font-display text-3xl leading-none">Hub administratif</h1>
            <p className="text-sm text-muted-foreground mt-1">Tes démarches, ta santé, tes documents — chiffrés & cloisonnés.</p>
          </div>
        </div>

        <Glass className="p-3 flex items-center gap-2 text-sm text-muted-foreground my-4">
          <Shield size={16} className="text-primary shrink-0" />
          <span>Connexions <b className="text-foreground">eIDAS</b> avec pseudonyme par service. Rien n'est partagé sans ton accord.</span>
        </Glass>

        <div className="p-1 rounded-inner bg-muted/60 flex gap-1 mb-5">
          {[['connectors', 'Connecteurs'], ['vault', 'Coffre-fort'], ['compta', 'Compta']].map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)}
              className={cx('press flex-1 py-2.5 rounded-[10px] text-sm font-semibold', tab === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>{label}</button>
          ))}
        </div>

        {/* -------- CONNECTORS -------- */}
        {tab === 'connectors' && (
          <div className="cascade space-y-2.5">
            <div className="text-xs text-muted-foreground mb-1">{connectedCount} service{connectedCount > 1 ? 's' : ''} connecté{connectedCount > 1 ? 's' : ''} · {connectors.length} disponibles</div>
            {connectors.map((c) => (
              <button key={c.id} onClick={() => setDetail(c)} className="press w-full text-left">
                <Glass className="p-3 flex items-center gap-3">
                  <ConnIcon c={c} size={48} />
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm flex items-center gap-1.5">{c.name}{c.sensitive && <Pill tone="gold">Sensible</Pill>}</div>
                    <div className="text-xs text-muted-foreground truncate">{c.desc}</div>
                  </div>
                  {c.connected
                    ? <Pill tone="success" className="shrink-0">Connecté</Pill>
                    : <span className="shrink-0 text-xs font-semibold px-3 py-1.5 rounded-full bg-primary/10 text-primary">Connecter</span>}
                </Glass>
              </button>
            ))}
            {connectors.length === 0 && <Glass className="p-10 text-center text-muted-foreground">Chargement…</Glass>}
          </div>
        )}

        {/* -------- VAULT -------- */}
        {tab === 'vault' && (
          <div className="cascade space-y-2.5">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1"><Lock size={12} className="text-primary" /> Chiffré de bout en bout · {docs.length} document{docs.length > 1 ? 's' : ''}</div>
              <button onClick={() => setAdding(true)} className="press text-xs font-semibold text-primary flex items-center gap-1"><Plus size={14} /> Ajouter</button>
            </div>
            {docs.map((d) => (
              <Glass key={d.id} className="p-3 flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl grid place-items-center bg-primary/8 text-2xl shrink-0">{d.emoji}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm truncate flex items-center gap-1.5">{d.title}<Lock size={11} className="text-muted-foreground" /></div>
                  <div className="text-xs text-muted-foreground truncate">{d.category} · {d.issuer}{d.shared && <span className="text-gold"> · partagé</span>}</div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {d.shared
                    ? <button onClick={() => unshareDoc(d)} className="press w-9 h-9 rounded-full grid place-items-center bg-gold/12 text-gold" aria-label="Révoquer le partage"><Clock size={16} /></button>
                    : <button onClick={() => shareDoc(d)} className="press w-9 h-9 rounded-full grid place-items-center bg-primary/10 text-primary" aria-label="Partager"><Share2 size={16} /></button>}
                  <button onClick={() => delDoc(d)} className="press w-9 h-9 rounded-full grid place-items-center bg-destructive/10 text-destructive" aria-label="Supprimer"><Trash2 size={16} /></button>
                </div>
              </Glass>
            ))}
            {docs.length === 0 && (
              <Glass className="p-10 text-center">
                <FileText size={30} className="mx-auto mb-2 text-muted-foreground" />
                <div className="text-sm text-muted-foreground">Ton coffre-fort est vide.</div>
                <button onClick={() => setAdding(true)} className="press mt-3 text-sm font-semibold text-primary">Ajouter un document</button>
              </Glass>
            )}
          </div>
        )}

        {/* -------- COMPTA -------- */}
        {tab === 'compta' && (
          <div className="cascade space-y-3">
            {acc ? (
              <>
                <div className="grid grid-cols-3 gap-2.5">
                  <Glass className="p-3.5 text-center">
                    <TrendingUp size={16} className="mx-auto mb-1 text-success" />
                    <div className="font-display tabular text-lg text-success">+{eur(acc.incomeCents)}</div>
                    <div className="text-[10px] text-muted-foreground">Entrées</div>
                  </Glass>
                  <Glass className="p-3.5 text-center">
                    <TrendingDown size={16} className="mx-auto mb-1 text-destructive" />
                    <div className="font-display tabular text-lg text-destructive">−{eur(acc.expenseCents)}</div>
                    <div className="text-[10px] text-muted-foreground">Sorties</div>
                  </Glass>
                  <Glass className="p-3.5 text-center">
                    <Landmark size={16} className="mx-auto mb-1 text-primary" />
                    <div className={cx('font-display tabular text-lg', acc.netCents >= 0 ? 'text-primary' : 'text-destructive')}>{acc.netCents >= 0 ? '+' : '−'}{eur(Math.abs(acc.netCents))}</div>
                    <div className="text-[10px] text-muted-foreground">Solde net</div>
                  </Glass>
                </div>
                <Glass className="p-4">
                  <div className="font-semibold text-sm mb-3">Dépenses par catégorie</div>
                  {acc.categories.length === 0 && <div className="text-sm text-muted-foreground text-center py-4">Aucune dépense à catégoriser.</div>}
                  <div className="space-y-3">
                    {acc.categories.map((c) => {
                      const pct = acc.expenseCents > 0 ? Math.round((c.amountCents / acc.expenseCents) * 100) : 0
                      return (
                        <div key={c.name}>
                          <div className="flex justify-between text-sm mb-1"><span>{c.name}</span><span className="font-display tabular text-muted-foreground">{eur(c.amountCents)} €</span></div>
                          <div className="h-2 rounded-full bg-muted/60 overflow-hidden"><div className="h-full rounded-full grad-primary" style={{ width: `${pct}%` }} /></div>
                        </div>
                      )
                    })}
                  </div>
                </Glass>
                <Glass className="p-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <Shield size={14} className="text-primary shrink-0" /> Vue calculée localement à partir de ton grand livre · {acc.count} opérations.
                </Glass>
              </>
            ) : <Glass className="p-10 text-center text-muted-foreground">Chargement…</Glass>}
          </div>
        )}
      </div>

      <AnimatePresence>
        {detail && <ConnectorDetail c={detail} onClose={() => setDetail(null)} onConnect={() => connect(detail)} onDisconnect={() => disconnect(detail)} />}
        {adding && <AddDocSheet onClose={() => setAdding(false)} onAdd={addDoc} />}
        {shareInfo && <ShareSheet d={shareInfo} onClose={() => setShareInfo(null)} onCopy={() => toast('Lien copié')} />}
      </AnimatePresence>
    </div>
  )
}

function ConnectorDetail({ c, onClose, onConnect, onDisconnect }) {
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass sheen strong className="p-5 pb-safe rounded-b-none sm:rounded-b-[var(--radius)] overlay-scroll no-scrollbar">
          <div className="flex justify-end mb-2"><button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button></div>
          <div className="flex items-center gap-4 mb-4">
            <ConnIcon c={c} size={64} />
            <div><div className="font-display text-2xl">{c.name}</div><div className="text-sm text-muted-foreground">{c.cat}</div></div>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed mb-4">{c.desc}</p>

          {c.sensitive && (
            <Glass className="p-3 mb-4 text-sm flex items-center gap-2 !bg-gold/10"><AlertTriangle size={16} className="text-gold shrink-0" /> Données sensibles — chiffrées et jamais utilisées à des fins publicitaires.</Glass>
          )}

          <div className="mb-4">
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5"><Shield size={15} className="text-primary" /> Données consultées</h3>
            <div className="space-y-1.5">
              {c.scopes?.map((s) => <div key={s} className="flex items-center gap-2 text-sm rounded-inner bg-card/60 border border-border px-3 py-2"><Check size={14} className="text-primary" /> {s}</div>)}
            </div>
          </div>

          {c.connected && c.data?.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-semibold mb-2">Aperçu</h3>
              <Glass className="divide-y divide-border">
                {c.data.map((d) => (
                  <div key={d.label} className="flex items-center justify-between px-3.5 py-2.5 text-sm"><span className="text-muted-foreground">{d.label}</span><span className="font-medium tabular">{d.value}</span></div>
                ))}
              </Glass>
            </div>
          )}

          {c.connected ? (
            <>
              <Glass className="p-3 mb-3 text-sm flex items-center gap-2 !bg-success/10"><Shield size={16} className="text-success" /> Connecté sous <b className="font-grotesk">{c.pseudonym || 'eidas-••••'}</b></Glass>
              <button onClick={onDisconnect} className="press w-full py-3 rounded-inner border border-destructive/30 bg-destructive/10 text-destructive font-medium flex items-center justify-center gap-1.5"><Unlink size={16} /> Déconnecter</button>
            </>
          ) : (
            <button onClick={onConnect} className="press w-full py-3.5 rounded-inner font-semibold text-white flex items-center justify-center gap-2 grad-primary"><Link2 size={18} /> Connecter · eIDAS</button>
          )}
          <p className="text-[11px] text-muted-foreground text-center mt-3">Révocable à tout moment depuis Profil › Qui voit quoi.</p>
        </Glass>
      </motion.div>
    </motion.div>
  )
}

const CATS = ['Impôts', 'Santé', 'Social', 'Identité', 'Logement', 'Autre']
const EMOJIS = { 'Impôts': '🧾', 'Santé': '⚕️', 'Social': '👨‍👩‍👧', 'Identité': '🪪', 'Logement': '🏠', 'Autre': '📄' }
function AddDocSheet({ onClose, onAdd }) {
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('Impôts')
  const [issuer, setIssuer] = useState('')
  const submit = () => { if (!title.trim()) return; onAdd({ title: title.trim(), category, issuer: issuer.trim() || 'Moi', emoji: EMOJIS[category] }) }
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass sheen strong className="p-5 pb-safe rounded-b-none sm:rounded-b-[var(--radius)] overlay-scroll no-scrollbar">
          <div className="flex items-center justify-between mb-4"><h3 className="font-display text-xl">Nouveau document</h3><button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button></div>
          <label className="text-xs text-muted-foreground">Intitulé</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex. Quittance de loyer" className="w-full mt-1 mb-3 rounded-inner border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary" />
          <label className="text-xs text-muted-foreground">Catégorie</label>
          <div className="flex gap-2 overflow-x-auto no-scrollbar mt-1 mb-3">
            {CATS.map((c) => <button key={c} onClick={() => setCategory(c)} className={cx('press whitespace-nowrap px-3.5 py-1.5 rounded-full text-sm font-medium border', category === c ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>{EMOJIS[c]} {c}</button>)}
          </div>
          <label className="text-xs text-muted-foreground">Émetteur (optionnel)</label>
          <input value={issuer} onChange={(e) => setIssuer(e.target.value)} placeholder="Ex. Mon bailleur" className="w-full mt-1 mb-4 rounded-inner border border-border bg-card/60 px-3.5 py-3 text-sm outline-none focus:border-primary" />
          <Glass className="p-2.5 mb-4 text-xs text-muted-foreground flex items-center gap-2"><Lock size={13} className="text-primary" /> Chiffré côté client avant stockage.</Glass>
          <button onClick={submit} disabled={!title.trim()} className="press w-full py-3.5 rounded-inner font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-40 grad-primary"><Plus size={18} /> Ajouter au coffre-fort</button>
        </Glass>
      </motion.div>
    </motion.div>
  )
}

function ShareSheet({ d, onClose, onCopy }) {
  const link = typeof window !== 'undefined' ? `${window.location.origin}/d/${d.shareToken}` : `divarc.eu/d/${d.shareToken}`
  const exp = new Date(d.expiresAt)
  const copy = () => { try { navigator.clipboard?.writeText(link) } catch (e) {} onCopy() }
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }} className="relative w-full sm:max-w-md">
        <Glass sheen strong className="p-5 pb-safe rounded-b-none sm:rounded-b-[var(--radius)] overlay-scroll no-scrollbar">
          <div className="flex items-center justify-between mb-4"><h3 className="font-display text-xl">Partage sécurisé</h3><button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button></div>
          <div className="text-center mb-4"><div className="text-3xl mb-1">{d.emoji}</div><div className="font-semibold">{d.title}</div></div>
          <Glass className="p-3 flex items-center gap-2 mb-3">
            <span className="flex-1 text-sm font-grotesk truncate">{link}</span>
            <button onClick={copy} className="press w-9 h-9 rounded-full grid place-items-center bg-primary/10 text-primary shrink-0"><Copy size={16} /></button>
          </Glass>
          <Glass className="p-3 text-xs text-muted-foreground flex items-center gap-2"><Clock size={14} className="text-gold shrink-0" /> Lien à usage unique · expire le {exp.toLocaleDateString('fr-FR')} à {exp.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}.</Glass>
        </Glass>
      </motion.div>
    </motion.div>
  )
}
