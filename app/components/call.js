'use client'

// Appels audio/vidéo 1:1 en WebRTC. Signalisation via le WebSocket temps réel déjà en place.
// STUN public par défaut (gratuit) ; un TURN peut être ajouté côté serveur (env) pour fiabiliser.
import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Phone, PhoneOff, Video, VideoOff, Mic, MicOff, X } from 'lucide-react'
import { onRealtime, sendRealtime } from '@/lib/realtime'
import { api } from '@/lib/api'

const cx = (...a) => a.filter(Boolean).join(' ')
const rid = () => (crypto?.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2))

// Ouvre un appel depuis n'importe où : window.dispatchEvent(new CustomEvent('divarc:call', {detail:{peerId,peerName,peerColor,video}}))
export function startCall(peerId, peerName, peerColor, video) {
  window.dispatchEvent(new CustomEvent('divarc:call', { detail: { peerId, peerName, peerColor, video } }))
}

const Avatar = ({ name, color, size = 96 }) => (
  <div className="rounded-full grid place-items-center text-white font-semibold"
    style={{ width: size, height: size, background: color || 'linear-gradient(135deg,#4353F0,#2C39C7)', fontSize: size * 0.36 }}>
    {(name || '?').slice(0, 1).toUpperCase()}
  </div>
)

export default function CallLayer({ me }) {
  const [status, setStatus] = useState('idle') // idle | incoming | calling | connecting | active | ended
  const [peer, setPeer] = useState(null)        // { id, name, color }
  const [isVideo, setIsVideo] = useState(true)
  const [muted, setMuted] = useState(false)
  const [camOff, setCamOff] = useState(false)
  const [endMsg, setEndMsg] = useState('')
  const [hasRemoteVideo, setHasRemoteVideo] = useState(false)

  const pcRef = useRef(null)
  const localStreamRef = useRef(null)
  const remoteStreamRef = useRef(null)
  const callIdRef = useRef(null)
  const peerIdRef = useRef(null)
  const roleRef = useRef(null)          // 'caller' | 'callee'
  const pendingIce = useRef([])
  const ringTimer = useRef(null)
  const localVideoRef = useRef(null)
  const remoteVideoRef = useRef(null)
  const iceServersRef = useRef(null)

  const signal = useCallback((type, extra = {}) => {
    if (!peerIdRef.current) return
    sendRealtime({ type, to: peerIdRef.current, callId: callIdRef.current, ...extra })
  }, [])

  const getIceServers = useCallback(async () => {
    if (iceServersRef.current) return iceServersRef.current
    try {
      const r = await api('/rtc/config')
      iceServersRef.current = r?.iceServers || [{ urls: ['stun:stun.l.google.com:19302'] }]
    } catch {
      iceServersRef.current = [{ urls: ['stun:stun.l.google.com:19302'] }]
    }
    return iceServersRef.current
  }, [])

  const cleanup = useCallback(() => {
    if (ringTimer.current) { clearTimeout(ringTimer.current); ringTimer.current = null }
    try { pcRef.current?.close() } catch {}
    pcRef.current = null
    localStreamRef.current?.getTracks().forEach((t) => { try { t.stop() } catch {} })
    localStreamRef.current = null
    remoteStreamRef.current = null
    pendingIce.current = []
    callIdRef.current = null
    peerIdRef.current = null
    roleRef.current = null
    setHasRemoteVideo(false); setMuted(false); setCamOff(false)
  }, [])

  const endCall = useCallback((msg = '') => {
    cleanup()
    if (msg) { setEndMsg(msg); setStatus('ended'); setTimeout(() => setStatus('idle'), 1800) }
    else setStatus('idle')
  }, [cleanup])

  const getMedia = useCallback(async (video) => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: video ? { facingMode: 'user' } : false,
    })
    localStreamRef.current = stream
    return stream
  }, [])

  const buildPeer = useCallback(async () => {
    const pc = new RTCPeerConnection({ iceServers: await getIceServers() })
    pc.onicecandidate = (e) => { if (e.candidate) signal('call:ice', { candidate: e.candidate }) }
    pc.ontrack = (e) => {
      const [stream] = e.streams
      remoteStreamRef.current = stream
      if (remoteVideoRef.current) remoteVideoRef.current.srcObject = stream
      setHasRemoteVideo(stream.getVideoTracks().some((t) => t.enabled))
      setStatus('active')
    }
    pc.oniceconnectionstatechange = () => {
      const s = pc.iceConnectionState
      if (s === 'connected' || s === 'completed') setStatus('active')
      if (s === 'failed') endCall('Connexion perdue')
    }
    // ajoute les pistes locales
    localStreamRef.current?.getTracks().forEach((t) => pc.addTrack(t, localStreamRef.current))
    pcRef.current = pc
    return pc
  }, [getIceServers, signal, endCall])

  const flushIce = useCallback(async () => {
    const pc = pcRef.current
    if (!pc) return
    for (const c of pendingIce.current) { try { await pc.addIceCandidate(c) } catch {} }
    pendingIce.current = []
  }, [])

  // ---- Démarrage d'un appel sortant ----
  const startOutgoing = useCallback(async ({ peerId, peerName, peerColor, video }) => {
    if (status !== 'idle') return
    try {
      callIdRef.current = rid(); peerIdRef.current = peerId; roleRef.current = 'caller'
      setPeer({ id: peerId, name: peerName, color: peerColor }); setIsVideo(!!video); setStatus('calling')
      await getMedia(!!video)
      if (localVideoRef.current) localVideoRef.current.srcObject = localStreamRef.current
      await buildPeer()
      signal('call:invite', { video: !!video })
      ringTimer.current = setTimeout(() => endCall('Pas de réponse'), 30000)
    } catch (e) {
      endCall(e?.name === 'NotAllowedError' ? 'Micro/caméra refusés' : "Impossible de démarrer l'appel")
    }
  }, [status, getMedia, buildPeer, signal, endCall])

  // ---- Acceptation d'un appel entrant ----
  const acceptCall = useCallback(async () => {
    try {
      setStatus('connecting')
      await getMedia(isVideo)
      if (localVideoRef.current) localVideoRef.current.srcObject = localStreamRef.current
      await buildPeer()
      signal('call:accept')
    } catch (e) {
      signal('call:hangup')
      endCall(e?.name === 'NotAllowedError' ? 'Micro/caméra refusés' : "Impossible de répondre")
    }
  }, [isVideo, getMedia, buildPeer, signal, endCall])

  const rejectCall = useCallback(() => { signal('call:reject'); endCall() }, [signal, endCall])
  const hangup = useCallback(() => { signal('call:hangup'); endCall() }, [signal, endCall])

  // ---- Réception de la signalisation ----
  useEffect(() => {
    const offInvite = onRealtime('call:invite', (m) => {
      if (status !== 'idle' || callIdRef.current) { sendRealtime({ type: 'call:busy', to: m.from, callId: m.callId }); return }
      callIdRef.current = m.callId; peerIdRef.current = m.from; roleRef.current = 'callee'
      setPeer({ id: m.from, name: m.fromName, color: m.fromAvatarColor }); setIsVideo(!!m.video); setStatus('incoming')
    })
    const offAccept = onRealtime('call:accept', async (m) => {
      if (m.callId !== callIdRef.current || roleRef.current !== 'caller') return
      if (ringTimer.current) { clearTimeout(ringTimer.current); ringTimer.current = null }
      setStatus('connecting')
      try {
        const pc = pcRef.current
        const offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        signal('call:offer', { sdp: pc.localDescription })
      } catch { endCall('Échec de connexion') }
    })
    const offOffer = onRealtime('call:offer', async (m) => {
      if (m.callId !== callIdRef.current || roleRef.current !== 'callee') return
      try {
        const pc = pcRef.current
        await pc.setRemoteDescription(new RTCSessionDescription(m.sdp))
        await flushIce()
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        signal('call:answer', { sdp: pc.localDescription })
      } catch { endCall('Échec de connexion') }
    })
    const offAnswer = onRealtime('call:answer', async (m) => {
      if (m.callId !== callIdRef.current || roleRef.current !== 'caller') return
      try { await pcRef.current.setRemoteDescription(new RTCSessionDescription(m.sdp)); await flushIce() }
      catch { endCall('Échec de connexion') }
    })
    const offIce = onRealtime('call:ice', async (m) => {
      if (m.callId !== callIdRef.current || !m.candidate) return
      const cand = new RTCIceCandidate(m.candidate)
      if (pcRef.current?.remoteDescription) { try { await pcRef.current.addIceCandidate(cand) } catch {} }
      else pendingIce.current.push(cand)
    })
    const offReject = onRealtime('call:reject', (m) => { if (m.callId === callIdRef.current) endCall('Appel refusé') })
    const offHangup = onRealtime('call:hangup', (m) => { if (m.callId === callIdRef.current) endCall() })
    const offBusy = onRealtime('call:busy', (m) => { if (m.callId === callIdRef.current) endCall('Occupé') })
    const offUnavail = onRealtime('call:unavailable', (m) => { if (m.callId === callIdRef.current) endCall('Indisponible') })
    return () => { offInvite(); offAccept(); offOffer(); offAnswer(); offIce(); offReject(); offHangup(); offBusy(); offUnavail() }
  }, [status, signal, flushIce, endCall])

  // Démarrage d'appel déclenché depuis le chat
  useEffect(() => {
    const onStart = (e) => startOutgoing(e.detail || {})
    window.addEventListener('divarc:call', onStart)
    return () => window.removeEventListener('divarc:call', onStart)
  }, [startOutgoing])

  // (Ré)attache les flux aux balises vidéo quand elles apparaissent
  useEffect(() => {
    if (localVideoRef.current && localStreamRef.current) localVideoRef.current.srcObject = localStreamRef.current
    if (remoteVideoRef.current && remoteStreamRef.current) remoteVideoRef.current.srcObject = remoteStreamRef.current
  }, [status])

  const toggleMute = () => {
    const on = !muted; setMuted(on)
    localStreamRef.current?.getAudioTracks().forEach((t) => { t.enabled = !on })
  }
  const toggleCam = () => {
    const off = !camOff; setCamOff(off)
    localStreamRef.current?.getVideoTracks().forEach((t) => { t.enabled = !off })
  }

  if (status === 'idle') return null

  const inCall = status === 'calling' || status === 'connecting' || status === 'active'

  return (
    <AnimatePresence>
      <motion.div key="call" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[90] bg-ink text-white flex flex-col">
        {/* Appel entrant */}
        {status === 'incoming' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-6 p-8">
            <div className="text-center">
              <div className="mb-5 mx-auto w-fit"><Avatar name={peer?.name} color={peer?.color} size={110} /></div>
              <div className="text-2xl font-display">{peer?.name || 'Appel'}</div>
              <div className="text-white/60 mt-1">{isVideo ? 'Appel vidéo entrant…' : 'Appel entrant…'}</div>
            </div>
            <div className="flex items-center gap-10 mt-4">
              <button onClick={rejectCall} aria-label="Refuser" className="press w-16 h-16 rounded-full bg-danger grid place-items-center shadow-xl"><PhoneOff size={26} /></button>
              <button onClick={acceptCall} aria-label="Accepter" className="press w-16 h-16 rounded-full bg-success grid place-items-center shadow-xl"><Phone size={26} /></button>
            </div>
          </div>
        )}

        {/* En appel (sortant / connexion / actif) */}
        {inCall && (
          <>
            {/* vidéo distante plein écran (ou avatar si audio) */}
            <div className="absolute inset-0 grid place-items-center bg-ink">
              {isVideo && hasRemoteVideo ? (
                <video ref={remoteVideoRef} autoPlay playsInline className="w-full h-full object-cover" />
              ) : (
                <div className="text-center">
                  <div className="mb-5 mx-auto w-fit"><Avatar name={peer?.name} color={peer?.color} size={120} /></div>
                  <div className="text-2xl font-display">{peer?.name}</div>
                  <div className="text-white/60 mt-1">
                    {status === 'active' ? 'En communication' : status === 'connecting' ? 'Connexion…' : 'Appel en cours…'}
                  </div>
                </div>
              )}
            </div>

            {/* aperçu local (PiP) en vidéo */}
            {isVideo && (
              <video ref={localVideoRef} autoPlay playsInline muted
                className={cx('absolute top-4 right-4 w-28 h-40 rounded-2xl object-cover border border-white/20 shadow-xl bg-black', camOff && 'hidden')} />
            )}

            {/* bandeau d'état haut */}
            <div className="relative z-10 pt-safe px-4 pt-4">
              <div className="text-sm text-white/70">
                {status === 'active' ? '' : peer?.name}
              </div>
            </div>

            {/* contrôles */}
            <div className="relative z-10 mt-auto pb-safe px-6 pb-8 flex items-center justify-center gap-5">
              <button onClick={toggleMute} aria-label={muted ? 'Activer le micro' : 'Couper le micro'}
                className={cx('press w-14 h-14 rounded-full grid place-items-center', muted ? 'bg-white text-ink' : 'bg-white/15')}>
                {muted ? <MicOff size={22} /> : <Mic size={22} />}
              </button>
              {isVideo && (
                <button onClick={toggleCam} aria-label={camOff ? 'Activer la caméra' : 'Couper la caméra'}
                  className={cx('press w-14 h-14 rounded-full grid place-items-center', camOff ? 'bg-white text-ink' : 'bg-white/15')}>
                  {camOff ? <VideoOff size={22} /> : <Video size={22} />}
                </button>
              )}
              <button onClick={hangup} aria-label="Raccrocher" className="press w-16 h-16 rounded-full bg-danger grid place-items-center shadow-xl">
                <PhoneOff size={26} />
              </button>
            </div>
          </>
        )}

        {/* fin d'appel */}
        {status === 'ended' && (
          <div className="flex-1 grid place-items-center">
            <div className="text-center">
              <PhoneOff size={40} className="mx-auto mb-3 text-white/60" />
              <div className="text-lg">{endMsg || 'Appel terminé'}</div>
            </div>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
