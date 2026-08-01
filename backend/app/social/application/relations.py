"""Pont entre le graphe (edges) et le domaine pur (ViewerRelation)."""
from __future__ import annotations

from ..domain.visibility import ViewerRelation


async def resolve_relation(edges, viewer_id: str, author_id: str) -> ViewerRelation:
    """Construit la relation lecteur↔auteur à partir des arêtes du graphe."""
    if viewer_id == author_id:
        return ViewerRelation()  # non pertinent : l'auteur se voit toujours (géré par le domaine)
    kinds = await edges.kinds_between(viewer_id, author_id)
    is_friend = "out:friend" in kinds and "in:friend" in kinds  # amitié = bidirectionnelle
    is_blocked = "out:block" in kinds or "in:block" in kinds
    is_following = "out:follow" in kinds
    # cercles / appartenance de groupe : couches 4 et 6
    return ViewerRelation(is_friend=is_friend, is_blocked=is_blocked, is_following=is_following)
