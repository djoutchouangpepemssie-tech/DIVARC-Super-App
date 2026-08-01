"""DIVARC+ — abonnement récurrent. Entitlement + octroi d'Éclats mensuels.

Facturation récurrente réelle = à brancher sur un PSP (Stripe/SEPA). Pour l'instant :
essai gratuit (1×) + activation période via le solde du wallet € (prêt PSP).
"""
from __future__ import annotations

from datetime import timedelta

from . import eclats as ec
from .config import settings
from .helpers import now


async def activate_period(db, user_id: str, days: int, reason: str = "plus") -> "datetime":
    """Étend DIVARC+ de `days` (cumulatif s'il est déjà actif) + Éclats de la période."""
    user = await db.users.find_one({"id": user_id})
    base = (user or {}).get("plusUntil")
    start = base if (base and base > now()) else now()
    until = start + timedelta(days=days)
    await db.users.update_one({"id": user_id}, {"$set": {
        "plusUntil": until, "plusAutoRenew": True,
        "plusSince": (user or {}).get("plusSince") or now(),
    }})
    if settings.PLUS_MONTHLY_ECLATS > 0:
        await ec.credit(db, user_id, settings.PLUS_MONTHLY_ECLATS, reason,
                        {"label": "DIVARC+ · Éclats du mois"})
    return until
