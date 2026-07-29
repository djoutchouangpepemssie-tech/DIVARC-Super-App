import { MongoClient } from 'mongodb'
import { v4 as uuidv4 } from 'uuid'
import { NextResponse } from 'next/server'
import crypto from 'crypto'
import { Resend } from 'resend'

// ---------------- MongoDB ----------------
let client
let db
let connectPromise
async function connectToMongo() {
  if (db) return db
  if (!connectPromise) {
    connectPromise = (async () => {
      client = new MongoClient(process.env.MONGO_URL)
      await client.connect()
      db = client.db(process.env.DB_NAME)
      return db
    })()
  }
  return await connectPromise
}

function handleCORS(response) {
  response.headers.set('Access-Control-Allow-Origin', process.env.CORS_ORIGINS || '*')
  response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
  response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  response.headers.set('Access-Control-Allow-Credentials', 'true')
  return response
}
export async function OPTIONS() { return handleCORS(new NextResponse(null, { status: 200 })) }
const ok = (data, status = 200) => handleCORS(NextResponse.json(data, { status }))
const err = (message, status = 400) => handleCORS(NextResponse.json({ error: message }, { status }))

// ---------------- helpers ----------------
const COLORS = [
  'linear-gradient(135deg,#4353F0,#6E7BF5)', 'linear-gradient(135deg,#E2AA2B,#F0CE7E)',
  'linear-gradient(135deg,#3FB68B,#7BE0BE)', 'linear-gradient(135deg,#9B5DE5,#C89BF5)',
  'linear-gradient(135deg,#F15BB5,#FBA3D8)', 'linear-gradient(135deg,#00BBF9,#7ADBFF)',
  'linear-gradient(135deg,#EF476F,#FF8FA8)', 'linear-gradient(135deg,#2C39C7,#4353F0)',
]
const initialsOf = (name) => name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
const sha = (s) => crypto.createHash('sha256').update(String(s)).digest('hex')
const todayStr = () => new Date().toISOString().slice(0, 10)
const yesterdayStr = () => new Date(Date.now() - 86400000).toISOString().slice(0, 10)

const LEVELS = [
  { min: 0, name: 'Connaissance', emoji: '🌱' },
  { min: 100, name: 'Ami·e', emoji: '💫' },
  { min: 300, name: 'Bon·ne ami·e', emoji: '💛' },
  { min: 700, name: 'Meilleur·e ami·e', emoji: '🔥' },
  { min: 1500, name: 'Âme sœur', emoji: '👑' },
]
const levelInfo = (xp) => {
  let idx = 0
  for (let i = 0; i < LEVELS.length; i++) if (xp >= LEVELS[i].min) idx = i
  const cur = LEVELS[idx]
  const next = LEVELS[idx + 1] || null
  const base = cur.min
  const span = next ? next.min - base : 1
  const pct = next ? Math.min(100, Math.round(((xp - base) / span) * 100)) : 100
  return { level: idx, name: cur.name, emoji: cur.emoji, xp, pct, next: next ? { name: next.name, at: next.min } : null }
}

async function getUser(request, db) {
  const auth = request.headers.get('authorization') || ''
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : null
  if (!token) return null
  const s = await db.collection('sessions').findOne({ token })
  if (!s) return null
  return await db.collection('users').findOne({ id: s.userId }, { projection: { _id: 0 } })
}

async function uniqueHandle(db, base) {
  let h = '@' + base.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 14)
  if (h === '@') h = '@user'
  let cand = h, n = 0
  while (await db.collection('users').findOne({ handle: cand })) { n++; cand = h + n }
  return cand
}

async function provisionUser(db, email, name) {
  const id = uuidv4()
  const displayName = name || email.split('@')[0].replace(/\W+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  const user = {
    id, email: email.toLowerCase(),
    handle: await uniqueHandle(db, email.split('@')[0]),
    name: displayName,
    initials: initialsOf(displayName) || 'U',
    avatarColor: COLORS[Math.floor(Math.random() * COLORS.length)],
    verified: false, kyc: 'non vérifié', bio: '', isBot: false,
    createdAt: new Date(),
  }
  await db.collection('users').insertOne(user)
  await db.collection('wallets').insertOne({
    id: uuidv4(), userId: id, balanceCents: 480000, currency: 'EUR',
    sepaInstant: true, carbonMonthKg: 0, createdAt: new Date(),
  })
  await db.collection('coffres').insertMany([
    { id: uuidv4(), userId: id, name: 'Vacances', emoji: '🏖️', balanceCents: 500, goalCents: 150000, rule: 'round_up', color: '#4353F0' },
    { id: uuidv4(), userId: id, name: 'Fonds d\u2019urgence', emoji: '🛟', balanceCents: 0, goalCents: 300000, rule: 'receive_over', color: '#E2AA2B' },
  ])
  await db.collection('transactions').insertOne({
    id: uuidv4(), userId: id, label: 'Bienvenue sur DIVARC 🎁', category: 'Cadeau',
    amountCents: 480000, carbonKg: 0, icon: '🎁', route: null, createdAt: new Date(),
  })
  // welcome DM with Marie (bot)
  await ensureDemoUsers(db)
  const marie = await db.collection('users').findOne({ id: 'bot-marie' })
  if (marie) {
    const convId = uuidv4()
    await db.collection('conversations').insertOne({
      id: convId, type: 'dm', name: null, avatarColor: null,
      memberIds: [id, marie.id], createdBy: 'system', reads: {},
      lastText: 'Bienvenue ! Envoie-moi un message pour lancer ta première flamme 🔥',
      lastMessageAt: new Date(), createdAt: new Date(),
    })
    await db.collection('messages').insertOne({
      id: uuidv4(), conversationId: convId, senderId: marie.id, senderName: marie.name,
      text: 'Salut et bienvenue sur DIVARC ! 🎉 Réponds-moi pour démarrer ta première flamme 🔥 et faire monter votre score d\u2019amitié.',
      kind: 'text', reactions: [], createdAt: new Date(),
    })
  }
  return user
}

const BOTS = [
  { id: 'bot-marie', name: 'Marie Laurent', handle: '@marie', color: COLORS[1], verified: true },
  { id: 'bot-thomas', name: 'Thomas Bernard', handle: '@thomas', color: COLORS[2], verified: false },
  { id: 'bot-lena', name: 'Léna Costa', handle: '@lena', color: COLORS[3], verified: true },
  { id: 'bot-yanis', name: 'Yanis Moreau', handle: '@yanis', color: COLORS[4], verified: false },
  { id: 'bot-sofia', name: 'Sofia Ricci', handle: '@sofia', color: COLORS[5], verified: true },
]
async function ensureDemoUsers(db) {
  for (const b of BOTS) {
    const ex = await db.collection('users').findOne({ id: b.id })
    if (!ex) {
      await db.collection('users').insertOne({
        id: b.id, email: `${b.handle.slice(1)}@divarc.fr`, handle: b.handle, name: b.name,
        initials: initialsOf(b.name), avatarColor: b.color, verified: b.verified,
        kyc: b.verified ? 'eIDAS' : 'non vérifié', bio: 'Ami·e DIVARC', isBot: true, createdAt: new Date(),
      })
    }
  }
  // ensure a public community exists
  const comm = await db.collection('conversations').findOne({ id: 'comm-paris' })
  if (!comm) {
    await db.collection('conversations').insertOne({
      id: 'comm-paris', type: 'community', name: 'Paris ✨', topic: 'La vie à Paris',
      avatarColor: COLORS[0], memberIds: BOTS.map((b) => b.id), createdBy: 'system',
      isPublic: true, reads: {}, lastText: 'Qui est chaud pour un pique-nique ?',
      lastMessageAt: new Date(), createdAt: new Date(),
    })
    await db.collection('messages').insertMany([
      { id: uuidv4(), conversationId: 'comm-paris', senderId: 'bot-lena', senderName: 'Léna Costa', text: 'Bienvenue dans la communauté Paris ! 🥖', kind: 'text', reactions: [], createdAt: new Date(Date.now() - 7200000) },
      { id: uuidv4(), conversationId: 'comm-paris', senderId: 'bot-yanis', senderName: 'Yanis Moreau', text: 'Qui est chaud pour un pique-nique aux Buttes-Chaumont ce week-end ?', kind: 'text', reactions: [{ userId: 'bot-lena', emoji: '🔥' }], createdAt: new Date(Date.now() - 3600000) },
    ])
  }
}

const BOT_REPLIES = [
  'Haha carrément 😄', 'Trop bien ! 🔥', 'Je te réponds direct ⚡', 'On fait ça 👌',
  'Ça marche pour moi 💛', 'Génial, à très vite !', 'Oui !! 🎉', 'Je note 📝', 'Top idée ✨',
]

async function bumpFriendship(db, uid, otherId, xpGain = 10) {
  const key = [uid, otherId].sort().join('|')
  let f = await db.collection('friendships').findOne({ key })
  const today = todayStr()
  if (!f) {
    f = { id: uuidv4(), key, members: [uid, otherId].sort(), xp: 0, streak: 0, streakLastDay: null, activeDays: {}, createdAt: new Date() }
    await db.collection('friendships').insertOne(f)
  }
  const activeDays = f.activeDays || {}
  activeDays[uid] = today
  const bothToday = f.members.every((m) => activeDays[m] === today)
  let streak = f.streak || 0
  let streakLastDay = f.streakLastDay
  if (bothToday && streakLastDay !== today) {
    streak = (streakLastDay === yesterdayStr()) ? streak + 1 : 1
    streakLastDay = today
  }
  const xp = (f.xp || 0) + xpGain
  await db.collection('friendships').updateOne({ key }, { $set: { activeDays, streak, streakLastDay, xp } })
  return { streak, xp, ...levelInfo(xp) }
}

async function getFriendship(db, uid, otherId) {
  const key = [uid, otherId].sort().join('|')
  const f = await db.collection('friendships').findOne({ key })
  const xp = f?.xp || 0
  return { streak: f?.streak || 0, streakLastDay: f?.streakLastDay || null, ...levelInfo(xp) }
}

async function sendOtpEmail(email, code) {
  if (!process.env.RESEND_API_KEY) return { preview: true }
  try {
    const resend = new Resend(process.env.RESEND_API_KEY)
    const r = await resend.emails.send({
      from: process.env.RESEND_FROM || 'DIVARC <onboarding@resend.dev>',
      to: [email], subject: `Ton code DIVARC : ${code}`,
      html: `<div style="font-family:sans-serif"><h2>DIVARC</h2><p>Ton code de connexion :</p><div style="font-size:32px;font-weight:800;letter-spacing:6px">${code}</div><p>Valable 10 minutes.</p></div>`,
    })
    if (r.error) return { error: r.error.message }
    return { sent: true }
  } catch (e) { return { error: e.message } }
}

// double-entry
async function postLedger(db, entries) {
  const batch = uuidv4()
  await db.collection('ledger').insertMany(entries.map((e) => ({ id: uuidv4(), batch, ...e, createdAt: new Date() })))
  return batch
}

async function creditWallet(db, userId, amt) {
  const r = await db.collection('wallets').updateOne({ userId }, { $inc: { balanceCents: amt } })
  if (r.matchedCount === 0) {
    await db.collection('wallets').insertOne({ id: uuidv4(), userId, balanceCents: amt, currency: 'EUR', sepaInstant: true, carbonMonthKg: 0, createdAt: new Date() })
  }
}

const VIDS = [
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4',
  'https://storage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
]
async function ensureSocialSeed(db) {
  const count = await db.collection('posts').countDocuments()
  if (count > 0) return
  await ensureDemoUsers(db)
  const seed = [
    { a: 'bot-lena', cap: 'Coucher de soleil sur Paris 🌇 Cette ville me fait vibrer.', tags: ['#paris', '#lifestyle'], likes: 1240, views: 18400, comments: 87 },
    { a: 'bot-yanis', cap: 'Recette express : pâtes truffe 🍝✨ (ça change la vie)', tags: ['#food', '#recette'], likes: 3420, views: 51200, comments: 210, product: { title: 'Huile de truffe artisanale', priceCents: 1490, emoji: '🫒' } },
    { a: 'bot-marie', cap: 'Mon setup créateur 2025 💻 Question ? Je réponds !', tags: ['#tech', '#setup'], likes: 890, views: 12300, comments: 64, product: { title: 'Micro podcast USB', priceCents: 8900, emoji: '🎙️' }, ai: true },
    { a: 'bot-sofia', cap: 'Routine sport du matin 🏃‍♀️ On se motive ensemble ?', tags: ['#sport', '#motivation'], likes: 2110, views: 33100, comments: 143 },
    { a: 'bot-thomas', cap: 'Voyage Lisbonne en 60 secondes 🇵🇹 Sauvegarde pour plus tard !', tags: ['#voyage', '#lisbonne'], likes: 5600, views: 98000, comments: 320 },
    { a: 'bot-lena', cap: 'DIY déco : transformer un mur en 3 étapes 🎨', tags: ['#diy', '#deco'], likes: 760, views: 9800, comments: 41, product: { title: 'Kit peinture éco', priceCents: 3200, emoji: '🎨' } },
    { a: 'bot-marie', cap: 'Le meilleur café de Paris est ici ☕ (adresse en com)', tags: ['#paris', '#food'], likes: 1980, views: 27600, comments: 176 },
    { a: 'bot-sofia', cap: 'Concert hier soir 🎶 Ambiance incroyable !', tags: ['#musique', '#live'], likes: 4300, views: 62000, comments: 258 },
  ]
  const now = Date.now()
  const docs = seed.map((s, i) => ({
    id: uuidv4(), authorId: s.a, caption: s.cap, mediaUrl: VIDS[i % VIDS.length], mediaType: 'video',
    poster: null, hashtags: s.tags, product: s.product || null, aiGenerated: !!s.ai,
    likes: s.likes, comments: s.comments, saves: Math.floor(s.likes * 0.12), views: s.views,
    earningsCents: 0, createdAt: new Date(now - i * 3600000 * 5),
  }))
  await db.collection('posts').insertMany(docs)
}

// ---------------- Marketplace v2 : catégories (type Leboncoin) ----------------
const MARKET_CATEGORIES = [
  { id: 'immobilier', name: 'Immobilier', emoji: '🏠', color: '#4353F0', types: ['sale', 'rent'],
    subcats: ['Ventes immobilières', 'Locations', 'Colocations', 'Bureaux & commerces', 'Locations de vacances'],
    fields: [
      { key: 'propertyType', label: 'Type de bien', type: 'select', options: ['Appartement', 'Maison', 'Studio', 'Loft', 'Terrain', 'Parking', 'Autre'] },
      { key: 'surface', label: 'Surface', type: 'number', unit: 'm²' },
      { key: 'rooms', label: 'Pièces', type: 'number' },
      { key: 'bedrooms', label: 'Chambres', type: 'number' },
      { key: 'furnished', label: 'Meublé', type: 'bool' },
      { key: 'energyClass', label: 'DPE', type: 'select', options: ['A', 'B', 'C', 'D', 'E', 'F', 'G'] },
    ] },
  { id: 'vehicules', name: 'Véhicules', emoji: '🚗', color: '#EF476F', types: ['sale', 'rent'],
    subcats: ['Voitures', 'Motos', 'Caravaning', 'Utilitaires', 'Nautisme'],
    fields: [
      { key: 'brand', label: 'Marque', type: 'text' },
      { key: 'model', label: 'Modèle', type: 'text' },
      { key: 'year', label: 'Année', type: 'number' },
      { key: 'mileage', label: 'Kilométrage', type: 'number', unit: 'km' },
      { key: 'fuel', label: 'Carburant', type: 'select', options: ['Essence', 'Diesel', 'Électrique', 'Hybride', 'GPL'] },
      { key: 'gearbox', label: 'Boîte', type: 'select', options: ['Manuelle', 'Automatique'] },
    ] },
  { id: 'multimedia', name: 'Multimédia', emoji: '📱', color: '#00BBF9', types: ['sale'],
    subcats: ['Informatique', 'Téléphonie', 'Image & son', 'Consoles & jeux vidéo', 'Accessoires'],
    fields: [{ key: 'brand', label: 'Marque', type: 'text' }] },
  { id: 'maison', name: 'Maison & Jardin', emoji: '🛋️', color: '#3FB68B', types: ['sale'],
    subcats: ['Ameublement', 'Électroménager', 'Décoration', 'Bricolage', 'Jardin & plantes', 'Vaisselle'],
    fields: [] },
  { id: 'mode', name: 'Mode', emoji: '👗', color: '#F15BB5', types: ['sale'],
    subcats: ['Vêtements', 'Chaussures', 'Accessoires & bagagerie', 'Montres & bijoux', 'Beauté'],
    fields: [{ key: 'size', label: 'Taille', type: 'text' }, { key: 'brand', label: 'Marque', type: 'text' }] },
  { id: 'loisirs', name: 'Loisirs', emoji: '🎸', color: '#9B5DE5', types: ['sale'],
    subcats: ['Vélos', 'Sport & plein air', 'Instruments de musique', 'Livres', 'Jeux & jouets', 'Collection'],
    fields: [] },
  { id: 'famille', name: 'Famille', emoji: '👶', color: '#F97C4E', types: ['sale'],
    subcats: ['Équipement bébé', 'Mobilier enfant', 'Vêtements bébé'],
    fields: [] },
  { id: 'emploi', name: 'Emploi & Services', emoji: '💼', color: '#E2AA2B', types: ['sale', 'service'],
    subcats: ['Offres d\u2019emploi', 'Services à la personne', 'Cours particuliers', 'Événements', 'Artisans'],
    fields: [] },
]
const CONDITIONS = ['Neuf', 'Comme neuf', 'Très bon état', 'Bon état', 'État correct']

// ---------------- Géolocalisation Europe (Geoapify + repli OpenStreetMap) ----------------
const EU_CC = 'fr,de,es,it,be,nl,pt,lu,at,ie,fi,se,dk,pl,cz,gr,ro,hu,sk,si,hr,bg,ee,lv,lt,cy,mt,ch,no'
async function geoAutocomplete(q, country) {
  const key = process.env.GEOAPIFY_API_KEY
  try {
    if (key) {
      const u = new URL('https://api.geoapify.com/v1/geocode/autocomplete')
      u.searchParams.set('text', q); u.searchParams.set('apiKey', key); u.searchParams.set('limit', '8'); u.searchParams.set('lang', 'fr')
      u.searchParams.set('filter', `countrycode:${country ? country.toLowerCase() : EU_CC}`)
      const r = await fetch(u, { cache: 'no-store' }); const j = await r.json()
      return (j.features || []).map((f) => ({
        label: f.properties.formatted, city: f.properties.city || f.properties.county || f.properties.name || '',
        postcode: f.properties.postcode || '', country: (f.properties.country_code || '').toUpperCase(),
        lat: f.properties.lat, lon: f.properties.lon, provider: 'geoapify',
      }))
    }
    const u = new URL('https://nominatim.openstreetmap.org/search')
    u.searchParams.set('q', q); u.searchParams.set('format', 'jsonv2'); u.searchParams.set('addressdetails', '1'); u.searchParams.set('limit', '8'); u.searchParams.set('accept-language', 'fr')
    u.searchParams.set('countrycodes', country ? country.toLowerCase() : EU_CC)
    const r = await fetch(u, { cache: 'no-store', headers: { 'User-Agent': 'DIVARC-Marketplace/1.0 (contact@divarc.eu)' } })
    const arr = await r.json()
    return (Array.isArray(arr) ? arr : []).map((a) => ({
      label: a.display_name, city: a.address?.city || a.address?.town || a.address?.village || a.address?.municipality || a.name || '',
      postcode: a.address?.postcode || '', country: (a.address?.country_code || '').toUpperCase(),
      lat: +a.lat, lon: +a.lon, provider: 'osm',
    }))
  } catch (e) { console.error('geoAutocomplete', e); return [] }
}
async function geoReverse(lat, lon) {
  const key = process.env.GEOAPIFY_API_KEY
  try {
    if (key) {
      const u = new URL('https://api.geoapify.com/v1/geocode/reverse')
      u.searchParams.set('lat', String(lat)); u.searchParams.set('lon', String(lon)); u.searchParams.set('lang', 'fr'); u.searchParams.set('apiKey', key)
      const r = await fetch(u, { cache: 'no-store' }); const j = await r.json(); const p = j.features?.[0]?.properties || {}
      return { label: p.formatted || '', city: p.city || p.county || '', postcode: p.postcode || '', country: (p.country_code || '').toUpperCase(), lat: +lat, lon: +lon }
    }
    const u = new URL('https://nominatim.openstreetmap.org/reverse')
    u.searchParams.set('lat', String(lat)); u.searchParams.set('lon', String(lon)); u.searchParams.set('format', 'jsonv2'); u.searchParams.set('addressdetails', '1'); u.searchParams.set('accept-language', 'fr')
    const r = await fetch(u, { cache: 'no-store', headers: { 'User-Agent': 'DIVARC-Marketplace/1.0 (contact@divarc.eu)' } })
    const a = await r.json()
    return { label: a.display_name || '', city: a.address?.city || a.address?.town || a.address?.village || '', postcode: a.address?.postcode || '', country: (a.address?.country_code || '').toUpperCase(), lat: +lat, lon: +lon }
  } catch (e) { console.error('geoReverse', e); return { label: '', city: '', postcode: '', country: '', lat: +lat, lon: +lon } }
}
function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371, dLat = (lat2 - lat1) * Math.PI / 180, dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

const MARKET_IMGS = {
  apartment: 'https://images.pexels.com/photos/2030037/pexels-photo-2030037.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
  house: 'https://images.pexels.com/photos/20296321/pexels-photo-20296321.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
  car: 'https://images.pexels.com/photos/14776589/pexels-photo-14776589.jpeg',
  motorcycle: 'https://images.unsplash.com/photo-1449426468159-d96dbf08f19f',
  sofa: 'https://images.pexels.com/photos/6758245/pexels-photo-6758245.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
  smartphone: 'https://images.pexels.com/photos/47261/pexels-photo-47261.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
  laptop: 'https://images.pexels.com/photos/8003992/pexels-photo-8003992.jpeg',
  sneakers: 'https://images.pexels.com/photos/1027130/pexels-photo-1027130.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
  bicycle: 'https://images.pexels.com/photos/37858364/pexels-photo-37858364.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
  guitar: 'https://images.pexels.com/photos/9057791/pexels-photo-9057791.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
}
const CITIES = {
  'Paris': [48.8566, 2.3522], 'Lyon': [45.7640, 4.8357], 'Marseille': [43.2965, 5.3698],
  'Bordeaux': [44.8378, -0.5792], 'Nantes': [47.2184, -1.5536], 'Lille': [50.6292, 3.0573],
  'Toulouse': [43.6047, 1.4442], 'Berlin': [52.5200, 13.4050], 'Madrid': [40.4168, -3.7038], 'Bruxelles': [50.8503, 4.3517],
}
async function ensureMarketSeed(db) {
  if (await db.collection('listings').countDocuments() > 0) return
  await ensureDemoUsers(db)
  const seed = [
    { s: 'bot-marie', t: 'Appartement T3 lumineux — 68 m²', d: 'Bel appartement rénové, 3e étage avec ascenseur, proche métro. Cuisine équipée, double vitrage, cave.', p: 34500000, cat: 'immobilier', sub: 'Ventes immobilières', tx: 'sale', cond: 'Comme neuf', img: 'apartment', city: 'Paris', attrs: { propertyType: 'Appartement', surface: 68, rooms: 3, bedrooms: 2, furnished: false, energyClass: 'C' } },
    { s: 'bot-thomas', t: 'Studio meublé à louer — 24 m²', d: 'Studio meublé idéal étudiant, charges comprises, disponible immédiatement. Proche campus.', p: 68000, cat: 'immobilier', sub: 'Locations', tx: 'rent', cond: 'Très bon état', img: 'apartment', city: 'Lyon', attrs: { propertyType: 'Studio', surface: 24, rooms: 1, bedrooms: 0, furnished: true, energyClass: 'D' } },
    { s: 'bot-sofia', t: 'Maison 5 pièces avec jardin — 120 m²', d: 'Maison familiale, 4 chambres, jardin 300 m², garage. Quartier calme et résidentiel.', p: 42000000, cat: 'immobilier', sub: 'Ventes immobilières', tx: 'sale', cond: 'Bon état', img: 'house', city: 'Bordeaux', attrs: { propertyType: 'Maison', surface: 120, rooms: 5, bedrooms: 4, furnished: false, energyClass: 'B' } },
    { s: 'bot-yanis', t: 'Citadine essence 2019 — 45 000 km', d: 'Entretien à jour, carnet complet, pneus neufs, CT ok. Première main, non fumeur.', p: 1250000, cat: 'vehicules', sub: 'Voitures', tx: 'sale', cond: 'Très bon état', img: 'car', city: 'Nantes', attrs: { brand: 'Renault', model: 'Clio', year: 2019, mileage: 45000, fuel: 'Essence', gearbox: 'Manuelle' } },
    { s: 'bot-lena', t: 'Moto roadster 650cc', d: 'Moto en excellent état, révision récente, deux casques offerts.', p: 480000, cat: 'vehicules', sub: 'Motos', tx: 'sale', cond: 'Bon état', img: 'motorcycle', city: 'Toulouse', attrs: { brand: 'Yamaha', model: 'MT-07', year: 2020, mileage: 18000, fuel: 'Essence', gearbox: 'Manuelle' } },
    { s: 'bot-thomas', t: 'Canapé 3 places en velours', d: 'Canapé design confortable, velours bleu nuit, très peu servi. À récupérer sur place.', p: 32000, cat: 'maison', sub: 'Ameublement', tx: 'sale', cond: 'Comme neuf', img: 'sofa', city: 'Paris', attrs: {} },
    { s: 'bot-marie', t: 'Smartphone 128 Go débloqué', d: 'Débloqué tout opérateur, batterie 92%, avec chargeur et coque. Facture disponible.', p: 29900, cat: 'multimedia', sub: 'Téléphonie', tx: 'sale', cond: 'Très bon état', img: 'smartphone', city: 'Lille', attrs: { brand: 'Samsung' } },
    { s: 'bot-yanis', t: 'Ordinateur portable 15" i7 16 Go', d: 'PC portable puissant, SSD 512 Go, parfait pour le travail et le montage. Batterie excellente.', p: 55000, cat: 'multimedia', sub: 'Informatique', tx: 'sale', cond: 'Bon état', img: 'laptop', city: 'Marseille', attrs: { brand: 'Lenovo' } },
    { s: 'bot-sofia', t: 'Sneakers rétro (42)', d: 'Édition running, semelle nickel, boîte incluse. Portées quelques fois.', p: 6900, cat: 'mode', sub: 'Chaussures', tx: 'sale', cond: 'Très bon état', img: 'sneakers', city: 'Lyon', attrs: { size: '42', brand: 'Nike' } },
    { s: 'bot-lena', t: 'Vélo de ville 7 vitesses', d: 'Vélo léger, freins révisés, antivol offert. Idéal trajets quotidiens en ville.', p: 18500, cat: 'loisirs', sub: 'Vélos', tx: 'sale', cond: 'Bon état', img: 'bicycle', city: 'Nantes', attrs: {} },
    { s: 'bot-thomas', t: 'Guitare acoustique folk', d: 'Guitare avec housse et accordeur. Son chaud, cordes neuves. Parfaite pour débuter.', p: 12000, cat: 'loisirs', sub: 'Instruments de musique', tx: 'sale', cond: 'Comme neuf', img: 'guitar', city: 'Bordeaux', attrs: {} },
    { s: 'bot-marie', t: 'Berline familiale 2021 — location', d: 'Location longue durée possible, entretien inclus. Idéale famille, spacieuse et sobre.', p: 39000, cat: 'vehicules', sub: 'Voitures', tx: 'rent', cond: 'Comme neuf', img: 'car', city: 'Paris', attrs: { brand: 'Peugeot', model: '508', year: 2021, mileage: 22000, fuel: 'Hybride', gearbox: 'Automatique' } },
  ]
  const now = Date.now()
  await db.collection('listings').insertMany(seed.map((x, i) => {
    const [lat, lon] = CITIES[x.city] || CITIES['Paris']
    return {
      id: uuidv4(), sellerId: x.s, title: x.t, description: x.d, priceCents: x.p, category: x.cat, subcategory: x.sub,
      transactionType: x.tx, condition: x.cond, attributes: x.attrs || {},
      images: [MARKET_IMGS[x.img]], city: x.city, postcode: '', country: 'FR', lat, lon,
      status: 'active', favorites: Math.floor(Math.random() * 40), views: Math.floor(Math.random() * 300), createdAt: new Date(now - i * 3600000 * 6),
    }
  }))
}

async function getSponsored(db) {
  const camps = await db.collection('campaigns').find({ status: 'active' }).toArray()
  return camps.filter((c) => (c.spentCents || 0) < c.budgetCents).slice(0, 3).map((c) => ({
    id: 'ad-' + c.id, sponsored: true, campaignId: c.id,
    author: { id: c.ownerId, name: c.brand || 'Annonceur', handle: c.brandHandle || '@annonceur', initials: (c.brand || 'AD').slice(0, 2).toUpperCase(), avatarColor: c.color || '#4353F0', verified: true },
    caption: `${c.creative?.headline || c.name}\n${c.creative?.body || ''}`.trim(),
    hashtags: [], likes: 0, comments: 0, saves: 0, views: c.impressions || 0,
    product: c.creative?.priceCents ? { title: c.creative?.cta || 'Découvrir', priceCents: c.creative.priceCents, emoji: c.creative?.emoji || '🛍️' } : null,
    aiGenerated: false, liked: false, saved: false, following: false,
    cta: c.creative?.cta || 'En savoir plus', color: c.color || '#4353F0', emoji: c.creative?.emoji || '📣',
    mediaUrl: c.creative?.mediaUrl || null, reason: 'Sponsorisé', createdAt: new Date(),
  }))
}
function injectAds(out, ads) {
  if (!ads.length) return out
  const merged = [...out]
  let pos = 1
  for (const ad of ads) { if (pos <= merged.length) { merged.splice(pos, 0, ad); pos += 4 } }
  return merged
}

// ---------------- Ads Manager v2 (type Google Ads) ----------------
const ADS_CONFIG = {
  types: [
    { id: 'search', name: 'Search', emoji: '🔎', color: '#4353F0', desc: 'Annonces textuelles sur les recherches par mots-clés.', defaultBid: 'cpc' },
    { id: 'display', name: 'Display', emoji: '🖼️', color: '#9B5DE5', desc: 'Bannières visuelles sur le réseau DIVARC.', defaultBid: 'cpm' },
    { id: 'video', name: 'Vidéo', emoji: '🎬', color: '#EF476F', desc: 'Spots vidéo dans le feed Social.', defaultBid: 'cpm' },
    { id: 'shopping', name: 'Shopping', emoji: '🛍️', color: '#3FB68B', desc: 'Fiches produit avec prix dans le Marketplace.', defaultBid: 'cpc' },
  ],
  objectives: [
    { id: 'sales', name: 'Ventes', emoji: '💰' }, { id: 'leads', name: 'Prospects', emoji: '🎯' },
    { id: 'traffic', name: 'Trafic', emoji: '🌐' }, { id: 'awareness', name: 'Notoriété', emoji: '📣' },
    { id: 'app', name: 'Promotion d\u2019app', emoji: '📱' },
  ],
  bidStrategies: [
    { id: 'cpc', name: 'CPC manuel', desc: 'Coût par clic' }, { id: 'cpm', name: 'CPM', desc: 'Coût pour 1000 impressions' },
    { id: 'maximize', name: 'Maximiser les clics', desc: 'Enchère automatique' }, { id: 'target_cpa', name: 'CPA cible', desc: 'Coût par acquisition visé' },
  ],
  interests: ['Tech', 'Mode', 'Voyage', 'Food', 'Sport', 'Musique', 'Gaming', 'Finance', 'Immobilier', 'Auto', 'Beauté', 'Éducation', 'Écologie', 'Famille'],
  devices: ['Mobile', 'Ordinateur', 'Tablette'],
  ageRanges: ['18-24', '25-34', '35-44', '45-54', '55-64', '65+'],
  genders: ['Tous', 'Femmes', 'Hommes'],
}
function adDerived(c) {
  const impr = c.impressions || 0, clk = c.clicks || 0, spent = c.spentCents || 0, conv = c.conversions || 0
  return {
    ...c,
    ctr: impr ? +(clk / impr * 100).toFixed(2) : 0,
    cpcCents: clk ? Math.round(spent / clk) : 0,
    cpmCents: impr ? Math.round(spent / impr * 1000) : 0,
    convRate: clk ? +(conv / clk * 100).toFixed(2) : 0,
    cpaCents: conv ? Math.round(spent / conv) : 0,
    remainingCents: Math.max(0, (c.budgetCents || 0) - spent),
  }
}
// Estimateur de portée quotidienne selon budget, enchère et largeur du ciblage
function estimateReach({ dailyBudgetCents = 0, bidStrategy = 'cpc', maxBidCents = 0, targeting = {} }) {
  const locs = (targeting.locations || []).length
  const ints = (targeting.interests || []).length
  const ages = (targeting.ageRange || []).length
  // largeur : moins de filtres => audience plus large
  let breadth = 1
  breadth *= locs === 0 ? 1 : Math.min(1, 0.25 + locs * 0.15)
  breadth *= ints === 0 ? 1 : Math.min(1, 0.3 + ints * 0.12)
  breadth *= ages === 0 ? 1 : Math.min(1, 0.35 + ages * 0.14)
  const audience = Math.round(2_400_000 * breadth) // audience potentielle
  const cpmBase = bidStrategy === 'cpm' ? Math.max(300, maxBidCents || 500) : 550
  const cpcBase = bidStrategy === 'cpc' || bidStrategy === 'maximize' ? Math.max(15, maxBidCents || 45) : 45
  const dailyImpr = dailyBudgetCents > 0 ? Math.round(dailyBudgetCents / cpmBase * 1000) : 0
  const ctr = 0.012 + Math.random() * 0.006
  const dailyClicks = Math.round(dailyImpr * ctr)
  const dailyReach = Math.min(audience, Math.round(dailyImpr * 0.78))
  return {
    audience,
    impressionsPerDay: [Math.round(dailyImpr * 0.75), Math.round(dailyImpr * 1.25)],
    clicksPerDay: [Math.round(dailyClicks * 0.7), Math.round(dailyClicks * 1.3)],
    reachPerDay: [Math.round(dailyReach * 0.75), Math.round(dailyReach * 1.25)],
    estCpcCents: cpcBase, estCtr: +(ctr * 100).toFixed(2),
  }
}
// Historique simulé sur N jours (pour des analytics vivantes dès la création)
function simulateHistory(camp, days = 7) {
  const daily = []
  let totImpr = 0, totClk = 0, totSpent = 0, totConv = 0
  const perDayBudget = camp.budgetType === 'daily' ? (camp.dailyBudgetCents || Math.round(camp.budgetCents / 30)) : Math.round(camp.budgetCents / 14)
  const cpc = camp.maxBidCents || 45
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10)
    const spend = Math.min(perDayBudget, Math.round(perDayBudget * (0.55 + Math.random() * 0.5)))
    const ctr = 0.012 + Math.random() * 0.008
    const impr = Math.round(spend / (camp.type === 'display' || camp.type === 'video' ? 6 : 5.2))
    const clicks = Math.max(0, Math.round(impr * ctr))
    const conv = Math.max(0, Math.round(clicks * (0.03 + Math.random() * 0.05)))
    daily.push({ date, impressions: impr, clicks, spentCents: spend, conversions: conv })
    totImpr += impr; totClk += clicks; totSpent += spend; totConv += conv
  }
  const capped = Math.min(totSpent, camp.budgetCents)
  return { daily, impressions: totImpr, clicks: totClk, spentCents: capped, conversions: totConv }
}
function adKeywordSuggest(seed) {
  const s = (seed || 'produit').toLowerCase().trim()
  const mods = ['pas cher', 'en ligne', 'livraison', 'avis', 'meilleur', 'promo', 'près de moi', 'occasion', 'neuf', '2025']
  const base = [s, ...mods.map((m) => `${s} ${m}`)]
  return base.slice(0, 10).map((text) => ({
    text, matchType: 'broad',
    volume: Math.floor(Math.random() * 40000 + 1000),
    competition: ['Faible', 'Moyenne', 'Élevée'][Math.floor(Math.random() * 3)],
    suggestedBidCents: Math.floor(Math.random() * 80 + 20),
  }))
}

// ---------------- App Store : vraies apps du marché (logos via Simple Icons CDN) ----------------
const APP_CAT_PERMS = {
  'Social': ['Profil', 'Photos', 'Contacts'],
  'Réseaux pro': ['Profil', 'Contacts', 'Expérience'],
  'Vidéo': ['Profil', 'Historique'],
  'Messagerie': ['Profil', 'Contacts'],
  'Streaming': ['Profil', 'Paiement'],
  'Musique': ['Profil', 'Paiement'],
  'Finance': ['Profil', 'Identité', 'Paiement'],
  'Mobilité': ['Profil', 'Localisation', 'Paiement'],
  'Shopping': ['Profil', 'Adresse', 'Paiement'],
  'Repas': ['Profil', 'Localisation', 'Paiement'],
  'Productivité': ['Profil', 'Fichiers'],
  'Rencontre': ['Profil', 'Photos', 'Localisation'],
}
const APP_CAT_DESC = {
  'Social': (n) => `Partage tes moments, tes stories et suis tes amis sur ${n}.`,
  'Réseaux pro': (n) => `Développe ton réseau professionnel et ta carrière avec ${n}.`,
  'Vidéo': (n) => `Regarde et diffuse des vidéos en direct sur ${n}.`,
  'Messagerie': (n) => `Discute en privé et en groupe, chiffré, sur ${n}.`,
  'Streaming': (n) => `Films & séries en illimité — reprends la lecture partout avec ${n}.`,
  'Musique': (n) => `Des millions de titres et playlists à écouter sur ${n}.`,
  'Finance': (n) => `Gère ton argent, tes paiements et tes cartes avec ${n}.`,
  'Mobilité': (n) => `Déplace-toi en un tap, payé depuis ton wallet, avec ${n}.`,
  'Shopping': (n) => `Achète tout, livré rapidement, paiement wallet sur ${n}.`,
  'Repas': (n) => `Fais-toi livrer tes plats préférés avec ${n}.`,
  'Productivité': (n) => `Organise ton travail et tes fichiers avec ${n}.`,
  'Rencontre': (n) => `Fais de nouvelles rencontres près de chez toi sur ${n}.`,
}
// [id, name, simpleicons slug, brand color, category, featured]
const STORE_RAW = [
  ['instagram', 'Instagram', 'instagram', '#E4405F', 'Social', true],
  ['tiktok', 'TikTok', 'tiktok', '#010101', 'Social', true],
  ['facebook', 'Facebook', 'facebook', '#0866FF', 'Social', false],
  ['x', 'X', 'x', '#000000', 'Social', false],
  ['snapchat', 'Snapchat', 'snapchat', '#0FADFF', 'Social', false],
  ['pinterest', 'Pinterest', 'pinterest', '#BD081C', 'Social', false],
  ['reddit', 'Reddit', 'reddit', '#FF4500', 'Social', false],
  ['threads', 'Threads', 'threads', '#000000', 'Social', false],
  ['linkedin', 'LinkedIn', 'linkedin', '#0A66C2', 'Réseaux pro', true],
  ['youtube', 'YouTube', 'youtube', '#FF0000', 'Vidéo', true],
  ['twitch', 'Twitch', 'twitch', '#9146FF', 'Vidéo', false],
  ['whatsapp', 'WhatsApp', 'whatsapp', '#25D366', 'Messagerie', true],
  ['telegram', 'Telegram', 'telegram', '#26A5E4', 'Messagerie', false],
  ['messenger', 'Messenger', 'messenger', '#00B2FF', 'Messagerie', false],
  ['signal', 'Signal', 'signal', '#3A76F0', 'Messagerie', false],
  ['discord', 'Discord', 'discord', '#5865F2', 'Messagerie', false],
  ['netflix', 'Netflix', 'netflix', '#E50914', 'Streaming', true],
  ['primevideo', 'Prime Video', 'primevideo', '#1F2E5E', 'Streaming', false],
  ['disneyplus', 'Disney+', 'disneyplus', '#113CCF', 'Streaming', false],
  ['spotify', 'Spotify', 'spotify', '#1DB954', 'Musique', true],
  ['deezer', 'Deezer', 'deezer', '#A238FF', 'Musique', false],
  ['paypal', 'PayPal', 'paypal', '#003087', 'Finance', false],
  ['revolut', 'Revolut', 'revolut', '#191C1F', 'Finance', false],
  ['coinbase', 'Coinbase', 'coinbase', '#0052FF', 'Finance', false],
  ['uber', 'Uber', 'uber', '#000000', 'Mobilité', true],
  ['blablacar', 'BlaBlaCar', 'blablacar', '#00AFF5', 'Mobilité', false],
  ['amazon', 'Amazon', 'amazon', '#FF9900', 'Shopping', false],
  ['vinted', 'Vinted', 'vinted', '#09B1BA', 'Shopping', false],
  ['zalando', 'Zalando', 'zalando', '#FF6900', 'Shopping', false],
  ['ubereats', 'Uber Eats', 'ubereats', '#06C167', 'Repas', false],
  ['deliveroo', 'Deliveroo', 'deliveroo', '#00CCBC', 'Repas', false],
  ['notion', 'Notion', 'notion', '#000000', 'Productivité', false],
  ['slack', 'Slack', 'slack', '#4A154B', 'Productivité', false],
  ['zoom', 'Zoom', 'zoom', '#0B5CFF', 'Productivité', false],
  ['dropbox', 'Dropbox', 'dropbox', '#0061FF', 'Productivité', false],
  ['tinder', 'Tinder', 'tinder', '#FF6B6B', 'Rencontre', false],
  ['bumble', 'Bumble', 'bumble', '#FFC629', 'Rencontre', false],
]
const STORE_APPS = STORE_RAW.map(([id, name, slug, color, cat, featured]) => ({
  id, name, slug, color, cat, featured: !!featured,
  logo: `https://cdn.simpleicons.org/${slug}/FFFFFF`,
  emoji: '📱',
  desc: (APP_CAT_DESC[cat] || (() => `Connecte ${name} à ton identité DIVARC.`))(name),
  perms: APP_CAT_PERMS[cat] || ['Profil'],
}))
async function ensureAppStoreSeed(db) {
  if (await db.collection('store_apps').countDocuments() > 0) return
  const ratings = {}
  await db.collection('store_apps').insertMany(STORE_APPS.map((a) => ({
    ...a, rating: +(4.2 + Math.random() * 0.75).toFixed(1),
    users: Math.floor(Math.random() * 900 + 80) * 1000000,
    reviews: Math.floor(Math.random() * 4000 + 200) * 1000,
  })))
}

// ---------------- Hub administratif & santé : connecteurs État (mockés via "ports" eIDAS) ----------------
const ADMIN_CONN = [
  { id: 'impots', name: 'Impôts.gouv', cat: 'Fiscalité', emoji: '🧾', color: '#4353F0', desc: 'Ton avis d\u2019imposition, tes acomptes et ton taux de prélèvement à la source.', scopes: ['Identité', 'Revenus fiscaux'], sensitive: false },
  { id: 'ameli', name: 'Ameli · Assurance Maladie', cat: 'Santé', emoji: '⚕️', color: '#3FB68B', desc: 'Tes remboursements, ta carte Vitale et ton médecin traitant.', scopes: ['Identité', 'Données de santé'], sensitive: true },
  { id: 'caf', name: 'CAF · Allocations', cat: 'Social', emoji: '👨‍👩‍👧', color: '#E2AA2B', desc: 'Tes droits, quotient familial et versements d\u2019aides.', scopes: ['Identité', 'Situation familiale'], sensitive: false },
  { id: 'ants', name: 'ANTS · Titres', cat: 'Identité', emoji: '🪪', color: '#6E7BF5', desc: 'Permis de conduire, carte grise, points et démarches.', scopes: ['Identité', 'Titres'], sensitive: false },
  { id: 'assurance', name: 'Retraite · Info', cat: 'Retraite', emoji: '🏛️', color: '#5B5A50', desc: 'Relevé de carrière et estimation de ta future pension.', scopes: ['Identité', 'Carrière'], sensitive: false },
]
const ADMIN_DATA = {
  impots: [
    { label: 'Revenu fiscal de référence', value: '38 420 €' },
    { label: 'Taux de prélèvement', value: '9,3 %' },
    { label: 'Prochain acompte', value: '298 € · 15 juil.' },
    { label: 'Avis 2024', value: 'Disponible' },
  ],
  ameli: [
    { label: 'Remboursements en attente', value: '2 · 47,80 €' },
    { label: 'Médecin traitant', value: 'Dr. Lefèvre' },
    { label: 'Carte Vitale', value: 'À jour' },
    { label: 'Plafond mutuelle', value: '82 %' },
  ],
  caf: [
    { label: 'Quotient familial', value: '1 240' },
    { label: 'Aides actives', value: 'APL · 214 €/mois' },
    { label: 'Prochain versement', value: '5 du mois' },
    { label: 'Situation', value: 'À jour' },
  ],
  ants: [
    { label: 'Permis', value: 'Valide · 12 pts' },
    { label: 'Carte grise', value: 'AB-123-CD' },
    { label: 'Démarche en cours', value: 'Aucune' },
  ],
  assurance: [
    { label: 'Trimestres validés', value: '68' },
    { label: 'Pension estimée', value: '1 640 €/mois' },
    { label: 'Départ estimé', value: '2049' },
  ],
}

// ---------------- Router ----------------
async function handleRoute(request, { params }) {
  const { path = [] } = await params
  const route = `/${path.join('/')}`
  const method = request.method
  try {
    const db = await connectToMongo()
    const url = new URL(request.url)
    const body = ['POST', 'PATCH', 'PUT'].includes(method) ? await request.json().catch(() => ({})) : {}

    if ((route === '/' || route === '/health') && method === 'GET') {
      return ok({ service: 'DIVARC API', status: 'live', time: new Date().toISOString() })
    }

    /* ===================== AUTH ===================== */
    if (route === '/auth/otp/send' && method === 'POST') {
      const email = String(body.email || '').trim().toLowerCase()
      if (!email.includes('@')) return err('E-mail invalide')
      const code = String(crypto.randomInt(100000, 1000000))
      await db.collection('otp_codes').updateOne(
        { email },
        { $set: { email, codeHash: sha(code), expiresAt: new Date(Date.now() + 10 * 60000), attempts: 0, createdAt: new Date() } },
        { upsert: true }
      )
      const mail = await sendOtpEmail(email, code)
      const exists = !!(await db.collection('users').findOne({ email }))
      // preview mode returns the code so the flow works without an email provider
      return ok({ ok: true, isNew: !exists, previewCode: mail.preview ? code : undefined, delivery: mail.sent ? 'email' : 'preview' })
    }

    if (route === '/auth/otp/verify' && method === 'POST') {
      const email = String(body.email || '').trim().toLowerCase()
      const code = String(body.code || '').trim()
      const row = await db.collection('otp_codes').findOne({ email })
      if (!row || row.expiresAt < new Date()) return err('Code expiré ou introuvable')
      if (row.codeHash !== sha(code)) {
        await db.collection('otp_codes').updateOne({ email }, { $inc: { attempts: 1 } })
        return err('Code invalide')
      }
      await db.collection('otp_codes').deleteOne({ email })
      let user = await db.collection('users').findOne({ email }, { projection: { _id: 0 } })
      let isNew = false
      if (!user) { user = await provisionUser(db, email, body.name); isNew = true }
      const token = crypto.randomBytes(24).toString('hex')
      await db.collection('sessions').insertOne({ token, userId: user.id, createdAt: new Date() })
      const { _id, ...clean } = user
      return ok({ token, user: clean, isNew })
    }

    if (route === '/auth/me' && method === 'GET') {
      const user = await getUser(request, db)
      if (!user) return err('Non authentifié', 401)
      return ok(user)
    }

    if (route === '/auth/logout' && method === 'POST') {
      const auth = request.headers.get('authorization') || ''
      const token = auth.startsWith('Bearer ') ? auth.slice(7) : null
      if (token) await db.collection('sessions').deleteOne({ token })
      return ok({ ok: true })
    }

    // Public: sert les images uploadées (les balises <img> n'envoient pas de Bearer)
    if (route.startsWith('/market/image/') && path.length === 3 && method === 'GET') {
      const img = await db.collection('market_images').findOne({ id: path[2] })
      if (!img) return err('Image introuvable', 404)
      const buf = Buffer.from(img.data, 'base64')
      return handleCORS(new NextResponse(buf, { status: 200, headers: { 'Content-Type': img.contentType || 'image/jpeg', 'Cache-Control': 'public, max-age=31536000, immutable' } }))
    }

    // Everything below requires auth
    const me = await getUser(request, db)
    if (!me) return err('Non authentifié', 401)

    /* ===================== PROFILE ===================== */
    if (route === '/users/me' && method === 'PATCH') {
      const upd = {}
      if (body.name) { upd.name = body.name; upd.initials = initialsOf(body.name) }
      if (body.bio !== undefined) upd.bio = body.bio
      if (body.avatarColor) upd.avatarColor = body.avatarColor
      await db.collection('users').updateOne({ id: me.id }, { $set: upd })
      const u = await db.collection('users').findOne({ id: me.id }, { projection: { _id: 0 } })
      return ok(u)
    }

    if (route === '/users' && method === 'GET') {
      await ensureDemoUsers(db)
      const q = (url.searchParams.get('q') || '').toLowerCase()
      let users = await db.collection('users').find({ id: { $ne: me.id } }, { projection: { _id: 0, email: 0 } }).limit(50).toArray()
      if (q) users = users.filter((u) => u.name.toLowerCase().includes(q) || u.handle.toLowerCase().includes(q))
      return ok(users)
    }

    /* ===================== WALLET (per user) ===================== */
    if (route === '/wallet' && method === 'GET') {
      const wallet = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      const coffres = await db.collection('coffres').find({ userId: me.id }, { projection: { _id: 0 } }).toArray()
      return ok({ ...wallet, coffres })
    }
    if (route === '/transactions' && method === 'GET') {
      const txs = await db.collection('transactions').find({ userId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).limit(100).toArray()
      return ok(txs)
    }
    if (route === '/contacts' && method === 'GET') {
      await ensureDemoUsers(db)
      const users = await db.collection('users').find({ id: { $ne: me.id } }, { projection: { _id: 0, email: 0 } }).limit(20).toArray()
      return ok(users.map((u) => ({ ...u, color: u.avatarColor })))
    }
    if (route === '/coffres' && method === 'POST') {
      const coffre = { id: uuidv4(), userId: me.id, name: body.name || 'Nouveau coffre', emoji: body.emoji || '🎯', balanceCents: body.balanceCents || 0, goalCents: body.goalCents || 100000, rule: body.rule || 'round_up', color: body.color || '#4353F0', createdAt: new Date() }
      await db.collection('coffres').insertOne(coffre)
      const { _id, ...clean } = coffre
      return ok(clean)
    }

    if (route === '/send' && method === 'POST') {
      const { toHandle, toName, amountCents, idempotencyKey, route: payRoute } = body
      if (!amountCents || amountCents <= 0) return err('Montant invalide')
      const idem = idempotencyKey || uuidv4()
      const dup = await db.collection('transactions').findOne({ idempotencyKey: idem, userId: me.id }, { projection: { _id: 0 } })
      if (dup) return ok({ transaction: dup, idempotent: true })
      const wallet = await db.collection('wallets').findOne({ userId: me.id })
      if (!wallet || wallet.balanceCents < amountCents) return err('Solde insuffisant', 402)
      await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: -amountCents } })
      const batch = await postLedger(db, [
        { account: `user:${me.id}`, direction: 'debit', amountCents },
        { account: `user:${toHandle || 'external'}`, direction: 'credit', amountCents },
      ])
      const tx = { id: uuidv4(), userId: me.id, label: `Envoyé à ${toName || toHandle || 'un ami'}`, category: 'P2P', amountCents: -Math.abs(amountCents), carbonKg: 0, icon: '⚡', route: payRoute || 'A2A', idempotencyKey: idem, ledgerBatch: batch, status: 'settled', createdAt: new Date() }
      await db.collection('transactions').insertOne(tx)
      const updated = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      const { _id, ...cleanTx } = tx
      return ok({ transaction: cleanTx, balanceCents: updated.balanceCents })
    }

    /* ===================== ENVELOPPE ===================== */
    if (route === '/enveloppe/create' && method === 'POST') {
      const totalCents = body.totalCents
      const count = Math.max(1, Math.min(body.count || 1, 20))
      if (!totalCents || totalCents <= 0) return err('Montant invalide')
      const wallet = await db.collection('wallets').findOne({ userId: me.id })
      if (!wallet || wallet.balanceCents < totalCents) return err('Solde insuffisant', 402)
      await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: -totalCents } })
      let remaining = totalCents, left = count
      const shares = []
      for (let i = 0; i < count; i++) {
        if (i === count - 1) { shares.push(remaining); break }
        const max = Math.floor((remaining / left) * 2)
        const amt = Math.max(1, Math.floor(Math.random() * (max - 1)) + 1)
        shares.push(amt); remaining -= amt; left--
      }
      for (let i = shares.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[shares[i], shares[j]] = [shares[j], shares[i]] }
      const env = { id: uuidv4(), userId: me.id, message: body.message || 'Bonne chance ! 🧧', totalCents, count, shares: shares.map((amt) => ({ id: uuidv4(), amountCents: amt, claimedBy: null, claimedAt: null })), theme: body.theme || 'gold', expiresAt: new Date(Date.now() + 24 * 3600 * 1000), createdAt: new Date() }
      await db.collection('enveloppes').insertOne(env)
      await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: `Enveloppe (${count} part${count > 1 ? 's' : ''})`, category: 'Enveloppe', amountCents: -totalCents, carbonKg: 0, icon: '🧧', route: null, createdAt: new Date() })
      const updated = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      const { _id, ...clean } = env
      return ok({ enveloppe: clean, balanceCents: updated.balanceCents })
    }
    if (route === '/enveloppe/open' && method === 'POST') {
      const env = await db.collection('enveloppes').findOne({ id: body.enveloppeId })
      if (!env) return err('Enveloppe introuvable', 404)
      const claimer = body.claimer || me.id
      const already = env.shares.find((s) => s.claimedBy === claimer)
      if (already) return ok({ amountCents: already.amountCents, alreadyClaimed: true, message: env.message })
      const free = env.shares.find((s) => !s.claimedBy)
      if (!free) return err('Toutes les parts ont été réclamées', 410)
      free.claimedBy = claimer; free.claimedAt = new Date()
      await db.collection('enveloppes').updateOne({ id: env.id }, { $set: { shares: env.shares } })
      const remaining = env.shares.filter((s) => !s.claimedBy).length
      return ok({ amountCents: free.amountCents, message: env.message, remaining, total: env.count })
    }

    /* ===================== MESSAGING ===================== */
    // list conversations
    if (route === '/conversations' && method === 'GET') {
      await ensureDemoUsers(db)
      const convos = await db.collection('conversations').find({ memberIds: me.id }, { projection: { _id: 0 } }).sort({ lastMessageAt: -1 }).toArray()
      const out = []
      for (const c of convos) {
        let title = c.name, avatarColor = c.avatarColor, other = null, friendship = null
        if (c.type === 'dm') {
          const otherId = c.memberIds.find((m) => m !== me.id)
          other = await db.collection('users').findOne({ id: otherId }, { projection: { _id: 0, email: 0 } })
          title = other?.name; avatarColor = other?.avatarColor
          friendship = await getFriendship(db, me.id, otherId)
        }
        const lastRead = (c.reads || {})[me.id]
        const unread = await db.collection('messages').countDocuments({ conversationId: c.id, senderId: { $ne: me.id }, createdAt: { $gt: lastRead ? new Date(lastRead) : new Date(0) } })
        out.push({ id: c.id, type: c.type, title, avatarColor, other, friendship, memberCount: c.memberIds.length, lastText: c.lastText, lastMessageAt: c.lastMessageAt, unread, topic: c.topic })
      }
      return ok(out)
    }
    // discover public communities
    if (route === '/communities' && method === 'GET') {
      await ensureDemoUsers(db)
      const comms = await db.collection('conversations').find({ type: 'community', isPublic: true }, { projection: { _id: 0 } }).toArray()
      return ok(comms.map((c) => ({ id: c.id, name: c.name, topic: c.topic, avatarColor: c.avatarColor, memberCount: c.memberIds.length, joined: c.memberIds.includes(me.id) })))
    }
    // create conversation (dm/group/community)
    if (route === '/conversations' && method === 'POST') {
      const type = body.type || 'dm'
      const handles = (body.memberHandles || []).map((h) => h.startsWith('@') ? h : '@' + h)
      const members = await db.collection('users').find({ handle: { $in: handles } }).toArray()
      const memberIds = [me.id, ...members.map((m) => m.id)]
      if (type === 'dm') {
        const otherId = memberIds.find((m) => m !== me.id)
        if (!otherId) return err('Destinataire introuvable', 404)
        const existing = await db.collection('conversations').findOne({ type: 'dm', memberIds: { $all: [me.id, otherId], $size: 2 } })
        if (existing) return ok({ id: existing.id, existing: true })
      }
      const conv = { id: uuidv4(), type, name: body.name || null, topic: body.topic || null, avatarColor: body.avatarColor || COLORS[Math.floor(Math.random() * COLORS.length)], memberIds: [...new Set(memberIds)], createdBy: me.id, isPublic: type === 'community', reads: {}, lastText: null, lastMessageAt: new Date(), createdAt: new Date() }
      await db.collection('conversations').insertOne(conv)
      return ok({ id: conv.id })
    }
    // join community
    if (route.startsWith('/conversations/') && path[2] === 'join' && method === 'POST') {
      const cid = path[1]
      await db.collection('conversations').updateOne({ id: cid }, { $addToSet: { memberIds: me.id } })
      return ok({ ok: true })
    }
    // get messages
    if (route.startsWith('/conversations/') && path[2] === 'messages' && method === 'GET') {
      const cid = path[1]
      const conv = await db.collection('conversations').findOne({ id: cid })
      if (!conv || !conv.memberIds.includes(me.id)) return err('Conversation introuvable', 404)
      const msgs = await db.collection('messages').find({ conversationId: cid }, { projection: { _id: 0 } }).sort({ createdAt: 1 }).limit(200).toArray()
      await db.collection('conversations').updateOne({ id: cid }, { $set: { [`reads.${me.id}`]: new Date() } })
      let friendship = null, other = null
      if (conv.type === 'dm') {
        const otherId = conv.memberIds.find((m) => m !== me.id)
        other = await db.collection('users').findOne({ id: otherId }, { projection: { _id: 0, email: 0 } })
        friendship = await getFriendship(db, me.id, otherId)
      }
      return ok({ conversation: { id: conv.id, type: conv.type, name: conv.name, topic: conv.topic, memberCount: conv.memberIds.length, other, friendship }, messages: msgs })
    }
    // send message
    if (route.startsWith('/conversations/') && path[2] === 'messages' && method === 'POST') {
      const cid = path[1]
      const conv = await db.collection('conversations').findOne({ id: cid })
      if (!conv || !conv.memberIds.includes(me.id)) return err('Conversation introuvable', 404)
      const text = String(body.text || '').trim()
      if (!text) return err('Message vide')
      const msg = { id: uuidv4(), conversationId: cid, senderId: me.id, senderName: me.name, text, kind: body.kind || 'text', reactions: [], createdAt: new Date() }
      await db.collection('messages').insertOne(msg)
      await db.collection('conversations').updateOne({ id: cid }, { $set: { lastText: text, lastMessageAt: new Date() } })

      let friendship = null
      if (conv.type === 'dm') {
        const otherId = conv.memberIds.find((m) => m !== me.id)
        friendship = await bumpFriendship(db, me.id, otherId, 10)
        // bot auto-reply to keep it alive
        const other = await db.collection('users').findOne({ id: otherId })
        if (other?.isBot) {
          const reply = BOT_REPLIES[Math.floor(Math.random() * BOT_REPLIES.length)]
          await db.collection('messages').insertOne({ id: uuidv4(), conversationId: cid, senderId: other.id, senderName: other.name, text: reply, kind: 'text', reactions: [], createdAt: new Date(Date.now() + 900) })
          await db.collection('conversations').updateOne({ id: cid }, { $set: { lastText: reply, lastMessageAt: new Date(Date.now() + 900) } })
          friendship = await bumpFriendship(db, otherId, me.id, 10)
        }
      }
      const { _id, ...clean } = msg
      return ok({ message: clean, friendship })
    }
    // react to a message
    if (route.startsWith('/messages/') && path[2] === 'react' && method === 'POST') {
      const mid = path[1]
      const msg = await db.collection('messages').findOne({ id: mid })
      if (!msg) return err('Message introuvable', 404)
      const emoji = body.emoji || '❤️'
      const reactions = (msg.reactions || []).filter((r) => r.userId !== me.id)
      const had = (msg.reactions || []).some((r) => r.userId === me.id && r.emoji === emoji)
      if (!had) reactions.push({ userId: me.id, emoji })
      await db.collection('messages').updateOne({ id: mid }, { $set: { reactions } })
      return ok({ reactions })
    }

    /* ===================== DIVARC SOCIAL ===================== */
    await ensureSocialSeed(db)

    if (route === '/social/feed' && method === 'GET') {
      const mode = url.searchParams.get('mode') || 'foryou'
      const scope = url.searchParams.get('scope') || 'all'
      const interests = (await db.collection('interests').findOne({ userId: me.id }))?.topics || []
      const follows = (await db.collection('follows').find({ followerId: me.id }).toArray()).map((f) => f.authorId)
      const liked = new Set((await db.collection('post_likes').find({ userId: me.id }).toArray()).map((x) => x.postId))
      const saved = new Set((await db.collection('post_saves').find({ userId: me.id }).toArray()).map((x) => x.postId))
      const ni = new Set((await db.collection('social_events').find({ userId: me.id, type: 'notinterested' }).toArray()).map((x) => x.postId))
      let posts = await db.collection('posts').find({}, { projection: { _id: 0 } }).toArray()
      posts = posts.filter((p) => !ni.has(p.id))
      if (scope === 'following') posts = posts.filter((p) => follows.includes(p.authorId))

      const authors = {}
      for (const p of posts) {
        if (!authors[p.authorId]) authors[p.authorId] = await db.collection('users').findOne({ id: p.authorId }, { projection: { _id: 0, email: 0 } })
      }
      const now = Date.now()
      const scored = posts.map((p) => {
        const ageH = (now - new Date(p.createdAt).getTime()) / 3600000
        const freshness = Math.max(0, 1 - ageH / 72)
        const eng = ((p.likes || 0) + (p.comments || 0) * 2 + (p.saves || 0) * 1.5) / ((p.views || 0) + 12)
        const tagMatch = (p.hashtags || []).filter((h) => interests.includes(h)).length
        const interestMatch = interests.length ? Math.min(1, tagMatch / 1) : 0
        const followBoost = follows.includes(p.authorId) ? 1 : 0
        const explore = Math.random() * 0.3
        const factors = {
          'Tu suis ce créateur': 2 * followBoost,
          [`Basé sur ton intérêt ${(p.hashtags || []).find((h) => interests.includes(h)) || ''}`]: 2.5 * interestMatch,
          'Populaire en ce moment': 3 * eng,
          'Fraîchement publié': 1.8 * freshness,
          'Une découverte pour toi': explore,
        }
        const score = Object.values(factors).reduce((a, b) => a + b, 0)
        const reason = Object.entries(factors).sort((a, b) => b[1] - a[1])[0][0]
        return { ...p, score, reason }
      })
      if (mode === 'chrono') scored.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
      else scored.sort((a, b) => b.score - a.score)

      const out = scored.map((p) => ({
        id: p.id, caption: p.caption, mediaUrl: p.mediaUrl, mediaType: p.mediaType, poster: p.poster,
        hashtags: p.hashtags, likes: p.likes, comments: p.comments, saves: p.saves, views: p.views,
        product: p.product || null, aiGenerated: !!p.aiGenerated,
        author: authors[p.authorId] ? { id: authors[p.authorId].id, name: authors[p.authorId].name, handle: authors[p.authorId].handle, initials: authors[p.authorId].initials, avatarColor: authors[p.authorId].avatarColor, verified: authors[p.authorId].verified } : null,
        liked: liked.has(p.id), saved: saved.has(p.id), following: follows.includes(p.authorId),
        reason: mode === 'chrono' ? 'Ordre chronologique' : p.reason,
        createdAt: p.createdAt,
      }))
      const sponsored = mode === 'chrono' ? [] : await getSponsored(db)
      return ok(injectAds(out, sponsored))
    }

    if (route === '/social/posts' && method === 'POST') {
      const post = {
        id: uuidv4(), authorId: me.id, caption: body.caption || '', mediaUrl: body.mediaUrl,
        mediaType: body.mediaType || 'video', poster: body.poster || null,
        hashtags: (body.hashtags || []).map((h) => h.startsWith('#') ? h : '#' + h),
        product: body.product || null, aiGenerated: !!body.aiGenerated,
        likes: 0, comments: 0, saves: 0, views: 0, earningsCents: 0, createdAt: new Date(),
      }
      await db.collection('posts').insertOne(post)
      const { _id, ...clean } = post
      return ok(clean)
    }

    if (route.startsWith('/social/posts/') && path[3] === 'like' && method === 'POST') {
      const pid = path[2]
      const ex = await db.collection('post_likes').findOne({ postId: pid, userId: me.id })
      if (ex) { await db.collection('post_likes').deleteOne({ postId: pid, userId: me.id }); await db.collection('posts').updateOne({ id: pid }, { $inc: { likes: -1 } }) }
      else { await db.collection('post_likes').insertOne({ postId: pid, userId: me.id, createdAt: new Date() }); await db.collection('posts').updateOne({ id: pid }, { $inc: { likes: 1 } }) }
      const p = await db.collection('posts').findOne({ id: pid })
      return ok({ liked: !ex, likes: p.likes })
    }
    if (route.startsWith('/social/posts/') && path[3] === 'save' && method === 'POST') {
      const pid = path[2]
      const ex = await db.collection('post_saves').findOne({ postId: pid, userId: me.id })
      if (ex) { await db.collection('post_saves').deleteOne({ postId: pid, userId: me.id }); await db.collection('posts').updateOne({ id: pid }, { $inc: { saves: -1 } }) }
      else { await db.collection('post_saves').insertOne({ postId: pid, userId: me.id, createdAt: new Date() }); await db.collection('posts').updateOne({ id: pid }, { $inc: { saves: 1 } }) }
      const p = await db.collection('posts').findOne({ id: pid })
      return ok({ saved: !ex, saves: p.saves })
    }
    if (route.startsWith('/social/posts/') && path[3] === 'notinterested' && method === 'POST') {
      await db.collection('social_events').insertOne({ userId: me.id, postId: path[2], type: 'notinterested', createdAt: new Date() })
      return ok({ ok: true })
    }
    if (route.startsWith('/social/posts/') && path[3] === 'view' && method === 'POST') {
      await db.collection('posts').updateOne({ id: path[2] }, { $inc: { views: 1 } })
      return ok({ ok: true })
    }
    if (route.startsWith('/social/posts/') && path[3] === 'comments' && method === 'GET') {
      const comments = await db.collection('comments').find({ postId: path[2] }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).limit(100).toArray()
      return ok(comments)
    }
    if (route.startsWith('/social/posts/') && path[3] === 'comments' && method === 'POST') {
      const text = String(body.text || '').trim()
      if (!text) return err('Commentaire vide')
      const c = { id: uuidv4(), postId: path[2], userId: me.id, name: me.name, initials: me.initials, avatarColor: me.avatarColor, text, createdAt: new Date() }
      await db.collection('comments').insertOne(c)
      await db.collection('posts').updateOne({ id: path[2] }, { $inc: { comments: 1 } })
      const { _id, ...clean } = c
      return ok(clean)
    }
    if (route.startsWith('/social/follow/') && method === 'POST') {
      const authorId = path[2]
      const ex = await db.collection('follows').findOne({ followerId: me.id, authorId })
      if (ex) await db.collection('follows').deleteOne({ followerId: me.id, authorId })
      else await db.collection('follows').insertOne({ followerId: me.id, authorId, createdAt: new Date() })
      return ok({ following: !ex })
    }
    if (route.startsWith('/social/posts/') && (path[3] === 'buy' || path[3] === 'tip') && method === 'POST') {
      const pid = path[2]
      const post = await db.collection('posts').findOne({ id: pid })
      if (!post) return err('Publication introuvable', 404)
      const isTip = path[3] === 'tip'
      const amount = isTip ? Number(body.amountCents) : (post.product?.priceCents || 0)
      if (!amount || amount <= 0) return err('Montant invalide')
      const wallet = await db.collection('wallets').findOne({ userId: me.id })
      if (!wallet || wallet.balanceCents < amount) return err('Solde insuffisant', 402)
      await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: -amount } })
      await creditWallet(db, post.authorId, amount)
      await db.collection('posts').updateOne({ id: pid }, { $inc: { earningsCents: amount, ...(isTip ? {} : { sales: 1 }) } })
      const author = await db.collection('users').findOne({ id: post.authorId })
      await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: isTip ? `Pourboire à ${author?.name || 'créateur'}` : `Achat : ${post.product?.title || 'article'}`, category: 'Social', amountCents: -amount, carbonKg: 0, icon: isTip ? '💛' : '🛍️', route: null, createdAt: new Date() })
      await postLedger(db, [{ account: `user:${me.id}`, direction: 'debit', amountCents: amount }, { account: `user:${post.authorId}`, direction: 'credit', amountCents: amount }])
      const updated = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      return ok({ ok: true, balanceCents: updated.balanceCents, amountCents: amount })
    }
    if (route === '/social/interests' && method === 'POST') {
      await db.collection('interests').updateOne({ userId: me.id }, { $set: { userId: me.id, topics: body.topics || [] } }, { upsert: true })
      return ok({ ok: true, topics: body.topics || [] })
    }
    if (route === '/social/creator' && method === 'GET') {
      const posts = await db.collection('posts').find({ authorId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      const followers = await db.collection('follows').countDocuments({ authorId: me.id })
      const earnings = posts.reduce((a, p) => a + (p.earningsCents || 0), 0)
      const views = posts.reduce((a, p) => a + (p.views || 0), 0)
      const likes = posts.reduce((a, p) => a + (p.likes || 0), 0)
      return ok({ posts, followers, earningsCents: earnings, views, likes })
    }

    /* ===================== GÉOLOCALISATION (Europe) ===================== */
    if (route === '/geo/autocomplete' && method === 'GET') {
      const q = (url.searchParams.get('q') || '').trim()
      if (q.length < 3) return ok([])
      const country = url.searchParams.get('country') || ''
      return ok(await geoAutocomplete(q, country))
    }
    if (route === '/geo/reverse' && method === 'GET') {
      const lat = Number(url.searchParams.get('lat')), lon = Number(url.searchParams.get('lon'))
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return err('Coordonnées invalides')
      return ok(await geoReverse(lat, lon))
    }

    /* ===================== MARKETPLACE ===================== */
    await ensureMarketSeed(db)

    if (route === '/market/categories' && method === 'GET') {
      return ok({ categories: MARKET_CATEGORIES, conditions: CONDITIONS })
    }

    // Upload image -> stockée en base64, servie via /market/image/:id
    if (route === '/market/upload' && method === 'POST') {
      const data = String(body.data || '')
      const m = data.match(/^data:(image\/[a-zA-Z+]+);base64,(.+)$/)
      const contentType = m ? m[1] : (body.contentType || 'image/jpeg')
      const b64 = m ? m[2] : data
      if (!b64) return err('Image invalide')
      // limite ~6 Mo décodés
      if (b64.length > 8_000_000) return err('Image trop lourde (max ~6 Mo)', 413)
      const id = uuidv4()
      await db.collection('market_images').insertOne({ id, userId: me.id, data: b64, contentType, createdAt: new Date() })
      return ok({ id, url: `/api/market/image/${id}` })
    }

    if (route === '/market/listings' && method === 'GET') {
      const q = (url.searchParams.get('q') || '').toLowerCase()
      const cat = url.searchParams.get('cat') || ''
      const subcat = url.searchParams.get('subcat') || ''
      const txType = url.searchParams.get('type') || ''
      const cond = url.searchParams.get('condition') || ''
      const minP = Number(url.searchParams.get('minPrice')) || 0
      const maxP = Number(url.searchParams.get('maxPrice')) || 0
      const sort = url.searchParams.get('sort') || 'recent'
      const lat = Number(url.searchParams.get('lat')), lon = Number(url.searchParams.get('lon'))
      const radiusKm = Number(url.searchParams.get('radiusKm')) || 0
      const hasGeo = Number.isFinite(lat) && Number.isFinite(lon)

      let items = await db.collection('listings').find({ status: 'active' }, { projection: { _id: 0 } }).toArray()
      if (cat && cat !== 'Tout') items = items.filter((i) => i.category === cat)
      if (subcat) items = items.filter((i) => i.subcategory === subcat)
      if (txType) items = items.filter((i) => (i.transactionType || 'sale') === txType)
      if (cond) items = items.filter((i) => i.condition === cond)
      if (minP) items = items.filter((i) => i.priceCents >= minP)
      if (maxP) items = items.filter((i) => i.priceCents <= maxP)
      if (q) items = items.filter((i) => i.title.toLowerCase().includes(q) || (i.description || '').toLowerCase().includes(q) || (i.city || '').toLowerCase().includes(q))
      if (hasGeo) {
        items = items.map((i) => ({ ...i, distanceKm: (Number.isFinite(i.lat) && Number.isFinite(i.lon)) ? Math.round(haversineKm(lat, lon, i.lat, i.lon)) : null }))
        if (radiusKm > 0) items = items.filter((i) => i.distanceKm != null && i.distanceKm <= radiusKm)
      }
      if (sort === 'price_asc') items.sort((a, b) => a.priceCents - b.priceCents)
      else if (sort === 'price_desc') items.sort((a, b) => b.priceCents - a.priceCents)
      else if (sort === 'distance' && hasGeo) items.sort((a, b) => (a.distanceKm ?? 1e9) - (b.distanceKm ?? 1e9))
      else items.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))

      const favs = new Set((await db.collection('market_favorites').find({ userId: me.id }).toArray()).map((f) => f.listingId))
      const out = []
      for (const i of items) {
        const seller = await db.collection('users').findOne({ id: i.sellerId }, { projection: { _id: 0, email: 0 } })
        out.push({ ...i, favorited: favs.has(i.id), seller: seller ? { id: seller.id, name: seller.name, handle: seller.handle, initials: seller.initials, avatarColor: seller.avatarColor, verified: seller.verified } : null })
      }
      return ok(out)
    }

    if (route === '/market/listings' && method === 'POST') {
      const catDef = MARKET_CATEGORIES.find((c) => c.id === body.category)
      const listing = {
        id: uuidv4(), sellerId: me.id, title: body.title || 'Annonce', description: body.description || '',
        priceCents: Math.max(0, Math.round(body.priceCents || 0)),
        category: catDef ? catDef.id : 'maison', subcategory: body.subcategory || (catDef?.subcats?.[0] || 'Autre'),
        transactionType: body.transactionType || 'sale', condition: body.condition || 'Bon état',
        attributes: (body.attributes && typeof body.attributes === 'object') ? body.attributes : {},
        images: Array.isArray(body.images) ? body.images.filter(Boolean).slice(0, 8) : [],
        city: body.city || '', postcode: body.postcode || '', country: body.country || 'FR',
        lat: Number.isFinite(+body.lat) ? +body.lat : null, lon: Number.isFinite(+body.lon) ? +body.lon : null,
        status: 'active', favorites: 0, views: 0, createdAt: new Date(),
      }
      await db.collection('listings').insertOne(listing)
      const { _id, ...clean } = listing
      return ok(clean)
    }

    if (route.startsWith('/market/listings/') && path.length === 3 && method === 'GET') {
      const l = await db.collection('listings').findOne({ id: path[2] }, { projection: { _id: 0 } })
      if (!l) return err('Annonce introuvable', 404)
      await db.collection('listings').updateOne({ id: path[2] }, { $inc: { views: 1 } })
      const seller = await db.collection('users').findOne({ id: l.sellerId }, { projection: { _id: 0, email: 0 } })
      const favs = new Set((await db.collection('market_favorites').find({ userId: me.id }).toArray()).map((f) => f.listingId))
      const similar = await db.collection('listings').find({ category: l.category, status: 'active', id: { $ne: l.id } }, { projection: { _id: 0 } }).limit(4).toArray()
      return ok({ ...l, favorited: favs.has(l.id), seller, isMine: l.sellerId === me.id, similar })
    }

    if (route.startsWith('/market/listings/') && path.length === 3 && method === 'DELETE') {
      const l = await db.collection('listings').findOne({ id: path[2] })
      if (!l) return err('Annonce introuvable', 404)
      if (l.sellerId !== me.id) return err('Non autorisé', 403)
      await db.collection('listings').deleteOne({ id: path[2] })
      return ok({ ok: true })
    }

    if (route.startsWith('/market/listings/') && path[3] === 'favorite' && method === 'POST') {
      const lid = path[2]
      const ex = await db.collection('market_favorites').findOne({ listingId: lid, userId: me.id })
      if (ex) { await db.collection('market_favorites').deleteOne({ listingId: lid, userId: me.id }); await db.collection('listings').updateOne({ id: lid }, { $inc: { favorites: -1 } }) }
      else { await db.collection('market_favorites').insertOne({ listingId: lid, userId: me.id }); await db.collection('listings').updateOne({ id: lid }, { $inc: { favorites: 1 } }) }
      const l = await db.collection('listings').findOne({ id: lid })
      return ok({ favorited: !ex, favorites: l.favorites })
    }

    if (route.startsWith('/market/listings/') && path[3] === 'buy' && method === 'POST') {
      const l = await db.collection('listings').findOne({ id: path[2] })
      if (!l) return err('Annonce introuvable', 404)
      if (l.status !== 'active') return err('Déjà vendu', 410)
      if (l.sellerId === me.id) return err('Tu ne peux pas acheter ta propre annonce')
      const priceCents = Math.round(body.priceCents || l.priceCents) // supporte prix négocié
      const wallet = await db.collection('wallets').findOne({ userId: me.id })
      if (!wallet || wallet.balanceCents < priceCents) return err('Solde insuffisant', 402)
      await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: -priceCents } })
      await creditWallet(db, l.sellerId, priceCents)
      const newStatus = l.transactionType === 'rent' ? 'rented' : 'sold'
      await db.collection('listings').updateOne({ id: l.id }, { $set: { status: newStatus, buyerId: me.id, soldAt: new Date() } })
      const order = { id: uuidv4(), listingId: l.id, title: l.title, image: l.images?.[0] || null, buyerId: me.id, sellerId: l.sellerId, priceCents, createdAt: new Date() }
      await db.collection('orders').insertOne(order)
      await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: `Achat : ${l.title}`, category: 'Marketplace', amountCents: -priceCents, carbonKg: 0, icon: '🛍️', route: null, createdAt: new Date() })
      await postLedger(db, [{ account: `user:${me.id}`, direction: 'debit', amountCents: priceCents }, { account: `user:${l.sellerId}`, direction: 'credit', amountCents: priceCents }])
      const updated = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      return ok({ ok: true, order: { id: order.id }, balanceCents: updated.balanceCents })
    }

    if (route === '/market/mine' && method === 'GET') {
      const selling = await db.collection('listings').find({ sellerId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      const orders = await db.collection('orders').find({ buyerId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      const favIds = (await db.collection('market_favorites').find({ userId: me.id }).toArray()).map((f) => f.listingId)
      const favorites = await db.collection('listings').find({ id: { $in: favIds }, status: 'active' }, { projection: { _id: 0 } }).toArray()
      return ok({ selling, purchases: orders, favorites })
    }

    /* ===================== MARKETPLACE — CHAT & OFFRES ===================== */
    // Démarre (ou récupère) une conversation avec le vendeur d'une annonce
    if (route.startsWith('/market/listings/') && path[3] === 'chat' && method === 'POST') {
      const l = await db.collection('listings').findOne({ id: path[2] })
      if (!l) return err('Annonce introuvable', 404)
      if (l.sellerId === me.id) return err('C\u2019est ta propre annonce')
      let thread = await db.collection('market_threads').findOne({ listingId: l.id, buyerId: me.id })
      if (!thread) {
        thread = { id: uuidv4(), listingId: l.id, listingTitle: l.title, listingImage: l.images?.[0] || null, listingPriceCents: l.priceCents, buyerId: me.id, sellerId: l.sellerId, createdAt: new Date(), lastMessageAt: new Date() }
        await db.collection('market_threads').insertOne(thread)
        if (body.text) await db.collection('market_messages').insertOne({ id: uuidv4(), threadId: thread.id, senderId: me.id, type: 'text', text: String(body.text), createdAt: new Date() })
      }
      const { _id, ...clean } = thread
      return ok({ thread: clean, existing: !!_id && false })
    }

    if (route === '/market/threads' && method === 'GET') {
      const threads = await db.collection('market_threads').find({ $or: [{ buyerId: me.id }, { sellerId: me.id }] }, { projection: { _id: 0 } }).sort({ lastMessageAt: -1 }).toArray()
      const out = []
      for (const t of threads) {
        const otherId = t.buyerId === me.id ? t.sellerId : t.buyerId
        const other = await db.collection('users').findOne({ id: otherId }, { projection: { _id: 0, email: 0 } })
        const last = await db.collection('market_messages').find({ threadId: t.id }).sort({ createdAt: -1 }).limit(1).toArray()
        out.push({ ...t, role: t.buyerId === me.id ? 'buyer' : 'seller', other: other ? { id: other.id, name: other.name, handle: other.handle, initials: other.initials, avatarColor: other.avatarColor } : null, lastMessage: last[0] ? { text: last[0].text, type: last[0].type, amountCents: last[0].amountCents } : null })
      }
      return ok(out)
    }

    if (route.startsWith('/market/threads/') && path[3] === 'messages' && method === 'GET') {
      const t = await db.collection('market_threads').findOne({ id: path[2] }, { projection: { _id: 0 } })
      if (!t || (t.buyerId !== me.id && t.sellerId !== me.id)) return err('Conversation introuvable', 404)
      const msgs = await db.collection('market_messages').find({ threadId: t.id }, { projection: { _id: 0 } }).sort({ createdAt: 1 }).toArray()
      const otherId = t.buyerId === me.id ? t.sellerId : t.buyerId
      const other = await db.collection('users').findOne({ id: otherId }, { projection: { _id: 0, email: 0 } })
      const listing = await db.collection('listings').findOne({ id: t.listingId }, { projection: { _id: 0 } })
      return ok({ thread: { ...t, role: t.buyerId === me.id ? 'buyer' : 'seller' }, messages: msgs, other, listing })
    }

    if (route.startsWith('/market/threads/') && path[3] === 'messages' && method === 'POST') {
      const t = await db.collection('market_threads').findOne({ id: path[2] })
      if (!t || (t.buyerId !== me.id && t.sellerId !== me.id)) return err('Conversation introuvable', 404)
      const msg = { id: uuidv4(), threadId: t.id, senderId: me.id, type: 'text', text: String(body.text || '').slice(0, 2000), createdAt: new Date() }
      if (!msg.text.trim()) return err('Message vide')
      await db.collection('market_messages').insertOne(msg)
      await db.collection('market_threads').updateOne({ id: t.id }, { $set: { lastMessageAt: new Date() } })
      const { _id, ...clean } = msg
      return ok(clean)
    }

    // Faire une offre (négociation)
    if (route.startsWith('/market/threads/') && path[3] === 'offer' && path.length === 4 && method === 'POST') {
      const t = await db.collection('market_threads').findOne({ id: path[2] })
      if (!t || (t.buyerId !== me.id && t.sellerId !== me.id)) return err('Conversation introuvable', 404)
      const amountCents = Math.round(body.amountCents || 0)
      if (amountCents <= 0) return err('Montant invalide')
      const offerId = uuidv4()
      const msg = { id: uuidv4(), offerId, threadId: t.id, senderId: me.id, type: 'offer', amountCents, offerStatus: 'pending', createdAt: new Date() }
      await db.collection('market_messages').insertOne(msg)
      await db.collection('market_threads').updateOne({ id: t.id }, { $set: { lastMessageAt: new Date() } })
      const { _id, ...clean } = msg
      return ok(clean)
    }

    // Répondre à une offre : accept | reject
    if (route.startsWith('/market/threads/') && path[3] === 'offer' && path.length === 6 && path[5] === 'respond' && method === 'POST') {
      const t = await db.collection('market_threads').findOne({ id: path[2] })
      if (!t || (t.buyerId !== me.id && t.sellerId !== me.id)) return err('Conversation introuvable', 404)
      const offerId = path[4]
      const offer = await db.collection('market_messages').findOne({ threadId: t.id, offerId, type: 'offer' })
      if (!offer) return err('Offre introuvable', 404)
      if (offer.senderId === me.id) return err('Tu ne peux pas répondre à ta propre offre')
      const action = body.action === 'accept' ? 'accepted' : 'rejected'
      await db.collection('market_messages').updateOne({ offerId }, { $set: { offerStatus: action } })
      await db.collection('market_messages').insertOne({ id: uuidv4(), threadId: t.id, senderId: me.id, type: 'system', text: action === 'accepted' ? `Offre acceptée : ${(offer.amountCents / 100).toFixed(2)} €` : 'Offre refusée', createdAt: new Date() })
      await db.collection('market_threads').updateOne({ id: t.id }, { $set: { lastMessageAt: new Date(), acceptedPriceCents: action === 'accepted' ? offer.amountCents : t.acceptedPriceCents } })
      return ok({ ok: true, offerStatus: action, amountCents: offer.amountCents })
    }


    /* ===================== ADS MANAGER v2 (type Google Ads) ===================== */
    if (route === '/ads/config' && method === 'GET') {
      return ok(ADS_CONFIG)
    }
    if (route === '/ads/keywords' && method === 'GET') {
      return ok(adKeywordSuggest(url.searchParams.get('q') || ''))
    }
    if (route === '/ads/estimate' && method === 'POST') {
      return ok(estimateReach({
        dailyBudgetCents: Math.round(body.dailyBudgetCents || 0),
        bidStrategy: body.bidStrategy || 'cpc',
        maxBidCents: Math.round(body.maxBidCents || 0),
        targeting: body.targeting || {},
      }))
    }
    if (route === '/ads/insights' && method === 'GET') {
      const camps = await db.collection('campaigns').find({ ownerId: me.id }, { projection: { _id: 0 } }).toArray()
      const tot = camps.reduce((a, c) => ({
        impressions: a.impressions + (c.impressions || 0), clicks: a.clicks + (c.clicks || 0),
        spentCents: a.spentCents + (c.spentCents || 0), conversions: a.conversions + (c.conversions || 0),
        budgetCents: a.budgetCents + (c.budgetCents || 0),
      }), { impressions: 0, clicks: 0, spentCents: 0, conversions: 0, budgetCents: 0 })
      // série agrégée par jour (14 jours)
      const map = {}
      for (const c of camps) for (const d of (c.daily || [])) {
        if (!map[d.date]) map[d.date] = { date: d.date, impressions: 0, clicks: 0, spentCents: 0, conversions: 0 }
        map[d.date].impressions += d.impressions; map[d.date].clicks += d.clicks; map[d.date].spentCents += d.spentCents; map[d.date].conversions += d.conversions
      }
      const daily = Object.values(map).sort((a, b) => a.date.localeCompare(b.date)).slice(-14)
      const top = camps.map(adDerived).sort((a, b) => (b.impressions || 0) - (a.impressions || 0)).slice(0, 5)
      return ok({
        totals: { ...tot, ctr: tot.impressions ? +(tot.clicks / tot.impressions * 100).toFixed(2) : 0, cpcCents: tot.clicks ? Math.round(tot.spentCents / tot.clicks) : 0, convRate: tot.clicks ? +(tot.conversions / tot.clicks * 100).toFixed(2) : 0 },
        daily, top,
        counts: { total: camps.length, active: camps.filter((c) => c.status === 'active').length, paused: camps.filter((c) => c.status === 'paused').length },
      })
    }

    if (route === '/ads/campaigns' && method === 'POST') {
      const budgetCents = Math.round(body.budgetCents || 0)
      if (budgetCents <= 0) return err('Budget invalide')
      const wallet = await db.collection('wallets').findOne({ userId: me.id })
      if (!wallet || wallet.balanceCents < budgetCents) return err('Solde insuffisant pour financer la campagne', 402)
      await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: -budgetCents } })
      const typeDef = ADS_CONFIG.types.find((t) => t.id === body.type) || ADS_CONFIG.types[0]
      const camp = {
        id: uuidv4(), ownerId: me.id, name: body.name || 'Campagne',
        type: typeDef.id, objective: body.objective || 'awareness',
        brand: body.brand || me.name, brandHandle: me.handle,
        budgetCents, budgetType: body.budgetType === 'daily' ? 'daily' : 'total',
        dailyBudgetCents: Math.round(body.dailyBudgetCents || 0),
        bidStrategy: body.bidStrategy || typeDef.defaultBid, maxBidCents: Math.round(body.maxBidCents || 45),
        targetCpaCents: Math.round(body.targetCpaCents || 0),
        targeting: {
          locations: body.targeting?.locations || [], radiusKm: body.targeting?.radiusKm || 0,
          ageRange: body.targeting?.ageRange || [], genders: body.targeting?.genders || ['Tous'],
          interests: body.targeting?.interests || [], devices: body.targeting?.devices || ADS_CONFIG.devices,
        },
        keywords: Array.isArray(body.keywords) ? body.keywords.map((k) => ({ text: typeof k === 'string' ? k : k.text, matchType: k.matchType || 'broad', bidCents: k.bidCents || Math.round(body.maxBidCents || 45) })) : [],
        creative: {
          headline: body.creative?.headline || 'Découvre DIVARC', headline2: body.creative?.headline2 || '',
          body: body.creative?.body || '', cta: body.creative?.cta || 'En savoir plus', emoji: body.creative?.emoji || '📣',
          mediaUrl: body.creative?.mediaUrl || null, priceCents: body.creative?.priceCents || null, finalUrl: body.creative?.finalUrl || '',
        },
        color: typeDef.color, impressions: 0, clicks: 0, spentCents: 0, conversions: 0, daily: [],
        status: 'active', createdAt: new Date(),
      }
      // historique simulé pour analytics immédiates
      const hist = simulateHistory(camp)
      camp.daily = hist.daily; camp.impressions = hist.impressions; camp.clicks = hist.clicks; camp.spentCents = hist.spentCents; camp.conversions = hist.conversions
      await db.collection('campaigns').insertOne(camp)
      await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: `Budget pub : ${camp.name}`, category: 'Publicité', amountCents: -budgetCents, carbonKg: 0, icon: '📣', route: null, createdAt: new Date() })
      const updated = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      const { _id, ...clean } = camp
      return ok({ campaign: adDerived(clean), balanceCents: updated.balanceCents })
    }

    if (route === '/ads/campaigns' && method === 'GET') {
      const camps = await db.collection('campaigns').find({ ownerId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      return ok(camps.map(adDerived))
    }

    if (route.startsWith('/ads/campaigns/') && path.length === 3 && method === 'GET') {
      const c = await db.collection('campaigns').findOne({ id: path[2], ownerId: me.id }, { projection: { _id: 0 } })
      if (!c) return err('Campagne introuvable', 404)
      return ok(adDerived(c))
    }

    if (route.startsWith('/ads/campaigns/') && path.length === 3 && method === 'PATCH') {
      const c = await db.collection('campaigns').findOne({ id: path[2], ownerId: me.id })
      if (!c) return err('Campagne introuvable', 404)
      const set = {}
      if (body.status) {
        if (body.status === 'ended' && c.status !== 'ended') {
          const refund = Math.max(0, c.budgetCents - (c.spentCents || 0))
          if (refund > 0) {
            await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: refund } })
            await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: `Remboursement pub : ${c.name}`, category: 'Publicité', amountCents: refund, carbonKg: 0, icon: '↩️', route: null, createdAt: new Date() })
          }
        }
        set.status = body.status
      }
      if (body.name) set.name = body.name
      if (body.maxBidCents != null) set.maxBidCents = Math.round(body.maxBidCents)
      if (body.bidStrategy) set.bidStrategy = body.bidStrategy
      if (body.dailyBudgetCents != null) set.dailyBudgetCents = Math.round(body.dailyBudgetCents)
      if (body.targeting) set.targeting = { ...c.targeting, ...body.targeting }
      if (body.creative) set.creative = { ...c.creative, ...body.creative }
      if (body.keywords) set.keywords = body.keywords
      await db.collection('campaigns').updateOne({ id: c.id }, { $set: set })
      const updated = await db.collection('campaigns').findOne({ id: c.id }, { projection: { _id: 0 } })
      return ok(adDerived(updated))
    }

    if (route.startsWith('/ads/campaigns/') && path.length === 3 && method === 'DELETE') {
      const c = await db.collection('campaigns').findOne({ id: path[2], ownerId: me.id })
      if (!c) return err('Campagne introuvable', 404)
      if (c.status !== 'ended') {
        const refund = Math.max(0, c.budgetCents - (c.spentCents || 0))
        if (refund > 0) { await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: refund } }); await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: `Remboursement pub : ${c.name}`, category: 'Publicité', amountCents: refund, carbonKg: 0, icon: '↩️', route: null, createdAt: new Date() }) }
      }
      await db.collection('campaigns').deleteOne({ id: c.id })
      return ok({ ok: true })
    }

    if (route.startsWith('/ads/campaigns/') && path[3] === 'track' && method === 'POST') {
      const c = await db.collection('campaigns').findOne({ id: path[2] })
      if (!c || c.status !== 'active') return ok({ ok: false })
      const type = ['click', 'conversion'].includes(body.type) ? body.type : 'impression'
      const cpc = c.maxBidCents || 45
      const cost = type === 'click' ? cpc : type === 'conversion' ? 0 : Math.max(1, Math.round((c.bidStrategy === 'cpm' ? (c.maxBidCents || 500) : 550) / 1000))
      const newSpent = Math.min((c.spentCents || 0) + cost, c.budgetCents)
      const set = { spentCents: newSpent }
      if (newSpent >= c.budgetCents) set.status = 'ended'
      const inc = type === 'click' ? { clicks: 1 } : type === 'conversion' ? { conversions: 1 } : { impressions: 1 }
      // maj de la série du jour
      const today = new Date().toISOString().slice(0, 10)
      const daily = Array.isArray(c.daily) ? [...c.daily] : []
      let td = daily.find((d) => d.date === today)
      if (!td) { td = { date: today, impressions: 0, clicks: 0, spentCents: 0, conversions: 0 }; daily.push(td) }
      td.impressions += type === 'impression' ? 1 : 0; td.clicks += type === 'click' ? 1 : 0; td.conversions += type === 'conversion' ? 1 : 0; td.spentCents += cost
      set.daily = daily
      await db.collection('campaigns').updateOne({ id: c.id }, { $set: set, $inc: inc })
      return ok({ ok: true })
    }


    /* ===================== APP STORE ===================== */
    await ensureAppStoreSeed(db)

    if (route === '/store/apps' && method === 'GET') {
      const q = (url.searchParams.get('q') || '').toLowerCase()
      const cat = url.searchParams.get('cat') || ''
      let apps = await db.collection('store_apps').find({}, { projection: { _id: 0 } }).toArray()
      if (cat && cat !== 'Tout') apps = apps.filter((a) => a.cat === cat)
      if (q) apps = apps.filter((a) => a.name.toLowerCase().includes(q) || a.cat.toLowerCase().includes(q) || a.desc.toLowerCase().includes(q))
      const conns = await db.collection('app_connections').find({ userId: me.id }).toArray()
      const connMap = Object.fromEntries(conns.map((c) => [c.appId, c]))
      const out = apps.map((a) => ({ ...a, connected: !!connMap[a.id], pseudonym: connMap[a.id]?.pseudonym || null, since: connMap[a.id]?.since || null }))
      out.sort((a, b) => (b.featured - a.featured) || ((b.users || 0) - (a.users || 0)))
      return ok(out)
    }

    if (route.startsWith('/store/apps/') && path[3] === 'connect' && method === 'POST') {
      const appId = path[2]
      const app = await db.collection('store_apps').findOne({ id: appId })
      if (!app) return err('App introuvable', 404)
      const ex = await db.collection('app_connections').findOne({ userId: me.id, appId })
      if (ex) { const { _id, ...c } = ex; return ok({ connection: c, existing: true }) }
      const conn = { id: uuidv4(), userId: me.id, appId, appName: app.name, pseudonym: 'divarc-' + crypto.randomBytes(2).toString('hex'), scopes: app.perms, color: app.color, emoji: app.emoji, since: new Date() }
      await db.collection('app_connections').insertOne(conn)
      const { _id, ...clean } = conn
      return ok({ connection: clean })
    }

    if (route.startsWith('/store/apps/') && path[3] === 'disconnect' && method === 'POST') {
      await db.collection('app_connections').deleteOne({ userId: me.id, appId: path[2] })
      return ok({ ok: true })
    }

    if (route === '/store/connections' && method === 'GET') {
      const conns = await db.collection('app_connections').find({ userId: me.id }, { projection: { _id: 0 } }).sort({ since: -1 }).toArray()
      return ok(conns)
    }

    /* ===================== HUB ADMINISTRATIF & SANTÉ ===================== */
    if (route === '/admin/connectors' && method === 'GET') {
      const conns = await db.collection('admin_connections').find({ userId: me.id }).toArray()
      const map = Object.fromEntries(conns.map((c) => [c.connectorId, c]))
      return ok(ADMIN_CONN.map((a) => ({ ...a, connected: !!map[a.id], pseudonym: map[a.id]?.pseudonym || null, since: map[a.id]?.since || null, data: map[a.id]?.data || [] })))
    }
    if (route.startsWith('/admin/connectors/') && path[3] === 'connect' && method === 'POST') {
      const def = ADMIN_CONN.find((a) => a.id === path[2])
      if (!def) return err('Connecteur introuvable', 404)
      const ex = await db.collection('admin_connections').findOne({ userId: me.id, connectorId: def.id })
      if (ex) { const { _id, ...c } = ex; return ok({ connection: c, existing: true }) }
      const conn = { id: uuidv4(), userId: me.id, connectorId: def.id, name: def.name, pseudonym: 'eidas-' + crypto.randomBytes(3).toString('hex'), scopes: def.scopes, sensitive: !!def.sensitive, data: ADMIN_DATA[def.id] || [], since: new Date() }
      await db.collection('admin_connections').insertOne(conn)
      const { _id, ...clean } = conn
      return ok({ connection: clean })
    }
    if (route.startsWith('/admin/connectors/') && path[3] === 'disconnect' && method === 'POST') {
      await db.collection('admin_connections').deleteOne({ userId: me.id, connectorId: path[2] })
      return ok({ ok: true })
    }

    if (route === '/admin/documents' && method === 'GET') {
      const count = await db.collection('admin_documents').countDocuments({ userId: me.id })
      if (count === 0) {
        await db.collection('admin_documents').insertMany([
          { id: uuidv4(), userId: me.id, title: 'Avis d\u2019imposition 2024', category: 'Impôts', issuer: 'DGFiP', emoji: '🧾', encrypted: true, shared: false, createdAt: new Date() },
          { id: uuidv4(), userId: me.id, title: 'Attestation carte Vitale', category: 'Santé', issuer: 'Ameli', emoji: '⚕️', encrypted: true, shared: false, createdAt: new Date() },
        ])
      }
      const docs = await db.collection('admin_documents').find({ userId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      return ok(docs)
    }
    if (route === '/admin/documents' && method === 'POST') {
      const doc = { id: uuidv4(), userId: me.id, title: body.title || 'Document', category: body.category || 'Autre', issuer: body.issuer || 'Moi', emoji: body.emoji || '📄', encrypted: true, shared: false, createdAt: new Date() }
      await db.collection('admin_documents').insertOne(doc)
      const { _id, ...clean } = doc
      return ok(clean)
    }
    if (route.startsWith('/admin/documents/') && path[3] === 'share' && method === 'POST') {
      const shareToken = crypto.randomBytes(4).toString('hex')
      const expiresAt = new Date(Date.now() + (body.hours || 24) * 3600000)
      await db.collection('admin_documents').updateOne({ id: path[2], userId: me.id }, { $set: { shared: true, shareToken, shareExpiresAt: expiresAt } })
      return ok({ shared: true, shareToken, expiresAt })
    }
    if (route.startsWith('/admin/documents/') && path[3] === 'unshare' && method === 'POST') {
      await db.collection('admin_documents').updateOne({ id: path[2], userId: me.id }, { $set: { shared: false }, $unset: { shareToken: '', shareExpiresAt: '' } })
      return ok({ shared: false })
    }
    if (route.startsWith('/admin/documents/') && path.length === 3 && method === 'DELETE') {
      await db.collection('admin_documents').deleteOne({ id: path[2], userId: me.id })
      return ok({ ok: true })
    }

    if (route === '/admin/accounting' && method === 'GET') {
      const txs = await db.collection('transactions').find({ userId: me.id }).toArray()
      let income = 0, expense = 0
      const byCat = {}
      for (const t of txs) {
        if (t.amountCents > 0) income += t.amountCents
        else { expense += -t.amountCents; byCat[t.category] = (byCat[t.category] || 0) + (-t.amountCents) }
      }
      const categories = Object.entries(byCat).map(([name, amountCents]) => ({ name, amountCents })).sort((a, b) => b.amountCents - a.amountCents).slice(0, 6)
      return ok({ incomeCents: income, expenseCents: expense, netCents: income - expense, categories, count: txs.length })
    }

    return err(`Route ${route} introuvable`, 404)
  } catch (error) {
    console.error('API Error:', error)
    return err('Erreur interne du serveur', 500)
  }
}

export const GET = handleRoute
export const POST = handleRoute
export const PUT = handleRoute
export const DELETE = handleRoute
export const PATCH = handleRoute
