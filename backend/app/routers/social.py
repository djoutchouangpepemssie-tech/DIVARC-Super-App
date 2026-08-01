"""Routes DIVARC Social : feed personnalisé, posts, likes, commentaires, follow, achat/pourboire."""
from __future__ import annotations

import random
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from .. import eclats as ec
from ..config import settings
from ..db import get_db
from ..helpers import body_of, credit_wallet, err, get_sponsored, inject_ads, now, ok, post_ledger, uid
from ..notify import notify
from ..seed import ensure_social_seed
from ..security import require_user

router = APIRouter()


@router.get("/social/feed")
async def social_feed(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    await ensure_social_seed(db)
    mode = request.query_params.get("mode") or "foryou"
    scope = request.query_params.get("scope") or "all"
    interests = ((await db.interests.find_one({"userId": me["id"]})) or {}).get("topics") or []
    follows = [f["authorId"] for f in await db.follows.find({"followerId": me["id"]}).to_list(length=None)]
    liked = {x["postId"] for x in await db.post_likes.find({"userId": me["id"]}).to_list(length=None)}
    saved = {x["postId"] for x in await db.post_saves.find({"userId": me["id"]}).to_list(length=None)}
    ni = {x["postId"] for x in await db.social_events.find({"userId": me["id"], "type": "notinterested"}).to_list(length=None)}
    posts = await db.posts.find({}, {"_id": 0}).to_list(length=None)
    posts = [p for p in posts if p["id"] not in ni]
    if scope == "following":
        posts = [p for p in posts if p["authorId"] in follows]

    authors: dict = {}
    for p in posts:
        if p["authorId"] not in authors:
            authors[p["authorId"]] = await db.users.find_one({"id": p["authorId"]}, {"_id": 0, "email": 0})

    now_ts = now().timestamp() * 1000
    scored = []
    for p in posts:
        age_h = (now_ts - p["createdAt"].timestamp() * 1000) / 3600000
        freshness = max(0, 1 - age_h / 72)
        eng = ((p.get("likes") or 0) + (p.get("comments") or 0) * 2 + (p.get("saves") or 0) * 1.5) / ((p.get("views") or 0) + 12)
        tag_match = len([h for h in (p.get("hashtags") or []) if h in interests])
        interest_match = min(1, tag_match / 1) if interests else 0
        follow_boost = 1 if p["authorId"] in follows else 0
        explore = random.random() * 0.3
        matched_tag = next((h for h in (p.get("hashtags") or []) if h in interests), "")
        factors = {
            "Tu suis ce créateur": 2 * follow_boost,
            f"Basé sur ton intérêt {matched_tag}": 2.5 * interest_match,
            "Populaire en ce moment": 3 * eng,
            "Fraîchement publié": 1.8 * freshness,
            "Une découverte pour toi": explore,
        }
        score = sum(factors.values())
        reason = sorted(factors.items(), key=lambda kv: kv[1], reverse=True)[0][0]
        scored.append({**p, "score": score, "reason": reason})

    if mode == "chrono":
        scored.sort(key=lambda p: p["createdAt"], reverse=True)
    else:
        scored.sort(key=lambda p: p["score"], reverse=True)
    # Posts boostés (Éclats) en tête (tri stable)
    _t = now()
    scored.sort(key=lambda p: 0 if (p.get("boostedUntil") and p["boostedUntil"] > _t) else 1)

    out = []
    for p in scored:
        a = authors.get(p["authorId"])
        out.append({
            "id": p["id"], "caption": p["caption"], "mediaUrl": p["mediaUrl"], "mediaType": p["mediaType"], "poster": p.get("poster"),
            "hashtags": p["hashtags"], "likes": p["likes"], "comments": p["comments"], "saves": p["saves"], "views": p["views"],
            "product": p.get("product"), "aiGenerated": bool(p.get("aiGenerated")),
            "author": ({"id": a["id"], "name": a["name"], "handle": a["handle"], "initials": a["initials"],
                        "avatarColor": a["avatarColor"], "verified": a["verified"]} if a else None),
            "liked": p["id"] in liked, "saved": p["id"] in saved, "following": p["authorId"] in follows,
            "reason": "Ordre chronologique" if mode == "chrono" else p["reason"], "createdAt": p["createdAt"],
        })
    sponsored = [] if mode == "chrono" else await get_sponsored(db)
    return ok(inject_ads(out, sponsored))


@router.post("/social/posts")
async def create_post(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    post = {
        "id": uid(), "authorId": me["id"], "caption": body.get("caption") or "", "mediaUrl": body.get("mediaUrl"),
        "mediaType": body.get("mediaType") or "video", "poster": body.get("poster"),
        "hashtags": [(h if h.startswith("#") else "#" + h) for h in (body.get("hashtags") or [])],
        "product": body.get("product"), "aiGenerated": bool(body.get("aiGenerated")),
        "likes": 0, "comments": 0, "saves": 0, "views": 0, "earningsCents": 0, "createdAt": now(),
    }
    await db.posts.insert_one(dict(post))
    post.pop("_id", None)
    return ok(post)


@router.post("/social/posts/{pid}/like")
async def like_post(pid: str, me: dict = Depends(require_user)):
    db = get_db()
    ex = await db.post_likes.find_one({"postId": pid, "userId": me["id"]})
    if ex:
        await db.post_likes.delete_one({"postId": pid, "userId": me["id"]})
        await db.posts.update_one({"id": pid}, {"$inc": {"likes": -1}})
    else:
        await db.post_likes.insert_one({"postId": pid, "userId": me["id"], "createdAt": now()})
        await db.posts.update_one({"id": pid}, {"$inc": {"likes": 1}})
    p = await db.posts.find_one({"id": pid})
    return ok({"liked": not ex, "likes": p["likes"]})


@router.post("/social/posts/{pid}/save")
async def save_post(pid: str, me: dict = Depends(require_user)):
    db = get_db()
    ex = await db.post_saves.find_one({"postId": pid, "userId": me["id"]})
    if ex:
        await db.post_saves.delete_one({"postId": pid, "userId": me["id"]})
        await db.posts.update_one({"id": pid}, {"$inc": {"saves": -1}})
    else:
        await db.post_saves.insert_one({"postId": pid, "userId": me["id"], "createdAt": now()})
        await db.posts.update_one({"id": pid}, {"$inc": {"saves": 1}})
    p = await db.posts.find_one({"id": pid})
    return ok({"saved": not ex, "saves": p["saves"]})


@router.post("/social/posts/{pid}/notinterested")
async def not_interested(pid: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.social_events.insert_one({"userId": me["id"], "postId": pid, "type": "notinterested", "createdAt": now()})
    return ok({"ok": True})


@router.post("/social/posts/{pid}/view")
async def view_post(pid: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.posts.update_one({"id": pid}, {"$inc": {"views": 1}})
    return ok({"ok": True})


@router.get("/social/posts/{pid}/comments")
async def get_comments(pid: str, me: dict = Depends(require_user)):
    db = get_db()
    comments = await db.comments.find({"postId": pid}, {"_id": 0}).sort("createdAt", -1).limit(100).to_list(length=100)
    return ok(comments)


@router.post("/social/posts/{pid}/comments")
async def add_comment(pid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    text = str(body.get("text") or "").strip()
    if not text:
        return err("Commentaire vide")
    c = {"id": uid(), "postId": pid, "userId": me["id"], "name": me.get("name"), "initials": me.get("initials"),
         "avatarColor": me.get("avatarColor"), "text": text, "createdAt": now()}
    await db.comments.insert_one(dict(c))
    await db.posts.update_one({"id": pid}, {"$inc": {"comments": 1}})
    c.pop("_id", None)
    return ok(c)


@router.post("/social/follow/{author_id}")
async def follow(author_id: str, me: dict = Depends(require_user)):
    db = get_db()
    ex = await db.follows.find_one({"followerId": me["id"], "authorId": author_id})
    if ex:
        await db.follows.delete_one({"followerId": me["id"], "authorId": author_id})
    else:
        await db.follows.insert_one({"followerId": me["id"], "authorId": author_id, "createdAt": now()})
    return ok({"following": not ex})


@router.post("/social/posts/{pid}/buy")
@router.post("/social/posts/{pid}/tip")
async def buy_or_tip(pid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    is_tip = request.url.path.endswith("/tip")
    body = await body_of(request)
    post = await db.posts.find_one({"id": pid})
    if not post:
        return err("Publication introuvable", 404)
    amount = int(body.get("amountCents") or 0) if is_tip else ((post.get("product") or {}).get("priceCents") or 0)
    if not amount or amount <= 0:
        return err("Montant invalide")
    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < amount:
        return err("Solde insuffisant", 402)
    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -amount}})
    await credit_wallet(db, post["authorId"], amount)
    inc = {"earningsCents": amount} if is_tip else {"earningsCents": amount, "sales": 1}
    await db.posts.update_one({"id": pid}, {"$inc": inc})
    author = await db.users.find_one({"id": post["authorId"]})
    label = f"Pourboire à {(author or {}).get('name') or 'créateur'}" if is_tip else f"Achat : {(post.get('product') or {}).get('title') or 'article'}"
    await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": label, "category": "Social",
                                      "amountCents": -amount, "carbonKg": 0, "icon": "💛" if is_tip else "🛍️",
                                      "route": None, "createdAt": now()})
    await post_ledger(db, [{"account": f"user:{me['id']}", "direction": "debit", "amountCents": amount},
                           {"account": f"user:{post['authorId']}", "direction": "credit", "amountCents": amount}])
    await notify(db, post["authorId"], "social",
                 "💛 Pourboire reçu" if is_tip else "🛍️ Vente sur ta publication",
                 f"{amount / 100:.2f} € de {me.get('name')}", {"postId": pid})
    updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    return ok({"ok": True, "balanceCents": updated["balanceCents"], "amountCents": amount})


@router.post("/social/posts/{pid}/boost")
async def boost_post(pid: str, me: dict = Depends(require_user)):
    """Booster sa publication (mise en avant dans le fil) — payé en Éclats (puits)."""
    db = get_db()
    post = await db.posts.find_one({"id": pid})
    if not post:
        return err("Publication introuvable", 404)
    if post["authorId"] != me["id"]:
        return err("Seul l'auteur peut booster sa publication", 403)
    cost = settings.ECLATS_BOOST_POST
    op = uid()
    spent = await ec.spend(db, me["id"], cost, "boost_post",
                           {"label": "Boost de publication", "postId": pid}, idem=f"boostpost:{op}")
    if not spent.get("ok"):
        return err(spent.get("error") or "Solde d'Éclats insuffisant", 402)
    until = now() + timedelta(hours=settings.ECLATS_BOOST_HOURS)
    await db.posts.update_one({"id": pid}, {"$set": {"boostedUntil": until}})
    return ok({"ok": True, "boostedUntil": until, "cost": cost, "eclatsBalance": spent.get("balance")})


@router.post("/social/interests")
async def set_interests(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    topics = body.get("topics") or []
    await db.interests.update_one({"userId": me["id"]}, {"$set": {"userId": me["id"], "topics": topics}}, upsert=True)
    return ok({"ok": True, "topics": topics})


@router.get("/social/creator")
async def creator_dashboard(me: dict = Depends(require_user)):
    db = get_db()
    posts = await db.posts.find({"authorId": me["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    followers = await db.follows.count_documents({"authorId": me["id"]})
    earnings = sum(p.get("earningsCents") or 0 for p in posts)
    views = sum(p.get("views") or 0 for p in posts)
    likes = sum(p.get("likes") or 0 for p in posts)
    return ok({"posts": posts, "followers": followers, "earningsCents": earnings, "views": views, "likes": likes})
