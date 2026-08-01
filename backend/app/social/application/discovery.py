"""Use cases 'découverte' : fil classé explicable, suggestions d'amis, recherche."""
from __future__ import annotations

from datetime import timezone

from ...helpers import now as _now
from ..domain.policy import PolicyService
from .posts import audience_of
from .ranking import score_post
from .access import view_relation


async def get_ranked_feed(uow, policy: PolicyService, viewer_id: str, *, limit: int = 20):
    """Retourne [(post, raison)] classés par pertinence (heuristique explicable)."""
    following = await uow.edges.following_ids(viewer_id)
    blocked = await uow.edges.blocked_ids(viewer_id)
    muted = await uow.edges.muted_ids(viewer_id)
    hidden = await uow.hidden.hidden_ids(viewer_id)
    pages = await uow.pages.followed_ids(viewer_id)
    excluded = blocked | muted
    authors = [a for a in ([viewer_id] + following + pages) if a == viewer_id or a not in excluded]
    candidates = await uow.posts.list_recent_by_authors(authors, limit=limit * 4)
    now_ts = _now()
    rel_cache: dict = {}
    scored = []
    for p in candidates:
        if p.id in hidden:
            continue
        if p.author_id == viewer_id:
            is_own, is_friend, is_following = True, False, False
        else:
            rel = rel_cache.get(p.author_id)
            if rel is None:
                rel = await view_relation(uow, viewer_id, p)
                rel_cache[p.author_id] = rel
            if not policy.can_view_post(viewer_id, audience_of(p), rel):
                continue
            is_own, is_friend, is_following = False, rel.is_friend, rel.is_following
        ca = p.created_at if p.created_at.tzinfo else p.created_at.replace(tzinfo=timezone.utc)
        age_h = max(0.0, (now_ts - ca).total_seconds() / 3600.0)
        s, reason = score_post(is_friend=is_friend, is_following=is_following, is_own=is_own,
                               age_hours=age_h, reactions=p.like_count, comments=p.comment_count)
        scored.append((s, reason, p))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [(p, reason) for _s, reason, p in scored[:limit]]


async def suggestions(uow, viewer_id: str, *, limit: int = 10) -> list[tuple[str, int]]:
    """Amis d'amis, triés par nombre d'amis en commun. Retourne [(user_id, mutuels)]."""
    friends = set(await uow.edges.list_out(viewer_id, "friend"))
    blocked = await uow.edges.blocked_ids(viewer_id)
    pending_out = set(await uow.edges.list_out(viewer_id, "request"))
    counts: dict[str, int] = {}
    for f in friends:
        for ff in await uow.edges.list_out(f, "friend"):
            if ff == viewer_id or ff in friends or ff in blocked or ff in pending_out:
                continue
            counts[ff] = counts.get(ff, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:limit]


async def search_posts(uow, policy: PolicyService, viewer_id: str, q: str, limit: int = 20):
    """Recherche dans les publications PUBLIQUES (respect de la visibilité)."""
    if len(q.strip()) < 2:
        return []
    return await uow.posts.search_public(q.strip(), limit=limit)
