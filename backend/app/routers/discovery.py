"""Découverte & ajout d'utilisateurs (façon WhatsApp/Signal, RGPD par conception).

Recherche par @handle/nom, carnet de contacts haché, invitations (bonus wallet), QR/lien de profil,
proximité expirante, demandes d'ajout, blocage/anti-spam. Aucun numéro/e-mail en clair côté serveur.
"""
from __future__ import annotations

import secrets
import string
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from ..config import settings
from ..db import get_db
from ..helpers import body_of, err, haversine_km, now, ok, uid
from ..notify import notify
from ..security import require_user

router = APIRouter()

_MAX_REQUESTS_PER_DAY = 30  # anti-spam
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


async def _blocked_between(db, a: str, b: str) -> bool:
    """True si l'un a bloqué l'autre (dans un sens ou l'autre)."""
    return bool(await db.blocks.find_one({"$or": [
        {"blockerId": a, "blockedId": b}, {"blockerId": b, "blockedId": a}]}))


async def _relation(db, me_id: str, other_id: str) -> str:
    """Relation entre moi et un autre : 'self' | 'contact' | 'pending_out' | 'pending_in' | 'none'."""
    if me_id == other_id:
        return "self"
    if await db.contacts_list.find_one({"ownerId": me_id, "contactId": other_id}):
        return "contact"
    if await db.contact_requests.find_one({"fromId": me_id, "toId": other_id, "status": "pending"}):
        return "pending_out"
    if await db.contact_requests.find_one({"fromId": other_id, "toId": me_id, "status": "pending"}):
        return "pending_in"
    return "none"


def _card(u: dict) -> dict:
    return {"id": u["id"], "name": u.get("name"), "handle": u.get("handle"),
            "initials": u.get("initials"), "avatarColor": u.get("avatarColor"),
            "verified": u.get("verified", False), "bio": u.get("bio") or ""}


# ============================ RECHERCHE (C1) ============================
@router.get("/discover/search")
async def search(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    q = (request.query_params.get("q") or "").strip().lower()
    if len(q) < 2:
        return ok([])
    users = await db.users.find(
        {"id": {"$ne": me["id"]}, "isBot": {"$ne": True}}, {"_id": 0}).limit(200).to_list(length=200)
    out = []
    for u in users:
        disc = u.get("discoverable") or {}
        # trouvable par @handle (opt-in activé par défaut) ; on matche handle OU nom
        if not disc.get("byHandle", True):
            continue
        if q not in (u.get("handle") or "").lower() and q not in (u.get("name") or "").lower():
            continue
        if await _blocked_between(db, me["id"], u["id"]):
            continue
        out.append({**_card(u), "relation": await _relation(db, me["id"], u["id"])})
        if len(out) >= 20:
            break
    return ok(out)


# ============================ CONTACTS HACHÉS (C2) ============================
@router.post("/discover/contacts/match")
async def contacts_match(request: Request, me: dict = Depends(require_user)):
    """Reçoit des HACHÉS (jamais de numéro/e-mail en clair) et renvoie les utilisateurs
    correspondants qui ont activé la découverte par téléphone/e-mail."""
    db = get_db()
    body = await body_of(request)
    phone_hashes = [h for h in (body.get("phoneHashes") or []) if isinstance(h, str)][:2000]
    email_hashes = [h for h in (body.get("emailHashes") or []) if isinstance(h, str)][:2000]
    found: dict[str, dict] = {}
    if phone_hashes:
        async for u in db.users.find({"phoneHash": {"$in": phone_hashes}, "discoverable.byPhone": True,
                                      "id": {"$ne": me["id"]}}, {"_id": 0}):
            found[u["id"]] = u
    if email_hashes:
        async for u in db.users.find({"emailHash": {"$in": email_hashes}, "discoverable.byEmail": True,
                                      "id": {"$ne": me["id"]}}, {"_id": 0}):
            found[u["id"]] = u
    out = []
    for u in found.values():
        if await _blocked_between(db, me["id"], u["id"]):
            continue
        out.append({**_card(u), "relation": await _relation(db, me["id"], u["id"])})
    return ok(out)


# ============================ INVITATIONS (C2) ============================
@router.post("/discover/invite")
async def invite_create(me: dict = Depends(require_user)):
    """Crée (ou réutilise) un lien d'invitation personnel. Le parrain gagne un bonus quand
    l'invité s'inscrit (traité à l'inscription)."""
    db = get_db()
    inv = await db.invites.find_one({"inviterId": me["id"]}, {"_id": 0})
    if not inv:
        code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(6))
        while await db.invites.find_one({"code": code}):
            code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(6))
        inv = {"code": code, "inviterId": me["id"], "inviterName": me.get("name"),
               "usedEmails": [], "count": 0, "createdAt": now()}
        await db.invites.insert_one(dict(inv))
        inv.pop("_id", None)
    base = (settings.APP_URL or "").rstrip("/")
    link = f"{base}/?invite={inv['code']}" if base else inv["code"]
    return ok({"code": inv["code"], "link": link, "count": inv.get("count", 0), "bonusCents": 500})


# ============================ PROFIL PUBLIC / LIEN (C3) ============================
@router.get("/discover/user/{handle}")
async def public_profile(handle: str, me: dict = Depends(require_user)):
    db = get_db()
    h = "@" + handle.lstrip("@").lower()
    u = await db.users.find_one({"handle": h}, {"_id": 0})
    if not u or not (u.get("discoverable") or {}).get("byHandle", True):
        return err("Profil introuvable", 404)
    if await _blocked_between(db, me["id"], u["id"]):
        return err("Profil introuvable", 404)
    return ok({**_card(u), "relation": await _relation(db, me["id"], u["id"])})


# ============================ PROXIMITÉ (C3) ============================
@router.post("/discover/nearby/ping")
async def nearby_ping(request: Request, me: dict = Depends(require_user)):
    """Signale ma position pour ~5 min (découverte ponctuelle et consentie, jamais continue)."""
    db = get_db()
    body = await body_of(request)
    try:
        lat, lon = float(body.get("lat")), float(body.get("lon"))
    except (TypeError, ValueError):
        return err("Coordonnées invalides")
    await db.nearby_pings.update_one({"userId": me["id"]}, {"$set": {
        "userId": me["id"], "lat": lat, "lon": lon,
        "expiresAt": now() + timedelta(minutes=5), "updatedAt": now()}}, upsert=True)
    return ok({"ok": True, "expiresInSec": 300})


@router.get("/discover/nearby")
async def nearby_list(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    mine = await db.nearby_pings.find_one({"userId": me["id"]})
    if not mine or mine["expiresAt"] < now():
        return err("Active d'abord ta position (proximité)", 400)
    radius = 2.0  # km
    out = []
    async for p in db.nearby_pings.find({"userId": {"$ne": me["id"]}, "expiresAt": {"$gt": now()}}):
        d = haversine_km(mine["lat"], mine["lon"], p["lat"], p["lon"])
        if d > radius:
            continue
        u = await db.users.find_one({"id": p["userId"]}, {"_id": 0})
        if not u or await _blocked_between(db, me["id"], u["id"]):
            continue
        out.append({**_card(u), "distanceM": round(d * 1000), "relation": await _relation(db, me["id"], u["id"])})
    out.sort(key=lambda x: x["distanceM"])
    return ok(out)


# ============================ DEMANDES D'AJOUT (C4) ============================
@router.post("/discover/request/{user_id}")
async def send_request(user_id: str, me: dict = Depends(require_user)):
    db = get_db()
    if user_id == me["id"]:
        return err("Impossible de s'ajouter soi-même")
    other = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not other:
        return err("Utilisateur introuvable", 404)
    if await _blocked_between(db, me["id"], user_id):
        return err("Action impossible", 403)
    if await db.contacts_list.find_one({"ownerId": me["id"], "contactId": user_id}):
        return ok({"status": "contact"})
    # anti-spam : limite de demandes par 24 h
    since = now() - timedelta(days=1)
    if await db.contact_requests.count_documents({"fromId": me["id"], "createdAt": {"$gt": since}}) >= _MAX_REQUESTS_PER_DAY:
        return err("Trop de demandes aujourd'hui, réessaie demain", 429)
    existing = await db.contact_requests.find_one({"fromId": me["id"], "toId": user_id, "status": "pending"})
    if existing:
        return ok({"status": "pending_out"})
    await db.contact_requests.insert_one({"id": uid(), "fromId": me["id"], "fromName": me.get("name"),
                                          "fromHandle": me.get("handle"), "toId": user_id,
                                          "status": "pending", "createdAt": now()})
    await notify(db, user_id, "contact", "👋 Nouvelle demande de contact",
                 f"{me.get('name')} ({me.get('handle')}) veut t'ajouter", {})
    return ok({"status": "pending_out"})


@router.get("/discover/requests")
async def list_requests(me: dict = Depends(require_user)):
    db = get_db()
    reqs = await db.contact_requests.find({"toId": me["id"], "status": "pending"}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    out = []
    for r in reqs:
        u = await db.users.find_one({"id": r["fromId"]}, {"_id": 0})
        if u:
            out.append({"requestId": r["id"], **_card(u)})
    return ok(out)


@router.post("/discover/request/{from_id}/respond")
async def respond_request(from_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    r = await db.contact_requests.find_one({"fromId": from_id, "toId": me["id"], "status": "pending"})
    if not r:
        return err("Demande introuvable", 404)
    accept = body.get("action") == "accept"
    await db.contact_requests.update_one({"id": r["id"]}, {"$set": {"status": "accepted" if accept else "rejected"}})
    if accept:
        # contact mutuel
        for a, b in [(me["id"], from_id), (from_id, me["id"])]:
            await db.contacts_list.update_one({"ownerId": a, "contactId": b},
                                              {"$setOnInsert": {"ownerId": a, "contactId": b, "createdAt": now()}}, upsert=True)
        await notify(db, from_id, "contact", "✅ Demande acceptée",
                     f"{me.get('name')} a accepté ta demande de contact", {})
    return ok({"ok": True, "accepted": accept})


@router.get("/discover/contacts")
async def my_contacts(me: dict = Depends(require_user)):
    """Mon carnet de contacts DIVARC (contacts acceptés)."""
    db = get_db()
    rows = await db.contacts_list.find({"ownerId": me["id"]}, {"_id": 0}).to_list(length=None)
    out = []
    for r in rows:
        u = await db.users.find_one({"id": r["contactId"]}, {"_id": 0})
        if u and not await _blocked_between(db, me["id"], u["id"]):
            out.append(_card(u))
    out.sort(key=lambda x: (x.get("name") or "").lower())
    return ok(out)


# ============================ BLOCAGE / SIGNALEMENT (C4) ============================
@router.post("/discover/block/{user_id}")
async def block_user(user_id: str, me: dict = Depends(require_user)):
    db = get_db()
    if user_id == me["id"]:
        return err("Action impossible")
    await db.blocks.update_one({"blockerId": me["id"], "blockedId": user_id},
                               {"$setOnInsert": {"blockerId": me["id"], "blockedId": user_id, "createdAt": now()}}, upsert=True)
    # retire des carnets et demandes en cours
    await db.contacts_list.delete_many({"$or": [{"ownerId": me["id"], "contactId": user_id},
                                                {"ownerId": user_id, "contactId": me["id"]}]})
    await db.contact_requests.update_many({"$or": [{"fromId": me["id"], "toId": user_id},
                                                   {"fromId": user_id, "toId": me["id"]}], "status": "pending"},
                                          {"$set": {"status": "rejected"}})
    return ok({"ok": True, "blocked": True})


@router.post("/discover/unblock/{user_id}")
async def unblock_user(user_id: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.blocks.delete_one({"blockerId": me["id"], "blockedId": user_id})
    return ok({"ok": True, "blocked": False})


@router.get("/discover/blocks")
async def list_blocks(me: dict = Depends(require_user)):
    db = get_db()
    rows = await db.blocks.find({"blockerId": me["id"]}, {"_id": 0}).to_list(length=None)
    out = []
    for r in rows:
        u = await db.users.find_one({"id": r["blockedId"]}, {"_id": 0})
        if u:
            out.append(_card(u))
    return ok(out)


@router.post("/discover/report/{user_id}")
async def report_user(user_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    await db.reports.insert_one({"id": uid(), "reporterId": me["id"], "reportedId": user_id,
                                 "reason": (body.get("reason") or "")[:500], "createdAt": now()})
    return ok({"ok": True})
