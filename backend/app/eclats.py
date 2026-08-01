"""Économie « Éclats » — monnaie interne DIVARC.

Règles gravées :
- Ledger 100 % SÉPARÉ du wallet € (collections `eclats_wallets` / `eclats_ledger`).
- SENS UNIQUE : on gagne/achète des Éclats, on les dépense dans l'app.
  JAMAIS reconvertibles en euros, jamais retirables, jamais remboursables.
- Aucune valeur monétaire. Aucun hasard à gains monétaires (pas de loot-box).
"""
from __future__ import annotations

from .config import settings
from .helpers import now, today_str, uid, yesterday_str

DISCLAIMER = ("Les Éclats sont une monnaie interne à DIVARC, sans valeur monétaire. "
              "Ils ne sont ni retirables, ni remboursables, ni convertibles en argent.")


async def _wallet(db, user_id: str) -> dict:
    w = await db.eclats_wallets.find_one({"userId": user_id}, {"_id": 0})
    if not w:
        w = {"id": uid(), "userId": user_id, "balance": 0,
             "lastCheckin": None, "checkinStreak": 0, "createdAt": now()}
        await db.eclats_wallets.insert_one(dict(w))
        w.pop("_id", None)
    return w


async def get_balance(db, user_id: str) -> int:
    return (await _wallet(db, user_id)).get("balance", 0)


async def _apply(db, user_id: str, delta: int, reason: str, meta: dict | None = None,
                 idem: str | None = None) -> dict:
    """Applique un mouvement (partie double) de façon idempotente. delta > 0 = gain, < 0 = dépense."""
    # Idempotence : un même idem ne s'applique qu'une fois
    if idem:
        existing = await db.eclats_ledger.find_one({"userId": user_id, "idempotencyKey": idem})
        if existing:
            return {"ok": True, "duplicate": True, "balance": (await _wallet(db, user_id))["balance"]}
    w = await _wallet(db, user_id)
    bal = w.get("balance", 0)
    if delta < 0 and bal + delta < 0:
        return {"ok": False, "error": "Solde d'Éclats insuffisant", "balance": bal}
    new_bal = bal + delta
    entry = {"id": uid(), "userId": user_id, "delta": delta, "reason": reason,
             "balanceAfter": new_bal, "meta": meta or {}, "createdAt": now()}
    if idem:
        entry["idempotencyKey"] = idem
    await db.eclats_ledger.insert_one(dict(entry))
    await db.eclats_wallets.update_one({"userId": user_id}, {"$set": {"balance": new_bal}})
    entry.pop("_id", None)
    return {"ok": True, "balance": new_bal, "entry": entry}


async def credit(db, user_id: str, amount: int, reason: str, meta: dict | None = None,
                 idem: str | None = None) -> dict:
    if amount <= 0:
        return {"ok": False, "error": "Montant invalide"}
    return await _apply(db, user_id, amount, reason, meta, idem)


async def spend(db, user_id: str, amount: int, reason: str, meta: dict | None = None,
                idem: str | None = None) -> dict:
    if amount <= 0:
        return {"ok": False, "error": "Montant invalide"}
    return await _apply(db, user_id, -amount, reason, meta, idem)


async def grant_welcome(db, user_id: str) -> None:
    """Cadeau de bienvenue (une seule fois par utilisateur)."""
    if settings.ECLATS_WELCOME > 0:
        await credit(db, user_id, settings.ECLATS_WELCOME, "welcome",
                     {"label": "Cadeau de bienvenue 🎁"}, idem=f"welcome:{user_id}")


async def cashback(db, user_id: str, amount_cents: int, meta: dict | None = None,
                   idem: str | None = None) -> int:
    """Cashback en Éclats sur un vrai achat (×PLUS_CASHBACK_MULT pour les abonnés DIVARC+)."""
    from .helpers import is_plus
    user = await db.users.find_one({"id": user_id})
    mult = settings.PLUS_CASHBACK_MULT if is_plus(user) else 1
    pts = (amount_cents * settings.ECLATS_CASHBACK_BPS * mult) // 10000
    if pts > 0:
        await credit(db, user_id, pts, "cashback", {**(meta or {}), "label": "Cashback achat"}, idem=idem)
    return pts


async def checkin(db, user_id: str) -> dict:
    """Check-in quotidien : +Éclats de base + bonus de série. Une fois par jour."""
    w = await _wallet(db, user_id)
    today = today_str()
    if w.get("lastCheckin") == today:
        return {"ok": False, "error": "Déjà validé aujourd'hui", "balance": w["balance"],
                "streak": w.get("checkinStreak", 0)}
    streak = w.get("checkinStreak", 0)
    streak = streak + 1 if w.get("lastCheckin") == yesterday_str() else 1
    bonus = min(max(streak - 1, 0), settings.ECLATS_DAILY_STREAK_MAX)
    reward = settings.ECLATS_DAILY + bonus
    await db.eclats_wallets.update_one({"userId": user_id},
                                       {"$set": {"lastCheckin": today, "checkinStreak": streak}})
    res = await credit(db, user_id, reward, "checkin",
                       {"label": f"Check-in quotidien (série {streak})", "streak": streak},
                       idem=f"checkin:{user_id}:{today}")
    return {"ok": True, "reward": reward, "streak": streak, "balance": res.get("balance", w["balance"])}
