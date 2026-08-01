"""Adaptateurs SQLAlchemy des ports de persistance."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Edge, Post


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
