"""API REST du contexte social — Couche 2 : publier & voir (posts + feed par curseur).

Auth = session Mongo existante (require_user). Autorisation = PolicyService.
Données social en PostgreSQL (UoW SQLAlchemy). Infos auteur lues côté Mongo.
"""
from __future__ import annotations

import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from ...config import settings
from ...db import get_db as get_mongo
from ...helpers import err, ok
from ...security import require_user
from ..adapters.persistence.uow import SqlAlchemyUnitOfWork
from ..application import posts as uc
from ..domain.policy import PolicyService

router = APIRouter()
_policy = PolicyService()


async def get_uow():
    # Le réseau social requiert PostgreSQL configuré (SOCIAL_DATABASE_URL).
    if not settings.SOCIAL_DATABASE_URL:
        raise HTTPException(status_code=503, detail="Réseau social pas encore activé (PostgreSQL requis)")
    async with SqlAlchemyUnitOfWork() as uow:
        yield uow


# ---------- curseur ----------
def _encode_cursor(p) -> str:
    raw = f"{p.created_at.isoformat()}|{p.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cur: str):
    try:
        raw = base64.urlsafe_b64decode(cur.encode()).decode()
        ts, pid = raw.split("|", 1)
        return datetime.fromisoformat(ts), pid
    except Exception:  # noqa: BLE001
        return None, None


# ---------- sérialisation (auteur lu côté Mongo) ----------
async def _authors_map(mongo, ids: set[str]) -> dict:
    if not ids:
        return {}
    users = await mongo.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "email": 0}).to_list(length=None)
    return {u["id"]: u for u in users}


def _post_out(p, authors: dict, viewer_id: str) -> dict:
    a = authors.get(p.author_id) or {}
    return {
        "id": p.id,
        "author": {"id": p.author_id, "name": a.get("name"), "initials": a.get("initials"),
                   "avatarColor": a.get("avatarColor"), "verified": bool(a.get("verified"))},
        "body": p.body_text, "visibility": p.visibility, "type": p.post_type,
        "media": [{"url": m.media_url, "kind": m.kind, "alt": m.alt_text} for m in p.media],
        "likeCount": p.like_count, "commentCount": p.comment_count,
        "mine": p.author_id == viewer_id,
        "editedAt": p.edited_at, "createdAt": p.created_at,
    }


# ---------- endpoints ----------
@router.post("/net/posts")
async def create_post(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    body = await request.json() if await request.body() else {}
    try:
        post = await uc.publish_post(
            uow, me["id"], body=body.get("body"), visibility=body.get("visibility") or "public",
            audience=body.get("audience"), media=body.get("media"),
            post_type=body.get("type") or "status", lang=body.get("lang"))
    except ValueError as e:
        return err(str(e) or "Publication invalide")
    await uow.commit()
    post = await uow.posts.get(post.id)  # rechargé avec médias (eager)
    authors = await _authors_map(get_mongo(), {post.author_id})
    return ok(_post_out(post, authors, me["id"]))


@router.get("/net/feed")
async def feed(request: Request, me: dict = Depends(require_user), uow=Depends(get_uow)):
    try:
        limit = max(1, min(int(request.query_params.get("limit") or 20), 50))
    except ValueError:
        limit = 20
    before_time, before_id = (None, None)
    cur = request.query_params.get("cursor")
    if cur:
        before_time, before_id = _decode_cursor(cur)
    items = await uc.get_feed(uow, _policy, me["id"], limit=limit,
                              before_time=before_time, before_id=before_id)
    authors = await _authors_map(get_mongo(), {p.author_id for p in items})
    next_cursor = _encode_cursor(items[-1]) if len(items) == limit else None
    return ok({"items": [_post_out(p, authors, me["id"]) for p in items], "nextCursor": next_cursor})


@router.get("/net/posts/{post_id}")
async def get_one(post_id: str, me: dict = Depends(require_user), uow=Depends(get_uow)):
    p = await uc.get_post(uow, _policy, me["id"], post_id)
    if not p:
        return err("Publication introuvable", 404)
    authors = await _authors_map(get_mongo(), {p.author_id})
    return ok(_post_out(p, authors, me["id"]))


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
    p = await uow.posts.get(post_id)  # rechargé avec médias (eager)
    authors = await _authors_map(get_mongo(), {p.author_id})
    return ok(_post_out(p, authors, me["id"]))


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
