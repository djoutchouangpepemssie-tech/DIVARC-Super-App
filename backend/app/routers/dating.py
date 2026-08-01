"""DIVARC Rencontres — verticale de rencontres intégrée, monétisée par les Éclats.

Trust & safety d'abord : âge 18+ (déclaratif, prêt EUDI), localisation APPROXIMATIVE,
blocage réutilisé de la messagerie, signalement, données sensibles cloisonnées (RGPD art. 9).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request

from .. import eclats as ec
from ..config import settings
from ..db import get_db
from ..helpers import body_of, err, haversine_km, now, ok, today_str, uid
from ..notify import notify
from ..realtime import manager
from ..security import require_user

router = APIRouter()

GENDERS = {"homme", "femme", "autre"}


def _age_from(birth: str) -> int | None:
    try:
        d = date.fromisoformat(birth[:10])
    except (TypeError, ValueError):
        return None
    t = now().date()
    return t.year - d.year - ((t.month, t.day) < (d.month, d.day))


def _round_geo(v):
    try:
        return round(float(v), 2)  # ~1,1 km : localisation approximative, jamais exacte
    except (TypeError, ValueError):
        return None


async def _blocked_ids(db, me_id: str) -> set[str]:
    rows = await db.blocks.find({"$or": [{"blockerId": me_id}, {"blockedId": me_id}]}).to_list(length=None)
    ids = set()
    for r in rows:
        ids.add(r["blockedId"] if r["blockerId"] == me_id else r["blockerId"])
    return ids


async def _card(db, prof: dict, me_lat=None, me_lon=None) -> dict:
    u = await db.users.find_one({"id": prof["userId"]}, {"_id": 0, "email": 0}) or {}
    dist = None
    if me_lat is not None and prof.get("lat") is not None:
        dist = round(haversine_km(me_lat, me_lon, prof["lat"], prof["lon"]))
    return {
        "userId": prof["userId"], "name": u.get("name"), "initials": u.get("initials"),
        "avatarColor": u.get("avatarColor"), "verified": bool(u.get("verified")),
        "age": _age_from(prof.get("birthDate", "")), "bio": prof.get("bio", ""),
        "photos": prof.get("photos", []), "gender": prof.get("gender"),
        "city": prof.get("city"), "distanceKm": dist,
        "ageVerified": bool(prof.get("ageVerified")), "photoVerified": bool(prof.get("photoVerified")),
        "boosted": bool(prof.get("boostedUntil") and prof["boostedUntil"] > now()),
    }


# ---------------- Profil (opt-in + âge) ----------------
@router.get("/dating/me")
async def dating_me(me: dict = Depends(require_user)):
    db = get_db()
    prof = await db.dating_profiles.find_one({"userId": me["id"]}, {"_id": 0})
    return ok({"profile": prof, "hasProfile": bool(prof)})


@router.post("/dating/profile")
async def dating_upsert_profile(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    existing = await db.dating_profiles.find_one({"userId": me["id"]})

    # Âge : obligatoire à la création, barrière 18+ stricte (déclaratif, prêt EUDI)
    birth = (body.get("birthDate") or (existing or {}).get("birthDate") or "").strip()
    age = _age_from(birth)
    if age is None:
        return err("Date de naissance requise (AAAA-MM-JJ)")
    if age < settings.DATING_MIN_AGE:
        return err(f"Rencontres est réservé aux {settings.DATING_MIN_AGE} ans et plus", 403)

    gender = (body.get("gender") or (existing or {}).get("gender") or "").lower()
    if gender not in GENDERS:
        return err("Genre invalide (homme, femme ou autre)")
    seeking = [g for g in (body.get("seeking") or (existing or {}).get("seeking") or []) if g in GENDERS]
    if not seeking:
        return err("Indique au moins un genre recherché")
    photos = [p for p in (body.get("photos") or (existing or {}).get("photos") or []) if p][:6]

    doc = {
        "userId": me["id"], "active": True, "paused": False,
        "birthDate": birth, "gender": gender, "seeking": seeking,
        "bio": (body.get("bio") if body.get("bio") is not None else (existing or {}).get("bio", ""))[:500],
        "photos": photos,
        "city": body.get("city") if body.get("city") is not None else (existing or {}).get("city", ""),
        "lat": _round_geo(body.get("lat")) if body.get("lat") is not None else (existing or {}).get("lat"),
        "lon": _round_geo(body.get("lon")) if body.get("lon") is not None else (existing or {}).get("lon"),
        "ageVerified": False,      # déclaratif tant que l'EUDI n'est pas branché
        "photoVerified": (existing or {}).get("photoVerified", False),
        "updatedAt": now(),
    }
    if existing:
        await db.dating_profiles.update_one({"userId": me["id"]}, {"$set": doc})
    else:
        doc["createdAt"] = now()
        await db.dating_profiles.insert_one(dict(doc))
    prof = await db.dating_profiles.find_one({"userId": me["id"]}, {"_id": 0})
    return ok(prof)


@router.post("/dating/pause")
async def dating_pause(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    paused = bool(body.get("paused", True))
    await db.dating_profiles.update_one({"userId": me["id"]}, {"$set": {"paused": paused}})
    return ok({"paused": paused})


@router.delete("/dating/profile")
async def dating_delete(me: dict = Depends(require_user)):
    """RGPD : suppression propagée (profil + swipes + matchs)."""
    db = get_db()
    mid = me["id"]
    await db.dating_profiles.delete_one({"userId": mid})
    await db.dating_swipes.delete_many({"$or": [{"swiperId": mid}, {"targetId": mid}]})
    await db.dating_matches.delete_many({"users": mid})
    return ok({"ok": True})


# ---------------- Découverte ----------------
@router.get("/dating/discover")
async def dating_discover(me: dict = Depends(require_user)):
    db = get_db()
    my = await db.dating_profiles.find_one({"userId": me["id"]})
    if not my:
        return err("Crée d'abord ton profil Rencontres", 403)
    swiped = {s["targetId"] for s in await db.dating_swipes.find({"swiperId": me["id"]}).to_list(length=None)}
    blocked = await _blocked_ids(db, me["id"])
    my_seeking = my.get("seeking") or []
    my_gender = my.get("gender")

    cands = await db.dating_profiles.find({
        "active": True, "paused": {"$ne": True}, "userId": {"$ne": me["id"]},
    }, {"_id": 0}).to_list(length=None)
    out = []
    for p in cands:
        if p["userId"] in swiped or p["userId"] in blocked:
            continue
        if p.get("gender") not in my_seeking:      # correspond à ce que JE cherche
            continue
        if my_gender not in (p.get("seeking") or []):  # ET je corresponds à ce qu'IL cherche
            continue
        out.append(await _card(db, p, my.get("lat"), my.get("lon")))
    # Profils boostés en tête, puis les plus proches
    out.sort(key=lambda c: (c["distanceKm"] is None, c["distanceKm"] if c["distanceKm"] is not None else 1e9))
    out.sort(key=lambda c: 0 if c["boosted"] else 1)
    return ok(out[:30])


# ---------------- Swipe & match ----------------
async def _get_or_create_dm(db, a: str, b: str) -> str:
    existing = await db.conversations.find_one({"type": "dm", "memberIds": {"$all": [a, b], "$size": 2}})
    if existing:
        return existing["id"]
    cid = uid()
    await db.conversations.insert_one({
        "id": cid, "type": "dm", "name": None, "topic": None, "avatarColor": None,
        "memberIds": [a, b], "createdBy": "system", "isPublic": False, "reads": {},
        "lastText": "Vous avez matché sur DIVARC Rencontres 💜", "lastMessageAt": now(), "createdAt": now(),
    })
    return cid


@router.post("/dating/swipe/{target_id}")
async def dating_swipe(target_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    if target_id == me["id"]:
        return err("Action invalide")
    body = await body_of(request)
    action = body.get("action") or "like"
    if action not in ("like", "pass", "superlike"):
        return err("Action invalide")
    my = await db.dating_profiles.find_one({"userId": me["id"]})
    if not my:
        return err("Crée d'abord ton profil Rencontres", 403)
    if target_id in await _blocked_ids(db, me["id"]):
        return err("Utilisateur indisponible", 403)

    # Super-like : payé en Éclats. Like gratuit : plafond quotidien.
    if action == "superlike":
        op = uid()
        spent = await ec.spend(db, me["id"], settings.ECLATS_SUPERLIKE, "superlike",
                               {"label": "Super-like ⭐", "targetId": target_id}, idem=f"superlike:{op}")
        if not spent.get("ok"):
            return err(spent.get("error") or "Solde d'Éclats insuffisant", 402)
    elif action == "like":
        used = await db.dating_swipes.count_documents({"swiperId": me["id"], "action": "like", "day": today_str()})
        if used >= settings.DATING_DAILY_LIKES:
            return err("Limite de likes gratuits atteinte aujourd'hui — utilise un super-like ou reviens demain", 429)

    await db.dating_swipes.update_one(
        {"swiperId": me["id"], "targetId": target_id},
        {"$set": {"swiperId": me["id"], "targetId": target_id, "action": action,
                  "day": today_str(), "createdAt": now()}},
        upsert=True,
    )
    if action == "pass":
        return ok({"match": False})

    # Réciprocité -> match
    back = await db.dating_swipes.find_one({"swiperId": target_id, "targetId": me["id"],
                                            "action": {"$in": ["like", "superlike"]}})
    if not back:
        # notifie un super-like reçu (sans révéler l'identité pour un like normal)
        if action == "superlike":
            await notify(db, target_id, "system", "⭐ Quelqu'un t'a envoyé un super-like", "Ouvre Rencontres pour voir", {})
        return ok({"match": False})

    key = "|".join(sorted([me["id"], target_id]))
    if not await db.dating_matches.find_one({"key": key}):
        cid = await _get_or_create_dm(db, me["id"], target_id)
        await db.dating_matches.insert_one({"id": uid(), "key": key, "users": sorted([me["id"], target_id]),
                                            "conversationId": cid, "createdAt": now()})
        other = await db.users.find_one({"id": target_id}, {"_id": 0})
        await notify(db, target_id, "system", "💜 Nouveau match !", f"Toi et {me.get('name')} vous êtes plu", {"conversationId": cid})
        await manager.send_to_user(target_id, {"type": "notification", "notification": {"kind": "system"}})
        return ok({"match": True, "conversationId": cid,
                   "other": {"id": target_id, "name": (other or {}).get("name")}})
    m = await db.dating_matches.find_one({"key": key}, {"_id": 0})
    return ok({"match": True, "conversationId": m["conversationId"]})


@router.get("/dating/matches")
async def dating_matches(me: dict = Depends(require_user)):
    db = get_db()
    ms = await db.dating_matches.find({"users": me["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    out = []
    for m in ms:
        other_id = next((u for u in m["users"] if u != me["id"]), None)
        prof = await db.dating_profiles.find_one({"userId": other_id}, {"_id": 0})
        card = await _card(db, prof, None, None) if prof else {"userId": other_id}
        out.append({**card, "conversationId": m["conversationId"], "matchedAt": m["createdAt"]})
    return ok(out)


# ---------------- Qui t'a liké (révélation payante) ----------------
@router.get("/dating/likes")
async def dating_likes(me: dict = Depends(require_user)):
    """Nombre de personnes qui t'ont liké (teaser). La liste se révèle en Éclats."""
    db = get_db()
    matched = {m["key"] for m in await db.dating_matches.find({"users": me["id"]}).to_list(length=None)}
    likers = await db.dating_swipes.find({"targetId": me["id"], "action": {"$in": ["like", "superlike"]}}).to_list(length=None)
    # exclure ceux déjà matchés
    pending = [l for l in likers if "|".join(sorted([l["swiperId"], me["id"]])) not in matched]
    return ok({"count": len(pending), "revealCost": settings.ECLATS_REVEAL_LIKES})


@router.post("/dating/likes/reveal")
async def dating_reveal(me: dict = Depends(require_user)):
    db = get_db()
    matched = {m["key"] for m in await db.dating_matches.find({"users": me["id"]}).to_list(length=None)}
    likers = await db.dating_swipes.find({"targetId": me["id"], "action": {"$in": ["like", "superlike"]}}).to_list(length=None)
    pending = [l for l in likers if "|".join(sorted([l["swiperId"], me["id"]])) not in matched]
    if not pending:
        return ok({"revealed": [], "count": 0})
    op = uid()
    spent = await ec.spend(db, me["id"], settings.ECLATS_REVEAL_LIKES, "reveal_likes",
                           {"label": "Révélation « qui t'a liké »"}, idem=f"reveal:{op}")
    if not spent.get("ok"):
        return err(spent.get("error") or "Solde d'Éclats insuffisant", 402)
    blocked = await _blocked_ids(db, me["id"])
    out = []
    for l in pending:
        if l["swiperId"] in blocked:
            continue
        prof = await db.dating_profiles.find_one({"userId": l["swiperId"]}, {"_id": 0})
        if prof:
            out.append({**await _card(db, prof, None, None), "superlike": l["action"] == "superlike"})
    return ok({"revealed": out, "count": len(out), "eclatsBalance": spent.get("balance")})


# ---------------- Boost de profil ----------------
@router.post("/dating/boost")
async def dating_boost(me: dict = Depends(require_user)):
    db = get_db()
    my = await db.dating_profiles.find_one({"userId": me["id"]})
    if not my:
        return err("Crée d'abord ton profil Rencontres", 403)
    op = uid()
    spent = await ec.spend(db, me["id"], settings.ECLATS_DATING_BOOST, "dating_boost",
                           {"label": "Boost de profil Rencontres"}, idem=f"datingboost:{op}")
    if not spent.get("ok"):
        return err(spent.get("error") or "Solde d'Éclats insuffisant", 402)
    from datetime import timedelta
    until = now() + timedelta(hours=settings.ECLATS_BOOST_HOURS)
    await db.dating_profiles.update_one({"userId": me["id"]}, {"$set": {"boostedUntil": until}})
    return ok({"ok": True, "boostedUntil": until, "cost": settings.ECLATS_DATING_BOOST, "eclatsBalance": spent.get("balance")})


# ---------------- Signalement ----------------
@router.post("/dating/report/{user_id}")
async def dating_report(user_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    await db.dating_reports.insert_one({
        "id": uid(), "reporterId": me["id"], "targetId": user_id,
        "reason": (body.get("reason") or "non précisé")[:300], "status": "pending", "createdAt": now(),
    })
    return ok({"ok": True})
