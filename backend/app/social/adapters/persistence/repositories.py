"""Adaptateurs SQLAlchemy des ports de persistance."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (Bookmark, Circle, CircleMember, Comment, Edge, Event, EventRsvp, FeedEntry,
                     FeedSeen, Group, GroupMember, HiddenPost, ModerationAction, Page,
                     PageFollower, PageRole, Post, Profile, Reaction, Report, Story, StoryView)


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

    async def list_by_group(self, group_id: str, limit: int = 30) -> list[Post]:
        stmt = (select(Post).options(selectinload(Post.media))
                .where(Post.group_id == group_id, Post.deleted_at.is_(None))
                .order_by(Post.created_at.desc(), Post.id.desc()).limit(limit))
        return list((await self.session.scalars(stmt)).all())

    async def search_public(self, q: str, limit: int = 20) -> list[Post]:
        like = f"%{q.lower()}%"
        stmt = (select(Post).options(selectinload(Post.media))
                .where(Post.visibility == "public", Post.deleted_at.is_(None),
                       func.lower(Post.body_text).like(like))
                .order_by(Post.created_at.desc()).limit(limit))
        return list((await self.session.scalars(stmt)).all())

    async def all_by_author(self, author_id: str, include_deleted: bool = True) -> list[Post]:
        """Tous les posts d'un auteur (export/effacement RGPD)."""
        stmt = select(Post).options(selectinload(Post.media)).where(Post.author_id == author_id)
        if not include_deleted:
            stmt = stmt.where(Post.deleted_at.is_(None))
        return list((await self.session.scalars(stmt.order_by(Post.created_at))).all())

    async def get_many(self, post_ids: list[str]) -> list[Post]:
        """Charge des posts par ids (média eager). Ordre non garanti — le ranking réordonne."""
        if not post_ids:
            return []
        stmt = (select(Post).options(selectinload(Post.media))
                .where(Post.id.in_(post_ids), Post.deleted_at.is_(None)))
        return list((await self.session.scalars(stmt)).all())

    async def list_recent_by_authors_excluding(self, author_ids: list[str], exclude_ids: set[str],
                                               limit: int = 120) -> list[Post]:
        """Candidats pour le fil classé : posts récents des auteurs, hors posts déjà vus."""
        if not author_ids:
            return []
        stmt = (select(Post).options(selectinload(Post.media))
                .where(Post.author_id.in_(author_ids), Post.deleted_at.is_(None)))
        if exclude_ids:
            stmt = stmt.where(Post.id.not_in(exclude_ids))
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def affinity_counts(self, viewer_id: str, author_ids: list[str]) -> dict:
        """Affinité comportementale viewer→auteur = nb d'interactions (réactions + commentaires)
        du viewer sur les posts de chaque auteur. Une passe SQL par type d'interaction."""
        if not author_ids:
            return {}
        counts: dict = {}
        rx = (await self.session.execute(
            select(Post.author_id, func.count()).select_from(Post)
            .join(Reaction, Reaction.subject_id == Post.id)
            .where(Reaction.subject_type == "post", Reaction.user_id == viewer_id,
                   Post.author_id.in_(author_ids))
            .group_by(Post.author_id))).all()
        for aid, n in rx:
            counts[aid] = counts.get(aid, 0) + n
        cm = (await self.session.execute(
            select(Post.author_id, func.count()).select_from(Post)
            .join(Comment, Comment.post_id == Post.id)
            .where(Comment.author_id == viewer_id, Post.author_id.in_(author_ids))
            .group_by(Post.author_id))).all()
        for aid, n in cm:
            counts[aid] = counts.get(aid, 0) + n
        return counts


class SqlAlchemyFeedSeenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def seen_ids(self, user_id: str) -> set[str]:
        return set((await self.session.scalars(
            select(FeedSeen.post_id).where(FeedSeen.user_id == user_id))).all())

    async def mark_seen(self, user_id: str, post_ids: list[str]) -> None:
        if not post_ids:
            return
        existing = set((await self.session.scalars(
            select(FeedSeen.post_id).where(
                FeedSeen.user_id == user_id, FeedSeen.post_id.in_(post_ids)))).all())
        for pid in post_ids:
            if pid not in existing:
                self.session.add(FeedSeen(user_id=user_id, post_id=pid))


class SqlAlchemyFeedEntryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fan_out(self, user_ids, post_id: str, author_id: str, created_at) -> int:
        """Insère une entrée de fil par destinataire (idempotent sur (user_id, post_id))."""
        uids = list(dict.fromkeys(user_ids))  # dédoublonne en gardant l'ordre
        if not uids:
            return 0
        existing = set((await self.session.scalars(
            select(FeedEntry.user_id).where(
                FeedEntry.post_id == post_id, FeedEntry.user_id.in_(uids)))).all())
        n = 0
        for uid in uids:
            if uid not in existing:
                self.session.add(FeedEntry(user_id=uid, post_id=post_id,
                                           author_id=author_id, created_at=created_at))
                n += 1
        return n

    async def recent_post_ids(self, user_id: str, exclude_ids: set[str], limit: int) -> list[str]:
        stmt = select(FeedEntry.post_id).where(FeedEntry.user_id == user_id)
        if exclude_ids:
            stmt = stmt.where(FeedEntry.post_id.not_in(exclude_ids))
        stmt = stmt.order_by(FeedEntry.created_at.desc(), FeedEntry.post_id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def count_for(self, user_id: str) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(FeedEntry).where(FeedEntry.user_id == user_id)) or 0


class SqlAlchemyHiddenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def hide(self, user_id: str, post_id: str) -> None:
        exists = await self.session.scalar(select(HiddenPost.id).where(
            HiddenPost.user_id == user_id, HiddenPost.post_id == post_id))
        if not exists:
            self.session.add(HiddenPost(user_id=user_id, post_id=post_id))

    async def hidden_ids(self, user_id: str) -> set[str]:
        return set((await self.session.scalars(
            select(HiddenPost.post_id).where(HiddenPost.user_id == user_id))).all())


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

    async def followers_of(self, author_id: str) -> list[str]:
        """Qui reçoit les posts de l'auteur (fan-out) : ses amis + ceux qui le suivent."""
        stmt = select(Edge.src).where(Edge.dst == author_id,
                                      Edge.kind.in_(("friend", "follow")), Edge.status == "active")
        return list((await self.session.scalars(stmt)).all())

    async def blocked_ids(self, user_id: str) -> set[str]:
        stmt = select(Edge.src, Edge.dst).where(
            Edge.kind == "block", or_(Edge.src == user_id, Edge.dst == user_id))
        rows = (await self.session.execute(stmt)).all()
        return {(dst if src == user_id else src) for src, dst in rows}

    async def set(self, src: str, dst: str, kind: str, status: str = "active") -> None:
        e = await self.session.scalar(select(Edge).where(
            Edge.src == src, Edge.dst == dst, Edge.kind == kind))
        if e:
            e.status = status
        else:
            self.session.add(Edge(src=src, dst=dst, kind=kind, status=status))

    async def remove(self, src: str, dst: str, kind: str) -> None:
        await self.session.execute(delete(Edge).where(
            Edge.src == src, Edge.dst == dst, Edge.kind == kind))

    async def get_status(self, src: str, dst: str, kind: str) -> str | None:
        return await self.session.scalar(select(Edge.status).where(
            Edge.src == src, Edge.dst == dst, Edge.kind == kind))

    async def list_out(self, user_id: str, kind: str) -> list[str]:
        return list((await self.session.scalars(
            select(Edge.dst).where(Edge.src == user_id, Edge.kind == kind))).all())

    async def list_in(self, user_id: str, kind: str) -> list[str]:
        return list((await self.session.scalars(
            select(Edge.src).where(Edge.dst == user_id, Edge.kind == kind))).all())

    async def muted_ids(self, user_id: str) -> set[str]:
        return set(await self.list_out(user_id, "mute"))

    async def all_involving(self, user_id: str) -> list["Edge"]:
        return list((await self.session.scalars(
            select(Edge).where(or_(Edge.src == user_id, Edge.dst == user_id)))).all())

    async def delete_all_for(self, user_id: str) -> None:
        await self.session.execute(delete(Edge).where(or_(Edge.src == user_id, Edge.dst == user_id)))


class SqlAlchemyCircleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, owner_id: str, name: str) -> Circle:
        c = Circle(owner_id=owner_id, name=name[:60])
        self.session.add(c)
        return c

    async def get(self, circle_id: str) -> Circle | None:
        return await self.session.get(Circle, circle_id)

    async def list_owned(self, owner_id: str) -> list[Circle]:
        return list((await self.session.scalars(
            select(Circle).where(Circle.owner_id == owner_id).order_by(Circle.created_at))).all())

    async def delete(self, circle_id: str) -> None:
        await self.session.execute(delete(CircleMember).where(CircleMember.circle_id == circle_id))
        await self.session.execute(delete(Circle).where(Circle.id == circle_id))

    async def add_member(self, circle_id: str, owner_id: str, member_id: str) -> None:
        exists = await self.session.scalar(select(CircleMember.id).where(
            CircleMember.circle_id == circle_id, CircleMember.member_id == member_id))
        if not exists:
            self.session.add(CircleMember(circle_id=circle_id, owner_id=owner_id, member_id=member_id))

    async def remove_member(self, circle_id: str, member_id: str) -> None:
        await self.session.execute(delete(CircleMember).where(
            CircleMember.circle_id == circle_id, CircleMember.member_id == member_id))

    async def member_ids(self, circle_id: str) -> list[str]:
        return list((await self.session.scalars(
            select(CircleMember.member_id).where(CircleMember.circle_id == circle_id))).all())

    async def circles_containing(self, owner_id: str, member_id: str) -> set[str]:
        """Cercles de `owner` qui contiennent `member` (pour la visibilité CIRCLES)."""
        return set((await self.session.scalars(select(CircleMember.circle_id).where(
            CircleMember.owner_id == owner_id, CircleMember.member_id == member_id))).all())


class SqlAlchemyGroupRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, group: Group) -> None:
        self.session.add(group)

    async def get(self, group_id: str) -> Group | None:
        return await self.session.get(Group, group_id)

    async def add_member(self, group_id: str, user_id: str, role: str = "member", status: str = "active") -> GroupMember:
        m = GroupMember(group_id=group_id, user_id=user_id, role=role, status=status)
        self.session.add(m)
        return m

    async def membership(self, group_id: str, user_id: str) -> GroupMember | None:
        return await self.session.scalar(select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id))

    async def is_member(self, group_id: str, user_id: str) -> bool:
        return (await self.session.scalar(select(GroupMember.id).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id,
            GroupMember.status == "active"))) is not None

    async def remove_member(self, group_id: str, user_id: str) -> None:
        await self.session.execute(delete(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id))

    async def members(self, group_id: str, status: str = "active") -> list[GroupMember]:
        return list((await self.session.scalars(select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.status == status))).all())

    async def my_groups(self, user_id: str) -> list[Group]:
        stmt = (select(Group).join(GroupMember, GroupMember.group_id == Group.id)
                .where(GroupMember.user_id == user_id, GroupMember.status == "active")
                .order_by(Group.created_at.desc()))
        return list((await self.session.scalars(stmt)).all())

    async def discover(self, user_id: str, limit: int = 20) -> list[Group]:
        # groupes publics dont je ne suis pas membre
        sub = select(GroupMember.group_id).where(GroupMember.user_id == user_id)
        stmt = (select(Group).where(Group.privacy == "public", Group.id.not_in(sub))
                .order_by(Group.created_at.desc()).limit(limit))
        return list((await self.session.scalars(stmt)).all())

    async def member_count(self, group_id: str) -> int:
        return await self.session.scalar(select(func.count()).select_from(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.status == "active")) or 0


class SqlAlchemyStoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, story: Story) -> None:
        self.session.add(story)

    async def get(self, story_id: str) -> Story | None:
        return await self.session.get(Story, story_id)

    async def active_by_authors(self, author_ids: list[str], nowdt) -> list[Story]:
        if not author_ids:
            return []
        stmt = (select(Story).where(Story.author_id.in_(author_ids), Story.expires_at > nowdt)
                .order_by(Story.created_at.asc()))
        return list((await self.session.scalars(stmt)).all())

    async def record_view(self, story_id: str, user_id: str) -> None:
        exists = await self.session.scalar(select(StoryView.id).where(
            StoryView.story_id == story_id, StoryView.user_id == user_id))
        if not exists:
            self.session.add(StoryView(story_id=story_id, user_id=user_id))

    async def viewer_ids(self, story_id: str) -> list[str]:
        return list((await self.session.scalars(
            select(StoryView.user_id).where(StoryView.story_id == story_id))).all())


class SqlAlchemyPageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, page: Page) -> None:
        self.session.add(page)

    async def get(self, page_id: str) -> Page | None:
        return await self.session.get(Page, page_id)

    async def get_many(self, ids: list[str]) -> dict[str, Page]:
        if not ids:
            return {}
        rows = (await self.session.scalars(select(Page).where(Page.id.in_(ids)))).all()
        return {p.id: p for p in rows}

    async def set_role(self, page_id: str, user_id: str, role: str) -> None:
        r = await self.session.scalar(select(PageRole).where(
            PageRole.page_id == page_id, PageRole.user_id == user_id))
        if r:
            r.role = role
        else:
            self.session.add(PageRole(page_id=page_id, user_id=user_id, role=role))

    async def role_of(self, page_id: str, user_id: str) -> str | None:
        return await self.session.scalar(select(PageRole.role).where(
            PageRole.page_id == page_id, PageRole.user_id == user_id))

    async def set_follow(self, page_id: str, user_id: str, on: bool) -> bool:
        existing = await self.session.scalar(select(PageFollower).where(
            PageFollower.page_id == page_id, PageFollower.user_id == user_id))
        if on and not existing:
            self.session.add(PageFollower(page_id=page_id, user_id=user_id))
        elif not on and existing:
            await self.session.delete(existing)
        return on

    async def is_following(self, page_id: str, user_id: str) -> bool:
        return (await self.session.scalar(select(PageFollower.id).where(
            PageFollower.page_id == page_id, PageFollower.user_id == user_id))) is not None

    async def follower_count(self, page_id: str) -> int:
        return await self.session.scalar(select(func.count()).select_from(PageFollower).where(
            PageFollower.page_id == page_id)) or 0

    async def followed_ids(self, user_id: str) -> list[str]:
        return list((await self.session.scalars(
            select(PageFollower.page_id).where(PageFollower.user_id == user_id))).all())

    async def follower_user_ids(self, page_id: str) -> list[str]:
        """Utilisateurs abonnés à la page (destinataires du fan-out d'un post de page)."""
        return list((await self.session.scalars(
            select(PageFollower.user_id).where(PageFollower.page_id == page_id))).all())

    async def managed_by(self, user_id: str) -> list[Page]:
        stmt = (select(Page).join(PageRole, PageRole.page_id == Page.id)
                .where(PageRole.user_id == user_id).order_by(Page.created_at.desc()))
        return list((await self.session.scalars(stmt)).all())

    async def discover(self, limit: int = 15) -> list[Page]:
        return list((await self.session.scalars(
            select(Page).order_by(Page.created_at.desc()).limit(limit))).all())


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: Event) -> None:
        self.session.add(event)

    async def get(self, event_id: str) -> Event | None:
        return await self.session.get(Event, event_id)

    async def upcoming(self, nowdt, limit: int = 30) -> list[Event]:
        stmt = (select(Event).where(Event.starts_at >= nowdt)
                .order_by(Event.starts_at.asc()).limit(limit))
        return list((await self.session.scalars(stmt)).all())

    async def by_group(self, group_id: str, limit: int = 30) -> list[Event]:
        return list((await self.session.scalars(select(Event).where(
            Event.group_id == group_id).order_by(Event.starts_at.asc()).limit(limit))).all())

    async def set_rsvp(self, event_id: str, user_id: str, status: str | None) -> None:
        r = await self.session.scalar(select(EventRsvp).where(
            EventRsvp.event_id == event_id, EventRsvp.user_id == user_id))
        if status is None:
            if r:
                await self.session.delete(r)
        elif r:
            r.status = status
        else:
            self.session.add(EventRsvp(event_id=event_id, user_id=user_id, status=status))

    async def my_rsvp(self, event_id: str, user_id: str) -> str | None:
        return await self.session.scalar(select(EventRsvp.status).where(
            EventRsvp.event_id == event_id, EventRsvp.user_id == user_id))

    async def rsvp_counts(self, event_id: str) -> dict:
        stmt = (select(EventRsvp.status, func.count()).where(EventRsvp.event_id == event_id)
                .group_by(EventRsvp.status))
        return {s: n for s, n in (await self.session.execute(stmt)).all()}

    async def attendees(self, event_id: str, status: str) -> list[str]:
        return list((await self.session.scalars(select(EventRsvp.user_id).where(
            EventRsvp.event_id == event_id, EventRsvp.status == status))).all())

    async def my_events(self, user_id: str, nowdt) -> list[Event]:
        # créés par moi OU auxquels j'ai répondu, à venir
        sub = select(EventRsvp.event_id).where(EventRsvp.user_id == user_id)
        stmt = (select(Event).where(Event.starts_at >= nowdt,
                                    or_(Event.owner_id == user_id, Event.id.in_(sub)))
                .order_by(Event.starts_at.asc()))
        return list((await self.session.scalars(stmt)).all())


class SqlAlchemyProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: str) -> Profile | None:
        return await self.session.get(Profile, user_id)

    async def upsert(self, user_id: str, **fields) -> Profile:
        p = await self.session.get(Profile, user_id)
        if not p:
            p = Profile(user_id=user_id)
            self.session.add(p)
        for k, v in fields.items():
            if v is not None and hasattr(p, k):
                setattr(p, k, v)
        return p


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

    async def all_by_user(self, user_id: str) -> list["Reaction"]:
        return list((await self.session.scalars(
            select(Reaction).where(Reaction.user_id == user_id))).all())

    async def delete_all_by_user(self, user_id: str) -> None:
        await self.session.execute(delete(Reaction).where(Reaction.user_id == user_id))


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

    async def all_by_author(self, author_id: str, include_deleted: bool = True) -> list["Comment"]:
        stmt = select(Comment).where(Comment.author_id == author_id)
        if not include_deleted:
            stmt = stmt.where(Comment.deleted_at.is_(None))
        return list((await self.session.scalars(stmt.order_by(Comment.created_at))).all())


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

    async def delete_all_for(self, user_id: str) -> None:
        await self.session.execute(delete(Bookmark).where(Bookmark.user_id == user_id))


class SqlAlchemyReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, report: Report) -> None:
        self.session.add(report)

    async def get(self, report_id: str) -> Report | None:
        return await self.session.get(Report, report_id)

    async def pending_by(self, reporter_id: str, subject_type: str, subject_id: str) -> Report | None:
        return await self.session.scalar(select(Report).where(
            Report.reporter_id == reporter_id, Report.subject_type == subject_type,
            Report.subject_id == subject_id, Report.status == "pending"))

    async def list_by_status(self, status: str, limit: int = 100) -> list[Report]:
        return list((await self.session.scalars(
            select(Report).where(Report.status == status)
            .order_by(Report.created_at.desc()).limit(limit))).all())

    async def counts_by_status(self) -> dict:
        rows = (await self.session.execute(
            select(Report.status, func.count()).group_by(Report.status))).all()
        return {s: n for s, n in rows}

    async def open_count_for(self, subject_type: str, subject_id: str) -> int:
        return await self.session.scalar(select(func.count()).where(
            Report.subject_type == subject_type, Report.subject_id == subject_id,
            Report.status == "pending")) or 0


class SqlAlchemyModerationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, action: ModerationAction) -> None:
        self.session.add(action)

    async def recent(self, limit: int = 50) -> list[ModerationAction]:
        return list((await self.session.scalars(
            select(ModerationAction).order_by(ModerationAction.created_at.desc()).limit(limit))).all())

    async def counts_by_action(self) -> dict:
        rows = (await self.session.execute(
            select(ModerationAction.action, func.count()).group_by(ModerationAction.action))).all()
        return {a: n for a, n in rows}

    async def counts_by_reason(self) -> dict:
        rows = (await self.session.execute(
            select(ModerationAction.reason, func.count())
            .where(ModerationAction.reason.is_not(None)).group_by(ModerationAction.reason))).all()
        return {r: n for r, n in rows}
