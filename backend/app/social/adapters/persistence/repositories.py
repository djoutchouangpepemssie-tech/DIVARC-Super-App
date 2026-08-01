"""Adaptateurs SQLAlchemy des ports de persistance."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Bookmark, Comment, Edge, Post, Reaction


class SqlAlchemyPostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, post: Post) -> None:
        self.session.add(post)

    async def get(self, post_id: str) -> Post | None:
        # eager-load des médias pour éviter tout chargement paresseux hors contexte async
        stmt = select(Post).options(selectinload(Post.media)).where(Post.id == post_id)
        return await self.session.scalar(stmt)

    async def list_recent_by_authors(self, author_ids: list[str], limit: int = 30,
                                     before_time: datetime | None = None,
                                     before_id: str | None = None) -> list[Post]:
        """Pagination par CURSEUR (created_at, id) — jamais d'offset. Exclut les supprimés."""
        if not author_ids:
            return []
        stmt = (select(Post).options(selectinload(Post.media))
                .where(Post.author_id.in_(author_ids), Post.deleted_at.is_(None)))
        if before_time is not None:
            stmt = stmt.where(or_(Post.created_at < before_time,
                                  and_(Post.created_at == before_time, Post.id < (before_id or ""))))
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())


class SqlAlchemyEdgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, edge: Edge) -> None:
        self.session.add(edge)

    async def exists(self, src: str, dst: str, kind: str) -> bool:
        stmt = select(Edge.id).where(Edge.src == src, Edge.dst == dst, Edge.kind == kind)
        return (await self.session.scalar(stmt)) is not None

    async def kinds_between(self, a: str, b: str) -> set[str]:
        stmt = select(Edge.src, Edge.kind).where(
            or_((Edge.src == a) & (Edge.dst == b), (Edge.src == b) & (Edge.dst == a)))
        rows = (await self.session.execute(stmt)).all()
        return {f"{'out' if src == a else 'in'}:{kind}" for src, kind in rows}

    async def following_ids(self, user_id: str) -> list[str]:
        """Auteurs dont l'utilisateur voit les posts : amis + suivis (arêtes actives)."""
        stmt = select(Edge.dst).where(Edge.src == user_id,
                                      Edge.kind.in_(("friend", "follow")), Edge.status == "active")
        return list((await self.session.scalars(stmt)).all())

    async def blocked_ids(self, user_id: str) -> set[str]:
        stmt = select(Edge.src, Edge.dst).where(
            Edge.kind == "block", or_(Edge.src == user_id, Edge.dst == user_id))
        rows = (await self.session.execute(stmt)).all()
        return {(dst if src == user_id else src) for src, dst in rows}


class SqlAlchemyReactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set(self, subject_type: str, subject_id: str, user_id: str, rtype: str) -> None:
        existing = await self.session.scalar(select(Reaction).where(
            Reaction.subject_type == subject_type, Reaction.subject_id == subject_id,
            Reaction.user_id == user_id))
        if existing:
            existing.type = rtype
        else:
            self.session.add(Reaction(subject_type=subject_type, subject_id=subject_id,
                                      user_id=user_id, type=rtype))

    async def remove(self, subject_type: str, subject_id: str, user_id: str) -> None:
        await self.session.execute(delete(Reaction).where(
            Reaction.subject_type == subject_type, Reaction.subject_id == subject_id,
            Reaction.user_id == user_id))

    async def summaries(self, subject_type: str, subject_ids: list[str]) -> dict:
        """{subject_id: {'total': n, 'byType': {type: n}}}"""
        if not subject_ids:
            return {}
        stmt = (select(Reaction.subject_id, Reaction.type, func.count())
                .where(Reaction.subject_type == subject_type, Reaction.subject_id.in_(subject_ids))
                .group_by(Reaction.subject_id, Reaction.type))
        out: dict = {}
        for sid, rtype, n in (await self.session.execute(stmt)).all():
            d = out.setdefault(sid, {"total": 0, "byType": {}})
            d["byType"][rtype] = n
            d["total"] += n
        return out

    async def mine(self, subject_type: str, subject_ids: list[str], user_id: str) -> dict:
        if not subject_ids:
            return {}
        stmt = select(Reaction.subject_id, Reaction.type).where(
            Reaction.subject_type == subject_type, Reaction.subject_id.in_(subject_ids),
            Reaction.user_id == user_id)
        return {sid: t for sid, t in (await self.session.execute(stmt)).all()}


class SqlAlchemyCommentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, comment: Comment) -> None:
        self.session.add(comment)

    async def get(self, comment_id: str) -> Comment | None:
        return await self.session.get(Comment, comment_id)

    async def list_by_post(self, post_id: str, limit: int = 200) -> list[Comment]:
        stmt = (select(Comment).where(Comment.post_id == post_id)
                .order_by(Comment.path.asc(), Comment.created_at.asc()).limit(limit))
        return list((await self.session.scalars(stmt)).all())

    async def count_by_post(self, post_id: str) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(Comment).where(
                Comment.post_id == post_id, Comment.deleted_at.is_(None))) or 0


class SqlAlchemyBookmarkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def toggle(self, user_id: str, post_id: str) -> bool:
        existing = await self.session.scalar(select(Bookmark).where(
            Bookmark.user_id == user_id, Bookmark.post_id == post_id))
        if existing:
            await self.session.delete(existing)
            return False
        self.session.add(Bookmark(user_id=user_id, post_id=post_id))
        return True

    async def list_post_ids(self, user_id: str, limit: int = 100) -> list[str]:
        stmt = (select(Bookmark.post_id).where(Bookmark.user_id == user_id)
                .order_by(Bookmark.created_at.desc()).limit(limit))
        return list((await self.session.scalars(stmt)).all())

    async def mine_set(self, user_id: str, post_ids: list[str]) -> set[str]:
        if not post_ids:
            return set()
        stmt = select(Bookmark.post_id).where(Bookmark.user_id == user_id, Bookmark.post_id.in_(post_ids))
        return set((await self.session.scalars(stmt)).all())
