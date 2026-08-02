"""Unit of Work SQLAlchemy : une transaction = une session, avec les dépôts branchés."""
from __future__ import annotations

from .db import get_sessionmaker
from .repositories import (SqlAlchemyBookmarkRepository, SqlAlchemyCircleRepository,
                           SqlAlchemyCommentRepository, SqlAlchemyEdgeRepository,
                           SqlAlchemyEventRepository, SqlAlchemyFeedEntryRepository,
                           SqlAlchemyFeedSeenRepository,
                           SqlAlchemyGroupRepository, SqlAlchemyHiddenRepository,
                           SqlAlchemyModerationRepository, SqlAlchemyPageRepository,
                           SqlAlchemyPostRepository, SqlAlchemyProfileRepository,
                           SqlAlchemyReactionRepository, SqlAlchemyReportRepository,
                           SqlAlchemyStoryRepository)


class SqlAlchemyUnitOfWork:
    def __init__(self, sessionmaker=None):
        self._sessionmaker = sessionmaker or get_sessionmaker()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._sessionmaker()
        self.posts = SqlAlchemyPostRepository(self.session)
        self.edges = SqlAlchemyEdgeRepository(self.session)
        self.reactions = SqlAlchemyReactionRepository(self.session)
        self.comments = SqlAlchemyCommentRepository(self.session)
        self.bookmarks = SqlAlchemyBookmarkRepository(self.session)
        self.circles = SqlAlchemyCircleRepository(self.session)
        self.profiles = SqlAlchemyProfileRepository(self.session)
        self.hidden = SqlAlchemyHiddenRepository(self.session)
        self.groups = SqlAlchemyGroupRepository(self.session)
        self.stories = SqlAlchemyStoryRepository(self.session)
        self.pages = SqlAlchemyPageRepository(self.session)
        self.events = SqlAlchemyEventRepository(self.session)
        self.reports = SqlAlchemyReportRepository(self.session)
        self.moderation = SqlAlchemyModerationRepository(self.session)
        self.feed_seen = SqlAlchemyFeedSeenRepository(self.session)
        self.feed_entries = SqlAlchemyFeedEntryRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
