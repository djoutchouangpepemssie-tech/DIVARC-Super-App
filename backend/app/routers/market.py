"""Routes Marketplace v2 (annonces, filtres géo, chat, offres) + géolocalisation."""
from __future__ import annotations

import base64
import re

from fastapi import APIRouter, Depends, Request, Response

from ..data import CONDITIONS, MARKET_CATEGORIES
from ..db import get_db
from ..helpers import (body_of, credit_wallet, err, geo_autocomplete, geo_reverse, haversine_km,
                       now, ok, post_ledger, uid)
from ..notify import notify
from ..seed import ensure_market_seed
from ..security import require_user

router = APIRouter()

_DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z+]+);base64,(.+)$", re.S)


# ---------------- Image publique (les <img> n'envoient pas de Bearer) ----------------
@router.get("/market/image/{image_id}")
async def market_image(image_id: str):
    db = get_db()
    img = await db.market_images.find_one({"id": image_id})
    if not img:
        return err("Image introuvable", 404)
    raw = base64.b64decode(img["data"])
    return Response(content=raw, media_type=img.get("contentType") or "image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


# ---------------- Géolocalisation (Europe) ----------------
@router.get("/geo/autocomplete")
async def geo_autocomplete_route(request: Request, me: dict = Depends(require_user)):
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 3:
        return ok([])
    country = request.query_params.get("country") or ""
    return ok(await geo_autocomplete(q, country))


@router.get("/geo/reverse")
async def geo_reverse_route(request: Request, me: dict = Depends(require_user)):
    try:
        lat = float(request.query_params.get("lat"))
        lon = float(request.query_params.get("lon"))
    except (TypeError, ValueError):
        return err("Coordonnées invalides")
    return ok(await geo_reverse(lat, lon))


# ---------------- Catégories & upload ----------------
@router.get("/market/categories")
async def market_categories(me: dict = Depends(require_user)):
    db = get_db()
    await ensure_market_seed(db)
    return ok({"categories": MARKET_CATEGORIES, "conditions": CONDITIONS})


@router.post("/market/upload")
async def market_upload(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    data = str(body.get("data") or "")
    m = _DATA_URL_RE.match(data)
    content_type = m.group(1) if m else (body.get("contentType") or "image/jpeg")
    b64 = m.group(2) if m else data
    if not b64:
        return err("Image invalide")
    if len(b64) > 8_000_000:
        return err("Image trop lourde (max ~6 Mo)", 413)
    iid = uid()
    await db.market_images.insert_one({"id": iid, "userId": me["id"], "data": b64, "contentType": content_type, "createdAt": now()})
    return ok({"id": iid, "url": f"/api/market/image/{iid}"})


# ---------------- Annonces ----------------
@router.get("/market/listings")
async def list_listings(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    await ensure_market_seed(db)
    qp = request.query_params
    q = (qp.get("q") or "").lower()
    cat = qp.get("cat") or ""
    subcat = qp.get("subcat") or ""
    tx_type = qp.get("type") or ""
    cond = qp.get("condition") or ""
    min_p = _num(qp.get("minPrice"))
    max_p = _num(qp.get("maxPrice"))
    sort = qp.get("sort") or "recent"
    lat, lon = _num(qp.get("lat"), None), _num(qp.get("lon"), None)
    radius_km = _num(qp.get("radiusKm"))
    has_geo = lat is not None and lon is not None

    items = await db.listings.find({"status": "active"}, {"_id": 0}).to_list(length=None)
    if cat and cat != "Tout":
        items = [i for i in items if i["category"] == cat]
    if subcat:
        items = [i for i in items if i.get("subcategory") == subcat]
    if tx_type:
        items = [i for i in items if (i.get("transactionType") or "sale") == tx_type]
    if cond:
        items = [i for i in items if i.get("condition") == cond]
    if min_p:
        items = [i for i in items if i["priceCents"] >= min_p]
    if max_p:
        items = [i for i in items if i["priceCents"] <= max_p]
    if q:
        items = [i for i in items if q in i["title"].lower() or q in (i.get("description") or "").lower() or q in (i.get("city") or "").lower()]
    if has_geo:
        for i in items:
            i["distanceKm"] = round(haversine_km(lat, lon, i["lat"], i["lon"])) if (i.get("lat") is not None and i.get("lon") is not None) else None
        if radius_km > 0:
            items = [i for i in items if i.get("distanceKm") is not None and i["distanceKm"] <= radius_km]
    if sort == "price_asc":
        items.sort(key=lambda a: a["priceCents"])
    elif sort == "price_desc":
        items.sort(key=lambda a: a["priceCents"], reverse=True)
    elif sort == "distance" and has_geo:
        items.sort(key=lambda a: a.get("distanceKm") if a.get("distanceKm") is not None else 1e9)
    else:
        items.sort(key=lambda a: a["createdAt"], reverse=True)

    favs = {f["listingId"] for f in await db.market_favorites.find({"userId": me["id"]}).to_list(length=None)}
    out = []
    for i in items:
        seller = await db.users.find_one({"id": i["sellerId"]}, {"_id": 0, "email": 0})
        out.append({**i, "favorited": i["id"] in favs,
                    "seller": ({"id": seller["id"], "name": seller["name"], "handle": seller["handle"],
                                "initials": seller["initials"], "avatarColor": seller["avatarColor"],
                                "verified": seller["verified"]} if seller else None)})
    return ok(out)


@router.post("/market/listings")
async def create_listing(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    cat_def = next((c for c in MARKET_CATEGORIES if c["id"] == body.get("category")), None)
    attrs = body.get("attributes") if isinstance(body.get("attributes"), dict) else {}
    images = [x for x in body.get("images") if x][:8] if isinstance(body.get("images"), list) else []
    listing = {
        "id": uid(), "sellerId": me["id"], "title": body.get("title") or "Annonce", "description": body.get("description") or "",
        "priceCents": max(0, round(body.get("priceCents") or 0)),
        "category": cat_def["id"] if cat_def else "maison",
        "subcategory": body.get("subcategory") or ((cat_def.get("subcats") or ["Autre"])[0] if cat_def else "Autre"),
        "transactionType": body.get("transactionType") or "sale", "condition": body.get("condition") or "Bon état",
        "attributes": attrs, "images": images,
        "city": body.get("city") or "", "postcode": body.get("postcode") or "", "country": body.get("country") or "FR",
        "lat": _num(body.get("lat"), None), "lon": _num(body.get("lon"), None),
        "status": "active", "favorites": 0, "views": 0, "createdAt": now(),
    }
    await db.listings.insert_one(dict(listing))
    listing.pop("_id", None)
    return ok(listing)


@router.get("/market/mine")
async def market_mine(me: dict = Depends(require_user)):
    db = get_db()
    selling = await db.listings.find({"sellerId": me["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    orders = await db.orders.find({"buyerId": me["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    fav_ids = [f["listingId"] for f in await db.market_favorites.find({"userId": me["id"]}).to_list(length=None)]
    favorites = await db.listings.find({"id": {"$in": fav_ids}, "status": "active"}, {"_id": 0}).to_list(length=None)
    return ok({"selling": selling, "purchases": orders, "favorites": favorites})


@router.get("/market/listings/{lid}")
async def get_listing(lid: str, me: dict = Depends(require_user)):
    db = get_db()
    l = await db.listings.find_one({"id": lid}, {"_id": 0})
    if not l:
        return err("Annonce introuvable", 404)
    await db.listings.update_one({"id": lid}, {"$inc": {"views": 1}})
    seller = await db.users.find_one({"id": l["sellerId"]}, {"_id": 0, "email": 0})
    favs = {f["listingId"] for f in await db.market_favorites.find({"userId": me["id"]}).to_list(length=None)}
    similar = await db.listings.find({"category": l["category"], "status": "active", "id": {"$ne": l["id"]}}, {"_id": 0}).limit(4).to_list(length=4)
    return ok({**l, "favorited": l["id"] in favs, "seller": seller, "isMine": l["sellerId"] == me["id"], "similar": similar})


@router.delete("/market/listings/{lid}")
async def delete_listing(lid: str, me: dict = Depends(require_user)):
    db = get_db()
    l = await db.listings.find_one({"id": lid})
    if not l:
        return err("Annonce introuvable", 404)
    if l["sellerId"] != me["id"]:
        return err("Non autorisé", 403)
    await db.listings.delete_one({"id": lid})
    return ok({"ok": True})


@router.post("/market/listings/{lid}/favorite")
async def favorite_listing(lid: str, me: dict = Depends(require_user)):
    db = get_db()
    ex = await db.market_favorites.find_one({"listingId": lid, "userId": me["id"]})
    if ex:
        await db.market_favorites.delete_one({"listingId": lid, "userId": me["id"]})
        await db.listings.update_one({"id": lid}, {"$inc": {"favorites": -1}})
    else:
        await db.market_favorites.insert_one({"listingId": lid, "userId": me["id"]})
        await db.listings.update_one({"id": lid}, {"$inc": {"favorites": 1}})
    l = await db.listings.find_one({"id": lid})
    return ok({"favorited": not ex, "favorites": l["favorites"]})


@router.post("/market/listings/{lid}/buy")
async def buy_listing(lid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    l = await db.listings.find_one({"id": lid})
    if not l:
        return err("Annonce introuvable", 404)
    if l["status"] != "active":
        return err("Déjà vendu", 410)
    if l["sellerId"] == me["id"]:
        return err("Tu ne peux pas acheter ta propre annonce")
    price_cents = round(body.get("priceCents") or l["priceCents"])
    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < price_cents:
        return err("Solde insuffisant", 402)
    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -price_cents}})
    await credit_wallet(db, l["sellerId"], price_cents)
    new_status = "rented" if l.get("transactionType") == "rent" else "sold"
    await db.listings.update_one({"id": l["id"]}, {"$set": {"status": new_status, "buyerId": me["id"], "soldAt": now()}})
    order = {"id": uid(), "listingId": l["id"], "title": l["title"], "image": (l.get("images") or [None])[0],
             "buyerId": me["id"], "sellerId": l["sellerId"], "priceCents": price_cents, "createdAt": now()}
    await db.orders.insert_one(dict(order))
    await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Achat : {l['title']}", "category": "Marketplace",
                                      "amountCents": -price_cents, "carbonKg": 0, "icon": "🛍️", "route": None, "createdAt": now()})
    await post_ledger(db, [{"account": f"user:{me['id']}", "direction": "debit", "amountCents": price_cents},
                           {"account": f"user:{l['sellerId']}", "direction": "credit", "amountCents": price_cents}])
    await notify(db, l["sellerId"], "sale", "🛍️ Article vendu",
                 f"{l['title']} — {price_cents / 100:.2f} €", {"listingId": l["id"]})
    updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    return ok({"ok": True, "order": {"id": order["id"]}, "balanceCents": updated["balanceCents"]})


# ---------------- Chat & offres ----------------
@router.post("/market/listings/{lid}/chat")
async def start_chat(lid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    l = await db.listings.find_one({"id": lid})
    if not l:
        return err("Annonce introuvable", 404)
    if l["sellerId"] == me["id"]:
        return err("C’est ta propre annonce")
    thread = await db.market_threads.find_one({"listingId": l["id"], "buyerId": me["id"]}, {"_id": 0})
    if not thread:
        thread = {"id": uid(), "listingId": l["id"], "listingTitle": l["title"], "listingImage": (l.get("images") or [None])[0],
                  "listingPriceCents": l["priceCents"], "buyerId": me["id"], "sellerId": l["sellerId"],
                  "createdAt": now(), "lastMessageAt": now()}
        await db.market_threads.insert_one(dict(thread))
        thread.pop("_id", None)
        if body.get("text"):
            await db.market_messages.insert_one({"id": uid(), "threadId": thread["id"], "senderId": me["id"],
                                                 "type": "text", "text": str(body["text"]), "createdAt": now()})
    return ok({"thread": thread, "existing": False})


@router.get("/market/threads")
async def list_threads(me: dict = Depends(require_user)):
    db = get_db()
    threads = await db.market_threads.find({"$or": [{"buyerId": me["id"]}, {"sellerId": me["id"]}]}, {"_id": 0}).sort("lastMessageAt", -1).to_list(length=None)
    out = []
    for t in threads:
        other_id = t["sellerId"] if t["buyerId"] == me["id"] else t["buyerId"]
        other = await db.users.find_one({"id": other_id}, {"_id": 0, "email": 0})
        last = await db.market_messages.find({"threadId": t["id"]}).sort("createdAt", -1).limit(1).to_list(length=1)
        out.append({**t, "role": "buyer" if t["buyerId"] == me["id"] else "seller",
                    "other": ({"id": other["id"], "name": other["name"], "handle": other["handle"],
                               "initials": other["initials"], "avatarColor": other["avatarColor"]} if other else None),
                    "lastMessage": ({"text": last[0].get("text"), "type": last[0].get("type"), "amountCents": last[0].get("amountCents")} if last else None)})
    return ok(out)


@router.get("/market/threads/{tid}/messages")
async def thread_messages(tid: str, me: dict = Depends(require_user)):
    db = get_db()
    t = await db.market_threads.find_one({"id": tid}, {"_id": 0})
    if not t or (t["buyerId"] != me["id"] and t["sellerId"] != me["id"]):
        return err("Conversation introuvable", 404)
    msgs = await db.market_messages.find({"threadId": t["id"]}, {"_id": 0}).sort("createdAt", 1).to_list(length=None)
    other_id = t["sellerId"] if t["buyerId"] == me["id"] else t["buyerId"]
    other = await db.users.find_one({"id": other_id}, {"_id": 0, "email": 0})
    listing = await db.listings.find_one({"id": t["listingId"]}, {"_id": 0})
    return ok({"thread": {**t, "role": "buyer" if t["buyerId"] == me["id"] else "seller"}, "messages": msgs, "other": other, "listing": listing})


@router.post("/market/threads/{tid}/messages")
async def send_thread_message(tid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    t = await db.market_threads.find_one({"id": tid})
    if not t or (t["buyerId"] != me["id"] and t["sellerId"] != me["id"]):
        return err("Conversation introuvable", 404)
    body = await body_of(request)
    text = str(body.get("text") or "")[:2000]
    if not text.strip():
        return err("Message vide")
    msg = {"id": uid(), "threadId": t["id"], "senderId": me["id"], "type": "text", "text": text, "createdAt": now()}
    await db.market_messages.insert_one(dict(msg))
    await db.market_threads.update_one({"id": t["id"]}, {"$set": {"lastMessageAt": now()}})
    msg.pop("_id", None)
    return ok(msg)


@router.post("/market/threads/{tid}/offer")
async def make_offer(tid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    t = await db.market_threads.find_one({"id": tid})
    if not t or (t["buyerId"] != me["id"] and t["sellerId"] != me["id"]):
        return err("Conversation introuvable", 404)
    body = await body_of(request)
    amount_cents = round(body.get("amountCents") or 0)
    if amount_cents <= 0:
        return err("Montant invalide")
    offer_id = uid()
    msg = {"id": uid(), "offerId": offer_id, "threadId": t["id"], "senderId": me["id"], "type": "offer",
           "amountCents": amount_cents, "offerStatus": "pending", "createdAt": now()}
    await db.market_messages.insert_one(dict(msg))
    await db.market_threads.update_one({"id": t["id"]}, {"$set": {"lastMessageAt": now()}})
    msg.pop("_id", None)
    other = t["sellerId"] if me["id"] == t["buyerId"] else t["buyerId"]
    await notify(db, other, "offer", "💰 Nouvelle offre",
                 f"{amount_cents / 100:.2f} € pour {t.get('listingTitle') or 'un article'}", {"threadId": t["id"]})
    return ok(msg)


@router.post("/market/threads/{tid}/offer/{offer_id}/respond")
async def respond_offer(tid: str, offer_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    t = await db.market_threads.find_one({"id": tid})
    if not t or (t["buyerId"] != me["id"] and t["sellerId"] != me["id"]):
        return err("Conversation introuvable", 404)
    offer = await db.market_messages.find_one({"threadId": t["id"], "offerId": offer_id, "type": "offer"})
    if not offer:
        return err("Offre introuvable", 404)
    if offer["senderId"] == me["id"]:
        return err("Tu ne peux pas répondre à ta propre offre")
    body = await body_of(request)
    action = "accepted" if body.get("action") == "accept" else "rejected"
    await db.market_messages.update_one({"offerId": offer_id}, {"$set": {"offerStatus": action}})
    text = f"Offre acceptée : {offer['amountCents'] / 100:.2f} €" if action == "accepted" else "Offre refusée"
    await db.market_messages.insert_one({"id": uid(), "threadId": t["id"], "senderId": me["id"], "type": "system", "text": text, "createdAt": now()})
    await db.market_threads.update_one({"id": t["id"]}, {"$set": {"lastMessageAt": now(),
                                       "acceptedPriceCents": offer["amountCents"] if action == "accepted" else t.get("acceptedPriceCents")}})
    await notify(db, offer["senderId"], "offer",
                 "Offre acceptée ✅" if action == "accepted" else "Offre refusée",
                 text, {"threadId": t["id"]})
    return ok({"ok": True, "offerStatus": action, "amountCents": offer["amountCents"]})


def _num(v, default=0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default
