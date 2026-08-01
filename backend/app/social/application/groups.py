"""Use cases 'groupes' : création, adhésion (public/privé), rôles, file de validation, fil de groupe."""
from __future__ import annotations

from ..adapters.persistence.models import Group
from .access import view_relation
from .posts import audience_of

_MOD = {"admin", "moderator"}


async def _my_role(uow, me: str, group_id: str) -> str | None:
    m = await uow.groups.membership(group_id, me)
    return m.role if (m and m.status == "active") else None


async def create_group(uow, owner_id: str, name: str, description: str | None = None,
                       privacy: str = "public") -> Group:
    if not (name or "").strip():
        raise ValueError("Nom requis")
    if privacy not in ("public", "private", "secret"):
        privacy = "public"
    g = Group(name=name.strip()[:120], description=(description or None), privacy=privacy, owner_id=owner_id)
    await uow.groups.create(g)
    await uow.session.flush()
    await uow.groups.add_member(g.id, owner_id, role="admin", status="active")
    return g


async def join_group(uow, me: str, group_id: str) -> str:
    g = await uow.groups.get(group_id)
    if not g:
        raise LookupError("Groupe introuvable")
    existing = await uow.groups.membership(group_id, me)
    if existing:
        return existing.status
    status = "active" if g.privacy == "public" else "pending"
    await uow.groups.add_member(group_id, me, "member", status)
    return status


async def approve_member(uow, me: str, group_id: str, user_id: str) -> None:
    if await _my_role(uow, me, group_id) not in _MOD:
        raise PermissionError("Réservé aux modérateurs")
    m = await uow.groups.membership(group_id, user_id)
    if not m or m.status != "pending":
        raise LookupError("Aucune demande")
    m.status = "active"


async def reject_member(uow, me: str, group_id: str, user_id: str) -> None:
    if await _my_role(uow, me, group_id) not in _MOD:
        raise PermissionError("Réservé aux modérateurs")
    await uow.groups.remove_member(group_id, user_id)


async def set_role(uow, me: str, group_id: str, user_id: str, role: str) -> None:
    g = await uow.groups.get(group_id)
    if not g or g.owner_id != me:
        raise PermissionError("Réservé au propriétaire")
    if role not in ("admin", "moderator", "member"):
        raise ValueError("Rôle invalide")
    m = await uow.groups.membership(group_id, user_id)
    if not m:
        raise LookupError("Membre introuvable")
    m.role = role


async def leave_group(uow, me: str, group_id: str) -> None:
    await uow.groups.remove_member(group_id, me)


async def can_post_to_group(uow, me: str, group_id: str) -> bool:
    return await uow.groups.is_member(group_id, me)


async def group_feed(uow, policy, me: str, group_id: str, *, limit: int = 30):
    g = await uow.groups.get(group_id)
    if not g:
        return None
    member = await uow.groups.is_member(group_id, me)
    if not member and g.privacy != "public":
        return None  # groupe privé/secret : réservé aux membres
    posts = await uow.posts.list_by_group(group_id, limit=limit)
    out = []
    for p in posts:
        rel = await view_relation(uow, me, p)
        if policy.can_view_post(me, audience_of(p), rel):
            out.append(p)
    return out
