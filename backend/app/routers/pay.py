"""Paiement par QR : demandes de paiement, génération du QR, règlement avec flux d'argent réel."""
from __future__ import annotations

import random
import string
from datetime import timedelta

import segno
from fastapi import APIRouter, Depends, Request

from ..config import settings
from ..db import get_db
from ..helpers import body_of, credit_wallet, err, now, ok, post_ledger, uid
from ..notify import notify
from ..security import require_user

router = APIRouter()

# Caractères sans ambiguïté visuelle (pas de O/0/I/1) pour faciliter la saisie manuelle
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gen_code(n: int = 8) -> str:
    return "".join(random.choices(_ALPHABET, k=n))


@router.post("/pay/qr/create")
async def qr_create(request: Request, me: dict = Depends(require_user)):
    """Crée une demande de paiement (montant optionnel) et renvoie le QR + le code."""
    db = get_db()
    body = await body_of(request)
    amount = body.get("amountCents")
    amount = round(amount) if amount else None
    if amount is not None and amount <= 0:
        amount = None

    code = _gen_code()
    while await db.payment_requests.find_one({"code": code}):
        code = _gen_code()

    pr = {
        "id": uid(), "code": code, "payeeId": me["id"], "payeeName": me.get("name"),
        "payeeHandle": me.get("handle"), "payeeColor": me.get("avatarColor"),
        "amountCents": amount, "note": body.get("note") or "", "status": "pending",
        "payerId": None, "payerName": None, "paidAt": None,
        "createdAt": now(), "expiresAt": now() + timedelta(hours=24),
    }
    await db.payment_requests.insert_one(dict(pr))

    # Le QR encode une URL de paiement : scanné par l'appareil photo, il ouvre l'app pré-remplie.
    base = (settings.APP_URL or "").rstrip("/")
    pay_url = f"{base}/?pay={code}" if base else code
    qr = segno.make(pay_url, error="m")
    data_uri = qr.svg_data_uri(scale=6, dark="#2C39C7", light=None, border=2)
    return ok({"code": code, "amountCents": amount, "note": pr["note"], "qr": data_uri,
               "payUrl": pay_url, "expiresAt": pr["expiresAt"]})


@router.get("/pay/qr/{code}")
async def qr_get(code: str, me: dict = Depends(require_user)):
    """Détails d'une demande de paiement (affichés au payeur avant de confirmer)."""
    db = get_db()
    pr = await db.payment_requests.find_one({"code": code.strip().upper()}, {"_id": 0})
    if not pr:
        return err("Demande introuvable", 404)
    return ok({
        "code": pr["code"], "amountCents": pr["amountCents"], "note": pr["note"], "status": pr["status"],
        "payee": {"id": pr["payeeId"], "name": pr["payeeName"], "handle": pr["payeeHandle"], "color": pr.get("payeeColor")},
        "isMine": pr["payeeId"] == me["id"],
    })


@router.post("/pay/qr/{code}/pay")
async def qr_pay(code: str, request: Request, me: dict = Depends(require_user)):
    """Règle une demande de paiement : débit du payeur, crédit du bénéficiaire (idempotent par code)."""
    db = get_db()
    body = await body_of(request)
    pr = await db.payment_requests.find_one({"code": code.strip().upper()})
    if not pr:
        return err("Demande introuvable", 404)
    if pr["status"] == "paid":
        return err("Cette demande a déjà été réglée", 409)
    if pr["status"] != "pending" or pr["expiresAt"] < now():
        await db.payment_requests.update_one({"code": pr["code"]}, {"$set": {"status": "expired"}})
        return err("Demande expirée", 410)
    if pr["payeeId"] == me["id"]:
        return err("Tu ne peux pas payer ta propre demande")

    amount = pr["amountCents"] or round(body.get("amountCents") or 0)
    if not amount or amount <= 0:
        return err("Montant invalide")

    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < amount:
        return err("Solde insuffisant", 402)

    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -amount}})
    await credit_wallet(db, pr["payeeId"], amount)
    batch = await post_ledger(db, [
        {"account": f"user:{me['id']}", "direction": "debit", "amountCents": amount},
        {"account": f"user:{pr['payeeId']}", "direction": "credit", "amountCents": amount},
    ])
    await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Paiement QR à {pr['payeeName']}",
                                      "category": "QR", "amountCents": -amount, "carbonKg": 0, "icon": "📲",
                                      "route": "QR", "ledgerBatch": batch, "status": "settled", "createdAt": now()})
    await db.transactions.insert_one({"id": uid(), "userId": pr["payeeId"], "label": f"Paiement QR de {me.get('name')}",
                                      "category": "QR", "amountCents": amount, "carbonKg": 0, "icon": "📲",
                                      "route": "QR", "ledgerBatch": batch, "status": "settled", "createdAt": now()})
    await db.payment_requests.update_one({"code": pr["code"]}, {"$set": {
        "status": "paid", "payerId": me["id"], "payerName": me.get("name"), "paidAt": now()}})
    await notify(db, pr["payeeId"], "payment", "📲 Paiement reçu", f"{amount / 100:.2f} € de {me.get('name')}", {"code": pr["code"]})

    updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    return ok({"ok": True, "amountCents": amount, "balanceCents": updated["balanceCents"], "payee": pr["payeeName"]})
