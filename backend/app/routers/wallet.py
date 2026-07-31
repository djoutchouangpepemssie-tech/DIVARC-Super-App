"""Routes wallet : solde, transactions, contacts, coffres, envoi P2P, enveloppe (hongbao)."""
from __future__ import annotations

import random
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from ..db import get_db
from ..helpers import body_of, err, now, ok, post_ledger, uid
from ..seed import ensure_demo_users
from ..security import require_user

router = APIRouter()


@router.get("/wallet")
async def get_wallet(me: dict = Depends(require_user)):
    db = get_db()
    wallet = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    coffres = await db.coffres.find({"userId": me["id"]}, {"_id": 0}).to_list(length=None)
    return ok({**(wallet or {}), "coffres": coffres})


@router.get("/transactions")
async def get_transactions(me: dict = Depends(require_user)):
    db = get_db()
    txs = await db.transactions.find({"userId": me["id"]}, {"_id": 0}).sort("createdAt", -1).limit(100).to_list(length=100)
    return ok(txs)


@router.get("/contacts")
async def get_contacts(me: dict = Depends(require_user)):
    db = get_db()
    await ensure_demo_users(db)
    users = await db.users.find({"id": {"$ne": me["id"]}}, {"_id": 0, "email": 0}).limit(20).to_list(length=20)
    return ok([{**u, "color": u.get("avatarColor")} for u in users])


@router.post("/coffres")
async def create_coffre(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    coffre = {
        "id": uid(), "userId": me["id"], "name": body.get("name") or "Nouveau coffre",
        "emoji": body.get("emoji") or "🎯", "balanceCents": body.get("balanceCents") or 0,
        "goalCents": body.get("goalCents") or 100000, "rule": body.get("rule") or "round_up",
        "color": body.get("color") or "#4353F0", "createdAt": now(),
    }
    await db.coffres.insert_one(dict(coffre))
    coffre.pop("_id", None)
    return ok(coffre)


@router.post("/send")
async def send_money(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    to_handle = body.get("toHandle")
    to_name = body.get("toName")
    amount_cents = body.get("amountCents")
    pay_route = body.get("route")
    if not amount_cents or amount_cents <= 0:
        return err("Montant invalide")
    idem = body.get("idempotencyKey") or uid()
    dup = await db.transactions.find_one({"idempotencyKey": idem, "userId": me["id"]}, {"_id": 0})
    if dup:
        return ok({"transaction": dup, "idempotent": True})
    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < amount_cents:
        return err("Solde insuffisant", 402)
    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -amount_cents}})
    batch = await post_ledger(db, [
        {"account": f"user:{me['id']}", "direction": "debit", "amountCents": amount_cents},
        {"account": f"user:{to_handle or 'external'}", "direction": "credit", "amountCents": amount_cents},
    ])
    tx = {
        "id": uid(), "userId": me["id"], "label": f"Envoyé à {to_name or to_handle or 'un ami'}", "category": "P2P",
        "amountCents": -abs(amount_cents), "carbonKg": 0, "icon": "⚡", "route": pay_route or "A2A",
        "idempotencyKey": idem, "ledgerBatch": batch, "status": "settled", "createdAt": now(),
    }
    await db.transactions.insert_one(dict(tx))
    updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    tx.pop("_id", None)
    return ok({"transaction": tx, "balanceCents": updated["balanceCents"]})


@router.post("/enveloppe/create")
async def enveloppe_create(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    total_cents = body.get("totalCents")
    count = max(1, min(body.get("count") or 1, 20))
    if not total_cents or total_cents <= 0:
        return err("Montant invalide")
    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < total_cents:
        return err("Solde insuffisant", 402)
    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -total_cents}})
    remaining = total_cents
    left = count
    shares: list[int] = []
    for i in range(count):
        if i == count - 1:
            shares.append(remaining)
            break
        mx = (remaining // left) * 2
        amt = max(1, random.randint(0, max(0, mx - 2)) + 1)
        shares.append(amt)
        remaining -= amt
        left -= 1
    for i in range(len(shares) - 1, 0, -1):
        j = random.randint(0, i)
        shares[i], shares[j] = shares[j], shares[i]
    env = {
        "id": uid(), "userId": me["id"], "message": body.get("message") or "Bonne chance ! 🧧",
        "totalCents": total_cents, "count": count,
        "shares": [{"id": uid(), "amountCents": amt, "claimedBy": None, "claimedAt": None} for amt in shares],
        "theme": body.get("theme") or "gold", "expiresAt": now() + timedelta(hours=24), "createdAt": now(),
    }
    await db.enveloppes.insert_one(dict(env))
    await db.transactions.insert_one({
        "id": uid(), "userId": me["id"], "label": f"Enveloppe ({count} part{'s' if count > 1 else ''})",
        "category": "Enveloppe", "amountCents": -total_cents, "carbonKg": 0, "icon": "🧧", "route": None, "createdAt": now(),
    })
    updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    env.pop("_id", None)
    return ok({"enveloppe": env, "balanceCents": updated["balanceCents"]})


@router.post("/enveloppe/open")
async def enveloppe_open(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    env = await db.enveloppes.find_one({"id": body.get("enveloppeId")})
    if not env:
        return err("Enveloppe introuvable", 404)
    claimer = body.get("claimer") or me["id"]
    already = next((s for s in env["shares"] if s["claimedBy"] == claimer), None)
    if already:
        return ok({"amountCents": already["amountCents"], "alreadyClaimed": True, "message": env["message"]})
    free = next((s for s in env["shares"] if not s["claimedBy"]), None)
    if not free:
        return err("Toutes les parts ont été réclamées", 410)
    free["claimedBy"] = claimer
    free["claimedAt"] = now()
    await db.enveloppes.update_one({"id": env["id"]}, {"$set": {"shares": env["shares"]}})
    remaining = len([s for s in env["shares"] if not s["claimedBy"]])
    return ok({"amountCents": free["amountCents"], "message": env["message"], "remaining": remaining, "total": env["count"]})
