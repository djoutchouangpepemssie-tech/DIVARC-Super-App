"""Couche 1 — persistance SQLAlchemy async (testée sur SQLite async, prête pour Postgres)."""
import asyncio

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.social.adapters.persistence import models as m
from app.social.adapters.persistence.db import Base
from app.social.adapters.persistence.repositories import (SqlAlchemyEdgeRepository,
                                                          SqlAlchemyPostRepository)
from app.social.adapters.persistence.uow import SqlAlchemyUnitOfWork


def _make():
    # SQLite en mémoire partagé (StaticPool) pour toutes les connexions du test
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False},
                                 poolclass=StaticPool)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _create(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _run(coro):
    return asyncio.run(coro)


def test_post_crud_et_feed_par_curseur():
    async def scenario():
        engine, sm = _make()
        await _create(engine)
        async with sm() as s:
            repo = SqlAlchemyPostRepository(s)
            p1 = m.Post(author_id="a", body_text="1", visibility="public")
            p1.media.append(m.PostMedia(media_url="/img/1", alt_text="une photo"))
            await repo.add(p1)
            await s.commit()
            p2 = m.Post(author_id="a", body_text="2", visibility="public")
            await repo.add(p2)
            await s.commit()
        async with sm() as s:
            repo = SqlAlchemyPostRepository(s)
            feed = await repo.list_recent_by_authors(["a"], limit=10)
            assert [p.body_text for p in feed] == ["2", "1"]  # plus récent d'abord
            assert await repo.list_recent_by_authors([], limit=10) == []
            got = await repo.get(feed[-1].id)
            assert got.media[0].alt_text == "une photo"  # média + a11y persistés
        await engine.dispose()
    _run(scenario())


def test_reaction_unique_par_user():
    async def scenario():
        engine, sm = _make()
        await _create(engine)
        async with sm() as s:
            s.add(m.Reaction(subject_type="post", subject_id="p1", user_id="u", type="like"))
            await s.commit()
        with pytest.raises(IntegrityError):
            async with sm() as s:
                s.add(m.Reaction(subject_type="post", subject_id="p1", user_id="u", type="love"))
                await s.commit()
        await engine.dispose()
    _run(scenario())


def test_edges_relation_bidirectionnelle():
    async def scenario():
        engine, sm = _make()
        await _create(engine)
        async with SqlAlchemyUnitOfWork(sm) as uow:
            await uow.edges.add(m.Edge(src="a", dst="b", kind="friend"))
            await uow.edges.add(m.Edge(src="b", dst="a", kind="friend"))
            await uow.edges.add(m.Edge(src="a", dst="b", kind="follow"))
            await uow.commit()
        async with SqlAlchemyUnitOfWork(sm) as uow:
            assert await uow.edges.exists("a", "b", "friend") is True
            kinds = await uow.edges.kinds_between("a", "b")
            assert "out:friend" in kinds and "in:friend" in kinds and "out:follow" in kinds
        await engine.dispose()
    _run(scenario())
