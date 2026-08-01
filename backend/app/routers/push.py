"""Routes des notifications push Web (abonnement des appareils + clé publique VAPID)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import settings
from ..db import get_db
from ..helpers import body_of, err, now, ok
from ..push import push_enabled
from ..security import require_user

router = APIRouter()


@router.get("/push/vapid")
async def push_vapid():
    """Clé publique VAPID pour que le navigateur s'abonne (vide si push désactivé)."""
    return ok({"publicKey": settings.VAPID_PUBLIC_KEY, "enabled": push_enabled()})


@router.post("/push/subscribe")
async def push_subscribe(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    sub = body.get("subscription") or body
    endpoint = sub.get("endpoint")
    if not endpoint or not (sub.get("keys") or {}).get("p256dh"):
        return err("Abonnement invalide")
    doc = {
        "endpoint": endpoint,
        "userId": me["id"],
        "subscription": sub,
        "ua": request.headers.get("user-agent", "")[:200],
        "updatedAt": now(),
    }
    # upsert par endpoint (un même appareil ne crée pas de doublon, et rattache au bon user)
    await db.push_subscriptions.update_one(
        {"endpoint": endpoint},
        {"$set": doc, "$setOnInsert": {"createdAt": now()}},
        upsert=True,
    )
    return ok({"ok": True})


@router.post("/push/unsubscribe")
async def push_unsubscribe(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    endpoint = body.get("endpoint") or (body.get("subscription") or {}).get("endpoint")
    if endpoint:
        await db.push_subscriptions.delete_one({"endpoint": endpoint, "userId": me["id"]})
    return ok({"ok": True})
