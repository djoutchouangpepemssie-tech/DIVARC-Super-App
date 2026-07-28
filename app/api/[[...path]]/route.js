import { MongoClient } from 'mongodb'
import { v4 as uuidv4 } from 'uuid'
import { NextResponse } from 'next/server'
import crypto from 'crypto'
import { Resend } from 'resend'

// ---------------- MongoDB ----------------
let client
let db
async function connectToMongo() {
  if (!client) {
    client = new MongoClient(process.env.MONGO_URL)
    await client.connect()
    db = client.db(process.env.DB_NAME)
  }
  return db
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

const MARKET_IMGS = {
  fashion: 'https://images.unsplash.com/photo-1731505583021-16c3a17339cd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1Mjh8MHwxfHNlYXJjaHw0fHxmYXNoaW9ufGVufDB8fHx8MTc4NTI3MDU2M3ww&ixlib=rb-4.1.0&q=85',
  sneakers: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwxfHxzbmVha2Vyc3xlbnwwfHx8fDE3ODUyMzAwODN8MA&ixlib=rb-4.1.0&q=85',
  furniture: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHw0fHxmdXJuaXR1cmV8ZW58MHx8fHwxNzg1MjcwNTYzfDA&ixlib=rb-4.1.0&q=85',
  bicycle: 'https://images.unsplash.com/photo-1618762044398-ec1e7e048bbd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzR8MHwxfHNlYXJjaHwzfHxiaWN5Y2xlfGVufDB8fHx8MTc4NTI3MDU2M3ww&ixlib=rb-4.1.0&q=85',
  smartphone: 'https://images.unsplash.com/photo-1634403665481-74948d815f03?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDR8MHwxfHNlYXJjaHw0fHxzbWFydHBob25lfGVufDB8fHx8MTc4NTI3MDU2M3ww&ixlib=rb-4.1.0&q=85',
  plant: 'https://images.unsplash.com/photo-1592150621744-aca64f48394a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDB8MHwxfHNlYXJjaHwyfHxob3VzZXBsYW50fGVufDB8fHx8MTc4NTI3MDU2M3ww&ixlib=rb-4.1.0&q=85',
}
async function ensureMarketSeed(db) {
  if (await db.collection('listings').countDocuments() > 0) return
  await ensureDemoUsers(db)
  const seed = [
    { s: 'bot-lena', t: 'Veste en jean vintage', d: 'Taille M, très bon état, portée quelques fois. Coupe oversize tendance.', p: 3500, cat: 'Mode', cond: 'Très bon état', type: 'item', img: MARKET_IMGS.fashion, loc: 'Paris 11e' },
    { s: 'bot-yanis', t: 'Sneakers rétro (42)', d: 'Édition running, semelle nickel, boîte incluse.', p: 6900, cat: 'Chaussures', cond: 'Bon état', type: 'item', img: MARKET_IMGS.sneakers, loc: 'Lyon' },
    { s: 'bot-thomas', t: 'Fauteuil design scandinave', d: 'Fauteuil en tissu, structure bois. Parfait pour un salon cosy.', p: 12000, cat: 'Maison', cond: 'Très bon état', type: 'item', img: MARKET_IMGS.furniture, loc: 'Bordeaux' },
    { s: 'bot-sofia', t: 'Vélo de ville', d: 'Vélo léger, 7 vitesses, freins révisés. Idéal trajets quotidiens.', p: 18500, cat: 'Vélo', cond: 'Bon état', type: 'item', img: MARKET_IMGS.bicycle, loc: 'Nantes' },
    { s: 'bot-marie', t: 'Smartphone 128 Go', d: 'Débloqué tout opérateur, batterie 92%, avec chargeur.', p: 29900, cat: 'Tech', cond: 'Très bon état', type: 'item', img: MARKET_IMGS.smartphone, loc: 'Paris 9e' },
    { s: 'bot-lena', t: 'Monstera en pot', d: 'Belle plante d\u2019intérieur, ~80cm. À récupérer sur place.', p: 2500, cat: 'Jardin', cond: 'Neuf', type: 'ad', img: MARKET_IMGS.plant, loc: 'Paris 20e' },
  ]
  const now = Date.now()
  await db.collection('listings').insertMany(seed.map((x, i) => ({
    id: uuidv4(), sellerId: x.s, title: x.t, description: x.d, priceCents: x.p, category: x.cat,
    condition: x.cond, type: x.type, images: [x.img], location: x.loc, status: 'active',
    favorites: Math.floor(Math.random() * 40), views: Math.floor(Math.random() * 300), createdAt: new Date(now - i * 3600000 * 8),
  })))
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
      return ok(out)
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

    /* ===================== MARKETPLACE ===================== */
    await ensureMarketSeed(db)

    if (route === '/market/listings' && method === 'GET') {
      const q = (url.searchParams.get('q') || '').toLowerCase()
      const cat = url.searchParams.get('cat') || ''
      const sort = url.searchParams.get('sort') || 'recent'
      let items = await db.collection('listings').find({ status: 'active' }, { projection: { _id: 0 } }).toArray()
      if (cat && cat !== 'Tout') items = items.filter((i) => i.category === cat)
      if (q) items = items.filter((i) => i.title.toLowerCase().includes(q) || i.description.toLowerCase().includes(q))
      if (sort === 'price_asc') items.sort((a, b) => a.priceCents - b.priceCents)
      else if (sort === 'price_desc') items.sort((a, b) => b.priceCents - a.priceCents)
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
      const listing = {
        id: uuidv4(), sellerId: me.id, title: body.title || 'Article', description: body.description || '',
        priceCents: Math.max(0, Math.round(body.priceCents || 0)), category: body.category || 'Autre',
        condition: body.condition || 'Bon état', type: body.type || 'item',
        images: body.images && body.images.length ? body.images : [], emoji: body.emoji || '📦',
        color: body.color || '#4353F0', location: body.location || 'France', status: 'active',
        favorites: 0, views: 0, createdAt: new Date(),
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
      return ok({ ...l, favorited: favs.has(l.id), seller })
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
      const wallet = await db.collection('wallets').findOne({ userId: me.id })
      if (!wallet || wallet.balanceCents < l.priceCents) return err('Solde insuffisant', 402)
      await db.collection('wallets').updateOne({ userId: me.id }, { $inc: { balanceCents: -l.priceCents } })
      await creditWallet(db, l.sellerId, l.priceCents)
      await db.collection('listings').updateOne({ id: l.id }, { $set: { status: 'sold', buyerId: me.id, soldAt: new Date() } })
      const order = { id: uuidv4(), listingId: l.id, title: l.title, buyerId: me.id, sellerId: l.sellerId, priceCents: l.priceCents, createdAt: new Date() }
      await db.collection('orders').insertOne(order)
      const seller = await db.collection('users').findOne({ id: l.sellerId })
      await db.collection('transactions').insertOne({ id: uuidv4(), userId: me.id, label: `Achat : ${l.title}`, category: 'Marketplace', amountCents: -l.priceCents, carbonKg: 0, icon: '🛍️', route: null, createdAt: new Date() })
      await postLedger(db, [{ account: `user:${me.id}`, direction: 'debit', amountCents: l.priceCents }, { account: `user:${l.sellerId}`, direction: 'credit', amountCents: l.priceCents }])
      const updated = await db.collection('wallets').findOne({ userId: me.id }, { projection: { _id: 0 } })
      return ok({ ok: true, order: { id: order.id }, balanceCents: updated.balanceCents })
    }

    if (route === '/market/mine' && method === 'GET') {
      const selling = await db.collection('listings').find({ sellerId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      const orders = await db.collection('orders').find({ buyerId: me.id }, { projection: { _id: 0 } }).sort({ createdAt: -1 }).toArray()
      return ok({ selling, purchases: orders })
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
