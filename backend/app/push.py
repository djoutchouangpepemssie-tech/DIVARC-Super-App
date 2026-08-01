"""Envoi de notifications push Web (VAPID) — réveille le téléphone même app fermée.

Sans clés VAPID configurées, tout est simplement ignoré (aucune erreur).
L'appel pywebpush est bloquant : on le déporte dans un thread pour ne pas figer la boucle asyncio.
"""
from __future__ import annotations

import asyncio
import json

from .config import settings


def push_enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _send_one(subscription: dict, payload: str) -> int:
    """Envoie à UN abonnement. Retourne le code HTTP (410/404 = abonnement mort)."""
    from pywebpush import WebPushException, webpush
    try:
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=86400,
        )
        return 201
    except WebPushException as e:  # noqa: BLE001
        return getattr(e.response, "status_code", 0) or 0


async def send_web_push(db, user_id: str, notif: dict) -> None:
    """Pousse `notif` (dict de notification) à tous les appareils de l'utilisateur."""
    if not push_enabled():
        return
    subs = await db.push_subscriptions.find({"userId": user_id}, {"_id": 0}).to_list(length=None)
    if not subs:
        return
    meta = notif.get("meta") or {}
    payload = json.dumps({
        "title": notif.get("title") or "DIVARC",
        "body": notif.get("body") or "",
        "kind": notif.get("kind") or "system",
        "url": meta.get("url") or "/",
        "conversationId": meta.get("conversationId"),
        "tag": meta.get("conversationId") or notif.get("id"),
    })
    for s in subs:
        sub = s.get("subscription")
        if not sub:
            continue
        try:
            status = await asyncio.to_thread(_send_one, sub, payload)
        except Exception as e:  # noqa: BLE001
            print(f"[push] échec envoi: {e}")
            continue
        # Abonnement expiré / révoqué -> on le supprime
        if status in (404, 410):
            await db.push_subscriptions.delete_one({"endpoint": s.get("endpoint")})
