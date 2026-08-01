"""Relation d'accès à un POST : combine relation de graphe + appartenance au groupe du post."""
from __future__ import annotations

from dataclasses import replace

from .relations import resolve_relation


async def view_relation(uow, viewer_id: str, post):
    """ViewerRelation pour ce post précis (ajoute l'appartenance/rôle de groupe si post de groupe)."""
    rel = await resolve_relation(uow, viewer_id, post.author_id)
    if getattr(post, "group_id", None):
        m = await uow.groups.membership(post.group_id, viewer_id)
        if m and m.status == "active":
            rel = replace(rel, is_group_member=True, group_role=m.role)
    return rel
