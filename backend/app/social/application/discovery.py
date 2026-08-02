"""Use cases 'découverte' : fil classé explicable, suggestions d'amis, recherche."""
from __future__ import annotations

from datetime import timezone

from ...helpers import now as _now
from ..domain.policy import PolicyService
from .posts import audience_of
from .ranking import diversify, score_post
from .access import view_relation


async def get_ranked_feed(uow, policy: PolicyService, viewer_id: str, *, limit: int = 20,
                          exclude_seen: bool = True):
    """Pipeline de fil classé inspiré de Facebook, mais transparent :
      1) RETRIEVAL : posts récents des auteurs suivis/amis + pages (hors bloqués/sourdine/vus).
      2) LIGHT/HEAVY RANK : score multi-signaux (lien + affinité comportementale + engagement
         + fraîcheur + format), chacun explicable.
      3) RE-RANK DIVERSITÉ : on évite d'enchaîner plusieurs posts du même auteur.
    Retourne [(post, raison)] classés.
    """
    following = await uow.edges.following_ids(viewer_id)
    blocked = await uow.edges.blocked_ids(viewer_id)
    muted = await uow.edges.muted_ids(viewer_id)
    hidden = await uow.hidden.hidden_ids(viewer_id)
    pages = await uow.pages.followed_ids(viewer_id)
    seen = await uow.feed_seen.seen_ids(viewer_id) if exclude_seen else set()
    excluded = blocked | muted
    authors = [a for a in ([viewer_id] + following + pages) if a == viewer_id or a not in excluded]
    # RETRIEVAL : on récupère large (pour laisser respirer le re-rank diversité), hors déjà-vus.
    candidates = await uow.posts.list_recent_by_authors_excluding(
        authors, exclude_ids=hidden | seen, limit=max(limit * 6, 60))
    # Affinité comportementale : combien TU interagis avec chaque auteur (normalisée 0..1).
    author_ids = [a for a in {p.author_id for p in candidates} if a != viewer_id]
    aff_raw = await uow.posts.affinity_counts(viewer_id, author_ids) if author_ids else {}
    now_ts = _now()
    rel_cache: dict = {}
    scored = []
    for p in candidates:
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
        n = aff_raw.get(p.author_id, 0)
        affinity = n / (n + 3.0)  # normalisation douce
        s, reason = score_post(is_friend=is_friend, is_following=is_following, is_own=is_own,
                               age_hours=age_h, reactions=p.like_count, comments=p.comment_count,
                               affinity=affinity, has_media=bool(p.media))
        scored.append((s, reason, p))
    # RE-RANK diversité puis coupe au nombre demandé.
    ranked = diversify(scored)[:limit]
    return [(p, reason) for _s, reason, p in ranked]


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
