'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence, useMotionValue, animate } from 'framer-motion'
import { api } from '@/lib/api'
import {
  ArrowLeft, Send, Sparkles, Loader2, ChevronRight, Check, ShieldAlert, Zap,
  HandCoins, Store, Megaphone, Compass, X,
} from 'lucide-react'

const cx = (...a) => a.filter(Boolean).join(' ')
const Glass = ({ className, sheen, strong, children, ...p }) => <div className={cx('glass', sheen && 'glass-sheen', strong && 'glass-strong', className)} {...p}>{children}</div>
const euro = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const SUGGESTIONS = ['Envoie 20 € à un ami', 'Vends mon vélo 150 €', 'Lance une pub Notoriété à 50 €', 'Montre-moi mon wallet']
const ACTION_META = {
  send_money: { icon: HandCoins, label: 'Envoi d\u2019argent', color: '#E2AA2B', tint: 'bg-gold/15 text-gold-deep' },
  create_listing: { icon: Store, label: 'Nouvelle annonce', color: '#3FB68B', tint: 'bg-success/10 text-success' },
  launch_ad: { icon: Megaphone, label: 'Campagne pub', color: '#9B5DE5', tint: 'bg-violet/10 text-violet' },
  navigate: { icon: Compass, label: 'Ouvrir', color: '#4353F0', tint: 'bg-primary/10 text-primary' },
}

export default function Assistant({ me, onNavigate, onWalletRefresh, onClose }) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    let sid = null
    try { sid = localStorage.getItem('divarc_ai_session') } catch (e) {}
    if (!sid) { sid = (crypto?.randomUUID?.() || String(Date.now())); try { localStorage.setItem('divarc_ai_session', sid) } catch (e) {} }
    setSessionId(sid)
    api(`/ai/history?sessionId=${sid}`).then((r) => { if (r.messages) setMessages(r.messages) })
  }, [])
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [messages, busy])

  const send = useCallback(async (txt) => {
    const text = (txt ?? input).trim()
    if (!text || busy || !sessionId) return
    setInput(''); setBusy(true)
    setMessages((m) => [...m, { id: 'tmp-' + Date.now(), role: 'user', content: text }])
    const r = await api('/ai/chat', { method: 'POST', body: JSON.stringify({ sessionId, text }) })
    setBusy(false)
    if (r.error) { setMessages((m) => [...m, { id: 'err' + Date.now(), role: 'assistant', content: '⚠️ ' + r.error, actions: [] }]); return }
    setMessages((m) => [...m.filter((x) => !String(x.id).startsWith('tmp-')), r.userMessage, r.message])
  }, [input, busy, sessionId])

  const execute = async (msgId, action) => {
    const r = await api(`/ai/actions/${action.id}/execute`, { method: 'POST', body: JSON.stringify({ sessionId }) })
    if (r.error) return { error: r.error }
    setMessages((m) => m.map((msg) => msg.id === msgId ? { ...msg, actions: msg.actions.map((a) => a.id === action.id ? { ...a, status: 'executed', result: r.result } : a) } : msg))
    if (r.result?.kind === 'navigate') { setTimeout(() => { onNavigate?.(r.result.tab); onClose?.() }, 500) }
    if (['send_money', 'launch_ad'].includes(r.result?.kind)) onWalletRefresh?.()
    return { ok: true, result: r.result }
  }

  return (
    <div className="min-h-[100dvh] bg-app-gradient flex flex-col">
      <div className="mx-auto w-full max-w-2xl flex flex-col h-[100dvh]">
        {/* header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-card/60 border border-border"><ArrowLeft size={18} /></button>
          <div className="w-9 h-9 rounded-2xl grid place-items-center text-white grad-diva"><Sparkles size={17} /></div>
          <div className="flex-1"><div className="font-display text-lg leading-none">DIVA</div><div className="text-[11px] text-muted-foreground">Ton copilote IA · Claude Sonnet 4.5</div></div>
        </div>

        {/* messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
          {messages.length === 0 && !busy && (
            <div className="text-center pt-10">
              <div className="w-16 h-16 rounded-3xl grid place-items-center text-white mx-auto mb-4 grad-diva"><Sparkles size={28} /></div>
              <h2 className="font-display text-2xl mb-1">Bonjour {me?.name?.split(' ')[0] || ''}</h2>
              <p className="text-sm text-muted-foreground mb-6 max-w-xs mx-auto">Je peux envoyer de l'argent, créer une annonce, lancer une pub… Tu confirmes toujours d'un glissement.</p>
              <div className="flex flex-col gap-2 max-w-sm mx-auto">
                {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} className="press text-left"><Glass className="p-3 flex items-center gap-2 text-sm"><Sparkles size={14} className="text-primary shrink-0" /> {s}<ChevronRight size={15} className="ml-auto text-muted-foreground" /></Glass></button>)}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id}>
              <div className={cx('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div className={cx('px-4 py-2.5 rounded-2xl max-w-[85%] text-sm whitespace-pre-wrap leading-relaxed', m.role === 'user' ? 'bg-primary text-white rounded-br-md' : 'glass rounded-bl-md')}>{m.content}</div>
              </div>
              {m.role === 'assistant' && m.actions?.length > 0 && (
                <div className="mt-2.5 space-y-2.5">
                  {m.actions.map((a) => <ActionCard key={a.id} action={a} onExecute={() => execute(m.id, a)} />)}
                </div>
              )}
            </div>
          ))}
          {busy && <div className="flex justify-start"><div className="glass px-4 py-3 rounded-2xl rounded-bl-md flex items-center gap-2"><Loader2 className="animate-spin text-primary" size={15} /><span className="text-sm text-muted-foreground">DIVA réfléchit…</span></div></div>}
        </div>

        {/* input */}
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Écris à DIVA…" className="flex-1 rounded-full border border-border bg-card/60 px-4 py-3 text-sm outline-none focus:border-primary" />
            <button onClick={() => send()} disabled={busy || !input.trim()} className="press w-11 h-11 rounded-full grid place-items-center text-white shrink-0 disabled:opacity-40 grad-diva"><Send size={18} /></button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ActionCard({ action, onExecute }) {
  const meta = ACTION_META[action.type] || ACTION_META.navigate
  const Icon = meta.icon
  const done = action.status === 'executed'
  const [error, setError] = useState(null)
  const p = action.payload || {}

  const detail = () => {
    if (action.type === 'send_money') return `${euro(p.amountCents)} € → ${p.toName || 'destinataire'}`
    if (action.type === 'create_listing') return `${p.title || 'Annonce'} · ${euro(p.priceCents)} €`
    if (action.type === 'launch_ad') return `${p.name || 'Campagne'} · budget ${euro(p.budgetCents)} €`
    return p.tab ? `Écran : ${p.tab}` : ''
  }

  return (
    <Glass strong className="p-3.5 max-w-[92%]">
      <div className="flex items-center gap-2.5 mb-2">
        <div className={cx('w-9 h-9 rounded-inner grid place-items-center shrink-0', meta.tint)}><Icon size={17} /></div>
        <div className="flex-1 min-w-0"><div className="font-semibold text-sm">{action.title}</div><div className="text-[11px] text-muted-foreground">{meta.label}{action.risk === 'high' ? ' · sensible' : ''}</div></div>
        {action.risk === 'high' && !done && <ShieldAlert size={16} className="text-gold shrink-0" />}
      </div>
      {action.summary && <p className="text-xs text-muted-foreground mb-1">{action.summary}</p>}
      <div className="text-sm font-medium tabular mb-3">{detail()}</div>
      {done ? (
        <div className="flex items-center gap-2 py-2 px-3 rounded-inner bg-success/10 text-success text-sm font-semibold"><Check size={16} /> Effectué{action.result?.balanceCents != null ? ` · solde ${euro(action.result.balanceCents)} €` : ''}</div>
      ) : (
        <SlideToConfirm color={meta.color} onConfirm={async () => { const r = await onExecute(); if (r?.error) { setError(r.error); return false } return true }} />
      )}
      {error && <div className="text-xs text-destructive mt-2">⚠️ {error}</div>}
    </Glass>
  )
}

function SlideToConfirm({ onConfirm, color }) {
  const trackRef = useRef(null)
  const x = useMotionValue(0)
  const [loading, setLoading] = useState(false)
  const KNOB = 44
  const maxX = () => Math.max(0, (trackRef.current?.offsetWidth || 260) - KNOB - 6)

  const onDragEnd = async () => {
    const m = maxX()
    if (x.get() >= m - 8) {
      animate(x, m, { duration: 0.1 })
      setLoading(true)
      const ok = await onConfirm()
      if (ok === false) { setLoading(false); animate(x, 0, { type: 'spring', stiffness: 400, damping: 30 }) }
    } else {
      animate(x, 0, { type: 'spring', stiffness: 400, damping: 30 })
    }
  }

  return (
    <div ref={trackRef} className="relative h-11 rounded-full overflow-hidden select-none" style={{ background: `${color}1a` }}>
      <div className="absolute inset-0 grid place-items-center text-sm font-semibold pointer-events-none" style={{ color }}>{loading ? '…' : 'Glisse pour confirmer'}</div>
      <motion.div drag="x" dragConstraints={{ left: 0, right: maxX() }} dragElastic={0.02} dragMomentum={false} style={{ x }} onDragEnd={onDragEnd}
        className="absolute top-[3px] left-[3px] rounded-full grid place-items-center text-white shadow-lg cursor-grab active:cursor-grabbing touch-none"
        whileTap={{ scale: 0.96 }}>
        <div style={{ width: KNOB, height: KNOB, background: color }} className="rounded-full grid place-items-center">{loading ? <Loader2 className="animate-spin" size={18} /> : <ChevronRight size={20} />}</div>
      </motion.div>
    </div>
  )
}
