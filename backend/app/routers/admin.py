"""Routes Hub administratif & santé : connecteurs eIDAS, documents chiffrés, comptabilité."""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from ..data import ADMIN_CONN, ADMIN_DATA
from ..db import get_db
from ..helpers import body_of, err, now, ok, uid
from ..security import require_user

router = APIRouter()


@router.get("/admin/connectors")
async def list_connectors(me: dict = Depends(require_user)):
    db = get_db()
    conns = await db.admin_connections.find({"userId": me["id"]}).to_list(length=None)
    cmap = {c["connectorId"]: c for c in conns}
    return ok([{**a, "connected": a["id"] in cmap,
                "pseudonym": cmap.get(a["id"], {}).get("pseudonym"),
                "since": cmap.get(a["id"], {}).get("since"),
                "data": cmap.get(a["id"], {}).get("data") or []} for a in ADMIN_CONN])


@router.post("/admin/connectors/{connector_id}/connect")
async def connect_connector(connector_id: str, me: dict = Depends(require_user)):
    db = get_db()
    definition = next((a for a in ADMIN_CONN if a["id"] == connector_id), None)
    if not definition:
        return err("Connecteur introuvable", 404)
    ex = await db.admin_connections.find_one({"userId": me["id"], "connectorId": definition["id"]}, {"_id": 0})
    if ex:
        return ok({"connection": ex, "existing": True})
    conn = {"id": uid(), "userId": me["id"], "connectorId": definition["id"], "name": definition["name"],
            "pseudonym": "eidas-" + secrets.token_hex(3), "scopes": definition["scopes"],
            "sensitive": bool(definition.get("sensitive")), "data": ADMIN_DATA.get(definition["id"]) or [], "since": now()}
    await db.admin_connections.insert_one(dict(conn))
    conn.pop("_id", None)
    return ok({"connection": conn})


@router.post("/admin/connectors/{connector_id}/disconnect")
async def disconnect_connector(connector_id: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.admin_connections.delete_one({"userId": me["id"], "connectorId": connector_id})
    return ok({"ok": True})


@router.get("/admin/documents")
async def list_documents(me: dict = Depends(require_user)):
    db = get_db()
    count = await db.admin_documents.count_documents({"userId": me["id"]})
    if count == 0:
        await db.admin_documents.insert_many([
            {"id": uid(), "userId": me["id"], "title": "Avis d’imposition 2024", "category": "Impôts", "issuer": "DGFiP", "emoji": "🧾", "encrypted": True, "shared": False, "createdAt": now()},
            {"id": uid(), "userId": me["id"], "title": "Attestation carte Vitale", "category": "Santé", "issuer": "Ameli", "emoji": "⚕️", "encrypted": True, "shared": False, "createdAt": now()},
        ])
    docs = await db.admin_documents.find({"userId": me["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    return ok(docs)


@router.post("/admin/documents")
async def create_document(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    doc = {"id": uid(), "userId": me["id"], "title": body.get("title") or "Document", "category": body.get("category") or "Autre",
           "issuer": body.get("issuer") or "Moi", "emoji": body.get("emoji") or "📄", "encrypted": True, "shared": False, "createdAt": now()}
    await db.admin_documents.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)


@router.post("/admin/documents/{doc_id}/share")
async def share_document(doc_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    share_token = secrets.token_hex(4)
    expires_at = now() + timedelta(hours=body.get("hours") or 24)
    await db.admin_documents.update_one({"id": doc_id, "userId": me["id"]},
                                        {"$set": {"shared": True, "shareToken": share_token, "shareExpiresAt": expires_at}})
    return ok({"shared": True, "shareToken": share_token, "expiresAt": expires_at})


@router.post("/admin/documents/{doc_id}/unshare")
async def unshare_document(doc_id: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.admin_documents.update_one({"id": doc_id, "userId": me["id"]},
                                        {"$set": {"shared": False}, "$unset": {"shareToken": "", "shareExpiresAt": ""}})
    return ok({"shared": False})


@router.delete("/admin/documents/{doc_id}")
async def delete_document(doc_id: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.admin_documents.delete_one({"id": doc_id, "userId": me["id"]})
    return ok({"ok": True})


@router.get("/admin/accounting")
async def accounting(me: dict = Depends(require_user)):
    db = get_db()
    txs = await db.transactions.find({"userId": me["id"]}).to_list(length=None)
    income = expense = 0
    by_cat: dict = {}
    for t in txs:
        if t["amountCents"] > 0:
            income += t["amountCents"]
        else:
            expense += -t["amountCents"]
            by_cat[t["category"]] = (by_cat.get(t["category"]) or 0) + (-t["amountCents"])
    categories = sorted([{"name": n, "amountCents": a} for n, a in by_cat.items()], key=lambda c: c["amountCents"], reverse=True)[:6]
    return ok({"incomeCents": income, "expenseCents": expense, "netCents": income - expense, "categories": categories, "count": len(txs)})
