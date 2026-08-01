"""Routes DIVARC+ (abonnement) : statut, essai gratuit, abonnement, résiliation."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import settings
from ..db import get_db
from ..helpers import err, is_plus, now, ok, post_ledger, uid
from ..plus import activate_period
from ..security import require_user

router = APIRouter()

PERKS = [
    "Likes illimités dans Rencontres",
    "« Qui t'a liké » inclus (révélations gratuites)",
    "Mode incognito",
    f"{settings.PLUS_MONTHLY_ECLATS} Éclats offerts chaque mois",
    f"Cashback ×{settings.PLUS_CASHBACK_MULT} sur tes achats",
    "Navigation sans publicité",
]


def _state(me: dict) -> dict:
    return {
        "active": is_plus(me),
        "until": me.get("plusUntil"),
        "trialUsed": bool(me.get("plusTrialUsed")),
        "autoRenew": bool(me.get("plusAutoRenew")) and is_plus(me),
        "priceCents": settings.PLUS_PRICE_CENTS,
        "trialDays": settings.PLUS_TRIAL_DAYS,
        "monthlyEclats": settings.PLUS_MONTHLY_ECLATS,
        "perks": PERKS,
    }


@router.get("/plus")
async def plus_status(me: dict = Depends(require_user)):
    return ok(_state(me))


@router.post("/plus/trial")
async def plus_trial(me: dict = Depends(require_user)):
    db = get_db()
    if me.get("plusTrialUsed"):
        return err("Essai gratuit déjà utilisé", 409)
    if is_plus(me):
        return err("Tu es déjà abonné DIVARC+", 409)
    await db.users.update_one({"id": me["id"]}, {"$set": {"plusTrialUsed": True}})
    until = await activate_period(db, me["id"], settings.PLUS_TRIAL_DAYS, reason="plus_trial")
    fresh = await db.users.find_one({"id": me["id"]}, {"_id": 0})
    return ok({"ok": True, "until": until, **_state(fresh)})


@router.post("/plus/subscribe")
async def plus_subscribe(me: dict = Depends(require_user)):
    """Active un mois de DIVARC+ en débitant le wallet € (prêt à basculer sur un PSP réel)."""
    db = get_db()
    price = settings.PLUS_PRICE_CENTS
    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < price:
        return err("Solde insuffisant pour l'abonnement (recharge à venir)", 402)
    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -price}})
    await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": "Abonnement DIVARC+",
                                      "category": "Abonnement", "amountCents": -price, "carbonKg": 0,
                                      "icon": "⭐", "route": None, "createdAt": now()})
    await post_ledger(db, [{"account": f"user:{me['id']}", "direction": "debit", "amountCents": price},
                           {"account": "divarc:plus", "direction": "credit", "amountCents": price}])
    until = await activate_period(db, me["id"], settings.PLUS_PERIOD_DAYS, reason="plus_sub")
    fresh = await db.users.find_one({"id": me["id"]}, {"_id": 0})
    return ok({"ok": True, "until": until, **_state(fresh)})


@router.post("/plus/cancel")
async def plus_cancel(me: dict = Depends(require_user)):
    """Résiliation en un tap : stoppe le renouvellement, garde l'accès jusqu'à l'échéance."""
    db = get_db()
    await db.users.update_one({"id": me["id"]}, {"$set": {"plusAutoRenew": False}})
    fresh = await db.users.find_one({"id": me["id"]}, {"_id": 0})
    return ok({"ok": True, **_state(fresh)})
