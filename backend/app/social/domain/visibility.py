"""Règles de visibilité d'un contenu social — value objects purs (aucune I/O).

Sépare le QUOI (l'audience choisie d'un post) du QUI (la relation entre le lecteur et l'auteur),
pour que la décision d'accès soit déterministe et entièrement testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Visibility(str, Enum):
    PUBLIC = "public"          # tout le monde
    FRIENDS = "friends"        # amis (relation bidirectionnelle acceptée)
    FRIENDS_EXCEPT = "friends_except"  # amis sauf une liste
    CIRCLES = "circles"        # cercles/listes précis
    ONLY_ME = "only_me"        # l'auteur seul
    GROUP = "group"            # membres d'un groupe


@dataclass(frozen=True)
class PostAudience:
    """L'audience telle que définie sur le post (le QUOI)."""
    visibility: Visibility
    author_id: str
    circle_ids: frozenset[str] = field(default_factory=frozenset)   # pour CIRCLES
    excluded_ids: frozenset[str] = field(default_factory=frozenset)  # pour FRIENDS_EXCEPT
    group_id: str | None = None
    deleted: bool = False


@dataclass(frozen=True)
class ViewerRelation:
    """La relation entre le lecteur et l'auteur/le contexte (le QUI)."""
    is_friend: bool = False
    is_blocked: bool = False               # blocage dans un sens ou l'autre
    is_following: bool = False
    viewer_circle_ids: frozenset[str] = field(default_factory=frozenset)  # cercles de l'auteur où est le lecteur
    is_group_member: bool = False
    group_role: str | None = None          # 'admin' | 'moderator' | 'member' | None


def can_view(viewer_id: str, post: PostAudience, rel: ViewerRelation) -> bool:
    """Le lecteur peut-il VOIR ce post ? Décision pure et déterministe."""
    is_author = viewer_id == post.author_id
    if post.deleted:
        return False  # tombstone géré à l'API ; le contenu n'est plus servi
    if is_author:
        return True
    if rel.is_blocked:
        return False  # le blocage prime sur tout (sauf sa propre vue)

    v = post.visibility
    if v == Visibility.PUBLIC:
        return True
    if v == Visibility.ONLY_ME:
        return False
    if v == Visibility.FRIENDS:
        return rel.is_friend
    if v == Visibility.FRIENDS_EXCEPT:
        return rel.is_friend and viewer_id not in post.excluded_ids
    if v == Visibility.CIRCLES:
        return bool(rel.viewer_circle_ids & post.circle_ids)
    if v == Visibility.GROUP:
        return rel.is_group_member
    return False
