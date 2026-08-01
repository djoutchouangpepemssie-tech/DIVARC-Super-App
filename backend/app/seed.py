"""Provisioning des utilisateurs et jeux de données de démonstration (portés depuis route.js)."""
from __future__ import annotations

import random

from .config import settings
from .data import BOTS, CITIES, COLORS, MARKET_IMGS, STORE_APPS, VIDS
from .helpers import hash_email, hash_phone, initials_of, now, uid

# Compte officiel DIVARC (émetteur du message de bienvenue). Ce n'est pas un « ami ».
OFFICIAL_ID = "divarc-official"


async def ensure_official_account(db) -> None:
    """Crée le compte officiel DIVARC (idempotent). Toujours présent, même hors démo."""
    if not await db.users.find_one({"id": OFFICIAL_ID}):
        await db.users.insert_one({
            "id": OFFICIAL_ID, "email": "official@divarc.fr", "handle": "@divarc", "name": "DIVARC",
            "initials": "D", "avatarColor": "#4353F0", "verified": True, "kyc": "eIDAS",
            "bio": "Compte officiel DIVARC", "isBot": True, "official": True, "createdAt": now(),
        })


async def ensure_demo_users(db) -> None:
    # Le compte officiel existe toujours ; les faux amis/communautés uniquement en mode démo.
    await ensure_official_account(db)
    if not settings.DEMO_MODE:
        return
    for b in BOTS:
        ex = await db.users.find_one({"id": b["id"]})
        if not ex:
            await db.users.insert_one({
                "id": b["id"], "email": f"{b['handle'][1:]}@divarc.fr", "handle": b["handle"], "name": b["name"],
                "initials": initials_of(b["name"]), "avatarColor": b["color"], "verified": b["verified"],
                "kyc": "eIDAS" if b["verified"] else "non vérifié", "bio": "Ami·e DIVARC", "isBot": True, "createdAt": now(),
            })
    comm = await db.conversations.find_one({"id": "comm-paris"})
    if not comm:
        await db.conversations.insert_one({
            "id": "comm-paris", "type": "community", "name": "Paris ✨", "topic": "La vie à Paris",
            "avatarColor": COLORS[0], "memberIds": [b["id"] for b in BOTS], "createdBy": "system",
            "isPublic": True, "reads": {}, "lastText": "Qui est chaud pour un pique-nique ?",
            "lastMessageAt": now(), "createdAt": now(),
        })
        await db.messages.insert_many([
            {"id": uid(), "conversationId": "comm-paris", "senderId": "bot-lena", "senderName": "Léna Costa",
             "text": "Bienvenue dans la communauté Paris ! 🥖", "kind": "text", "reactions": [], "createdAt": now()},
            {"id": uid(), "conversationId": "comm-paris", "senderId": "bot-yanis", "senderName": "Yanis Moreau",
             "text": "Qui est chaud pour un pique-nique aux Buttes-Chaumont ce week-end ?", "kind": "text",
             "reactions": [{"userId": "bot-lena", "emoji": "🔥"}], "createdAt": now()},
        ])


async def unique_handle(db, base: str) -> str:
    import re
    h = "@" + re.sub(r"[^a-z0-9]", "", base.lower())[:14]
    if h == "@":
        h = "@user"
    cand = h
    n = 0
    while await db.users.find_one({"handle": cand}):
        n += 1
        cand = h + str(n)
    return cand


async def provision_user(db, email: str, name: str | None = None, phone: str | None = None) -> dict:
    _id = uid()
    if name:
        display_name = name
    else:
        import re
        base = re.sub(r"\W+", " ", email.split("@")[0])
        display_name = re.sub(r"\b\w", lambda m: m.group(0).upper(), base)
    user = {
        "id": _id, "email": email.lower(),
        "handle": await unique_handle(db, email.split("@")[0]),
        "name": display_name,
        "initials": initials_of(display_name) or "U",
        "avatarColor": random.choice(COLORS),
        "verified": False, "kyc": "non vérifié", "bio": "", "isBot": False,
        # --- découverte (RGPD : opt-in désactivé par défaut sauf @handle) ---
        "phone": phone or None,
        "emailHash": hash_email(email),
        "phoneHash": hash_phone(phone),
        "discoverable": {"byHandle": True, "byEmail": False, "byPhone": False, "byPhoto": False},
        "handleChanged": False,
        "createdAt": now(),
    }
    await db.users.insert_one(dict(user))
    # Solde de départ : fictif en démo, sinon 0 € (vraie app)
    start_balance = 480000 if settings.DEMO_MODE else 0
    await db.wallets.insert_one({
        "id": uid(), "userId": _id, "balanceCents": start_balance, "currency": "EUR",
        "sepaInstant": True, "carbonMonthKg": 0, "createdAt": now(),
    })
    # Cadeau de bienvenue en Éclats (monnaie interne — real economy, hors mode démo)
    from .eclats import grant_welcome
    await grant_welcome(db, _id)
    if settings.DEMO_MODE:
        await db.coffres.insert_many([
            {"id": uid(), "userId": _id, "name": "Vacances", "emoji": "🏖️", "balanceCents": 500, "goalCents": 150000, "rule": "round_up", "color": "#4353F0"},
            {"id": uid(), "userId": _id, "name": "Fonds d’urgence", "emoji": "🛟", "balanceCents": 0, "goalCents": 300000, "rule": "receive_over", "color": "#E2AA2B"},
        ])
        await db.transactions.insert_one({
            "id": uid(), "userId": _id, "label": "Bienvenue sur DIVARC 🎁", "category": "Cadeau",
            "amountCents": 480000, "carbonKg": 0, "icon": "🎁", "route": None, "createdAt": now(),
        })

    # Conversation de bienvenue du compte OFFICIEL DIVARC (pas un ami, pas de réponse auto)
    await ensure_official_account(db)
    conv_id = uid()
    await db.conversations.insert_one({
        "id": conv_id, "type": "dm", "name": None, "avatarColor": None,
        "memberIds": [_id, OFFICIAL_ID], "createdBy": "system", "reads": {},
        "lastText": "Bienvenue sur DIVARC 🎉",
        "lastMessageAt": now(), "createdAt": now(),
    })
    await db.messages.insert_one({
        "id": uid(), "conversationId": conv_id, "senderId": OFFICIAL_ID, "senderName": "DIVARC",
        "text": ("Bienvenue sur DIVARC 🎉\n\nTon compte est prêt. Ajoute tes amis, discute, "
                 "envoie de l'argent et découvre les mini-apps. Bonne visite !"),
        "kind": "text", "reactions": [], "createdAt": now(),
    })
    return strip(user)


def strip(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ---------------- Seeds ----------------

async def ensure_social_seed(db) -> None:
    if not settings.DEMO_MODE:
        return
    if await db.posts.count_documents({}) > 0:
        return
    await ensure_demo_users(db)
    seed = [
        {"a": "bot-lena", "cap": "Coucher de soleil sur Paris 🌇 Cette ville me fait vibrer.", "tags": ["#paris", "#lifestyle"], "likes": 1240, "views": 18400, "comments": 87},
        {"a": "bot-yanis", "cap": "Recette express : pâtes truffe 🍝✨ (ça change la vie)", "tags": ["#food", "#recette"], "likes": 3420, "views": 51200, "comments": 210, "product": {"title": "Huile de truffe artisanale", "priceCents": 1490, "emoji": "🫒"}},
        {"a": "bot-marie", "cap": "Mon setup créateur 2025 💻 Question ? Je réponds !", "tags": ["#tech", "#setup"], "likes": 890, "views": 12300, "comments": 64, "product": {"title": "Micro podcast USB", "priceCents": 8900, "emoji": "🎙️"}, "ai": True},
        {"a": "bot-sofia", "cap": "Routine sport du matin 🏃‍♀️ On se motive ensemble ?", "tags": ["#sport", "#motivation"], "likes": 2110, "views": 33100, "comments": 143},
        {"a": "bot-thomas", "cap": "Voyage Lisbonne en 60 secondes 🇵🇹 Sauvegarde pour plus tard !", "tags": ["#voyage", "#lisbonne"], "likes": 5600, "views": 98000, "comments": 320},
        {"a": "bot-lena", "cap": "DIY déco : transformer un mur en 3 étapes 🎨", "tags": ["#diy", "#deco"], "likes": 760, "views": 9800, "comments": 41, "product": {"title": "Kit peinture éco", "priceCents": 3200, "emoji": "🎨"}},
        {"a": "bot-marie", "cap": "Le meilleur café de Paris est ici ☕ (adresse en com)", "tags": ["#paris", "#food"], "likes": 1980, "views": 27600, "comments": 176},
        {"a": "bot-sofia", "cap": "Concert hier soir 🎶 Ambiance incroyable !", "tags": ["#musique", "#live"], "likes": 4300, "views": 62000, "comments": 258},
    ]
    from datetime import timedelta
    base = now()
    docs = []
    for i, s in enumerate(seed):
        docs.append({
            "id": uid(), "authorId": s["a"], "caption": s["cap"], "mediaUrl": VIDS[i % len(VIDS)], "mediaType": "video",
            "poster": None, "hashtags": s["tags"], "product": s.get("product"), "aiGenerated": bool(s.get("ai")),
            "likes": s["likes"], "comments": s["comments"], "saves": int(s["likes"] * 0.12), "views": s["views"],
            "earningsCents": 0, "createdAt": base - timedelta(hours=i * 5),
        })
    await db.posts.insert_many(docs)


_MARKET_SEED = [
    {"s": "bot-marie", "t": "Appartement T3 lumineux — 68 m²", "d": "Bel appartement rénové, 3e étage avec ascenseur, proche métro. Cuisine équipée, double vitrage, cave.", "p": 34500000, "cat": "immobilier", "sub": "Ventes immobilières", "tx": "sale", "cond": "Comme neuf", "img": "apartment", "city": "Paris", "attrs": {"propertyType": "Appartement", "surface": 68, "rooms": 3, "bedrooms": 2, "furnished": False, "energyClass": "C"}},
    {"s": "bot-thomas", "t": "Studio meublé à louer — 24 m²", "d": "Studio meublé idéal étudiant, charges comprises, disponible immédiatement. Proche campus.", "p": 68000, "cat": "immobilier", "sub": "Locations", "tx": "rent", "cond": "Très bon état", "img": "apartment", "city": "Lyon", "attrs": {"propertyType": "Studio", "surface": 24, "rooms": 1, "bedrooms": 0, "furnished": True, "energyClass": "D"}},
    {"s": "bot-sofia", "t": "Maison 5 pièces avec jardin — 120 m²", "d": "Maison familiale, 4 chambres, jardin 300 m², garage. Quartier calme et résidentiel.", "p": 42000000, "cat": "immobilier", "sub": "Ventes immobilières", "tx": "sale", "cond": "Bon état", "img": "house", "city": "Bordeaux", "attrs": {"propertyType": "Maison", "surface": 120, "rooms": 5, "bedrooms": 4, "furnished": False, "energyClass": "B"}},
    {"s": "bot-yanis", "t": "Citadine essence 2019 — 45 000 km", "d": "Entretien à jour, carnet complet, pneus neufs, CT ok. Première main, non fumeur.", "p": 1250000, "cat": "vehicules", "sub": "Voitures", "tx": "sale", "cond": "Très bon état", "img": "car", "city": "Nantes", "attrs": {"brand": "Renault", "model": "Clio", "year": 2019, "mileage": 45000, "fuel": "Essence", "gearbox": "Manuelle"}},
    {"s": "bot-lena", "t": "Moto roadster 650cc", "d": "Moto en excellent état, révision récente, deux casques offerts.", "p": 480000, "cat": "vehicules", "sub": "Motos", "tx": "sale", "cond": "Bon état", "img": "motorcycle", "city": "Toulouse", "attrs": {"brand": "Yamaha", "model": "MT-07", "year": 2020, "mileage": 18000, "fuel": "Essence", "gearbox": "Manuelle"}},
    {"s": "bot-thomas", "t": "Canapé 3 places en velours", "d": "Canapé design confortable, velours bleu nuit, très peu servi. À récupérer sur place.", "p": 32000, "cat": "maison", "sub": "Ameublement", "tx": "sale", "cond": "Comme neuf", "img": "sofa", "city": "Paris", "attrs": {}},
    {"s": "bot-marie", "t": "Smartphone 128 Go débloqué", "d": "Débloqué tout opérateur, batterie 92%, avec chargeur et coque. Facture disponible.", "p": 29900, "cat": "multimedia", "sub": "Téléphonie", "tx": "sale", "cond": "Très bon état", "img": "smartphone", "city": "Lille", "attrs": {"brand": "Samsung"}},
    {"s": "bot-yanis", "t": "Ordinateur portable 15\" i7 16 Go", "d": "PC portable puissant, SSD 512 Go, parfait pour le travail et le montage. Batterie excellente.", "p": 55000, "cat": "multimedia", "sub": "Informatique", "tx": "sale", "cond": "Bon état", "img": "laptop", "city": "Marseille", "attrs": {"brand": "Lenovo"}},
    {"s": "bot-sofia", "t": "Sneakers rétro (42)", "d": "Édition running, semelle nickel, boîte incluse. Portées quelques fois.", "p": 6900, "cat": "mode", "sub": "Chaussures", "tx": "sale", "cond": "Très bon état", "img": "sneakers", "city": "Lyon", "attrs": {"size": "42", "brand": "Nike"}},
    {"s": "bot-lena", "t": "Vélo de ville 7 vitesses", "d": "Vélo léger, freins révisés, antivol offert. Idéal trajets quotidiens en ville.", "p": 18500, "cat": "loisirs", "sub": "Vélos", "tx": "sale", "cond": "Bon état", "img": "bicycle", "city": "Nantes", "attrs": {}},
    {"s": "bot-thomas", "t": "Guitare acoustique folk", "d": "Guitare avec housse et accordeur. Son chaud, cordes neuves. Parfaite pour débuter.", "p": 12000, "cat": "loisirs", "sub": "Instruments de musique", "tx": "sale", "cond": "Comme neuf", "img": "guitar", "city": "Bordeaux", "attrs": {}},
    {"s": "bot-marie", "t": "Berline familiale 2021 — location", "d": "Location longue durée possible, entretien inclus. Idéale famille, spacieuse et sobre.", "p": 39000, "cat": "vehicules", "sub": "Voitures", "tx": "rent", "cond": "Comme neuf", "img": "car", "city": "Paris", "attrs": {"brand": "Peugeot", "model": "508", "year": 2021, "mileage": 22000, "fuel": "Hybride", "gearbox": "Automatique"}},
]


async def ensure_market_seed(db) -> None:
    if not settings.DEMO_MODE:
        return
    if await db.listings.count_documents({}) > 0:
        return
    await ensure_demo_users(db)
    from datetime import timedelta
    base = now()
    docs = []
    for i, x in enumerate(_MARKET_SEED):
        lat, lon = CITIES.get(x["city"]) or CITIES["Paris"]
        docs.append({
            "id": uid(), "sellerId": x["s"], "title": x["t"], "description": x["d"], "priceCents": x["p"],
            "category": x["cat"], "subcategory": x["sub"], "transactionType": x["tx"], "condition": x["cond"],
            "attributes": x.get("attrs") or {}, "images": [MARKET_IMGS[x["img"]]], "city": x["city"], "postcode": "",
            "country": "FR", "lat": lat, "lon": lon, "status": "active",
            "favorites": random.randint(0, 39), "views": random.randint(0, 299), "createdAt": base - timedelta(hours=i * 6),
        })
    await db.listings.insert_many(docs)


async def ensure_app_store_seed(db) -> None:
    if await db.store_apps.count_documents({}) > 0:
        return
    docs = []
    for a in STORE_APPS:
        if settings.DEMO_MODE:
            stats = {"rating": round(4.2 + random.random() * 0.75, 1),
                     "users": random.randint(80, 979) * 1000000,
                     "reviews": random.randint(200, 4199) * 1000}
        else:
            # Vraie app : pas de chiffres gonflés
            stats = {"rating": None, "users": 0, "reviews": 0}
        docs.append({**a, **stats})
    await db.store_apps.insert_many(docs)
