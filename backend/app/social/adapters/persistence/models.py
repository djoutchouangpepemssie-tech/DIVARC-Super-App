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
