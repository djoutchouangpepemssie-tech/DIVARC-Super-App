"""Routes du centre de notifications."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..db import get_db
from ..helpers import ok
from ..security import require_user

router = APIRouter()


@router.get("/notifications")
async def list_notifications(me: dict = Depends(require_user)):
    db = get_db()
    items = await db.notifications.find({"userId": me["id"]}, {"_id": 0}).sort("createdAt", -1).limit(50).to_list(length=50)
    unread = await db.notifications.count_documents({"userId": me["id"], "read": False})
    return ok({"items": items, "unread": unread})


@router.post("/notifications/read")
async def mark_all_read(me: dict = Depends(require_user)):
    db = get_db()
    r = await db.notifications.update_many({"userId": me["id"], "read": False}, {"$set": {"read": True}})
    return ok({"ok": True, "updated": r.modified_count})


@router.post("/notifications/{nid}/read")
async def mark_one_read(nid: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.notifications.update_one({"id": nid, "userId": me["id"]}, {"$set": {"read": True}})
    return ok({"ok": True})
