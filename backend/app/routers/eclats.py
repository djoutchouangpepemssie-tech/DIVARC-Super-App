"""Routes de l'économie Éclats (monnaie interne, sens unique, sans valeur monétaire)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from .. import eclats as ec
from ..config import settings
from ..db import get_db
from ..helpers import body_of, err, now, ok, today_str, uid
from ..notify import notify
from ..security import require_user

router = APIRouter()


@router.get("/eclats")
async def eclats_state(me: dict = Depends(require_user)):
    db = get_db()
    w = await ec._wallet(db, me["id"])
    history = await db.eclats_ledger.find({"userId": me["id"]}, {"_id": 0}) \
        .sort("createdAt", -1).limit(50).to_list(length=50)
    return ok({
        "balance": w.get("balance", 0),
        "streak": w.get("checkinStreak", 0),
        "canCheckin": w.get("lastCheckin") != today_str(),
        "history": history,
        "rates": {"daily": settings.ECLATS_DAILY, "referral": settings.ECLATS_REFERRAL,
                  "cashbackBps": settings.ECLATS_CASHBACK_BPS},
        "disclaimer": ec.DISCLAIMER,
    })


@router.post("/eclats/checkin")
async def eclats_checkin(me: dict = Depends(require_user)):
    db = get_db()
    r = await ec.checkin(db, me["id"])
    if not r.get("ok"):
        return err(r.get("error") or "Impossible", 409)
    return ok(r)


@router.post("/eclats/gift")
async def eclats_gift(request: Request, me: dict = Depends(require_user)):
    """Offrir des Éclats à un contact (puits social). Débité chez moi, crédité chez lui."""
    db = get_db()
    body = await body_of(request)
    try:
        amount = int(body.get("amount") or 0)
    except (TypeError, ValueError):
        return err("Montant invalide")
    if amount <= 0:
        return err("Montant invalide")

    # Destinataire par id ou @handle
    target = None
    if body.get("toId"):
        target = await db.users.find_one({"id": body["toId"]})
    elif body.get("toHandle"):
        h = body["toHandle"]
        target = await db.users.find_one({"handle": h if h.startswith("@") else "@" + h})
    if not target:
        return err("Destinataire introuvable", 404)
    if target["id"] == me["id"]:
        return err("Impossible de s'offrir des Éclats à soi-même")

    # Débit puis crédit (idempotent sur un jeton unique de l'opération)
    op = uid()
    deb = await ec.spend(db, me["id"], amount, "gift_out",
                         {"label": f"Cadeau à {target.get('name')}", "toId": target["id"]}, idem=f"gift:{op}:out")
    if not deb.get("ok"):
        return err(deb.get("error") or "Solde insuffisant", 400)
    await ec.credit(db, target["id"], amount, "gift_in",
                    {"label": f"Cadeau de {me.get('name')}", "fromId": me["id"]}, idem=f"gift:{op}:in")
    await notify(db, target["id"], "system", "⚡ Tu as reçu des Éclats",
                 f"{me.get('name')} t'a offert {amount} Éclats", {})
    return ok({"ok": True, "balance": deb.get("balance"), "amount": amount, "to": target.get("name")})
