"""Use cases 'stories' : publier (éphémère 24 h), lister (amis/suivis), voir, spectateurs."""
from __future__ import annotations

from datetime import timedelta, timezone

from ...helpers import now as _now
from ..adapters.persistence.models import Story


def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def post_story(uow, me: str, media_url: str, kind: str = "image",
                     caption: str | None = None, ttl_hours: int = 24) -> Story:
    if not (media_url or "").strip():
        raise ValueError("Média requis")
    s = Story(author_id=me, media_url=media_url.strip(), kind=kind,
              caption=(caption or None) and caption.strip()[:300],
              expires_at=_now() + timedelta(hours=ttl_hours))
    await uow.stories.add(s)
    return s


async def stories_feed(uow, me: str) -> list[Story]:
    """Stories actives de moi + amis/suivis (non expirées, ordre chronologique)."""
    following = await uow.edges.following_ids(me)
    blocked = await uow.edges.blocked_ids(me)
    authors = [a for a in ([me] + following) if a not in blocked]
    return await uow.stories.active_by_authors(authors, _now())


async def view_story(uow, me: str, story_id: str) -> Story:
    s = await uow.stories.get(story_id)
    if not s or _aware(s.expires_at) <= _now():
        raise LookupError("Story expirée ou introuvable")
    if s.author_id != me:
        following = set(await uow.edges.following_ids(me))
        if s.author_id not in following:
            raise PermissionError("Non autorisé")
    await uow.stories.record_view(story_id, me)
    return s


async def story_viewers(uow, me: str, story_id: str) -> list[str] | None:
    s = await uow.stories.get(story_id)
    if not s or s.author_id != me:
        return None  # seul l'auteur voit ses spectateurs
    return await uow.stories.viewer_ids(story_id)
