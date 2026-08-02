"""API REST du contexte social — Couches 2 & 3.

Publier & voir (posts, feed curseur) + Interagir (réactions, commentaires imbriqués,
partages, bookmarks) + temps réel (WS manager existant). Autorisation = PolicyService.
"""
from __future__ import annotations

import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from ... import eclats
from ...config import settings
from ...db import get_db as get_mongo
from ...helpers import err, ok, today_str
from ...realtime import manager
from ...security import require_user
from ..adapters.persistence.uow import SqlAlchemyUnitOfWork
from ..application import discovery as disc
from ..application import events as ev
from ..application import fanout as fo
from ..application import graph as gr
from ..application import groups as grp
from ..application import interactions as ix
from ..application import moderation as mod
from ..application import pages as pg_uc
from ..application import posts as uc
from ..application import privacy as rgpd
from ..application import stories as st
from ..domain.policy import PolicyService

router = APIRouter()
_policy = PolicyService()


def _is_moderator(me: dict) -> bool:
    return (me.get("email") or "").strip().lower() in settings.admin_emails_set


async def require_moderator(me: dict = Depends(require_user)) -> dict:
    if not _is_moderator(me):
        raise HTTPException(status_code=403, detail="Accès modération réservé")
    return me


async def get_uow():
    if not settings.social_enabled:
        raise HTTPException(status_code=503, detail="Réseau social pas encore activé (PostgreSQL requis)")
    async with SqlAlchemyUnitOfWork() as uow:
        yield uow


@router.get("/net/health")
async def net_health():
    """Diagnostic public : la base social est-elle configurée et joignable ?"""
    if not settings.social_enabled:
        return {"configured": False, "reachable": False,
                "detail": "Aucune base PostgreSQL configurée (SOCIAL_DATABASE_URL ou DATABASE_URL)."}
    from sqlalchemy import text
    from ..adapters.persistence.db import get_sessionmaker
    try:
        sm = get_sessionmaker()
        async with sm() as s:
            await s.execute(text("SELECT 1"))
        return {"configured": True, "reachable": True, "driver": settings.social_db_url.split("://", 1)[0]}
    except Exception as e:  # noqa: BLE001
        return {"configured": True, "reachable": False, "detail": str(e)[:300]}


# ---------- curseur ----------
def _encode_cursor(p) -> str:
    return base64.urlsafe_b64encode(f"{p.created_at.isoformat()}|{p.id}".encode()).decode()


def _decode_cursor(cur: str):
    try:
        ts, pid = base64.urlsafe_b64decode(cur.encode()).decode().split("|", 1)
        return datetime.fromisoformat(ts), pid
    except Exception:  # noqa: BLE001
        return None, None


# ---------- sérialisation ----------
async def _authors_map(mongo, ids) -> dict:
    ids = [i for i in ids if i]
    if not ids:
        return {}
    users = await mongo.users.find({"id": {"$in": ids}}, {"_id": 0, "email": 0}).to_list(length=None)
    return {u["id"]: u for u in users}


def _author(authors, uid) -> dict:
    a = authors.get(uid) or {}
    return {"id": uid, "name": a.get("name"), "initials": a.get("initials"),
            "avatarColor": a.get("avatarColor"), "verified": bool(a.get("verified"))}


def _author_of(p, authors, pages) -> dict:
    if p.author_type == "page":
        pg = pages.get(p.author_id)
        if pg:
            return {"id": pg.id, "name": pg.name, "initials": (pg.name[:2] or "PG").upper(),
                    "avatarColor": pg.avatar_color or "#4353F0", "verified": bool(pg.verified), "isPage": True}
    return {**_author(authors, p.author_id), "isPage": False}


def _post_base(p, authors, pages, viewer_id) -> dict:
    return {
        "id": p.id, "author": _author_of(p, authors, pages),
        "body": p.body_text, "visibility": p.visibility, "type": p.post_type,
        "media": [{"url": m.media_url, "kind": m.kind, "alt": m.alt_text} for m in p.media],
        "commentCount": p.comment_count,
        "mine": p.author_type == "user" and p.author_id == viewer_id,
        "editedAt": p.edited_at, "createdAt": p.created_at,
    }


async def _serialize_posts(uow, mongo, posts, viewer_id, hide_counts: bool = False) -> list[dict]:
    if not posts:
        return []
    shared_map = {}
    for sid in {p.shared_post_id for p in posts if p.shared_post_id}:
        sp = await uow.posts.get(sid)
        if sp and sp.deleted_at is None:
            shared_map[sid] = sp
    allp = list(posts) + list(shared_map.values())
    author_ids = {p.author_id for p in allp if p.author_type == "user"}
    pages = await uow.pages.get_many([p.author_id for p in allp if p.author_type == "page"])
    authors = await _authors_map(mongo, author_ids)
    keys = [p.id for p in posts] + list(shared_map.keys())
    summaries = await uow.reactions.summaries("post", keys)
    mine = await uow.reactions.mine("post", keys, viewer_id)
    marked = await uow.bookmarks.mine_set(viewer_id, [p.id for p in posts])

    def one(p, nested=True) -> dict:
        d = _post_base(p, authors, pages, viewer_id)
        d["reactions"] = summaries.get(p.id, {"total": 0, "byType": {}})
        d["myReaction"] = mine.get(p.id)
        d["bookmarked"] = p.id in marked
        if hide_counts:
            # Mode apaisé : on masque les chiffres (moins de comparaison sociale),
            # sans casser l'interaction (on garde ma propre réaction + byType pour les emojis).
            d["reactions"] = {"total": None, "byType": d["reactions"].get("byType", {})}
            d["commentCount"] = None
            d["countsHidden"] = True
        if nested and p.shared_post_id and p.shared_post_id in shared_map:
            d["sharedPost"] = one(shared_map[p.shared_post_id], nested=False)
        return d
    return [one(p) for p in posts]


async def _serialize_comments(uow, mongo, comments, viewer_id) -> list[dict]:
    if not comments:
        return []
    authors = await _authors_map(mongo, {c.author_id for c in comments})
    ids = [c.id for c in comments]
    summaries = await uow.reactions.summaries("comment", ids)
    mine = await uow.reactions.mine("comment", ids, viewer_id)
    return [{
        "id": c.id, "parentId": c.parent_id, "depth": c.depth,
        "author": _author(authors, c.author_id),
        "body": ("" if c.deleted_at else c.body_text), "deleted": c.deleted_at is not None,
        "mine": c.author_id == viewer_id, "createdAt": c.created_at,
        "reactions": summaries.get(c.id, {"total": 0, "byType": {}}), "myReaction": mine.get(c.id),
    } for c in comments]


# ========== Posts & feed (Couche 2) ==========
@router.post("/net/posts")
async def create_post(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        post = await uc.publish_post(uow, me["id"], body=body.get("body"),
                                     visibility=body.get("visibility") or "public",
                                     audience=body.get("audience"), media=body.get("media"),
                                     post_type=body.get("type") or "status", lang=body.get("lang"))
    except ValueError as e:
        return err(str(e) or "Publication invalide")
    await uow.commit()
    post = await uow.posts.get(post.id)
    # Fan-out on write (Track A) : pousse le post dans le fil pré-calculé des destinataires.
    await fo.fan_out_post(uow, post)
    await uow.commit()
    out = (await _serialize_posts(uow, get_mongo(), [post], me["id"]))[0]
    # Éclats sociaux (Couche 10) : récompense « contribution » = 1re publication du jour,
    # idempotente (1/jour) et plafonnée. Pas de récompense au volume/engagement (anti-addiction).
    if settings.ECLATS_SOCIAL_POST > 0:
        res = await eclats.credit(get_mongo(), me["id"], settings.ECLATS_SOCIAL_POST, "social_post",
                                  {"label": "Première publication du jour ✨", "postId": post.id},
                                  idem=f"social_post:{me['id']}:{today_str()}")
        if res.get("ok") and not res.get("duplicate"):
            out["eclatsEarned"] = settings.ECLATS_SOCIAL_POST
    return ok(out)


async def _wellbeing(user_id: str) -> dict:
    p = await get_mongo().social_wellbeing_prefs.find_one({"userId": user_id}, {"_id": 0}) or {}
    return {"calmMode": bool(p.get("calmMode")), "hideCounts": bool(p.get("hideCounts"))}


@router.get("/net/feed")
async def feed(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        limit = max(1, min(int(request.query_params.get("limit") or 20), 50))
    except ValueError:
        limit = 20
    wb = await _wellbeing(me["id"])
    mode = request.query_params.get("mode") or "ranked"
    # Mode apaisé : on force le fil chronologique (pas de « boost viral ») et on masque les chiffres.
    if wb["calmMode"]:
        mode = "recent"
    hide = wb["hideCounts"] or wb["calmMode"]
    if mode == "ranked":
        # Fil CLASSÉ transparent : pipeline multi-étages + diversité. Chaque post expose sa
        # raison. Pagination par « déjà-vu » : chaque page marque les posts servis comme vus,
        # la suivante renvoie les meilleurs NON vus → défilement infini + « Tu es à jour ».
        pairs = await disc.get_ranked_feed(uow, _policy, me["id"], limit=limit)
        posts = [p for p, _r in pairs]
        data = await _serialize_posts(uow, get_mongo(), posts, me["id"], hide_counts=hide)
        for d, (_p, reason) in zip(data, pairs):
            d["reason"] = reason
        await uow.feed_seen.mark_seen(me["id"], [p.id for p in posts])
        await uow.commit()
        more = len(posts) == limit
        return ok({"items": data, "nextCursor": "more" if more else None, "mode": "ranked",
                   "caughtUp": not more, "calm": wb["calmMode"]})
    # Fil chronologique (bascule permanente) : pagination par curseur
    bt, bi = _decode_cursor(request.query_params.get("cursor")) if request.query_params.get("cursor") else (None, None)
    items = await uc.get_feed(uow, _policy, me["id"], limit=limit, before_time=bt, before_id=bi)
    data = await _serialize_posts(uow, get_mongo(), items, me["id"], hide_counts=hide)
    for d in data:
        d["reason"] = "Fil apaisé" if wb["calmMode"] else "Ordre chronologique"
    next_cursor = _encode_cursor(items[-1]) if len(items) == limit else None
    return ok({"items": data, "nextCursor": next_cursor, "mode": "recent",
               "caughtUp": next_cursor is None, "calm": wb["calmMode"]})


@router.get("/net/posts/{post_id}")
async def get_one(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    p = await uc.get_post(uow, _policy, me["id"], post_id)
    if not p:
        return err("Publication introuvable", 404)
    return ok((await _serialize_posts(uow, get_mongo(), [p], me["id"]))[0])


@router.patch("/net/posts/{post_id}")
async def patch_post(post_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        p = await uc.edit_post(uow, _policy, me["id"], post_id, body=body.get("body"),
                               visibility=body.get("visibility"), audience=body.get("audience"))
    except PermissionError:
        return err("Non autorisé", 403)
    except ValueError as e:
        return err(str(e) or "Invalide")
    if not p:
        return err("Publication introuvable", 404)
    await uow.commit()
    p = await uow.posts.get(post_id)
    return ok((await _serialize_posts(uow, get_mongo(), [p], me["id"]))[0])


@router.delete("/net/posts/{post_id}")
async def remove_post(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        done = await uc.delete_post(uow, _policy, me["id"], post_id)
    except PermissionError:
        return err("Non autorisé", 403)
    if not done:
        return err("Publication introuvable", 404)
    await uow.commit()
    return ok({"ok": True})


# ========== Interagir (Couche 3) ==========
async def _social_notify(recipient: str, net_kind: str, title: str, body: str = "", meta: dict | None = None):
    """Crée une notification sociale persistée (bell + push), en respectant les préférences."""
    if not recipient:
        return
    mongo = get_mongo()
    prefs = await mongo.social_notif_prefs.find_one({"userId": recipient}) or {}
    if net_kind in (prefs.get("disabled") or []):
        return
    try:
        from ...notify import notify as _mongo_notify
        await _mongo_notify(mongo, recipient, "social", title, body, {**(meta or {}), "netKind": net_kind})
    except Exception:  # noqa: BLE001
        pass


async def _notify_author(uow, post_id: str, actor: dict, net_kind: str, verb: str):
    p = await uow.posts.get(post_id)
    if p and p.author_type == "user" and p.author_id != actor["id"]:
        await _social_notify(p.author_id, net_kind, f"{actor.get('name')} {verb}",
                             (p.body_text or "")[:60], {"postId": post_id})


@router.put("/net/posts/{post_id}/reactions")
async def react_post(post_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        total = await ix.react_post(uow, _policy, me["id"], post_id, body.get("type") or "like")
    except ValueError as e:
        return err(str(e))
    except PermissionError:
        return err("Non autorisé", 403)
    except LookupError:
        return err("Introuvable", 404)
    await uow.commit()
    await _notify_author(uow, post_id, me, "reaction", "a réagi à ta publication")
    return ok({"total": total, "myReaction": body.get("type") or "like"})


@router.delete("/net/posts/{post_id}/reactions")
async def unreact_post(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        total = await ix.unreact_post(uow, me["id"], post_id)
    except LookupError:
        return err("Introuvable", 404)
    await uow.commit()
    return ok({"total": total, "myReaction": None})


@router.post("/net/posts/{post_id}/comments")
async def add_comment(post_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        c = await ix.add_comment(uow, _policy, me["id"], post_id, body.get("body") or "", body.get("parentId"))
    except ValueError as e:
        return err(str(e))
    except PermissionError:
        return err("Non autorisé", 403)
    except LookupError:
        return err("Introuvable", 404)
    await uow.commit()
    await _notify_author(uow, post_id, me, "comment", "a commenté ta publication")
    # notifie aussi l'auteur du commentaire parent (réponse)
    if c.parent_id:
        parent = await uow.comments.get(c.parent_id)
        if parent and parent.author_id not in (me["id"],):
            await _social_notify(parent.author_id, "reply", f"{me.get('name')} a répondu à ton commentaire",
                                 c.body_text[:60], {"postId": post_id})
    return ok((await _serialize_comments(uow, get_mongo(), [c], me["id"]))[0])


@router.get("/net/posts/{post_id}/comments")
async def list_comments(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    comments = await ix.list_comments(uow, _policy, me["id"], post_id)
    if comments is None:
        return err("Publication introuvable", 404)
    return ok({"items": await _serialize_comments(uow, get_mongo(), comments, me["id"])})


@router.delete("/net/comments/{comment_id}")
async def delete_comment(comment_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        done = await ix.delete_comment(uow, me["id"], comment_id)
    except PermissionError:
        return err("Non autorisé", 403)
    if not done:
        return err("Commentaire introuvable", 404)
    await uow.commit()
    return ok({"ok": True})


@router.put("/net/comments/{comment_id}/reactions")
async def react_comment(comment_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        await ix.react_comment(uow, _policy, me["id"], comment_id, body.get("type") or "like")
    except ValueError as e:
        return err(str(e))
    except PermissionError:
        return err("Non autorisé", 403)
    except LookupError:
        return err("Introuvable", 404)
    await uow.commit()
    return ok({"ok": True, "myReaction": body.get("type") or "like"})


@router.delete("/net/comments/{comment_id}/reactions")
async def unreact_comment(comment_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await ix.unreact_comment(uow, me["id"], comment_id)
    await uow.commit()
    return ok({"ok": True})


@router.post("/net/posts/{post_id}/share")
async def share_post(post_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        p = await ix.share_post(uow, _policy, me["id"], post_id,
                                body=body.get("body"), visibility=body.get("visibility") or "public")
    except PermissionError:
        return err("Partage non autorisé", 403)
    except LookupError:
        return err("Introuvable", 404)
    await uow.commit()
    p = await uow.posts.get(p.id)
    return ok((await _serialize_posts(uow, get_mongo(), [p], me["id"]))[0])


@router.put("/net/posts/{post_id}/bookmark")
async def bookmark(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        on = await ix.toggle_bookmark(uow, _policy, me["id"], post_id)
    except PermissionError:
        return err("Non autorisé", 403)
    except LookupError:
        return err("Introuvable", 404)
    await uow.commit()
    return ok({"bookmarked": on})


@router.get("/net/bookmarks")
async def list_bookmarks(me: dict = Depends(require_user), uow=Depends(get_uow)):
    posts = await ix.list_bookmarks(uow, _policy, me["id"])
    return ok({"items": await _serialize_posts(uow, get_mongo(), posts, me["id"])})


async def _mongo_user(mongo, uid):
    return await mongo.users.find_one({"id": uid}, {"_id": 0, "email": 0})


# ========== Graphe social (Couche 4) ==========
async def _user_cards(mongo, uow, ids, me_id):
    authors = await _authors_map(mongo, ids)
    out = []
    for uid in ids:
        out.append({**_author(authors, uid), "relationship": await gr.relationship(uow, me_id, uid)})
    return out


@router.post("/net/friends/request/{user_id}")
async def friend_request(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        status = await gr.send_friend_request(uow, me["id"], user_id)
    except ValueError as e:
        return err(str(e))
    except PermissionError:
        return err("Indisponible", 403)
    await uow.commit()
    if status == "pending" and user_id != me["id"]:
        try:
            from ...notify import notify as _notify
            await _notify(get_mongo(), user_id, "contact", "👋 Demande d'ami reçue", me.get("name", ""), {})
        except Exception:  # noqa: BLE001
            pass
    return ok({"status": status})


@router.post("/net/friends/accept/{user_id}")
async def friend_accept(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        await gr.accept_friend(uow, me["id"], user_id)
    except LookupError:
        return err("Aucune demande", 404)
    await uow.commit()
    await _social_notify(user_id, "friend_accept", f"{me.get('name')} a accepté ta demande d'ami", "", {})
    return ok({"status": "friends"})


@router.post("/net/friends/decline/{user_id}")
async def friend_decline(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.decline_friend(uow, me["id"], user_id)
    await uow.commit()
    return ok({"ok": True})


@router.delete("/net/friends/request/{user_id}")
async def friend_cancel(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.cancel_request(uow, me["id"], user_id)
    await uow.commit()
    return ok({"ok": True})


@router.delete("/net/friends/{user_id}")
async def friend_remove(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.unfriend(uow, me["id"], user_id)
    await uow.commit()
    return ok({"ok": True})


@router.get("/net/friends")
async def friends_list(me: dict = Depends(require_user), uow=Depends(get_uow)):
    ids = await gr.list_friends(uow, me["id"])
    return ok({"items": await _user_cards(get_mongo(), uow, ids, me["id"])})


@router.get("/net/friends/requests")
async def friend_requests(me: dict = Depends(require_user), uow=Depends(get_uow)):
    inc = await gr.incoming_requests(uow, me["id"])
    outg = await gr.outgoing_requests(uow, me["id"])
    return ok({"incoming": await _user_cards(get_mongo(), uow, inc, me["id"]),
               "outgoing": await _user_cards(get_mongo(), uow, outg, me["id"])})


@router.post("/net/follow/{user_id}")
async def do_follow(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        await gr.follow(uow, me["id"], user_id)
    except ValueError as e:
        return err(str(e))
    except PermissionError:
        return err("Indisponible", 403)
    await uow.commit()
    return ok({"following": True})


@router.delete("/net/follow/{user_id}")
async def do_unfollow(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.unfollow(uow, me["id"], user_id)
    await uow.commit()
    return ok({"following": False})


@router.post("/net/block/{user_id}")
async def do_block(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.block(uow, me["id"], user_id)
    await uow.commit()
    return ok({"blocked": True})


@router.delete("/net/block/{user_id}")
async def do_unblock(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.unblock(uow, me["id"], user_id)
    await uow.commit()
    return ok({"blocked": False})


@router.post("/net/mute/{user_id}")
async def do_mute(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.mute(uow, me["id"], user_id)
    await uow.commit()
    return ok({"muted": True})


@router.delete("/net/mute/{user_id}")
async def do_unmute(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await gr.unmute(uow, me["id"], user_id)
    await uow.commit()
    return ok({"muted": False})


@router.get("/net/relationship/{user_id}")
async def get_relationship(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    return ok(await gr.relationship(uow, me["id"], user_id))


# ========== Cercles ==========
@router.post("/net/circles")
async def create_circle(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    name = (body.get("name") or "").strip()
    if not name:
        return err("Nom requis")
    c = await uow.circles.create(me["id"], name)
    await uow.commit()
    return ok({"id": c.id, "name": c.name, "memberCount": 0})


@router.get("/net/circles")
async def list_circles(me: dict = Depends(require_user), uow=Depends(get_uow)):
    circles = await uow.circles.list_owned(me["id"])
    out = []
    for c in circles:
        out.append({"id": c.id, "name": c.name, "memberCount": len(await uow.circles.member_ids(c.id))})
    return ok({"items": out})


@router.delete("/net/circles/{circle_id}")
async def delete_circle(circle_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    c = await uow.circles.get(circle_id)
    if not c or c.owner_id != me["id"]:
        return err("Cercle introuvable", 404)
    await uow.circles.delete(circle_id)
    await uow.commit()
    return ok({"ok": True})


@router.put("/net/circles/{circle_id}/members/{user_id}")
async def add_circle_member(circle_id: str, user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    c = await uow.circles.get(circle_id)
    if not c or c.owner_id != me["id"]:
        return err("Cercle introuvable", 404)
    await uow.circles.add_member(circle_id, me["id"], user_id)
    await uow.commit()
    return ok({"ok": True})


@router.delete("/net/circles/{circle_id}/members/{user_id}")
async def remove_circle_member(circle_id: str, user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    c = await uow.circles.get(circle_id)
    if not c or c.owner_id != me["id"]:
        return err("Cercle introuvable", 404)
    await uow.circles.remove_member(circle_id, user_id)
    await uow.commit()
    return ok({"ok": True})


@router.get("/net/circles/{circle_id}/members")
async def circle_members(circle_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    c = await uow.circles.get(circle_id)
    if not c or c.owner_id != me["id"]:
        return err("Cercle introuvable", 404)
    ids = await uow.circles.member_ids(circle_id)
    authors = await _authors_map(get_mongo(), ids)
    return ok({"items": [_author(authors, i) for i in ids]})


# ========== Profil ==========
def _profile_out(prof, u, rel=None) -> dict:
    u = u or {}
    d = {"userId": u.get("id"),
         "name": (prof.display_name if prof and prof.display_name else u.get("name")),
         "initials": u.get("initials"), "avatarColor": u.get("avatarColor"),
         "verified": bool(u.get("verified")),
         "handle": (prof.handle if prof else None) or u.get("handle"),
         "avatarUrl": prof.avatar_url if prof else None, "coverUrl": prof.cover_url if prof else None,
         "bio": prof.bio if prof else None, "info": (prof.info if prof else {}) or {}}
    if rel is not None:
        d["relationship"] = rel
    return d


@router.get("/net/profile")
async def my_profile(me: dict = Depends(require_user), uow=Depends(get_uow)):
    prof = await uow.profiles.get(me["id"])
    return ok(_profile_out(prof, await _mongo_user(get_mongo(), me["id"])))


@router.put("/net/profile")
async def update_profile(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    fields = {"display_name": body.get("displayName"), "bio": body.get("bio"),
              "avatar_url": body.get("avatarUrl"), "cover_url": body.get("coverUrl"),
              "info": body.get("info")}
    if body.get("handle") is not None:
        fields["handle"] = (str(body["handle"]).lstrip("@").lower()[:40]) or None
    await uow.profiles.upsert(me["id"], **{k: v for k, v in fields.items() if v is not None})
    try:
        await uow.commit()
    except Exception:  # noqa: BLE001  (identifiant unique)
        await uow.rollback()
        return err("Cet identifiant est déjà pris", 409)
    prof = await uow.profiles.get(me["id"])
    return ok(_profile_out(prof, await _mongo_user(get_mongo(), me["id"])))


@router.get("/net/profile/{user_id}")
async def public_profile(user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    u = await _mongo_user(get_mongo(), user_id)
    if not u:
        return err("Profil introuvable", 404)
    prof = await uow.profiles.get(user_id)
    rel = await gr.relationship(uow, me["id"], user_id)
    return ok(_profile_out(prof, u, rel))


# ========== Découverte & recherche (Couche 5) ==========
@router.post("/net/posts/{post_id}/hide")
async def hide_post(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    """« Voir moins » : masque ce post du fil de l'utilisateur."""
    await uow.hidden.hide(me["id"], post_id)
    await uow.commit()
    return ok({"hidden": True})


@router.get("/net/suggestions")
async def suggestions(me: dict = Depends(require_user), uow=Depends(get_uow)):
    pairs = await disc.suggestions(uow, me["id"], limit=12)
    authors = await _authors_map(get_mongo(), [uid for uid, _ in pairs])
    return ok({"items": [{**_author(authors, uid), "mutual": n,
                          "reason": f"{n} ami{'s' if n > 1 else ''} en commun"} for uid, n in pairs]})


@router.get("/net/search")
async def search(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 2:
        return ok({"people": [], "posts": []})
    mongo = get_mongo()
    # personnes : par nom ou @handle (exclut bots, soi, bloqués)
    blocked = await uow.edges.blocked_ids(me["id"])
    import re as _re
    rx = _re.compile(_re.escape(q), _re.I)
    users = await mongo.users.find(
        {"$or": [{"name": {"$regex": rx}}, {"handle": {"$regex": rx}}],
         "isBot": {"$ne": True}}, {"_id": 0, "email": 0}).limit(15).to_list(length=15)
    people = [{"id": u["id"], "name": u.get("name"), "initials": u.get("initials"),
               "avatarColor": u.get("avatarColor"), "verified": bool(u.get("verified")),
               "handle": u.get("handle")}
              for u in users if u["id"] != me["id"] and u["id"] not in blocked]
    # posts publics contenant q
    posts = await disc.search_posts(uow, _policy, me["id"], q, limit=15)
    posts_out = await _serialize_posts(uow, mongo, posts, me["id"])
    return ok({"people": people, "posts": posts_out})


# ========== Groupes (Couche 6a) ==========
async def _group_out(uow, g, me_id):
    m = await uow.groups.membership(g.id, me_id)
    return {"id": g.id, "name": g.name, "description": g.description, "privacy": g.privacy,
            "avatarColor": g.avatar_color, "ownerId": g.owner_id,
            "memberCount": await uow.groups.member_count(g.id),
            "myRole": (m.role if m and m.status == "active" else None),
            "myStatus": (m.status if m else None)}


@router.post("/net/groups")
async def create_group(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        g = await grp.create_group(uow, me["id"], body.get("name") or "",
                                   body.get("description"), body.get("privacy") or "public")
    except ValueError as e:
        return err(str(e))
    await uow.commit()
    return ok(await _group_out(uow, g, me["id"]))


@router.get("/net/groups")
async def my_groups(me: dict = Depends(require_user), uow=Depends(get_uow)):
    mine = await uow.groups.my_groups(me["id"])
    disc_g = await uow.groups.discover(me["id"], limit=15)
    return ok({"mine": [await _group_out(uow, g, me["id"]) for g in mine],
               "discover": [await _group_out(uow, g, me["id"]) for g in disc_g]})


@router.get("/net/groups/{group_id}")
async def group_detail(group_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    g = await uow.groups.get(group_id)
    if not g:
        return err("Groupe introuvable", 404)
    return ok(await _group_out(uow, g, me["id"]))


@router.post("/net/groups/{group_id}/join")
async def join_group(group_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        status = await grp.join_group(uow, me["id"], group_id)
    except LookupError:
        return err("Groupe introuvable", 404)
    await uow.commit()
    return ok({"status": status})


@router.post("/net/groups/{group_id}/leave")
async def leave_group(group_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await grp.leave_group(uow, me["id"], group_id)
    await uow.commit()
    return ok({"ok": True})


@router.get("/net/groups/{group_id}/members")
async def group_members(group_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    g = await uow.groups.get(group_id)
    if not g:
        return err("Groupe introuvable", 404)
    active = await uow.groups.members(group_id, "active")
    authors = await _authors_map(get_mongo(), [m.user_id for m in active])
    my_role = None
    mine = await uow.groups.membership(group_id, me["id"])
    if mine and mine.status == "active":
        my_role = mine.role
    out = {"members": [{**_author(authors, m.user_id), "role": m.role} for m in active]}
    if my_role in ("admin", "moderator"):
        pending = await uow.groups.members(group_id, "pending")
        pa = await _authors_map(get_mongo(), [m.user_id for m in pending])
        out["pending"] = [_author(pa, m.user_id) for m in pending]
    return ok(out)


@router.post("/net/groups/{group_id}/members/{user_id}/approve")
async def group_approve(group_id: str, user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        await grp.approve_member(uow, me["id"], group_id, user_id)
    except PermissionError:
        return err("Réservé aux modérateurs", 403)
    except LookupError:
        return err("Aucune demande", 404)
    g = await uow.groups.get(group_id)
    await uow.commit()
    await _social_notify(user_id, "group_approved", f"Bienvenue dans « {g.name if g else 'le groupe'} »",
                         "Ta demande a été acceptée", {"groupId": group_id})
    return ok({"ok": True})


@router.post("/net/groups/{group_id}/members/{user_id}/reject")
async def group_reject(group_id: str, user_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        await grp.reject_member(uow, me["id"], group_id, user_id)
    except PermissionError:
        return err("Réservé aux modérateurs", 403)
    await uow.commit()
    return ok({"ok": True})


@router.put("/net/groups/{group_id}/members/{user_id}/role")
async def group_set_role(group_id: str, user_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        await grp.set_role(uow, me["id"], group_id, user_id, body.get("role") or "member")
    except PermissionError:
        return err("Réservé au propriétaire", 403)
    except (ValueError, LookupError) as e:
        return err(str(e) or "Invalide")
    await uow.commit()
    return ok({"ok": True})


@router.post("/net/groups/{group_id}/posts")
async def group_post(group_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    if not await grp.can_post_to_group(uow, me["id"], group_id):
        return err("Réservé aux membres du groupe", 403)
    body = await request.json() if await request.body() else {}
    try:
        post = await uc.publish_post(uow, me["id"], body=body.get("body"), visibility="group",
                                     media=body.get("media"), post_type="status", group_id=group_id)
    except ValueError as e:
        return err(str(e))
    await uow.commit()
    post = await uow.posts.get(post.id)
    await fo.fan_out_post(uow, post)  # fan-out vers les membres du groupe
    await uow.commit()
    return ok((await _serialize_posts(uow, get_mongo(), [post], me["id"]))[0])


@router.get("/net/groups/{group_id}/feed")
async def group_feed(group_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    posts = await grp.group_feed(uow, _policy, me["id"], group_id, limit=30)
    if posts is None:
        return err("Groupe introuvable ou réservé", 404)
    return ok({"items": await _serialize_posts(uow, get_mongo(), posts, me["id"])})


# ========== Stories (Couche 6a) ==========
@router.post("/net/stories")
async def create_story(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        s = await st.post_story(uow, me["id"], body.get("mediaUrl") or "",
                                body.get("kind") or "image", body.get("caption"))
    except ValueError as e:
        return err(str(e))
    await uow.commit()
    return ok({"id": s.id, "mediaUrl": s.media_url, "kind": s.kind, "expiresAt": s.expires_at})


@router.get("/net/stories")
async def stories_feed(me: dict = Depends(require_user), uow=Depends(get_uow)):
    stories = await st.stories_feed(uow, me["id"])
    authors = await _authors_map(get_mongo(), {s.author_id for s in stories})
    # regroupées par auteur, dans l'ordre
    grouped: dict = {}
    for s in stories:
        g = grouped.setdefault(s.author_id, {"author": _author(authors, s.author_id), "items": []})
        g["items"].append({"id": s.id, "mediaUrl": s.media_url, "kind": s.kind,
                           "caption": s.caption, "createdAt": s.created_at, "mine": s.author_id == me["id"]})
    return ok({"items": list(grouped.values())})


@router.post("/net/stories/{story_id}/view")
async def view_story(story_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        s = await st.view_story(uow, me["id"], story_id)
    except PermissionError:
        return err("Non autorisé", 403)
    except LookupError:
        return err("Story expirée ou introuvable", 404)
    await uow.commit()
    return ok({"id": s.id, "mediaUrl": s.media_url, "kind": s.kind, "caption": s.caption})


@router.get("/net/stories/{story_id}/viewers")
async def story_viewers(story_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    ids = await st.story_viewers(uow, me["id"], story_id)
    if ids is None:
        return err("Non autorisé", 403)
    authors = await _authors_map(get_mongo(), ids)
    return ok({"items": [_author(authors, i) for i in ids], "count": len(ids)})


# ========== Pages (Couche 6b) ==========
async def _page_out(uow, pg, me_id):
    return {"id": pg.id, "name": pg.name, "category": pg.category, "bio": pg.bio,
            "avatarColor": pg.avatar_color, "verified": pg.verified,
            "followerCount": await uow.pages.follower_count(pg.id),
            "myRole": await uow.pages.role_of(pg.id, me_id),
            "following": await uow.pages.is_following(pg.id, me_id)}


@router.post("/net/pages")
async def create_page(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        p = await pg_uc.create_page(uow, me["id"], body.get("name") or "", body.get("category"), body.get("bio"))
    except ValueError as e:
        return err(str(e))
    await uow.commit()
    return ok(await _page_out(uow, p, me["id"]))


@router.get("/net/pages")
async def list_pages(me: dict = Depends(require_user), uow=Depends(get_uow)):
    mine = await uow.pages.managed_by(me["id"])
    disc_p = await uow.pages.discover(limit=15)
    mine_ids = {p.id for p in mine}
    return ok({"mine": [await _page_out(uow, p, me["id"]) for p in mine],
               "discover": [await _page_out(uow, p, me["id"]) for p in disc_p if p.id not in mine_ids]})


@router.get("/net/pages/{page_id}")
async def page_detail(page_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    p = await uow.pages.get(page_id)
    if not p:
        return err("Page introuvable", 404)
    return ok(await _page_out(uow, p, me["id"]))


@router.post("/net/pages/{page_id}/follow")
async def follow_page(page_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    if not await uow.pages.get(page_id):
        return err("Page introuvable", 404)
    await uow.pages.set_follow(page_id, me["id"], True)
    await uow.commit()
    return ok({"following": True})


@router.delete("/net/pages/{page_id}/follow")
async def unfollow_page(page_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    await uow.pages.set_follow(page_id, me["id"], False)
    await uow.commit()
    return ok({"following": False})


@router.post("/net/pages/{page_id}/posts")
async def page_post(page_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    if not await pg_uc.can_publish(uow, me["id"], page_id):
        return err("Réservé aux administrateurs de la page", 403)
    body = await request.json() if await request.body() else {}
    try:
        post = await uc.publish_post(uow, page_id, body=body.get("body"), visibility="public",
                                     media=body.get("media"), author_type="page")
    except ValueError as e:
        return err(str(e))
    await uow.commit()
    post = await uow.posts.get(post.id)
    await fo.fan_out_post(uow, post)  # fan-out vers les abonnés de la page
    await uow.commit()
    return ok((await _serialize_posts(uow, get_mongo(), [post], me["id"]))[0])


@router.get("/net/pages/{page_id}/feed")
async def page_feed(page_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    if not await uow.pages.get(page_id):
        return err("Page introuvable", 404)
    posts = await pg_uc.page_feed(uow, page_id, limit=30)
    return ok({"items": await _serialize_posts(uow, get_mongo(), posts, me["id"])})


# ========== Événements (Couche 6b) ==========
async def _event_out(uow, mongo, e, me_id):
    counts = await uow.events.rsvp_counts(e.id)
    owner = await _mongo_user(mongo, e.owner_id)
    return {"id": e.id, "title": e.title, "description": e.description, "location": e.location,
            "online": e.online, "startsAt": e.starts_at, "endsAt": e.ends_at, "groupId": e.group_id,
            "owner": {"id": e.owner_id, "name": (owner or {}).get("name"),
                      "avatarColor": (owner or {}).get("avatarColor"), "initials": (owner or {}).get("initials")},
            "going": counts.get("going", 0), "interested": counts.get("interested", 0),
            "myRsvp": await uow.events.my_rsvp(e.id, me_id), "mine": e.owner_id == me_id}


@router.post("/net/events")
async def create_event(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        e = await ev.create_event(uow, me["id"], title=body.get("title") or "",
                                  starts_at=body.get("startsAt") or "", description=body.get("description"),
                                  location=body.get("location"), online=bool(body.get("online")),
                                  group_id=body.get("groupId"))
    except ValueError as ex:
        return err(str(ex))
    await uow.commit()
    return ok(await _event_out(uow, get_mongo(), e, me["id"]))


@router.get("/net/events")
async def list_events(me: dict = Depends(require_user), uow=Depends(get_uow)):
    mine, upcoming = await ev.list_events(uow, me["id"])
    mine_ids = {e.id for e in mine}
    return ok({"mine": [await _event_out(uow, get_mongo(), e, me["id"]) for e in mine],
               "upcoming": [await _event_out(uow, get_mongo(), e, me["id"]) for e in upcoming if e.id not in mine_ids]})


@router.get("/net/events/{event_id}")
async def event_detail(event_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    e = await uow.events.get(event_id)
    if not e:
        return err("Événement introuvable", 404)
    return ok(await _event_out(uow, get_mongo(), e, me["id"]))


@router.post("/net/events/{event_id}/rsvp")
async def event_rsvp(event_id: str, request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        await ev.rsvp(uow, me["id"], event_id, body.get("status") or "going")
    except ValueError as e:
        return err(str(e))
    except LookupError:
        return err("Événement introuvable", 404)
    await uow.commit()
    e = await uow.events.get(event_id)
    return ok(await _event_out(uow, get_mongo(), e, me["id"]))


@router.get("/net/events/{event_id}/attendees")
async def event_attendees(event_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    going = await uow.events.attendees(event_id, "going")
    interested = await uow.events.attendees(event_id, "interested")
    authors = await _authors_map(get_mongo(), going + interested)
    return ok({"going": [_author(authors, i) for i in going],
               "interested": [_author(authors, i) for i in interested]})


# ========== Préférences de notifications sociales (Couche 8, Mongo — pas de Postgres requis) ==========
_NET_NOTIF_KINDS = ["reaction", "comment", "reply", "friend_accept", "group_approved", "mention"]


@router.get("/net/notifications/prefs")
async def get_notif_prefs(me: dict = Depends(require_user)):
    p = await get_mongo().social_notif_prefs.find_one({"userId": me["id"]}, {"_id": 0}) or {}
    return ok({"kinds": _NET_NOTIF_KINDS, "disabled": p.get("disabled", [])})


@router.put("/net/notifications/prefs")
async def set_notif_prefs(request: Request, me: dict = Depends(require_user)):
    body = await request.json() if await request.body() else {}
    disabled = [k for k in (body.get("disabled") or []) if k in _NET_NOTIF_KINDS]
    await get_mongo().social_notif_prefs.update_one(
        {"userId": me["id"]}, {"$set": {"userId": me["id"], "disabled": disabled}}, upsert=True)
    return ok({"disabled": disabled})


# ========================= Couche 9 — Confiance (modération + RGPD) =========================
@router.get("/net/moderation/config")
async def moderation_config(me: dict = Depends(require_user)):
    """Le front sait s'il doit afficher le panneau modération + les motifs de signalement."""
    return ok({"isModerator": _is_moderator(me), "reasons": mod.REASONS,
               "subjectTypes": mod.SUBJECT_TYPES, "actions": mod.ACTIONS})


@router.post("/net/report")
async def report_subject(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        r = await mod.create_report(uow, me["id"], body.get("subjectType"), body.get("subjectId"),
                                    body.get("reason"), body.get("details"))
    except ValueError as e:
        return err(str(e), 400)
    return ok({"id": r.id, "status": r.status})


@router.get("/net/moderation/queue")
async def moderation_queue(status: str = "pending", me: dict = Depends(require_moderator),
                           uow=Depends(get_uow)):
    reports = await mod.queue(uow, status)
    author_ids = [r.context.get("authorId") for r in reports if r.context]
    authors = await _authors_map(get_mongo(), [i for i in [*author_ids, *[r.reporter_id for r in reports]] if i])
    return ok({"items": [{
        "id": r.id, "subjectType": r.subject_type, "subjectId": r.subject_id,
        "reason": r.reason, "details": r.details, "status": r.status,
        "excerpt": (r.context or {}).get("excerpt"),
        "author": _author(authors, (r.context or {}).get("authorId")) if (r.context or {}).get("authorId") else None,
        "reporter": _author(authors, r.reporter_id),
        "createdAt": r.created_at.isoformat(),
    } for r in reports]})


@router.post("/net/moderation/reports/{report_id}/resolve")
async def moderation_resolve(report_id: str, request: Request,
                             me: dict = Depends(require_moderator), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        r = await mod.resolve_report(uow, me["id"], report_id, body.get("action"), body.get("note"))
    except LookupError:
        return err("Signalement introuvable", 404)
    except ValueError as e:
        return err(str(e), 400)
    return ok({"id": r.id, "status": r.status, "resolution": r.resolution})


@router.get("/net/moderation/stats")
async def moderation_stats(me: dict = Depends(require_moderator), uow=Depends(get_uow)):
    return ok(await mod.stats(uow))


@router.get("/net/transparency")
async def transparency(me: dict = Depends(require_user), uow=Depends(get_uow)):
    """Page publique de transparence : chiffres agrégés & anonymisés (aucune donnée perso)."""
    return ok(await mod.transparency(uow))


# ---------- RGPD : portabilité + droit à l'oubli ----------
@router.get("/net/me/export")
async def rgpd_export(me: dict = Depends(require_user), uow=Depends(get_uow)):
    return ok(await rgpd.export_my_data(uow, me["id"]))


@router.post("/net/me/erase")
async def rgpd_erase(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    if body.get("confirm") != "SUPPRIMER":
        return err('Confirmation requise : envoie {"confirm":"SUPPRIMER"}.', 400)
    return ok(await rgpd.erase_my_data(uow, me["id"]))


# ========== Bien-être / fil apaisé (Couche 10, Mongo — pas de Postgres requis) ==========
@router.get("/net/wellbeing/prefs")
async def get_wellbeing(me: dict = Depends(require_user)):
    p = await get_mongo().social_wellbeing_prefs.find_one({"userId": me["id"]}, {"_id": 0}) or {}
    return ok({"calmMode": bool(p.get("calmMode")), "hideCounts": bool(p.get("hideCounts")),
               "eclatsPerPost": settings.ECLATS_SOCIAL_POST})


@router.put("/net/wellbeing/prefs")
async def set_wellbeing(request: Request, me: dict = Depends(require_user)):
    body = await request.json() if await request.body() else {}
    prefs = {"calmMode": bool(body.get("calmMode")), "hideCounts": bool(body.get("hideCounts"))}
    await get_mongo().social_wellbeing_prefs.update_one(
        {"userId": me["id"]}, {"$set": {"userId": me["id"], **prefs}}, upsert=True)
    return ok(prefs)
