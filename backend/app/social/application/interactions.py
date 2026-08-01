"""Use cases 'interactions' : réactions, commentaires imbriqués, partages, bookmarks."""
from __future__ import annotations

from ...helpers import now as _now
from ..adapters.persistence.models import Comment, Post
from ..domain.policy import PolicyService
from .posts import audience_of
from .relations import resolve_relation

REACTIONS = {"like", "love", "bravo", "support", "haha", "wow", "sad", "grr"}
_MAX_DEPTH = 6


# ---------------- Réactions ----------------
async def _refresh_like_count(uow, post: Post) -> None:
    await uow.session.flush()
    s = await uow.reactions.summaries("post", [post.id])
    post.like_count = s.get(post.id, {}).get("total", 0)


async def react_post(uow, policy: PolicyService, viewer_id: str, post_id: str, rtype: str) -> int:
    if rtype not in REACTIONS:
        raise ValueError("Réaction invalide")
    post = await uow.posts.get(post_id)
    if not post or post.deleted_at is not None:
        raise LookupError("Introuvable")
    rel = await resolve_relation(uow.edges, viewer_id, post.author_id)
    if not policy.can_react(viewer_id, audience_of(post), rel):
        raise PermissionError("Non autorisé")
    await uow.reactions.set("post", post_id, viewer_id, rtype)
    await _refresh_like_count(uow, post)
    return post.like_count


async def unreact_post(uow, viewer_id: str, post_id: str) -> int:
    post = await uow.posts.get(post_id)
    if not post:
        raise LookupError("Introuvable")
    await uow.reactions.remove("post", post_id, viewer_id)
    await _refresh_like_count(uow, post)
    return post.like_count


async def react_comment(uow, policy: PolicyService, viewer_id: str, comment_id: str, rtype: str) -> None:
    if rtype not in REACTIONS:
        raise ValueError("Réaction invalide")
    c = await uow.comments.get(comment_id)
    if not c or c.deleted_at is not None:
        raise LookupError("Introuvable")
    post = await uow.posts.get(c.post_id)
    rel = await resolve_relation(uow.edges, viewer_id, post.author_id)
    if not policy.can_react(viewer_id, audience_of(post), rel):
        raise PermissionError("Non autorisé")
    await uow.reactions.set("comment", comment_id, viewer_id, rtype)


async def unreact_comment(uow, viewer_id: str, comment_id: str) -> None:
    await uow.reactions.remove("comment", comment_id, viewer_id)


# ---------------- Commentaires (imbriqués) ----------------
async def add_comment(uow, policy: PolicyService, viewer_id: str, post_id: str,
                      body: str, parent_id: str | None = None) -> Comment:
    text = (body or "").strip()
    if not text:
        raise ValueError("Commentaire vide")
    post = await uow.posts.get(post_id)
    if not post or post.deleted_at is not None:
        raise LookupError("Introuvable")
    rel = await resolve_relation(uow.edges, viewer_id, post.author_id)
    if not policy.can_comment(viewer_id, audience_of(post), rel):
        raise PermissionError("Non autorisé")
    depth, path = 0, ""
    if parent_id:
        parent = await uow.comments.get(parent_id)
        if not parent or parent.post_id != post_id or parent.deleted_at is not None:
            raise ValueError("Réponse invalide")
        depth = min(parent.depth + 1, _MAX_DEPTH)
        path = f"{parent.path}{parent.id}/"
    c = Comment(post_id=post_id, parent_id=parent_id, path=path, depth=depth,
                author_id=viewer_id, body_text=text)
    await uow.comments.add(c)
    await uow.session.flush()
    post.comment_count = await uow.comments.count_by_post(post_id)
    return c


async def list_comments(uow, policy: PolicyService, viewer_id: str, post_id: str) -> list[Comment] | None:
    post = await uow.posts.get(post_id)
    if not post or post.deleted_at is not None:
        return None
    rel = await resolve_relation(uow.edges, viewer_id, post.author_id)
    if not policy.can_view_post(viewer_id, audience_of(post), rel):
        return None
    return await uow.comments.list_by_post(post_id)


async def delete_comment(uow, viewer_id: str, comment_id: str) -> bool:
    c = await uow.comments.get(comment_id)
    if not c or c.deleted_at is not None:
        return False
    post = await uow.posts.get(c.post_id)
    # auteur du commentaire OU auteur du post (modération de son propre post)
    if viewer_id != c.author_id and (not post or viewer_id != post.author_id):
        raise PermissionError("Non autorisé")
    c.deleted_at = _now()
    c.body_text = ""
    if post:
        await uow.session.flush()
        post.comment_count = await uow.comments.count_by_post(post.id)
    return True


# ---------------- Partage ----------------
async def share_post(uow, policy: PolicyService, viewer_id: str, post_id: str, *,
                     body: str | None = None, visibility: str = "public") -> Post:
    from ..domain.visibility import Visibility
    original = await uow.posts.get(post_id)
    if not original or original.deleted_at is not None:
        raise LookupError("Introuvable")
    rel = await resolve_relation(uow.edges, viewer_id, original.author_id)
    aud = audience_of(original)
    if not policy.can_view_post(viewer_id, aud, rel):
        raise LookupError("Introuvable")  # ne révèle pas l'existence d'un post non visible
    if not policy.can_share(viewer_id, aud, rel):
        raise PermissionError("Partage non autorisé")  # visible mais non public
    shared = Post(author_id=viewer_id, body_text=((body or "").strip() or None),
                  visibility=Visibility(visibility).value, audience={}, post_type="share",
                  shared_post_id=original.id)
    await uow.posts.add(shared)
    await uow.session.flush()
    return shared


# ---------------- Bookmarks ----------------
async def toggle_bookmark(uow, policy: PolicyService, viewer_id: str, post_id: str) -> bool:
    post = await uow.posts.get(post_id)
    if not post or post.deleted_at is not None:
        raise LookupError("Introuvable")
    rel = await resolve_relation(uow.edges, viewer_id, post.author_id)
    if not policy.can_view_post(viewer_id, audience_of(post), rel):
        raise PermissionError("Non autorisé")
    return await uow.bookmarks.toggle(viewer_id, post_id)


async def list_bookmarks(uow, policy: PolicyService, viewer_id: str) -> list[Post]:
    ids = await uow.bookmarks.list_post_ids(viewer_id)
    out = []
    for pid in ids:
        p = await uow.posts.get(pid)
        if not p or p.deleted_at is not None:
            continue
        rel = await resolve_relation(uow.edges, viewer_id, p.author_id)
        if policy.can_view_post(viewer_id, audience_of(p), rel):
            out.append(p)
    return out
