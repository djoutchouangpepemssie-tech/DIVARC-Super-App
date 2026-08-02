"""Modèles SQLAlchemy 2.0 du contexte social (cœur — étendu couche par couche).

Clés = ULID (triées par le temps). Références utilisateur = id Mongo (str, pas de FK cross-DB).
Soft-delete via deleted_at. Timestamps UTC.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, TZDateTime, ulid


def _now() -> datetime:
    from ....helpers import now
    return now()


class Profile(Base):
    __tablename__ = "social_profiles"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # id Mongo
    display_name: Mapped[str | None] = mapped_column(String(120))
    handle: Mapped[str | None] = mapped_column(String(40), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    cover_url: Mapped[str | None] = mapped_column(String(512))
    bio: Mapped[str | None] = mapped_column(Text)
    verified_eudi: Mapped[bool] = mapped_column(Boolean, default=False)
    info: Mapped[dict] = mapped_column(default=dict)  # champs opt-in + visibilité par champ
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now, onupdate=_now)


class Post(Base):
    __tablename__ = "social_posts"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    author_id: Mapped[str] = mapped_column(String(64), index=True)
    author_type: Mapped[str] = mapped_column(String(10), default="user")  # user | page
    body_text: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(20), default="public")
    audience: Mapped[dict] = mapped_column(default=dict)  # {circle_ids:[], excluded_ids:[]}
    post_type: Mapped[str] = mapped_column(String(16), default="status")
    group_id: Mapped[str | None] = mapped_column(String(26), index=True)
    shared_post_id: Mapped[str | None] = mapped_column(String(26))
    poll_id: Mapped[str | None] = mapped_column(String(26))
    geo: Mapped[dict | None] = mapped_column(nullable=True)  # opt-in, approximatif
    lang: Mapped[str | None] = mapped_column(String(8))
    moderation_state: Mapped[str] = mapped_column(String(16), default="ok")
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    edited_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now, index=True)

    media: Mapped[list["PostMedia"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="PostMedia.position",
        lazy="selectin")

    __table_args__ = (Index("ix_social_posts_author_created", "author_id", "created_at"),)


class PostMedia(Base):
    __tablename__ = "social_post_media"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    post_id: Mapped[str] = mapped_column(ForeignKey("social_posts.id", ondelete="CASCADE"), index=True)
    media_url: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(10), default="image")  # image | video
    position: Mapped[int] = mapped_column(Integer, default=0)
    alt_text: Mapped[str | None] = mapped_column(String(500))  # a11y
    post: Mapped["Post"] = relationship(back_populates="media")


class Reaction(Base):
    __tablename__ = "social_reactions"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    subject_type: Mapped[str] = mapped_column(String(10))  # post | comment
    subject_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(16))  # like | love | bravo | support | haha | wow | sad | grr
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "user_id", name="uq_reaction_once"),)


class Comment(Base):
    __tablename__ = "social_comments"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    post_id: Mapped[str] = mapped_column(ForeignKey("social_posts.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(26), index=True)  # imbrication
    path: Mapped[str] = mapped_column(String(512), default="")  # chemin matérialisé (arbre)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    author_id: Mapped[str] = mapped_column(String(64), index=True)
    body_text: Mapped[str] = mapped_column(Text)
    moderation_state: Mapped[str] = mapped_column(String(16), default="ok")
    deleted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (Index("ix_social_comments_post_created", "post_id", "created_at"),)


class Bookmark(Base):
    __tablename__ = "social_bookmarks"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    post_id: Mapped[str] = mapped_column(String(26), index=True)
    collection_id: Mapped[str | None] = mapped_column(String(26))  # collections privées (couche +)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_bookmark_once"),)


class Group(Base):
    __tablename__ = "social_groups"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    privacy: Mapped[str] = mapped_column(String(10), default="public")  # public | private | secret
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    avatar_color: Mapped[str | None] = mapped_column(String(16))
    require_approval: Mapped[bool] = mapped_column(Boolean, default=False)  # file de validation des posts
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)


class GroupMember(Base):
    __tablename__ = "social_group_members"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    group_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(10), default="member")  # admin | moderator | member
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | pending
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)


class Page(Base):
    """Page (créateur/marque/asso) : publie en son nom, a des abonnés."""
    __tablename__ = "social_pages"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(60))
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_color: Mapped[str | None] = mapped_column(String(16))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)


class PageRole(Base):
    __tablename__ = "social_page_roles"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    page_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(10), default="editor")  # admin | editor
    __table_args__ = (UniqueConstraint("page_id", "user_id", name="uq_page_role"),)


class PageFollower(Base):
    __tablename__ = "social_page_followers"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    page_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("page_id", "user_id", name="uq_page_follower"),)


class Event(Base):
    __tablename__ = "social_events"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    group_id: Mapped[str | None] = mapped_column(String(26), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    starts_at: Mapped[datetime] = mapped_column(TZDateTime, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)


class EventRsvp(Base):
    __tablename__ = "social_event_rsvps"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    event_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(10))  # going | interested
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_rsvp"),)


class Story(Base):
    __tablename__ = "social_stories"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    author_id: Mapped[str] = mapped_column(String(64), index=True)
    media_url: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(10), default="image")  # image | video
    caption: Mapped[str | None] = mapped_column(String(300))
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)


class StoryView(Base):
    __tablename__ = "social_story_views"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    story_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("story_id", "user_id", name="uq_story_view"),)


class HiddenPost(Base):
    """« Voir moins » : posts masqués par un utilisateur (exclus de son fil)."""
    __tablename__ = "social_hidden_posts"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    post_id: Mapped[str] = mapped_column(String(26))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_hidden_once"),)


class Circle(Base):
    """Liste/cercle d'amis d'un utilisateur (audience CIRCLES d'un post)."""
    __tablename__ = "social_circles"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)


class CircleMember(Base):
    __tablename__ = "social_circle_members"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    circle_id: Mapped[str] = mapped_column(String(26), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)  # dénormalisé pour requête rapide
    member_id: Mapped[str] = mapped_column(String(64), index=True)
    __table_args__ = (UniqueConstraint("circle_id", "member_id", name="uq_circle_member"),)


class Edge(Base):
    """Graphe social : amis (symétrique via 2 arêtes) ET suivi (asymétrique)."""
    __tablename__ = "social_edges"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    src: Mapped[str] = mapped_column(String(64), index=True)
    dst: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # friend | follow | block | mute | request
    status: Mapped[str] = mapped_column(String(12), default="active")  # active | pending
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now)
    __table_args__ = (UniqueConstraint("src", "dst", "kind", name="uq_edge_once"),)


# ===================== Couche 9 — Confiance (modération + RGPD) =====================
class Report(Base):
    """Signalement d'un contenu ou d'un compte par un utilisateur → file manuelle."""
    __tablename__ = "social_reports"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    reporter_id: Mapped[str] = mapped_column(String(64), index=True)
    subject_type: Mapped[str] = mapped_column(String(12), index=True)  # post|comment|user|group|page
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(String(20))  # spam|harcelement|haine|violence|nudite|arnaque|autre
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)  # pending|actioned|dismissed
    context: Mapped[dict] = mapped_column(default=dict)  # instantané : author_id, extrait…
    resolution: Mapped[str | None] = mapped_column(String(20))  # dismiss|remove|warn
    note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(64))
    resolved_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now, index=True)
    __table_args__ = (
        UniqueConstraint("reporter_id", "subject_type", "subject_id", "status",
                         name="uq_report_once_pending"),
        Index("ix_social_reports_status_created", "status", "created_at"),
    )


class ModerationAction(Base):
    """Journal de transparence : chaque action de modération est tracée (pour audit + page publique)."""
    __tablename__ = "social_moderation_actions"
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid)
    moderator_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(20))  # dismiss|remove|warn|erase
    subject_type: Mapped[str] = mapped_column(String(12))
    subject_id: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text)
    report_id: Mapped[str | None] = mapped_column(String(26))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_now, index=True)
