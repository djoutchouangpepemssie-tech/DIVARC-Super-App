'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from 'next-themes'
import {
  Home, MessageCircle, QrCode, Compass, User, Send as SendIcon, Plus, Eye, EyeOff,
  Sun, Moon, ArrowUpRight, ArrowDownLeft, Gift, Split, Leaf, Shield, ChevronRight,
  Sparkles, X, Check, Fingerprint, Mail, ArrowLeft, Search, Bell, TrendingUp,
  Wallet as WalletIcon, Zap, Lock, ScanLine, RefreshCw, Delete, BadgeCheck,
  Utensils, Car, ShoppingBag, Ticket, HeartPulse, Globe, ChevronDown, Info,
  Landmark, CreditCard, Settings2, Trash2, Download, Users, Play
} from 'lucide-react'
import { api, getToken, setToken, clearToken } from '@/lib/api'
import Messaging from './components/messaging'
import Social from './components/social'
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'

/* ============================= helpers ============================= */
const eur = (cents, mask = false) => {
  if (mask) return '••••'
  const v = (cents / 100)
  return v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
const cx = (...a) => a.filter(Boolean).join(' ')

/* ============================= primitives ============================= */
const Glass = ({ className, sheen, strong, children, ...p }) => (
  <div className={cx('glass', sheen && 'glass-sheen', strong && 'glass-strong', className)} {...p}>
    {children}
  </div>
)

const Amount = ({ cents, mask, className, sign }) => (
  <span className={cx('font-display tabular', className)}>
    {sign && cents > 0 ? '+' : ''}{eur(Math.abs(cents), mask)}
  </span>
)

const Avatar = ({ c, size = 44 }) => (
  <div
    className="grid place-items-center rounded-full text-white font-semibold shrink-0 font-body"
    style={{ width: size, height: size, background: c?.color || c?.avatarColor || '#4353F0', fontSize: size * 0.36 }}
  >
    {c?.initials}
  </div>
)

const Pill = ({ children, className }) => (
  <span className={cx('inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold', className)}>
    {children}
  </span>
)

/* ============================= LOGIN (Email + OTP) ============================= */
function Login({ onAuthed }) {
  const [step, setStep] = useState('email') // email | otp
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [isNew, setIsNew] = useState(false)
  const [preview, setPreview] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const sendCode = async () => {
    setError('')
    if (!email.includes('@')) { setError('E-mail invalide'); return }
    setBusy(true)
    const r = await api('/auth/otp/send', { method: 'POST', body: JSON.stringify({ email }) })
    setBusy(false)
    if (r.error) { setError(r.error); return }
    setIsNew(r.isNew); setPreview(r.previewCode || ''); setStep('otp')
  }
  const verify = async () => {
    setError('')
    if (code.length < 6) { setError('Entre les 6 chiffres'); return }
    setBusy(true)
    const r = await api('/auth/otp/verify', { method: 'POST', body: JSON.stringify({ email, code, name: name || undefined }) })
    setBusy(false)
    if (r.error) { setError(r.error); return }
    setToken(r.token)
    onAuthed(r.user, r.isNew)
  }

  return (
    <div className="min-h-[100dvh] bg-app-gradient flex items-center justify-center p-4">
      <Glass sheen strong className="w-full max-w-[440px] p-7">
        <div className="w-16 h-16 rounded-3xl grid place-items-center mb-6 float-slow" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
          <span className="font-display italic text-gold text-4xl leading-none">D</span>
        </div>
        <AnimatePresence mode="wait">
          {step === 'email' ? (
            <motion.div key="email" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
              <h1 className="font-display text-4xl leading-tight mb-2">Bienvenue sur DIVARC</h1>
              <p className="text-muted-foreground mb-6 leading-relaxed">Connexion sécurisée par code e-mail. Pas de mot de passe.</p>
              <label className="text-xs text-muted-foreground">Ton e-mail</label>
              <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/60 px-4 py-3 mt-1.5 mb-2">
                <Mail size={18} className="text-muted-foreground" />
                <input type="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendCode()}
                  placeholder="toi@exemple.fr" className="flex-1 bg-transparent outline-none text-sm" />
              </div>
              {error && <p className="text-xs text-destructive mb-2">{error}</p>}
              <PrimaryBtn onClick={sendCode} full disabled={busy}>
                {busy ? <RefreshCw className="animate-spin" size={18} /> : <>Recevoir mon code <ChevronRight size={18} /></>}
              </PrimaryBtn>
              <p className="text-center text-xs text-muted-foreground mt-4">Conforme RGPD · Hébergé dans l'UE</p>
            </motion.div>
          ) : (
            <motion.div key="otp" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
              <button onClick={() => { setStep('email'); setCode(''); setError('') }} className="text-sm text-muted-foreground flex items-center gap-1 mb-4"><ArrowLeft size={15} /> Modifier l'e-mail</button>
              <h1 className="font-display text-3xl leading-tight mb-1.5">Entre ton code</h1>
              <p className="text-muted-foreground mb-5 text-sm">Envoyé à <b className="text-foreground">{email}</b></p>
              {preview && (
                <div className="mb-4 rounded-2xl bg-gold/12 border border-gold/30 px-4 py-2.5 text-sm flex items-center gap-2">
                  <Info size={15} className="text-gold" /> Mode aperçu — ton code : <b className="font-grotesk tracking-widest text-gold">{preview}</b>
                </div>
              )}
              <div className="flex justify-center mb-4">
                <InputOTP maxLength={6} value={code} onChange={setCode}>
                  <InputOTPGroup>
                    <InputOTPSlot index={0} /><InputOTPSlot index={1} /><InputOTPSlot index={2} />
                    <InputOTPSlot index={3} /><InputOTPSlot index={4} /><InputOTPSlot index={5} />
                  </InputOTPGroup>
                </InputOTP>
              </div>
              {isNew && (
                <div className="mb-4">
                  <label className="text-xs text-muted-foreground">Ton prénom & nom</label>
                  <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex. Camille Dubois"
                    className="w-full rounded-2xl border border-border bg-card/60 px-4 py-3 mt-1.5 text-sm" />
                </div>
              )}
              {error && <p className="text-xs text-destructive mb-2">{error}</p>}
              <PrimaryBtn onClick={verify} full disabled={busy}>
                {busy ? <RefreshCw className="animate-spin" size={18} /> : <><Sparkles size={16} /> {isNew ? 'Créer mon compte' : 'Se connecter'}</>}
              </PrimaryBtn>
              <button onClick={sendCode} className="w-full text-center text-xs text-muted-foreground mt-4">Renvoyer le code</button>
            </motion.div>
          )}
        </AnimatePresence>
      </Glass>
    </div>
  )
}
const StepHead = ({ icon, title, sub }) => (
  <div className="mb-6">
    <div className="w-12 h-12 rounded-2xl grid place-items-center mb-4 bg-primary/10 text-primary">{icon}</div>
    <h2 className="font-display text-3xl leading-tight mb-1.5">{title}</h2>
    <p className="text-sm text-muted-foreground leading-relaxed">{sub}</p>
  </div>
)

/* ============================= buttons ============================= */
const PrimaryBtn = ({ children, onClick, full, disabled, gold }) => (
  <button onClick={onClick} disabled={disabled}
    className={cx('press inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3.5 font-semibold text-white shadow-lg transition-opacity disabled:opacity-40',
      full && 'w-full')}
    style={{ background: gold ? 'linear-gradient(135deg,#F0CE7E,#E2AA2B,#B98514)' : 'linear-gradient(135deg,#4353F0,#2C39C7)',
      color: gold ? '#14162B' : '#fff' }}>
    {children}
  </button>
)
const GhostBtn = ({ children, onClick, active }) => (
  <button onClick={onClick}
    className={cx('press inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 font-medium border transition-colors',
      active ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-foreground')}>
    {children}
  </button>
)

/* ============================= tab bar ============================= */
const TABS = [
  { id: 'hub', label: 'Hub', icon: Home },
  { id: 'messages', label: 'Messages', icon: MessageCircle },
  { id: 'qr', label: 'QR', icon: QrCode, center: true },
  { id: 'discover', label: 'Découvrir', icon: Compass },
  { id: 'profile', label: 'Profil', icon: User },
]
function TabBar({ active, onChange }) {
  return (
    <div className="fixed bottom-0 inset-x-0 z-40 pb-[max(env(safe-area-inset-bottom),12px)] pt-2 px-3 pointer-events-none">
      <Glass strong className="mx-auto max-w-md flex items-end justify-around px-2 py-2 pointer-events-auto">
        {TABS.map((t) => {
          const Icon = t.icon
          const on = active === t.id
          if (t.center) {
            return (
              <button key={t.id} onClick={() => onChange(t.id)} aria-label={t.label}
                className="press -mt-7 w-14 h-14 rounded-full grid place-items-center text-white shadow-xl"
                style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
                <Icon size={24} />
              </button>
            )
          }
          return (
            <button key={t.id} onClick={() => onChange(t.id)} aria-label={t.label} aria-current={on}
              className={cx('press flex flex-col items-center gap-1 px-3 py-1.5 rounded-xl min-w-[56px]', on ? 'text-primary' : 'text-muted-foreground')}>
              <Icon size={21} strokeWidth={on ? 2.4 : 2} />
              <span className="text-[10px] font-medium">{t.label}</span>
            </button>
          )
        })}
      </Glass>
    </div>
  )
}

/* ============================= HUB ============================= */
function Hub({ user, wallet, txs, mask, setMask, onAction, onTab }) {
  const hour = new Date().getHours()
  const greet = hour < 12 ? 'Bonjour' : hour < 18 ? 'Bel après-midi' : 'Bonsoir'
  const actions = [
    { id: 'send', label: 'Envoyer', icon: ArrowUpRight, c: '#4353F0' },
    { id: 'receive', label: 'Recevoir', icon: ArrowDownLeft, c: '#3FB68B' },
    { id: 'qr', label: 'QR', icon: QrCode, c: '#9B5DE5' },
    { id: 'enveloppe', label: 'Enveloppe', icon: Gift, c: '#E2AA2B' },
  ]
  return (
    <Screen>
      <div className="cascade space-y-5">
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-3">
            <Avatar c={user} size={44} />
            <div>
              <div className="text-xs text-muted-foreground">{greet},</div>
              <div className="font-semibold leading-tight">{user?.name?.split(' ')[0]}</div>
            </div>
          </div>
          <Glass className="w-10 h-10 grid place-items-center press"><Bell size={18} /></Glass>
        </div>

        {/* balance hero */}
        <Glass sheen className="p-6 relative">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-muted-foreground">Solde disponible</span>
            <button onClick={() => setMask((m) => !m)} aria-label="Mode Confiance"
              className="press w-8 h-8 grid place-items-center rounded-full bg-muted/60 text-muted-foreground">
              {mask ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <div className="flex items-end gap-2 mb-4">
            <Amount cents={wallet?.balanceCents || 0} mask={mask} className="text-5xl" />
            <span className="gold-text font-display text-3xl mb-1">€</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Pill className="bg-primary/10 text-primary"><Zap size={12} /> SEPA Instant</Pill>
            <Pill className="bg-green-500/10 text-green-600 dark:text-green-400"><Shield size={12} /> Protégé</Pill>
          </div>
        </Glass>

        {/* quick actions */}
        <div className="grid grid-cols-4 gap-3">
          {actions.map((a) => (
            <button key={a.id} onClick={() => onAction(a.id)} className="press flex flex-col items-center gap-2">
              <Glass className="w-full aspect-square grid place-items-center" style={{ color: a.c }}>
                <a.icon size={22} />
              </Glass>
              <span className="text-[11px] font-medium">{a.label}</span>
            </button>
          ))}
        </div>

        {/* carbon */}
        <Glass className="p-4 flex items-center gap-4">
          <div className="w-11 h-11 rounded-2xl grid place-items-center bg-green-500/12 text-green-600 dark:text-green-400"><Leaf size={20} /></div>
          <div className="flex-1">
            <div className="text-sm font-semibold">Empreinte carbone</div>
            <div className="text-xs text-muted-foreground">{wallet?.carbonMonthKg} kg CO₂ ce mois — 12% de moins qu\u2019en mai</div>
          </div>
          <ChevronRight size={18} className="text-muted-foreground" />
        </Glass>

        {/* mini apps preview */}
        <div>
          <SectionTitle title="Mini-apps" action="Tout voir" onAction={() => onTab('discover')} />
          <div className="grid grid-cols-4 gap-3">
            {MINIAPPS.slice(0, 4).map((m) => (
              <button key={m.id} onClick={() => onTab('discover')} className="press flex flex-col items-center gap-1.5">
                <div className="w-full aspect-square rounded-2xl grid place-items-center text-white shadow" style={{ background: m.grad }}>
                  <m.icon size={22} />
                </div>
                <span className="text-[10px] font-medium text-center leading-tight">{m.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* recent activity */}
        <div>
          <SectionTitle title="Activité récente" action="Wallet" onAction={() => onTab('wallet')} />
          <Glass className="divide-y divide-border/60">
            {txs?.slice(0, 4).map((t) => <TxRow key={t.id} t={t} mask={mask} />)}
          </Glass>
        </div>

        {/* social teaser */}
        <button onClick={() => onTab('social')} className="press w-full text-left">
          <Glass sheen className="p-5 flex items-center gap-4 relative overflow-hidden">
            <div className="w-12 h-12 rounded-2xl grid place-items-center text-white" style={{ background: 'linear-gradient(135deg,#F15BB5,#9B5DE5)' }}><Play size={20} /></div>
            <div className="flex-1">
              <div className="font-semibold">DIVARC Social</div>
              <div className="text-xs text-muted-foreground">Vidéos, algorithme transparent, achats en 1 tap</div>
            </div>
            <Pill className="bg-gold/15 text-gold">Bientôt</Pill>
          </Glass>
        </button>
      </div>
    </Screen>
  )
}

/* ============================= WALLET ============================= */
function Wallet({ wallet, txs, mask, setMask, onAction }) {
  const actions = [
    { id: 'send', label: 'Envoyer', icon: ArrowUpRight },
    { id: 'receive', label: 'Recevoir', icon: ArrowDownLeft },
    { id: 'qr', label: 'QR', icon: QrCode },
    { id: 'enveloppe', label: 'Enveloppe', icon: Gift },
    { id: 'split', label: 'Diviser', icon: Split },
  ]
  return (
    <Screen>
      <div className="cascade space-y-5">
        <div className="flex items-center justify-between pt-2">
          <h1 className="font-display text-3xl">Wallet</h1>
          <button onClick={() => setMask((m) => !m)} className="press w-9 h-9 grid place-items-center rounded-full bg-muted/60 text-muted-foreground" aria-label="Mode Confiance">
            {mask ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        </div>

        <Glass sheen className="p-6 text-center relative">
          <span className="text-sm text-muted-foreground">Solde total</span>
          <div className="flex items-end justify-center gap-2 my-2">
            <Amount cents={wallet?.balanceCents || 0} mask={mask} className="text-6xl" />
            <span className="gold-text font-display text-4xl mb-1.5">€</span>
          </div>
          <Pill className="bg-primary/10 text-primary"><Zap size={12} /> SEPA Instant · ~10s</Pill>
        </Glass>

        <div className="grid grid-cols-5 gap-2">
          {actions.map((a) => (
            <button key={a.id} onClick={() => onAction(a.id)} className="press flex flex-col items-center gap-1.5">
              <Glass className="w-full aspect-square grid place-items-center text-primary"><a.icon size={20} /></Glass>
              <span className="text-[10px] font-medium">{a.label}</span>
            </button>
          ))}
        </div>

        {/* Coffres */}
        <div>
          <SectionTitle title="Coffres" action="+ Nouveau" onAction={() => onAction('coffre')} />
          <div className="space-y-3">
            {wallet?.coffres?.map((c) => {
              const pct = Math.min(100, Math.round((c.balanceCents / c.goalCents) * 100))
              return (
                <Glass key={c.id} className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-11 h-11 rounded-2xl grid place-items-center text-xl" style={{ background: `${c.color}1e` }}>{c.emoji}</div>
                    <div className="flex-1">
                      <div className="font-semibold text-sm">{c.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {c.rule === 'round_up' ? 'Arrondi chaque dépense' : 'Épargne à la réception'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-display tabular text-sm"><Amount cents={c.balanceCents} mask={mask} /> €</div>
                      <div className="text-[11px] text-muted-foreground">/ {eur(c.goalCents, mask)} €</div>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ background: c.color }}
                      initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }} />
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-1.5">{pct}% de l\u2019objectif</div>
                </Glass>
              )
            })}
          </div>
        </div>

        {/* transactions */}
        <div>
          <SectionTitle title="Transactions" />
          <Glass className="divide-y divide-border/60">
            {txs?.map((t) => <TxRow key={t.id} t={t} mask={mask} showRoute />)}
          </Glass>
        </div>
      </div>
    </Screen>
  )
}

const TxRow = ({ t, mask, showRoute }) => (
  <div className="flex items-center gap-3 p-3.5">
    <div className="w-10 h-10 rounded-2xl grid place-items-center text-lg bg-muted/60">{t.icon}</div>
    <div className="flex-1 min-w-0">
      <div className="font-medium text-sm truncate">{t.label}</div>
      <div className="text-xs text-muted-foreground flex items-center gap-1.5">
        {t.category}
        {showRoute && t.route && <Pill className="bg-primary/10 text-primary !py-0 !text-[10px]"><Zap size={10} /> {t.route}</Pill>}
      </div>
    </div>
    <div className="text-right">
      <div className={cx('font-display tabular text-sm', t.amountCents > 0 ? 'text-green-600 dark:text-green-400' : 'text-foreground')}>
        <Amount cents={t.amountCents} mask={mask} sign /> €
      </div>
      {t.carbonKg > 0 && <div className="text-[10px] text-muted-foreground flex items-center justify-end gap-0.5"><Leaf size={9} /> {t.carbonKg} kg</div>}
    </div>
  </div>
)

/* ============================= SEND overlay ============================= */
function SendSheet({ contacts, wallet, onClose, onSent }) {
  const [amount, setAmount] = useState(0) // cents
  const [target, setTarget] = useState(null)
  const [phase, setPhase] = useState('amount') // amount -> confirm -> success
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  const press = (d) => {
    if (d === 'del') return setAmount((a) => Math.floor(a / 10))
    setAmount((a) => Math.min(a * 10 + d, 99999999))
  }
  const after = (wallet?.balanceCents || 0) - amount
  const canSend = amount > 0 && after >= 0

  const confirm = async () => {
    setBusy(true)
    const r = await api('/send', { method: 'POST', body: JSON.stringify({
      toHandle: target?.handle, toName: target?.name, amountCents: amount, route: 'A2A',
      idempotencyKey: `${target?.handle}-${amount}-${Date.now()}`,
    }) })
    setBusy(false)
    if (r.error) { alert(r.error); return }
    setResult(r)
    setPhase('success')
    onSent(r)
  }

  return (
    <Sheet onClose={onClose} title="Envoyer">
      <AnimatePresence mode="wait">
        {phase === 'amount' && (
          <motion.div key="a" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {/* recipient */}
            <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1 mb-5">
              {contacts?.map((c) => (
                <button key={c.id} onClick={() => setTarget(c)}
                  className={cx('press flex flex-col items-center gap-1.5 min-w-[64px]', target?.id === c.id && 'scale-105')}>
                  <div className={cx('rounded-full p-0.5', target?.id === c.id ? 'ring-2 ring-primary' : '')}>
                    <Avatar c={c} size={52} />
                  </div>
                  <span className="text-[10px] font-medium truncate w-full text-center">{c.name.split(' ')[0]}</span>
                </button>
              ))}
            </div>

            <div className="text-center my-6">
              <div className="text-xs text-muted-foreground mb-1">
                {target ? `À ${target.name}` : 'Choisis un destinataire'}
              </div>
              <div className="flex items-end justify-center gap-1">
                <span className="font-display text-6xl tabular">{eur(amount)}</span>
                <span className="gold-text font-display text-4xl mb-1">€</span>
              </div>
              <div className="text-xs text-muted-foreground mt-2">
                Solde après envoi : <span className={cx('font-medium', after < 0 && 'text-destructive')}>{eur(after)} €</span>
              </div>
            </div>

            <Keypad onPress={press} />
            <div className="mt-4">
              <PrimaryBtn onClick={() => setPhase('confirm')} full disabled={!canSend || !target}>
                Continuer <ChevronRight size={18} />
              </PrimaryBtn>
            </div>
          </motion.div>
        )}

        {phase === 'confirm' && (
          <motion.div key="c" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="text-center py-4">
            <Avatar c={target} size={72} />
            <div className="mt-4 mb-1 text-sm text-muted-foreground">Tu envoies à</div>
            <div className="font-semibold text-lg">{target?.name} · {target?.handle}</div>
            <div className="my-5"><span className="font-display text-5xl tabular">{eur(amount)}</span> <span className="gold-text font-display text-3xl">€</span></div>
            <Glass className="p-3 flex items-center justify-between text-sm mb-5">
              <span className="flex items-center gap-2 text-muted-foreground"><Zap size={14} className="text-primary" /> Route la moins chère</span>
              <span className="font-medium">A2A gratuit · ~10s</span>
            </Glass>
            <PrimaryBtn onClick={confirm} full disabled={busy}>
              {busy ? <RefreshCw className="animate-spin" size={18} /> : <><Lock size={16} /> Confirmer l\u2019envoi</>}
            </PrimaryBtn>
            <button onClick={() => setPhase('amount')} className="mt-3 text-sm text-muted-foreground">Modifier</button>
          </motion.div>
        )}

        {phase === 'success' && (
          <motion.div key="s" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-8">
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 200, damping: 12 }}
              className="w-24 h-24 rounded-full grid place-items-center mx-auto mb-6 text-white" style={{ background: 'linear-gradient(135deg,#3FB68B,#2E9370)' }}>
              <Check size={44} strokeWidth={3} />
            </motion.div>
            <div className="font-display text-4xl mb-2">{eur(amount)} € envoyés</div>
            <p className="text-muted-foreground mb-8">À {target?.name} · reçu en ~8s ⚡</p>
            <PrimaryBtn onClick={onClose} full>Terminé</PrimaryBtn>
          </motion.div>
        )}
      </AnimatePresence>
    </Sheet>
  )
}

const Keypad = ({ onPress }) => {
  const keys = [1, 2, 3, 4, 5, 6, 7, 8, 9, '00', 0, 'del']
  return (
    <div className="grid grid-cols-3 gap-2">
      {keys.map((k) => (
        <button key={k} onClick={() => onPress(k === 'del' ? 'del' : k === '00' ? 0 : Number(k)) || (k === '00' && onPress(0))}
          className="press h-14 rounded-2xl bg-card/60 border border-border font-display text-2xl grid place-items-center">
          {k === 'del' ? <Delete size={22} /> : k}
        </button>
      ))}
    </div>
  )
}

/* ============================= ENVELOPPE (hongbao) ============================= */
function EnveloppeSheet({ wallet, onClose, onDone }) {
  const [phase, setPhase] = useState('setup') // setup -> created -> opening -> revealed
  const [total, setTotal] = useState(2000)
  const [count, setCount] = useState(3)
  const [msg, setMsg] = useState('Bonne chance ! 🧧')
  const [env, setEnv] = useState(null)
  const [reveal, setReveal] = useState(null)
  const [busy, setBusy] = useState(false)

  const create = async () => {
    setBusy(true)
    const r = await api('/enveloppe/create', { method: 'POST', body: JSON.stringify({ totalCents: total, count, message: msg }) })
    setBusy(false)
    if (r.error) { alert(r.error); return }
    setEnv(r.enveloppe)
    onDone(r)
    setPhase('created')
  }
  const open = async () => {
    setPhase('opening')
    const r = await api('/enveloppe/open', { method: 'POST', body: JSON.stringify({ enveloppeId: env.id, claimer: 'toi' }) })
    setTimeout(() => { setReveal(r); setPhase('revealed') }, 650)
  }

  return (
    <Sheet onClose={onClose} title="Enveloppe" gold>
      <AnimatePresence mode="wait">
        {phase === 'setup' && (
          <motion.div key="setup" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="text-center mb-6">
              <div className="text-7xl mb-2 float-slow">🧧</div>
              <p className="text-sm text-muted-foreground">Envoie une enveloppe surprise. Montant aléatoire pour chaque part.</p>
            </div>
            <label className="text-xs text-muted-foreground">Montant total</label>
            <div className="flex items-end gap-1 justify-center my-2">
              <span className="font-display text-5xl tabular">{eur(total)}</span><span className="gold-text font-display text-3xl">€</span>
            </div>
            <input type="range" min="500" max="20000" step="500" value={total} onChange={(e) => setTotal(Number(e.target.value))}
              className="w-full accent-[#E2AA2B]" />
            <label className="text-xs text-muted-foreground block mt-5 mb-2">Nombre de parts</label>
            <div className="flex gap-2">
              {[1, 3, 5, 8].map((n) => (
                <button key={n} onClick={() => setCount(n)}
                  className={cx('press flex-1 py-3 rounded-2xl border font-semibold', count === n ? 'bg-gold text-ink border-gold' : 'bg-card/60 border-border')}>
                  {n}
                </button>
              ))}
            </div>
            <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Ton message…"
              className="w-full mt-5 rounded-2xl border border-border bg-card/60 px-4 py-3 text-sm" />
            <div className="mt-6">
              <PrimaryBtn gold onClick={create} full disabled={busy}>
                {busy ? <RefreshCw className="animate-spin" size={18} /> : <><Gift size={18} /> Créer l\u2019enveloppe</>}
              </PrimaryBtn>
            </div>
          </motion.div>
        )}

        {phase === 'created' && (
          <motion.div key="created" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-4">Enveloppe prête ! Touche pour l\u2019ouvrir (aperçu de l\u2019expérience de tes amis).</p>
            <HongbaoCard message={env.message} onOpen={open} />
          </motion.div>
        )}

        {phase === 'opening' && (
          <motion.div key="opening" className="py-10 grid place-items-center">
            <HongbaoCard message={env.message} opening />
          </motion.div>
        )}

        {phase === 'revealed' && (
          <motion.div key="revealed" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-6 relative">
            <GoldParticles />
            <motion.div initial={{ scale: 0, rotate: -8 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: 'spring', stiffness: 180, damping: 12 }}>
              <div className="text-6xl mb-3">🧧</div>
              <div className="text-sm text-muted-foreground mb-1">{reveal.message}</div>
              <div className="my-3"><span className="gold-text font-display text-6xl tabular">{eur(reveal.amountCents)}</span> <span className="gold-text font-display text-4xl">€</span></div>
              <p className="text-xs text-muted-foreground mb-8">
                {reveal.remaining} part{reveal.remaining > 1 ? 's' : ''} restante{reveal.remaining > 1 ? 's' : ''} sur {reveal.total}
              </p>
              <PrimaryBtn gold onClick={onClose} full>Encaisser dans mon wallet</PrimaryBtn>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </Sheet>
  )
}

function HongbaoCard({ message, onOpen, opening }) {
  return (
    <button onClick={onOpen} disabled={opening} className="press relative mx-auto block" style={{ width: 220, height: 300 }}>
      <div className="absolute inset-0 rounded-[26px] shadow-2xl overflow-hidden"
        style={{ background: 'linear-gradient(160deg,#B98514,#E2AA2B 40%,#F0CE7E)' }}>
        <div className="absolute inset-0 opacity-30" style={{ background: 'radial-gradient(circle at 50% 30%, rgba(255,255,255,.6), transparent 60%)' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-white/25 grid place-items-center text-3xl">🧧</div>
        <div className="absolute bottom-6 inset-x-0 text-center text-ink/80 text-sm font-medium px-4">{message}</div>
      </div>
      {/* flap */}
      <motion.div className="absolute top-0 inset-x-0 origin-top rounded-t-[26px]" style={{ height: 150, background: 'linear-gradient(160deg,#D89A1E,#B98514)', transformStyle: 'preserve-3d' }}
        animate={opening ? { rotateX: -160 } : { rotateX: 0 }} transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}>
        <div className="absolute inset-0 grid place-items-center text-4xl">✨</div>
      </motion.div>
      {!opening && <div className="absolute -bottom-8 inset-x-0 text-xs text-muted-foreground">Touche pour ouvrir</div>}
    </button>
  )
}

function GoldParticles() {
  const parts = Array.from({ length: 18 })
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {parts.map((_, i) => (
        <motion.div key={i} className="absolute w-2 h-2 rounded-sm"
          style={{ background: i % 2 ? '#E2AA2B' : '#F0CE7E', left: `${50}%`, top: '40%' }}
          initial={{ opacity: 1, scale: 1 }}
          animate={{ x: (Math.random() - 0.5) * 320, y: (Math.random() - 0.5) * 360, opacity: 0, rotate: Math.random() * 360 }}
          transition={{ duration: 1.1, ease: 'easeOut' }} />
      ))}
    </div>
  )
}

/* ============================= QR ============================= */
function QRScreen({ user }) {
  const [mode, setMode] = useState('mine')
  const [seconds, setSeconds] = useState(600)
  useEffect(() => {
    if (mode !== 'mine') return
    const t = setInterval(() => setSeconds((s) => (s > 0 ? s - 1 : 600)), 1000)
    return () => clearInterval(t)
  }, [mode])
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return (
    <Screen>
      <div className="cascade space-y-5">
        <h1 className="font-display text-3xl pt-2">QR universel</h1>
        <div className="flex gap-2 p-1 rounded-2xl bg-muted/60">
          {[['mine', 'Mon QR'], ['scan', 'Scanner']].map(([id, label]) => (
            <button key={id} onClick={() => setMode(id)}
              className={cx('press flex-1 py-2.5 rounded-xl font-medium text-sm', mode === id ? 'bg-card shadow text-foreground' : 'text-muted-foreground')}>
              {label}
            </button>
          ))}
        </div>

        {mode === 'mine' ? (
          <Glass sheen className="p-6 text-center">
            <div className="relative w-56 h-56 mx-auto mb-4">
              <svg viewBox="0 0 100 100" className="w-full h-full rounded-2xl bg-white p-3">
                <g fill="#14162B">
                  {Array.from({ length: 12 }).map((_, r) => Array.from({ length: 12 }).map((_, c) =>
                    (Math.random() > 0.5 || (r < 3 && c < 3) || (r < 3 && c > 8) || (r > 8 && c < 3)) &&
                    <rect key={`${r}-${c}`} x={c * 8 + 2} y={r * 8 + 2} width="7" height="7" rx="1.5" />
                  ))}
                </g>
              </svg>
              <div className="absolute inset-0 grid place-items-center">
                <div className="w-12 h-12 rounded-2xl grid place-items-center text-white font-display italic text-2xl" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>D</div>
              </div>
            </div>
            <div className="font-semibold">{user?.name} · {user?.handle}</div>
            <div className="flex items-center justify-center gap-2 mt-3 text-sm text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              QR à usage unique · expire dans {mm}:{ss}
            </div>
            <div className="flex gap-2 mt-4">
              <GhostBtn onClick={() => setSeconds(600)}><RefreshCw size={15} /> Régénérer</GhostBtn>
              <PrimaryBtn onClick={() => {}} full><Users size={16} /> QR de groupe</PrimaryBtn>
            </div>
          </Glass>
        ) : (
          <Glass className="p-6">
            <div className="aspect-square rounded-2xl bg-ink/90 grid place-items-center relative overflow-hidden">
              <motion.div className="absolute inset-x-6 h-0.5 bg-primary shadow-[0_0_18px_#4353F0]"
                animate={{ top: ['15%', '85%', '15%'] }} transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }} />
              <div className="w-40 h-40 border-2 border-white/40 rounded-2xl" />
              <ScanLine className="absolute text-white/30" size={40} />
            </div>
            <Glass className="mt-4 p-3 flex items-center gap-3 !bg-green-500/10">
              <Shield size={18} className="text-green-600 dark:text-green-400" />
              <div className="text-xs"><b>Scam shield</b> — la vraie destination sera affichée avant toute action.</div>
            </Glass>
            <GhostBtn onClick={() => {}}><Plus size={15} /> Importer une image</GhostBtn>
          </Glass>
        )}
      </div>
    </Screen>
  )
}

/* ============================= DISCOVER ============================= */
const MINIAPPS = [
  { id: 'delivery', name: 'Livraison', cat: 'Repas', icon: Utensils, grad: 'linear-gradient(135deg,#F15BB5,#F97C4E)', why: 'Souvent utilisée le midi' },
  { id: 'messages', name: 'Messages', cat: 'Social', icon: MessageCircle, grad: 'linear-gradient(135deg,#4353F0,#6E7BF5)', why: 'Ta messagerie DIVARC' },
  { id: 'mobility', name: 'Mobilité', cat: 'Transport', icon: Car, grad: 'linear-gradient(135deg,#3FB68B,#7BE0BE)', why: 'VTC & transports proches' },
  { id: 'wallet', name: 'Wallet', cat: 'Finance', icon: WalletIcon, grad: 'linear-gradient(135deg,#E2AA2B,#F0CE7E)', why: 'Ton portefeuille' },
  { id: 'shops', name: 'Boutiques', cat: 'Shopping', icon: ShoppingBag, grad: 'linear-gradient(135deg,#9B5DE5,#C89BF5)', why: 'Catalogue local' },
  { id: 'tickets', name: 'Billetterie', cat: 'Événements', icon: Ticket, grad: 'linear-gradient(135deg,#00BBF9,#7ADBFF)', why: 'Événements ce week-end' },
  { id: 'health', name: 'Santé', cat: 'Santé', icon: HeartPulse, grad: 'linear-gradient(135deg,#EF476F,#FF8FA8)', why: 'RDV & téléconsultation' },
  { id: 'assistant', name: 'Assistant', cat: 'IA', icon: Sparkles, grad: 'linear-gradient(135deg,#2C39C7,#4353F0)', why: 'Copilote qui agit' },
]
function Discover({ onTab }) {
  const [why, setWhy] = useState(null)
  const cats = ['Tout', 'Repas', 'Transport', 'Shopping', 'Événements', 'Santé']
  const [cat, setCat] = useState('Tout')
  const list = MINIAPPS.filter((m) => cat === 'Tout' || m.cat === cat)
  return (
    <Screen>
      <div className="cascade space-y-5">
        <div className="flex items-center justify-between pt-2">
          <h1 className="font-display text-3xl">Découvrir</h1>
          <Glass className="w-10 h-10 grid place-items-center press"><Search size={18} /></Glass>
        </div>
        <Glass className="p-3 flex items-center gap-2 text-sm text-muted-foreground">
          <Info size={16} className="text-primary shrink-0" />
          <span>Classement <b className="text-foreground">transparent</b> et paramétrable (anti-DMA). Touche « Pourquoi ? » sur chaque app.</span>
        </Glass>
        <div className="flex gap-2 overflow-x-auto no-scrollbar">
          {cats.map((c) => (
            <button key={c} onClick={() => setCat(c)}
              className={cx('press whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium border', cat === c ? 'bg-primary text-white border-primary' : 'bg-card/60 border-border text-muted-foreground')}>
              {c}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-4">
          {list.map((m) => (
            <div key={m.id} className="flex flex-col items-center gap-2">
              <div className="press w-full aspect-square rounded-3xl grid place-items-center text-white shadow-lg relative" style={{ background: m.grad }}>
                <m.icon size={28} />
                <button onClick={() => setWhy(m)} aria-label="Pourquoi cette app"
                  className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-card border border-border grid place-items-center text-[10px] font-bold text-primary shadow">?</button>
              </div>
              <span className="text-[11px] font-medium">{m.name}</span>
            </div>
          ))}
        </div>
        <button onClick={() => onTab && onTab('social')} className="press w-full text-left"><SocialTeaser /></button>
      </div>

      <AnimatePresence>
        {why && (
          <Sheet onClose={() => setWhy(null)} title="Pourquoi cette app ?">
            <div className="text-center py-4">
              <div className="w-16 h-16 rounded-3xl grid place-items-center text-white mx-auto mb-4" style={{ background: why.grad }}><why.icon size={30} /></div>
              <div className="font-semibold text-lg mb-2">{why.name}</div>
              <p className="text-sm text-muted-foreground mb-4">Recommandée car : <b className="text-foreground">{why.why}</b>. Aucun paiement pour être mieux classée.</p>
              <GhostBtn onClick={() => setWhy(null)}><Settings2 size={15} /> Régler mes préférences</GhostBtn>
            </div>
          </Sheet>
        )}
      </AnimatePresence>
    </Screen>
  )
}
const SocialTeaser = () => (
  <Glass sheen className="p-5 relative overflow-hidden">
    <div className="flex items-center gap-3 mb-3">
      <div className="w-11 h-11 rounded-2xl grid place-items-center text-white" style={{ background: 'linear-gradient(135deg,#F15BB5,#9B5DE5)' }}><Play size={20} /></div>
      <div><div className="font-semibold">DIVARC Social</div><div className="text-xs text-muted-foreground">Réseau vidéo · algorithme transparent</div></div>
    </div>
    <p className="text-sm text-muted-foreground">Vidéos achetables en 1 tap, pourboires au créateur, « Pourquoi cette vidéo ? » et flux chronologique au choix.</p>
  </Glass>
)

/* ============================= PROFILE ============================= */
function Profile({ user, theme, setTheme, mask, setMask, onLogout }) {
  const accesses = [
    { name: 'Livraison', pseudo: 'divarc-a91f', since: '12 mai', icon: Utensils, c: '#F15BB5' },
    { name: 'Mobilité', pseudo: 'divarc-7c02', since: '3 avr', icon: Car, c: '#3FB68B' },
    { name: 'Billetterie', pseudo: 'divarc-2be8', since: '28 fév', icon: Ticket, c: '#00BBF9' },
  ]
  const [revoked, setRevoked] = useState([])
  return (
    <Screen>
      <div className="cascade space-y-5">
        <h1 className="font-display text-3xl pt-2">Profil & Confiance</h1>

        <Glass sheen className="p-5 flex items-center gap-4">
          <Avatar c={user} size={60} />
          <div className="flex-1">
            <div className="font-semibold text-lg leading-tight">{user?.name}</div>
            <div className="text-sm text-muted-foreground">{user?.handle}</div>
            <Pill className="bg-green-500/12 text-green-600 dark:text-green-400 mt-1"><BadgeCheck size={12} /> Vérifié {user?.kyc}</Pill>
          </div>
          <QrCode size={26} className="text-muted-foreground" />
        </Glass>

        {/* security */}
        <div>
          <SectionTitle title="Centre de sécurité" />
          <Glass className="divide-y divide-border/60">
            <Row icon={<Fingerprint size={18} />} title="Passkeys" sub="1 passkey active" ok />
            <Row icon={<Shield size={18} />} title="Double authentification" sub="Activée" ok />
            <Row icon={<CreditCard size={18} />} title="Appareils connectés" sub="Chrome sur macOS · France" />
          </Glass>
        </div>

        {/* who sees what */}
        <div>
          <SectionTitle title="Qui voit quoi" />
          <Glass className="divide-y divide-border/60">
            {accesses.map((a) => {
              const isRev = revoked.includes(a.name)
              return (
                <div key={a.name} className="flex items-center gap-3 p-3.5">
                  <div className="w-10 h-10 rounded-2xl grid place-items-center text-white" style={{ background: a.c }}><a.icon size={18} /></div>
                  <div className="flex-1">
                    <div className="font-medium text-sm">{a.name}</div>
                    <div className="text-xs text-muted-foreground">Pseudonyme {a.pseudo} · depuis {a.since}</div>
                  </div>
                  <button onClick={() => setRevoked((p) => isRev ? p.filter((x) => x !== a.name) : [...p, a.name])}
                    className={cx('press text-xs font-semibold px-3 py-1.5 rounded-full', isRev ? 'bg-muted text-muted-foreground' : 'bg-destructive/10 text-destructive')}>
                    {isRev ? 'Annuler' : 'Révoquer'}
                  </button>
                </div>
              )
            })}
          </Glass>
        </div>

        {/* preferences */}
        <div>
          <SectionTitle title="Préférences" />
          <Glass className="divide-y divide-border/60">
            <div className="flex items-center justify-between p-3.5">
              <div className="flex items-center gap-3"><div className="w-10 h-10 rounded-2xl grid place-items-center bg-muted/60">{theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}</div><span className="font-medium text-sm">Thème sombre</span></div>
              <Toggle on={theme === 'dark'} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} />
            </div>
            <div className="flex items-center justify-between p-3.5">
              <div className="flex items-center gap-3"><div className="w-10 h-10 rounded-2xl grid place-items-center bg-muted/60"><EyeOff size={18} /></div><span className="font-medium text-sm">Mode Confiance (masquer montants)</span></div>
              <Toggle on={mask} onClick={() => setMask((m) => !m)} />
            </div>
            <Row icon={<Globe size={18} />} title="Langue" sub="Français" />
          </Glass>
        </div>

        {/* RGPD */}
        <div>
          <SectionTitle title="Mes données (RGPD)" />
          <div className="grid grid-cols-2 gap-3">
            <GhostBtn onClick={() => {}}><Download size={16} /> Exporter</GhostBtn>
            <button className="press inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 font-medium border border-destructive/30 bg-destructive/10 text-destructive">
              <Trash2 size={16} /> Supprimer
            </button>
          </div>
        </div>
        <button onClick={onLogout} className="press w-full inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 font-medium border border-border bg-card/60 text-muted-foreground">
          <ArrowLeft size={16} /> Se déconnecter
        </button>
        <div className="text-center text-xs text-muted-foreground pb-2">DIVARC · Hébergé dans l\u2019UE · divarc.fr</div>
      </div>
    </Screen>
  )
}
const Row = ({ icon, title, sub, ok }) => (
  <div className="flex items-center gap-3 p-3.5">
    <div className="w-10 h-10 rounded-2xl grid place-items-center bg-muted/60 text-muted-foreground">{icon}</div>
    <div className="flex-1"><div className="font-medium text-sm">{title}</div><div className="text-xs text-muted-foreground">{sub}</div></div>
    {ok ? <Pill className="bg-green-500/12 text-green-600 dark:text-green-400"><Check size={11} /> OK</Pill> : <ChevronRight size={18} className="text-muted-foreground" />}
  </div>
)
const Toggle = ({ on, onClick }) => (
  <button onClick={onClick} role="switch" aria-checked={on}
    className={cx('press w-12 h-7 rounded-full p-0.5 transition-colors', on ? 'bg-primary' : 'bg-muted')}>
    <motion.div className="w-6 h-6 rounded-full bg-white shadow" animate={{ x: on ? 20 : 0 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} />
  </button>
)

/* ============================= MESSAGES ============================= */
function Messages({ contacts }) {
  const [active, setActive] = useState(null)
  const convos = (contacts || []).map((c, i) => ({
    ...c,
    last: ['On se voit à 20h ? 🍕', 'Je t\u2019envoie ma part', 'Merci pour l\u2019enveloppe 🧧', 'Ok parfait', 'À demain !'][i % 5],
    time: ['12:40', '11:02', 'Hier', 'Lun', 'Dim'][i % 5],
    unread: i === 0 ? 2 : 0,
  }))
  useEffect(() => { if (contacts?.length && !active) setActive(convos[0]) }, [contacts])
  return (
    <div className="min-h-[100dvh] bg-app-gradient">
      <div className="mx-auto max-w-5xl px-4 pt-6 pb-28 grid md:grid-cols-[320px_1fr] gap-4">
        {/* list */}
        <div className={cx(active && 'hidden md:block')}>
          <h1 className="font-display text-3xl mb-4">Messages</h1>
          <Glass className="p-2 space-y-1">
            {convos.map((c) => (
              <button key={c.id} onClick={() => setActive(c)}
                className={cx('press w-full flex items-center gap-3 p-2.5 rounded-2xl text-left', active?.id === c.id && 'bg-primary/10')}>
                <Avatar c={c} size={46} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 font-medium text-sm">{c.name.split(' ')[0]} {c.verified && <BadgeCheck size={13} className="text-primary" />}</div>
                  <div className="text-xs text-muted-foreground truncate">{c.last}</div>
                </div>
                <div className="text-right"><div className="text-[10px] text-muted-foreground">{c.time}</div>{c.unread > 0 && <div className="mt-1 inline-grid place-items-center w-5 h-5 rounded-full bg-primary text-white text-[10px]">{c.unread}</div>}</div>
              </button>
            ))}
          </Glass>
        </div>
        {/* chat */}
        <div className={cx(!active && 'hidden md:block')}>
          {active && <ChatView c={active} onBack={() => setActive(null)} />}
        </div>
      </div>
    </div>
  )
}
function ChatView({ c, onBack }) {
  const [msgs, setMsgs] = useState([
    { me: false, t: 'Salut ! Tu as vu le resto ?' },
    { me: true, t: 'Oui carrément, on y va ce soir 🍕' },
    { pay: true, amount: 2500, status: 'reçu' },
    { me: false, t: 'Merci pour ta part ⚡' },
  ])
  const [input, setInput] = useState('')
  const ref = useRef()
  useEffect(() => { ref.current?.scrollTo(0, ref.current.scrollHeight) }, [msgs])
  const send = () => { if (!input.trim()) return; setMsgs((m) => [...m, { me: true, t: input }]); setInput('') }
  return (
    <Glass className="flex flex-col h-[calc(100dvh-120px)] md:h-[calc(100dvh-64px)]">
      <div className="flex items-center gap-3 p-4 border-b border-border/60">
        <button onClick={onBack} className="md:hidden press"><ArrowLeft size={20} /></button>
        <Avatar c={c} size={40} />
        <div className="flex-1"><div className="font-medium text-sm flex items-center gap-1">{c.name} {c.verified && <BadgeCheck size={13} className="text-primary" />}</div><div className="text-xs text-green-600 dark:text-green-400">en ligne</div></div>
        <Lock size={16} className="text-muted-foreground" title="Chiffré de bout en bout" />
      </div>
      <div ref={ref} className="flex-1 overflow-y-auto p-4 space-y-3 no-scrollbar">
        {msgs.map((m, i) => m.pay ? (
          <div key={i} className="flex justify-center">
            <Glass className="p-3 !bg-gold/10 max-w-[220px] text-center">
              <div className="text-xs text-muted-foreground mb-1">Paiement reçu</div>
              <div className="font-display text-2xl">{eur(m.amount)} €</div>
              <Pill className="bg-green-500/15 text-green-600 dark:text-green-400 mt-1"><Zap size={11} /> Encaissé ⚡8s</Pill>
            </Glass>
          </div>
        ) : (
          <div key={i} className={cx('flex', m.me ? 'justify-end' : 'justify-start')}>
            <div className={cx('max-w-[75%] px-4 py-2.5 rounded-2xl text-sm', m.me ? 'bg-primary text-white rounded-br-md' : 'bg-card border border-border rounded-bl-md')}>{m.t}</div>
          </div>
        ))}
      </div>
      <div className="p-3 border-t border-border/60 flex items-center gap-2">
        <button className="press w-10 h-10 rounded-full grid place-items-center bg-muted/60 text-primary"><Plus size={20} /></button>
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Message…" className="flex-1 rounded-full border border-border bg-card/60 px-4 py-2.5 text-sm" />
        <button onClick={send} className="press w-10 h-10 rounded-full grid place-items-center text-white" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}><SendIcon size={18} /></button>
      </div>
    </Glass>
  )
}

/* ============================= shells ============================= */
const Screen = ({ children }) => (
  <div className="min-h-[100dvh] bg-app-gradient">
    <div className="mx-auto max-w-md px-4 pt-6 pb-28">{children}</div>
  </div>
)
const SectionTitle = ({ title, action, onAction }) => (
  <div className="flex items-center justify-between mb-3">
    <h2 className="font-semibold text-[15px]">{title}</h2>
    {action && <button onClick={onAction} className="text-xs text-primary font-medium press">{action}</button>}
  </div>
)
function Sheet({ children, onClose, title, gold }) {
  return (
    <motion.div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        className="relative w-full sm:max-w-md">
        <Glass strong className="p-5 rounded-b-none sm:rounded-b-[var(--radius)] max-h-[92dvh] overflow-y-auto no-scrollbar">
          <div className="flex items-center justify-between mb-4">
            <h3 className={cx('font-display text-2xl', gold && 'gold-text')}>{title}</h3>
            <button onClick={onClose} className="press w-9 h-9 rounded-full grid place-items-center bg-muted/60"><X size={18} /></button>
          </div>
          {children}
        </Glass>
      </motion.div>
    </motion.div>
  )
}

/* ============================= APP ============================= */
function App() {
  const { theme, setTheme } = useTheme()
  const [booted, setBooted] = useState(false)
  const [tab, setTab] = useState('hub')
  const [mask, setMask] = useState(false)
  const [overlay, setOverlay] = useState(null)
  const [user, setUser] = useState(null)
  const [wallet, setWallet] = useState(null)
  const [txs, setTxs] = useState([])
  const [contacts, setContacts] = useState([])

  const load = useCallback(async () => {
    const [w, t, c] = await Promise.all([api('/wallet'), api('/transactions'), api('/contacts')])
    if (!w.error) setWallet(w)
    if (Array.isArray(t)) setTxs(t)
    if (Array.isArray(c)) setContacts(c)
  }, [])

  useEffect(() => {
    (async () => {
      if (getToken()) {
        const me = await api('/auth/me')
        if (!me.error) { setUser(me); await load() }
        else clearToken()
      }
      setBooted(true)
    })()
  }, [load])

  const onAuthed = async (u) => { setUser(u); setTab('hub'); await load() }
  const logout = async () => { await api('/auth/logout', { method: 'POST' }); clearToken(); setUser(null); setWallet(null); setTxs([]); setContacts([]) }

  const handleAction = (id) => {
    if (id === 'send') return setOverlay('send')
    if (id === 'enveloppe') return setOverlay('enveloppe')
    if (id === 'qr' || id === 'receive') return setTab('qr')
    if (id === 'split') return setOverlay('send')
    if (id === 'coffre') return setOverlay('coffre')
  }
  const goTab = (t) => { setTab(t) }

  if (!booted) return <Boot />
  if (!user) return <Login onAuthed={onAuthed} />

  return (
    <div className="font-body text-foreground">
      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
          {tab === 'hub' && <Hub user={user} wallet={wallet} txs={txs} mask={mask} setMask={setMask} onAction={handleAction} onTab={goTab} />}
          {tab === 'wallet' && <Wallet wallet={wallet} txs={txs} mask={mask} setMask={setMask} onAction={handleAction} />}
          {tab === 'messages' && <Messaging me={user} />}
          {tab === 'qr' && <QRScreen user={user} />}
          {tab === 'discover' && <Discover onTab={goTab} />}
          {tab === 'profile' && <Profile user={user} theme={theme} setTheme={setTheme} mask={mask} setMask={setMask} onLogout={logout} />}
          {tab === 'social' && <Social me={user} onBack={() => setTab('hub')} />}
        </motion.div>
      </AnimatePresence>

      {tab !== 'social' && <TabBar active={tab === 'wallet' ? 'hub' : tab} onChange={goTab} />}

      <AnimatePresence>
        {overlay === 'send' && <SendSheet contacts={contacts} wallet={wallet} onClose={() => setOverlay(null)} onSent={() => load()} />}
        {overlay === 'enveloppe' && <EnveloppeSheet wallet={wallet} onClose={() => setOverlay(null)} onDone={() => load()} />}
        {overlay === 'coffre' && <Sheet onClose={() => setOverlay(null)} title="Nouveau coffre"><ComingSoon /></Sheet>}
      </AnimatePresence>
    </div>
  )
}

const ComingSoon = () => (
  <div className="text-center py-8 text-muted-foreground"><Sparkles className="mx-auto mb-3 text-primary" /> Bientôt disponible dans la prochaine couche.</div>
)
const Boot = () => (
  <div className="min-h-[100dvh] bg-app-gradient grid place-items-center">
    <div className="text-center">
      <div className="w-16 h-16 rounded-3xl grid place-items-center mx-auto mb-4 float-slow" style={{ background: 'linear-gradient(135deg,#4353F0,#2C39C7)' }}>
        <span className="font-display italic text-gold text-4xl">D</span>
      </div>
      <div className="font-display text-2xl">DIVARC</div>
      <div className="text-sm text-muted-foreground mt-1">Chargement…</div>
    </div>
  </div>
)

export default App
