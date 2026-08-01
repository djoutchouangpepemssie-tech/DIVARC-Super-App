"""Use cases 'posts' : publier, feed (curseur), voir, éditer, supprimer.

Orchestrent le domaine (PolicyService) + les ports (uow). Aucune dépendance FastAPI.
"""
from __future__ import annotations

from datetime import datetime

from ...helpers import now as _now
from ..adapters.persistence.models import Post, PostMedia
from ..domain.policy import PolicyService
from ..domain.visibility import PostAudience, Visibility
from .access import view_relation


def audience_of(p: Post) -> PostAudience:
    aud = p.audience or {}
    return PostAudience(
        visibility=Visibility(p.visibility),
        author_id=p.author_id,
        circle_ids=frozenset(aud.get("circle_ids") or []),
        excluded_ids=frozenset(aud.get("excluded_ids") or []),
        group_id=p.group_id,
        deleted=p.deleted_at is not None,
    )


async def publish_post(uow, author_id: str, *, body: str | None = None, visibility: str = "public",
                       audience: dict | None = None, media: list[dict] | None = None,
                       post_type: str = "status", lang: str | None = None,
                       group_id: str | None = None, author_type: str = "user") -> Post:
    vis = Visibility(visibility)  # lève ValueError si invalide
    clean_aud = {}
    if audience:
        if audience.get("circle_ids"):
            clean_aud["circle_ids"] = [str(c) for c in audience["circle_ids"]]
        if audience.get("excluded_ids"):
            clean_aud["excluded_ids"] = [str(u) for u in audience["excluded_ids"]]
    post = Post(author_id=author_id, author_type=author_type, body_text=((body or "").strip() or None),
                visibility=vis.value, audience=clean_aud, post_type=post_type, lang=lang, group_id=group_id)
    for i, m in enumerate((media or [])[:10]):
        url = (m.get("url") or "").strip()
        if not url:
            continue
        post.media.append(PostMedia(media_url=url, kind=(m.get("kind") or "image"),
                                    position=i, alt_text=(m.get("alt") or None)))
    if not post.body_text and not post.media:
        raise ValueError("Publication vide")
    await uow.posts.add(post)
    return post


async def get_feed(uow, policy: PolicyService, viewer_id: str, *, limit: int = 20,
                   before_time: datetime | None = None, before_id: str | None = None) -> list[Post]:
    following = await uow.edges.following_ids(viewer_id)
    blocked = await uow.edges.blocked_ids(viewer_id)
    muted = await uow.edges.muted_ids(viewer_id)
    pages = await uow.pages.followed_ids(viewer_id)  # posts des pages suivies
    excluded = blocked | muted
    authors = [a for a in ([viewer_id] + following + pages) if a == viewer_id or a not in excluded]
    # sur-échantillonnage : le filtrage par visibilité peut retirer des candidats
    candidates = await uow.posts.list_recent_by_authors(authors, limit=limit * 3,
                                                        before_time=before_time, before_id=before_id)
    rel_cache: dict[str, object] = {}
    out: list[Post] = []
    for p in candidates:
        if p.author_id == viewer_id:
            out.append(p)
        else:
            rel = rel_cache.get(p.author_id)
            if rel is None:
                rel = await view_relation(uow, viewer_id, p)
                rel_cache[p.author_id] = rel
            if policy.can_view_post(viewer_id, audience_of(p), rel):
                out.append(p)
        if len(out) >= limit:
            break
    return out


async def get_post(uow, policy: PolicyService, viewer_id: str, post_id: str) -> Post | None:
    p = await uow.posts.get(post_id)
    if not p or p.deleted_at is not None:
        return None
    rel = await view_relation(uow, viewer_id, p)
    return p if policy.can_view_post(viewer_id, audience_of(p), rel) else None


async def edit_post(uow, policy: PolicyService, viewer_id: str, post_id: str, *,
                    body: str | None = None, visibility: str | None = None,
                    audience: dict | None = None) -> Post | None:
    
    p = await uow.posts.get(post_id)
    if not p or p.deleted_at is not None:
        return None
    if not policy.can_edit(viewer_id, audience_of(p), await view_relation(uow, viewer_id, p)):
        raise PermissionError("Édition non autorisée")
    if body is not None:
        p.body_text = body.strip() or None
    if visibility is not None:
        p.visibility = Visibility(visibility).value
    if audience is not None:
        p.audience = {k: [str(x) for x in v] for k, v in audience.items() if k in ("circle_ids", "excluded_ids") and v}
    p.edited_at = _now()
    return p


async def delete_post(uow, policy: PolicyService, viewer_id: str, post_id: str) -> bool:
    
    p = await uow.posts.get(post_id)
    if not p or p.deleted_at is not None:
        return False
    if not policy.can_delete(viewer_id, audience_of(p), await view_relation(uow, viewer_id, p)):
        raise PermissionError("Suppression non autorisée")
    p.deleted_at = _now()
    return True
