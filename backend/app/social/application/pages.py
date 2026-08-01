"""Use cases 'pages' : création, rôles, abonnement, publication au nom de la page."""
from __future__ import annotations

from ..adapters.persistence.models import Page

_EDITORS = {"admin", "editor"}


async def create_page(uow, owner_id: str, name: str, category: str | None = None,
                      bio: str | None = None) -> Page:
    if not (name or "").strip():
        raise ValueError("Nom requis")
    p = Page(name=name.strip()[:120], category=(category or None), bio=(bio or None), owner_id=owner_id)
    await uow.pages.create(p)
    await uow.session.flush()
    await uow.pages.set_role(p.id, owner_id, "admin")
    return p


async def can_publish(uow, me: str, page_id: str) -> bool:
    return (await uow.pages.role_of(page_id, me)) in _EDITORS


async def page_feed(uow, page_id: str, *, limit: int = 30):
    # Les posts d'une page sont publics : author_id = page_id
    return await uow.posts.list_recent_by_authors([page_id], limit=limit)
