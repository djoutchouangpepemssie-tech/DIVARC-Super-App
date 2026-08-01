"""PolicyService — autorisation centralisée du contexte social (pur, testable).

Chaque lecture/écriture sensible passe par ici : voir, réagir, commenter, éditer, supprimer.
Applique visibilité + blocage + rôle, de façon déterministe.
"""
from __future__ import annotations

from .visibility import PostAudience, ViewerRelation, Visibility, can_view

_GROUP_MOD_ROLES = {"admin", "moderator"}


class PolicyService:
    """Service sans état : toutes les décisions dépendent uniquement des arguments."""

    def can_view_post(self, viewer_id: str, post: PostAudience, rel: ViewerRelation) -> bool:
        return can_view(viewer_id, post, rel)

    def can_comment(self, viewer_id: str, post: PostAudience, rel: ViewerRelation,
                    comments_closed: bool = False) -> bool:
        if comments_closed and viewer_id != post.author_id:
            return False
        return self.can_view_post(viewer_id, post, rel)

    def can_react(self, viewer_id: str, post: PostAudience, rel: ViewerRelation) -> bool:
        return self.can_view_post(viewer_id, post, rel)

    def can_share(self, viewer_id: str, post: PostAudience, rel: ViewerRelation) -> bool:
        # On ne partage que ce qui est public (respect de l'audience d'origine).
        if not self.can_view_post(viewer_id, post, rel):
            return False
        return post.visibility == Visibility.PUBLIC

    def can_edit(self, viewer_id: str, post: PostAudience, rel: ViewerRelation) -> bool:
        if post.deleted:
            return False
        return viewer_id == post.author_id

    def can_delete(self, viewer_id: str, post: PostAudience, rel: ViewerRelation) -> bool:
        if post.deleted:
            return False
        if viewer_id == post.author_id:
            return True
        # Modération de groupe : un admin/modérateur peut retirer un post du groupe
        if post.group_id and rel.is_group_member and (rel.group_role in _GROUP_MOD_ROLES):
            return True
        return False
