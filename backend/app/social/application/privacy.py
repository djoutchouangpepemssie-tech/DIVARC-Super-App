"""Use cases 'RGPD' (Couche 9) : portabilité (export) + droit à l'oubli (effacement).

Périmètre = contexte social (Postgres) uniquement. Le compte Mongo (identité, wallet,
messagerie) n'est PAS touché ici : l'effacement du compte global relève d'un autre flux.
"""
from __future__ import annotations

from ...helpers import now as _now


async def export_my_data(uow, user_id: str) -> dict:
    """Rassemble TOUTES les données sociales de l'utilisateur en un objet JSON portable."""
    profile = await uow.profiles.get(user_id)
    posts = await uow.posts.all_by_author(user_id)
    comments = await uow.comments.all_by_author(user_id)
    reactions = await uow.reactions.all_by_user(user_id)
    edges = await uow.edges.all_involving(user_id)
    bookmarks = await uow.bookmarks.list_post_ids(user_id, limit=10000)
    groups = await uow.groups.my_groups(user_id)
    pages = await uow.pages.managed_by(user_id)

    def _post(p):
        return {"id": p.id, "body": p.body_text, "visibility": p.visibility,
                "type": p.post_type, "groupId": p.group_id,
                "media": [{"url": m.media_url, "kind": m.kind, "alt": m.alt_text} for m in p.media],
                "createdAt": p.created_at.isoformat(), "deleted": p.deleted_at is not None}

    return {
        "exportedAt": _now().isoformat(),
        "userId": user_id,
        "profile": None if not profile else {
            "displayName": profile.display_name, "handle": profile.handle,
            "bio": profile.bio, "avatarUrl": profile.avatar_url, "coverUrl": profile.cover_url,
            "createdAt": profile.created_at.isoformat()},
        "posts": [_post(p) for p in posts],
        "comments": [{"id": c.id, "postId": c.post_id, "body": c.body_text,
                      "createdAt": c.created_at.isoformat(), "deleted": c.deleted_at is not None}
                     for c in comments],
        "reactions": [{"subjectType": r.subject_type, "subjectId": r.subject_id,
                       "type": r.type, "at": r.created_at.isoformat()} for r in reactions],
        "relations": [{"src": e.src, "dst": e.dst, "kind": e.kind, "status": e.status}
                      for e in edges],
        "bookmarks": list(bookmarks),
        "groups": [{"id": g.id, "name": g.name} for g in groups],
        "pages": [{"id": p.id, "name": p.name} for p in pages],
        "counts": {"posts": len(posts), "comments": len(comments), "reactions": len(reactions),
                   "relations": len(edges), "bookmarks": len(bookmarks)},
    }


async def erase_my_data(uow, user_id: str) -> dict:
    """Droit à l'oubli : anonymise le profil + soft-delete posts/commentaires + supprime
    réactions/relations/favoris. IRRÉVERSIBLE. Ne touche pas le compte Mongo."""
    now = _now()
    posts = await uow.posts.all_by_author(user_id, include_deleted=False)
    for p in posts:
        p.deleted_at = now
        p.body_text = None
        p.moderation_state = "erased"
    comments = await uow.comments.all_by_author(user_id, include_deleted=False)
    for c in comments:
        c.deleted_at = now
        c.body_text = "[supprimé]"
    await uow.reactions.delete_all_by_user(user_id)
    await uow.edges.delete_all_for(user_id)
    await uow.bookmarks.delete_all_for(user_id)
    # Profil anonymisé (on garde la ligne mais on vide tout — upsert ignore les None,
    # donc on modifie l'objet directement pour réellement effacer les champs).
    prof = await uow.profiles.get(user_id)
    if prof:
        prof.display_name = "Compte supprimé"
        prof.handle = None
        prof.bio = None
        prof.avatar_url = None
        prof.cover_url = None
        prof.info = {}
        prof.verified_eudi = False
    await uow.commit()
    return {"erased": True, "posts": len(posts), "comments": len(comments)}
