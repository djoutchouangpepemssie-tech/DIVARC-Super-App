"""API REST du contexte social — Couches 2 & 3.

Publier & voir (posts, feed curseur) + Interagir (réactions, commentaires imbriqués,
partages, bookmarks) + temps réel (WS manager existant). Autorisation = PolicyService.
"""
from __future__ import annotations

import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from ...config import settings
from ...db import get_db as get_mongo
from ...helpers import err, ok
from ...realtime import manager
from ...security import require_user
from ..adapters.persistence.uow import SqlAlchemyUnitOfWork
from ..application import graph as gr
from ..application import interactions as ix
from ..application import posts as uc
from ..domain.policy import PolicyService

router = APIRouter()
_policy = PolicyService()


async def get_uow():
    if not settings.SOCIAL_DATABASE_URL:
        raise HTTPException(status_code=503, detail="Réseau social pas encore activé (PostgreSQL requis)")
    async with SqlAlchemyUnitOfWork() as uow:
        yield uow


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


def _post_base(p, authors, viewer_id) -> dict:
    return {
        "id": p.id, "author": _author(authors, p.author_id),
        "body": p.body_text, "visibility": p.visibility, "type": p.post_type,
        "media": [{"url": m.media_url, "kind": m.kind, "alt": m.alt_text} for m in p.media],
        "commentCount": p.comment_count, "mine": p.author_id == viewer_id,
        "editedAt": p.edited_at, "createdAt": p.created_at,
    }


async def _serialize_posts(uow, mongo, posts, viewer_id) -> list[dict]:
    if not posts:
        return []
    shared_map = {}
    for sid in {p.shared_post_id for p in posts if p.shared_post_id}:
        sp = await uow.posts.get(sid)
        if sp and sp.deleted_at is None:
            shared_map[sid] = sp
    author_ids = {p.author_id for p in posts} | {sp.author_id for sp in shared_map.values()}
    authors = await _authors_map(mongo, author_ids)
    keys = [p.id for p in posts] + list(shared_map.keys())
    summaries = await uow.reactions.summaries("post", keys)
    mine = await uow.reactions.mine("post", keys, viewer_id)
    marked = await uow.bookmarks.mine_set(viewer_id, [p.id for p in posts])

    def one(p, nested=True) -> dict:
        d = _post_base(p, authors, viewer_id)
        d["reactions"] = summaries.get(p.id, {"total": 0, "byType": {}})
        d["myReaction"] = mine.get(p.id)
        d["bookmarked"] = p.id in marked
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
    return ok((await _serialize_posts(uow, get_mongo(), [post], me["id"]))[0])


@router.get("/net/feed")
async def feed(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        limit = max(1, min(int(request.query_params.get("limit") or 20), 50))
    except ValueError:
        limit = 20
    bt, bi = _decode_cursor(request.query_params.get("cursor")) if request.query_params.get("cursor") else (None, None)
    items = await uc.get_feed(uow, _policy, me["id"], limit=limit, before_time=bt, before_id=bi)
    data = await _serialize_posts(uow, get_mongo(), items, me["id"])
    return ok({"items": data, "nextCursor": _encode_cursor(items[-1]) if len(items) == limit else None})


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
async def _notify_author(uow, post_id: str, actor: dict, kind: str):
    p = await uow.posts.get(post_id)
    if p and p.author_id != actor["id"]:
        try:
            await manager.send_to_user(p.author_id, {"type": "net:activity", "kind": kind,
                                                     "postId": post_id, "actor": actor.get("name")})
        except Exception:  # noqa: BLE001
            pass


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
    await _notify_author(uow, post_id, me, "reaction")
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
    await _notify_author(uow, post_id, me, "comment")
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
