import { MongoClient } from 'mongodb'
import { v4 as uuidv4 } from 'uuid'
import { NextResponse } from 'next/server'

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

export async function OPTIONS() {
  return handleCORS(new NextResponse(null, { status: 200 }))
}

const ok = (data, status = 200) => handleCORS(NextResponse.json(data, { status }))
const err = (message, status = 400) => handleCORS(NextResponse.json({ error: message }, { status }))

// ---------------- Demo seed data ----------------
const DEMO_USER_ID = 'demo-adrien'

async function seedDemo(db) {
  const existing = await db.collection('users').findOne({ id: DEMO_USER_ID })
  if (existing) return existing

  const now = new Date()
  const user = {
    id: DEMO_USER_ID,
    handle: '@adrien',
    name: 'Adrien Vasseur',
    email: 'adrien@divarc.fr',
    avatarColor: 'linear-gradient(135deg,#4353F0,#6E7BF5)',
    initials: 'AV',
    verified: true,
    kyc: 'eIDAS',
    createdAt: now,
  }
  await db.collection('users').insertOne(user)

  await db.collection('wallets').insertOne({
    id: uuidv4(),
    userId: DEMO_USER_ID,
    balanceCents: 248750,
    currency: 'EUR',
    sepaInstant: true,
    carbonMonthKg: 42.3,
    createdAt: now,
  })

  const coffres = [
    { id: uuidv4(), userId: DEMO_USER_ID, name: 'Vacances Lisbonne', emoji: '🏖️', balanceCents: 62000, goalCents: 150000, rule: 'round_up', color: '#4353F0' },
    { id: uuidv4(), userId: DEMO_USER_ID, name: 'Fonds d\u2019urgence', emoji: '🛟', balanceCents: 180000, goalCents: 300000, rule: 'receive_over', color: '#E2AA2B' },
    { id: uuidv4(), userId: DEMO_USER_ID, name: 'Nouveau vélo', emoji: '🚲', balanceCents: 24000, goalCents: 90000, rule: 'round_up', color: '#3FB68B' },
  ]
  await db.collection('coffres').insertMany(coffres)

  const contacts = [
    { id: uuidv4(), userId: DEMO_USER_ID, handle: '@marie', name: 'Marie Laurent', initials: 'ML', color: 'linear-gradient(135deg,#E2AA2B,#F0CE7E)', verified: true },
    { id: uuidv4(), userId: DEMO_USER_ID, handle: '@thomas', name: 'Thomas Bernard', initials: 'TB', color: 'linear-gradient(135deg,#3FB68B,#7BE0BE)', verified: false },
    { id: uuidv4(), userId: DEMO_USER_ID, handle: '@lena', name: 'Léna Costa', initials: 'LC', color: 'linear-gradient(135deg,#9B5DE5,#C89BF5)', verified: true },
    { id: uuidv4(), userId: DEMO_USER_ID, handle: '@yanis', name: 'Yanis Moreau', initials: 'YM', color: 'linear-gradient(135deg,#F15BB5,#FBA3D8)', verified: false },
    { id: uuidv4(), userId: DEMO_USER_ID, handle: '@sofia', name: 'Sofia Ricci', initials: 'SR', color: 'linear-gradient(135deg,#00BBF9,#7ADBFF)', verified: true },
  ]
  await db.collection('contacts').insertMany(contacts)

  const tx = [
    { label: 'Marché Bio Bastille', category: 'Courses', amountCents: -3420, carbonKg: 1.2, icon: '🥬', minutesAgo: 45 },
    { label: 'Reçu de Marie Laurent', category: 'P2P', amountCents: 2500, carbonKg: 0, icon: '💸', minutesAgo: 180 },
    { label: 'Métro RATP', category: 'Transport', amountCents: -215, carbonKg: 0.1, icon: '🚇', minutesAgo: 320 },
    { label: 'Café des Arts', category: 'Restauration', amountCents: -480, carbonKg: 0.3, icon: '☕', minutesAgo: 1440 },
    { label: 'Salaire — Kaléo SAS', category: 'Revenu', amountCents: 240000, carbonKg: 0, icon: '🏢', minutesAgo: 4320 },
    { label: 'Spotify Premium', category: 'Abonnement', amountCents: -1099, carbonKg: 0.05, icon: '🎵', minutesAgo: 5760 },
    { label: 'Enveloppe à Léna', category: 'Enveloppe', amountCents: -2000, carbonKg: 0, icon: '🧧', minutesAgo: 7200 },
  ]
  const txDocs = tx.map((t) => ({
    id: uuidv4(),
    userId: DEMO_USER_ID,
    ...t,
    route: t.amountCents < 0 ? 'A2A' : null,
    createdAt: new Date(now.getTime() - t.minutesAgo * 60000),
  }))
  await db.collection('transactions').insertMany(txDocs)

  return user
}

// double-entry ledger helper
async function postLedger(db, entries) {
  const batch = uuidv4()
  const docs = entries.map((e) => ({ id: uuidv4(), batch, ...e, createdAt: new Date() }))
  await db.collection('ledger').insertMany(docs)
  return batch
}

// ---------------- Router ----------------
async function handleRoute(request, { params }) {
  const { path = [] } = await params
  const route = `/${path.join('/')}`
  const method = request.method

  try {
    const db = await connectToMongo()
    const url = new URL(request.url)
    const userId = url.searchParams.get('userId') || DEMO_USER_ID

    if ((route === '/' || route === '/health') && method === 'GET') {
      return ok({ service: 'DIVARC API', status: 'live', time: new Date().toISOString() })
    }

    // --- SEED / ME ---
    if (route === '/seed' && method === 'POST') {
      const user = await seedDemo(db)
      return ok({ userId: user.id, user })
    }

    if (route === '/me' && method === 'GET') {
      await seedDemo(db)
      const user = await db.collection('users').findOne({ id: userId }, { projection: { _id: 0 } })
      if (!user) return err('Utilisateur introuvable', 404)
      return ok(user)
    }

    // --- WALLET ---
    if (route === '/wallet' && method === 'GET') {
      await seedDemo(db)
      const wallet = await db.collection('wallets').findOne({ userId }, { projection: { _id: 0 } })
      const coffres = await db.collection('coffres').find({ userId }, { projection: { _id: 0 } }).toArray()
      return ok({
        ...wallet,
        coffres: coffres.map(({ _id, ...c }) => c),
      })
    }

    // --- TRANSACTIONS ---
    if (route === '/transactions' && method === 'GET') {
      await seedDemo(db)
      const txs = await db.collection('transactions')
        .find({ userId }, { projection: { _id: 0 } })
        .sort({ createdAt: -1 })
        .limit(100)
        .toArray()
      return ok(txs)
    }

    // --- CONTACTS ---
    if (route === '/contacts' && method === 'GET') {
      await seedDemo(db)
      const q = (url.searchParams.get('q') || '').toLowerCase()
      let contacts = await db.collection('contacts').find({ userId }, { projection: { _id: 0 } }).toArray()
      if (q) {
        contacts = contacts.filter((c) =>
          c.name.toLowerCase().includes(q) || c.handle.toLowerCase().includes(q))
      }
      return ok(contacts.map(({ _id, ...c }) => c))
    }

    // --- SEND P2P (idempotent + double-entry) ---
    if (route === '/send' && method === 'POST') {
      await seedDemo(db)
      const body = await request.json()
      const { toHandle, toName, amountCents, note, idempotencyKey, route: payRoute } = body
      if (!amountCents || amountCents <= 0) return err('Montant invalide')
      const idem = idempotencyKey || uuidv4()

      const dup = await db.collection('transactions').findOne({ idempotencyKey: idem }, { projection: { _id: 0 } })
      if (dup) return ok({ transaction: dup, idempotent: true })

      const wallet = await db.collection('wallets').findOne({ userId })
      if (!wallet || wallet.balanceCents < amountCents) return err('Solde insuffisant', 402)

      await db.collection('wallets').updateOne({ userId }, { $inc: { balanceCents: -amountCents } })

      const batch = await postLedger(db, [
        { account: `user:${userId}`, direction: 'debit', amountCents },
        { account: `user:${toHandle || 'external'}`, direction: 'credit', amountCents },
      ])

      const tx = {
        id: uuidv4(),
        userId,
        label: `Envoyé à ${toName || toHandle || 'un ami'}`,
        category: 'P2P',
        amountCents: -Math.abs(amountCents),
        carbonKg: 0,
        icon: '⚡',
        route: payRoute || 'A2A',
        note: note || '',
        idempotencyKey: idem,
        ledgerBatch: batch,
        status: 'settled',
        createdAt: new Date(),
      }
      await db.collection('transactions').insertOne(tx)
      const updated = await db.collection('wallets').findOne({ userId }, { projection: { _id: 0 } })
      const { _id, ...cleanTx } = tx
      return ok({ transaction: cleanTx, balanceCents: updated.balanceCents })
    }

    // --- COFFRES create ---
    if (route === '/coffres' && method === 'POST') {
      await seedDemo(db)
      const body = await request.json()
      const coffre = {
        id: uuidv4(),
        userId,
        name: body.name || 'Nouveau coffre',
        emoji: body.emoji || '🎯',
        balanceCents: body.balanceCents || 0,
        goalCents: body.goalCents || 100000,
        rule: body.rule || 'round_up',
        color: body.color || '#4353F0',
        createdAt: new Date(),
      }
      await db.collection('coffres').insertOne(coffre)
      const { _id, ...clean } = coffre
      return ok(clean)
    }

    // --- ENVELOPPE (hongbao) create ---
    if (route === '/enveloppe/create' && method === 'POST') {
      await seedDemo(db)
      const body = await request.json()
      const totalCents = body.totalCents
      const count = Math.max(1, Math.min(body.count || 1, 20))
      if (!totalCents || totalCents <= 0) return err('Montant invalide')

      const wallet = await db.collection('wallets').findOne({ userId })
      if (!wallet || wallet.balanceCents < totalCents) return err('Solde insuffisant', 402)
      await db.collection('wallets').updateOne({ userId }, { $inc: { balanceCents: -totalCents } })

      // random split (lucky money) — remainder distributed, min 1 cent each
      let remaining = totalCents
      let left = count
      const shares = []
      for (let i = 0; i < count; i++) {
        if (i === count - 1) { shares.push(remaining); break }
        const max = Math.floor((remaining / left) * 2)
        const amt = Math.max(1, Math.floor(Math.random() * (max - 1)) + 1)
        shares.push(amt)
        remaining -= amt
        left--
      }
      // shuffle
      for (let i = shares.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[shares[i], shares[j]] = [shares[j], shares[i]]
      }

      const env = {
        id: uuidv4(),
        userId,
        message: body.message || 'Bonne chance ! 🧧',
        totalCents,
        count,
        shares: shares.map((amt) => ({ id: uuidv4(), amountCents: amt, claimedBy: null, claimedAt: null })),
        theme: body.theme || 'gold',
        expiresAt: new Date(Date.now() + 24 * 3600 * 1000),
        createdAt: new Date(),
      }
      await db.collection('enveloppes').insertOne(env)

      const tx = {
        id: uuidv4(), userId,
        label: `Enveloppe (${count} part${count > 1 ? 's' : ''})`,
        category: 'Enveloppe', amountCents: -totalCents, carbonKg: 0, icon: '🧧',
        route: null, createdAt: new Date(),
      }
      await db.collection('transactions').insertOne(tx)

      const updated = await db.collection('wallets').findOne({ userId }, { projection: { _id: 0 } })
      const { _id, ...clean } = env
      return ok({ enveloppe: clean, balanceCents: updated.balanceCents })
    }

    // --- ENVELOPPE open/claim ---
    if (route === '/enveloppe/open' && method === 'POST') {
      const body = await request.json()
      const env = await db.collection('enveloppes').findOne({ id: body.enveloppeId })
      if (!env) return err('Enveloppe introuvable', 404)
      const claimer = body.claimer || 'invité'
      const already = env.shares.find((s) => s.claimedBy === claimer)
      if (already) return ok({ amountCents: already.amountCents, alreadyClaimed: true, message: env.message })
      const free = env.shares.find((s) => !s.claimedBy)
      if (!free) return err('Toutes les parts ont été réclamées', 410)
      free.claimedBy = claimer
      free.claimedAt = new Date()
      await db.collection('enveloppes').updateOne({ id: env.id }, { $set: { shares: env.shares } })
      const remaining = env.shares.filter((s) => !s.claimedBy).length
      return ok({ amountCents: free.amountCents, message: env.message, remaining, total: env.count })
    }

    if (route === '/enveloppe' && method === 'GET') {
      const id = url.searchParams.get('id')
      const env = await db.collection('enveloppes').findOne({ id }, { projection: { _id: 0 } })
      if (!env) return err('Enveloppe introuvable', 404)
      return ok(env)
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
