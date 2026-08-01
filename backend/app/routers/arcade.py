"""Arcade DIVARC — jeux de COMPÉTENCE (puits d'Éclats).

Garde-fous : AUCUN hasard à gains monétaires (pas de loot-box, pas de tirage payant).
La récompense est une fonction DÉTERMINISTE du score (donc du skill), affichée à l'avance.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from .. import eclats as ec
from ..config import settings
from ..db import get_db
from ..helpers import err, now, ok, today_str, uid
from ..security import require_user

router = APIRouter()

# Catalogue. `tiers` = paliers déterministes (scoreMin -> récompense en Éclats), transparents.
GAMES = {
    "reflex": {
        "id": "reflex", "name": "Reflex Or", "emoji": "⚡",
        "duration": 20, "maxScore": 60,
        "desc": "Touche un maximum d'éclairs en 20 secondes. Pur réflexe, aucun hasard.",
        "tiers": [(21, 20), (15, 12), (8, 6), (0, 0)],  # (scoreMin, récompense)
    },
    "memory": {
        "id": "memory", "name": "Mémoire Éclair", "emoji": "🧠",
        "duration": 0, "maxScore": 30,
        "desc": "Reproduis la séquence lumineuse la plus longue. Jeu de mémoire.",
        "tiers": [(12, 24), (8, 14), (5, 7), (0, 0)],
    },
}


def _reward_for(game: dict, score: int) -> int:
    for score_min, rew in game["tiers"]:
        if score >= score_min:
            return rew
    return 0


def _week_key() -> str:
    y, w, _ = now().isocalendar()
    return f"{y}-W{w:02d}"


def _public_game(g: dict) -> dict:
    return {"id": g["id"], "name": g["name"], "emoji": g["emoji"], "duration": g["duration"],
            "desc": g["desc"], "entryCost": settings.ARCADE_ENTRY, "freeDaily": settings.ARCADE_FREE_DAILY,
            "rewards": [{"scoreMin": s, "eclats": r} for s, r in g["tiers"] if r > 0]}


@router.get("/arcade")
async def arcade_home(me: dict = Depends(require_user)):
    db = get_db()
    bal = await ec.get_balance(db, me["id"])
    today = today_str()
    games = []
    for g in GAMES.values():
        best = await db.arcade_scores.find_one({"userId": me["id"], "game": g["id"]}, {"_id": 0}, sort=[("score", -1)])
        played_today = await db.arcade_sessions.count_documents({"userId": me["id"], "game": g["id"], "day": today})
        games.append({**_public_game(g), "myBest": (best or {}).get("score", 0),
                      "freeLeft": max(0, settings.ARCADE_FREE_DAILY - played_today)})
    return ok({"balance": bal, "games": games, "week": _week_key(),
               "notice": "Jeux de compétence : la récompense dépend UNIQUEMENT de ton score. Aucun hasard, aucune mise à gains."})


@router.post("/arcade/{game_id}/play")
async def arcade_play(game_id: str, me: dict = Depends(require_user)):
    db = get_db()
    g = GAMES.get(game_id)
    if not g:
        return err("Jeu introuvable", 404)
    today = today_str()
    played = await db.arcade_sessions.count_documents({"userId": me["id"], "game": game_id, "day": today})
    free = played < settings.ARCADE_FREE_DAILY
    cost = 0
    if not free:
        op = uid()
        spent = await ec.spend(db, me["id"], settings.ARCADE_ENTRY, "arcade_entry",
                               {"label": f"Partie {g['name']}", "game": game_id}, idem=f"arcade:{op}")
        if not spent.get("ok"):
            return err(spent.get("error") or "Solde d'Éclats insuffisant", 402)
        cost = settings.ARCADE_ENTRY
    sid = uid()
    await db.arcade_sessions.insert_one({"id": sid, "userId": me["id"], "game": game_id,
                                         "day": today, "cost": cost, "free": free, "scored": False, "createdAt": now()})
    return ok({"sessionId": sid, "free": free, "cost": cost, "duration": g["duration"], "maxScore": g["maxScore"]})


@router.post("/arcade/{game_id}/score")
async def arcade_score(game_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    g = GAMES.get(game_id)
    if not g:
        return err("Jeu introuvable", 404)
    body = await request.json() if await request.body() else {}
    sid = body.get("sessionId")
    sess = await db.arcade_sessions.find_one({"id": sid, "userId": me["id"], "game": game_id})
    if not sess:
        return err("Session invalide", 404)
    if sess.get("scored"):
        return err("Score déjà enregistré", 409)
    # bornage anti-triche basique
    try:
        score = max(0, min(int(body.get("score") or 0), g["maxScore"]))
    except (TypeError, ValueError):
        return err("Score invalide")
    reward = _reward_for(g, score)
    await db.arcade_sessions.update_one({"id": sid}, {"$set": {"scored": True}})
    await db.arcade_scores.insert_one({"id": uid(), "userId": me["id"], "game": game_id, "score": score,
                                       "reward": reward, "week": _week_key(), "createdAt": now()})
    if reward > 0:
        await ec.credit(db, me["id"], reward, "arcade_reward",
                        {"label": f"Récompense {g['name']} (score {score})", "game": game_id})
    best = await db.arcade_scores.find_one({"userId": me["id"], "game": game_id}, {"_id": 0}, sort=[("score", -1)])
    return ok({"score": score, "reward": reward, "myBest": (best or {}).get("score", score),
               "balance": await ec.get_balance(db, me["id"])})


@router.get("/arcade/{game_id}/leaderboard")
async def arcade_leaderboard(game_id: str, me: dict = Depends(require_user)):
    db = get_db()
    if game_id not in GAMES:
        return err("Jeu introuvable", 404)
    week = _week_key()
    rows = await db.arcade_scores.find({"game": game_id, "week": week}, {"_id": 0}).to_list(length=None)
    best_by_user: dict[str, int] = {}
    for r in rows:
        if r["score"] > best_by_user.get(r["userId"], -1):
            best_by_user[r["userId"]] = r["score"]
    ranked = sorted(best_by_user.items(), key=lambda kv: kv[1], reverse=True)[:20]
    out = []
    for i, (usr, score) in enumerate(ranked):
        u = await db.users.find_one({"id": usr}, {"_id": 0, "email": 0}) or {}
        out.append({"rank": i + 1, "userId": usr, "name": u.get("name"), "initials": u.get("initials"),
                    "avatarColor": u.get("avatarColor"), "score": score, "me": usr == me["id"]})
    return ok({"week": week, "leaderboard": out})
