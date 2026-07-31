"""Routes App Store : apps connectables (pseudonymes RGPD), connexions."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request

from ..db import get_db
from ..helpers import err, now, ok, uid
from ..seed import ensure_app_store_seed
from ..security import require_user

router = APIRouter()


@router.get("/store/apps")
async def store_apps(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    await ensure_app_store_seed(db)
    q = (request.query_params.get("q") or "").lower()
    cat = request.query_params.get("cat") or ""
    apps = await db.store_apps.find({}, {"_id": 0}).to_list(length=None)
    if cat and cat != "Tout":
        apps = [a for a in apps if a["cat"] == cat]
    if q:
        apps = [a for a in apps if q in a["name"].lower() or q in a["cat"].lower() or q in a["desc"].lower()]
    conns = await db.app_connections.find({"userId": me["id"]}).to_list(length=None)
    conn_map = {c["appId"]: c for c in conns}
    out = [{**a, "connected": a["id"] in conn_map,
            "pseudonym": conn_map.get(a["id"], {}).get("pseudonym"),
            "since": conn_map.get(a["id"], {}).get("since")} for a in apps]
    out.sort(key=lambda a: (not a["featured"], -(a.get("users") or 0)))
    return ok(out)


@router.post("/store/apps/{app_id}/connect")
async def connect_app(app_id: str, me: dict = Depends(require_user)):
    db = get_db()
    app = await db.store_apps.find_one({"id": app_id})
    if not app:
        return err("App introuvable", 404)
    ex = await db.app_connections.find_one({"userId": me["id"], "appId": app_id}, {"_id": 0})
    if ex:
        return ok({"connection": ex, "existing": True})
    conn = {"id": uid(), "userId": me["id"], "appId": app_id, "appName": app["name"],
            "pseudonym": "divarc-" + secrets.token_hex(2), "scopes": app["perms"],
            "color": app["color"], "emoji": app["emoji"], "since": now()}
    await db.app_connections.insert_one(dict(conn))
    conn.pop("_id", None)
    return ok({"connection": conn})


@router.post("/store/apps/{app_id}/disconnect")
async def disconnect_app(app_id: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.app_connections.delete_one({"userId": me["id"], "appId": app_id})
    return ok({"ok": True})


@router.get("/store/connections")
async def store_connections(me: dict = Depends(require_user)):
    db = get_db()
    conns = await db.app_connections.find({"userId": me["id"]}, {"_id": 0}).sort("since", -1).to_list(length=None)
    return ok(conns)
