'use client'

// Arcade DIVARC — jeux de COMPÉTENCE (puits d'Éclats). Récompense déterministe par score.
import { useState, useEffect, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { X, Zap, Trophy, RefreshCw, Info, Star } from 'lucide-react'
import { api } from '@/lib/api'
import { Eclats } from './ui-kit'

const cx = (...a) => a.filter(Boolean).join(' ')
const rnd = () => Math.random()

export default function ArcadeModule({ onClose }) {
  const [home, setHome] = useState(null)
  const [view, setView] = useState('home')      // home | playing | result
  const [session, setSession] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(async () => { const r = await api('/arcade'); if (r && !r.error) setHome(r) }, [])
  useEffect(() => { load() }, [load])

  const play = async () => {
    setBusy(true); setErr('')
    const r = await api('/arcade/reflex/play', { method: 'POST' })
    setBusy(false)
    if (r.error) { setErr(r.error); return }
    setSession(r); setView('playing')
  }
  const finish = async (score) => {
    const r = await api('/arcade/reflex/score', { method: 'POST', body: JSON.stringify({ sessionId: session.sessionId, score }) })
    setResult(r.error ? { error: r.error, score } : r)
    setView('result'); load()
  }

  return (
    <motion.div className="fixed inset-0 z-[70] flex flex-col bg-app-gradient" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 pt-safe border-b border-border/60">
        <button onClick={() => (view === 'home' ? onClose() : setView('home'))} className="press" aria-label="Retour"><X size={22} /></button>
        <h1 className="font-display text-2xl flex items-center gap-2"><Zap size={20} className="text-gold" /> Arcade</h1>
        {home && <span className="ml-auto text-sm font-display"><Eclats n={home.balance} size={14} /></span>}
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-safe">
        {view === 'home' && <Home home={home} onPlay={play} busy={busy} err={err} />}
        {view === 'playing' && <ReflexGame session={session} onEnd={finish} />}
        {view === 'result' && <Result result={result} onAgain={() => setView('home')} />}
      </div>
    </motion.div>
  )
}

function Home({ home, onPlay, busy, err }) {
  const [lb, setLb] = useState(null)
  useEffect(() => { api('/arcade/reflex/leaderboard').then((r) => !r.error && setLb(r.leaderboard)) }, [])
  if (!home) return <div className="grid place-items-center py-20"><RefreshCw className="animate-spin text-muted-foreground" /></div>
  const reflex = home.games.find((g) => g.id === 'reflex')

  return (
    <div className="py-4 space-y-4">
      <div className="rounded-lg bg-primary/8 border border-primary/20 p-3 text-xs text-muted-foreground flex items-start gap-2">
        <Info size={15} className="text-primary shrink-0 mt-0.5" />
        <span>{home.notice}</span>
      </div>

      {/* Jeu Reflex */}
      <div className="rounded-lg overflow-hidden border border-border">
        <div className="p-5 text-white relative grad-gold-deep">
          <div className="mb-1"><Zap size={36} fill="currentColor" strokeWidth={0} /></div>
          <div className="font-display text-2xl">{reflex.name}</div>
          <div className="text-sm text-white/85">{reflex.desc}</div>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Ton meilleur score</span>
            <span className="font-display tabular text-lg">{reflex.myBest}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {reflex.rewards.map((t) => (
              <span key={t.scoreMin} className="text-[11px] px-2 py-1 rounded-full bg-muted/60">score ≥ {t.scoreMin} → <Eclats n={`+${t.eclats}`} size={11} /></span>
            ))}
          </div>
          {err && <p className="text-xs text-destructive">{err}</p>}
          <button onClick={onPlay} disabled={busy} className="press w-full rounded-lg py-3.5 font-semibold text-white disabled:opacity-50 grad-gold-deep">
            {busy ? <RefreshCw size={18} className="animate-spin mx-auto" /> : (reflex.freeLeft > 0 ? 'Jouer (gratuit aujourd\'hui)' : <>Jouer · <Eclats n={reflex.entryCost} size={14} /></>)}
          </button>
        </div>
      </div>

      {/* Bientôt : Mémoire */}
      <div className="rounded-lg border border-border bg-card/40 p-4 flex items-center gap-3 opacity-70">
        <div className="text-2xl">🧠</div>
        <div className="flex-1"><div className="font-medium text-sm">Mémoire Éclair</div><div className="text-xs text-muted-foreground">Jeu de mémoire · bientôt</div></div>
        <span className="text-[11px] px-2 py-1 rounded-full bg-muted/60">Bientôt</span>
      </div>

      {/* Classement hebdo */}
      <div>
        <div className="flex items-center gap-2 mb-2 px-1"><Trophy size={16} className="text-gold" /><span className="text-sm font-semibold">Classement de la semaine</span></div>
        <div className="rounded-lg border border-border bg-card/40 divide-y divide-border/60">
          {!lb ? <div className="p-4 text-center"><RefreshCw className="animate-spin text-muted-foreground mx-auto" size={18} /></div>
            : lb.length === 0 ? <div className="p-4 text-center text-sm text-muted-foreground">Sois le premier à jouer cette semaine !</div>
            : lb.map((row) => (
              <div key={row.userId} className={cx('flex items-center gap-3 p-3', row.me && 'bg-primary/5')}>
                <span className="w-6 text-center font-display text-sm">{row.rank}</span>
                <div className="w-9 h-9 rounded-full grid place-items-center text-white text-sm font-semibold" style={{ background: row.avatarColor || '#4353F0' }}>{row.initials}</div>
                <span className="flex-1 text-sm font-medium truncate">{row.name}{row.me && ' (toi)'}</span>
                <span className="font-display tabular text-sm">{row.score}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}

/* ---------------- Jeu Reflex (skill, aucun hasard sur la récompense) ---------------- */
function ReflexGame({ session, onEnd }) {
  const [score, setScore] = useState(0)
  const [time, setTime] = useState(session.duration)
  const [pos, setPos] = useState({ x: 45, y: 45 })
  const [started, setStarted] = useState(false)
  const scoreRef = useRef(0)

  const relocate = () => setPos({ x: 6 + rnd() * 82, y: 6 + rnd() * 82 })

  useEffect(() => {
    if (!started) return
    relocate()
    const move = setInterval(relocate, 850)      // la cible bouge (raté) toutes les 850 ms
    const tick = setInterval(() => setTime((t) => Math.max(0, t - 1)), 1000)
    const end = setTimeout(() => { clearInterval(move); clearInterval(tick); onEnd(scoreRef.current) }, session.duration * 1000)
    return () => { clearInterval(move); clearInterval(tick); clearTimeout(end) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started])

  const hit = () => { scoreRef.current += 1; setScore(scoreRef.current); relocate() }

  if (!started) return (
    <div className="py-16 text-center">
      <div className="mb-4"><Zap size={56} className="mx-auto text-gold" fill="currentColor" strokeWidth={0} /></div>
      <div className="font-display text-2xl mb-2">Prêt ?</div>
      <p className="text-sm text-muted-foreground mb-6">Touche un maximum d'éclairs en {session.duration} secondes.</p>
      <button onClick={() => setStarted(true)} className="press px-8 py-3.5 rounded-lg font-semibold text-white grad-gold-deep">Commencer</button>
    </div>
  )

  return (
    <div className="py-3">
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-sm text-muted-foreground">Score : <b className="text-foreground font-display">{score}</b></span>
        <span className={cx('text-sm font-display tabular', time <= 5 && 'text-destructive')}>{time}s</span>
      </div>
      <div className="relative w-full rounded-lg border border-border overflow-hidden select-none" style={{ aspectRatio: '3/4', background: 'radial-gradient(circle at 50% 30%, rgba(226,170,43,0.14), transparent 60%)' }}>
        <motion.button key={`${pos.x}-${pos.y}`} onClick={hit} aria-label="Toucher"
          initial={{ scale: 0.4, opacity: 0.6 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.12 }}
          className="absolute w-16 h-16 rounded-full grid place-items-center text-white shadow-xl grad-gold"
          style={{ left: `${pos.x}%`, top: `${pos.y}%` }}>
          <Zap size={30} fill="#fff" />
        </motion.button>
      </div>
      <p className="text-center text-[11px] text-muted-foreground mt-3">Récompense selon ton score · aucun hasard</p>
    </div>
  )
}

function Result({ result, onAgain }) {
  if (result?.error) return (
    <div className="py-16 text-center">
      <div className="text-lg text-destructive mb-4">{result.error}</div>
      <button onClick={onAgain} className="press px-6 py-3 rounded-lg bg-primary/10 text-primary font-medium">Retour</button>
    </div>
  )
  return (
    <div className="py-14 text-center">
      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 200, damping: 12 }}>
        <div className="text-6xl mb-3">{result.reward > 0 ? '🎉' : '💪'}</div>
        <div className="font-display text-4xl">Score {result.score}</div>
      </motion.div>
      <div className={cx('mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-full font-semibold', result.reward > 0 ? 'grad-gold-deep text-white' : 'bg-muted text-muted-foreground')}>
        {result.reward > 0 ? <><Star size={16} fill="#fff" /> +{result.reward} Éclats</> : 'Aucune récompense cette fois'}
      </div>
      <div className="text-sm text-muted-foreground mt-3">Meilleur score : {result.myBest} · Solde : <Eclats n={result.balance} size={12} /></div>
      <button onClick={onAgain} className="press mt-6 px-8 py-3.5 rounded-lg font-semibold text-white grad-gold-deep">Rejouer</button>
    </div>
  )
}
