"""Création de notifications persistées + push temps réel via WebSocket."""
from __future__ import annotations

from .helpers import now, uid
from .realtime import manager


async def notify(db, user_id: str, kind: str, title: str, body: str = "", meta: dict | None = None) -> dict:
    """Crée une notification pour `user_id` et la pousse en direct s'il est connecté.

    kind : 'message' | 'payment' | 'sale' | 'offer' | 'social' | 'system' …
    """
    n = {"id": uid(), "userId": user_id, "kind": kind, "title": title, "body": body,
         "meta": meta or {}, "read": False, "createdAt": now()}
    await db.notifications.insert_one(dict(n))
    n.pop("_id", None)
    await manager.send_to_user(user_id, {"type": "notification", "notification": n})
    return n
