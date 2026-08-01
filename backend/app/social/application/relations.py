"""Pont entre le graphe (edges + cercles) et le domaine pur (ViewerRelation)."""
from __future__ import annotations

from ..domain.visibility import ViewerRelation


async def resolve_relation(uow, viewer_id: str, author_id: str) -> ViewerRelation:
    """Construit la relation lecteur↔auteur à partir des arêtes et des cercles."""
    if viewer_id == author_id:
        return ViewerRelation()  # l'auteur se voit toujours (géré par le domaine)
    kinds = await uow.edges.kinds_between(viewer_id, author_id)
    is_friend = "out:friend" in kinds and "in:friend" in kinds  # amitié = bidirectionnelle
    is_blocked = "out:block" in kinds or "in:block" in kinds
    is_following = "out:follow" in kinds
    # cercles de l'AUTEUR contenant le LECTEUR (pour l'audience CIRCLES)
    circle_ids = frozenset(await uow.circles.circles_containing(author_id, viewer_id))
    return ViewerRelation(is_friend=is_friend, is_blocked=is_blocked, is_following=is_following,
                          viewer_circle_ids=circle_ids)
