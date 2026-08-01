"""Adaptateurs SQLAlchemy des ports de persistance."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Edge, Post


class SqlAlchemyPostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, post: Post) -> None:
        self.session.add(post)

    async def get(self, post_id: str) -> Post | None:
        return await self.session.get(Post, post_id)

    async def list_recent_by_authors(self, author_ids: list[str], limit: int = 30,
                                     before: datetime | None = None) -> list[Post]:
        if not author_ids:
            return []
        stmt = select(Post).where(Post.author_id.in_(author_ids), Post.deleted_at.is_(None))
        if before is not None:
            stmt = stmt.where(Post.created_at < before)
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
