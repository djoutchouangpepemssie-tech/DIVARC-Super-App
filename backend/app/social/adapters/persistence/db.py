"""Connexion PostgreSQL async (SQLAlchemy 2.0) pour le contexte social.

En prod : PostgreSQL (Railway). En test/local sans DB : SQLite async (aiosqlite).
Types portables : JSONB sur Postgres, JSON sur SQLite.
"""
from __future__ import annotations

import os
import time
from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ....config import settings

# JSON portable : JSONB (Postgres) / JSON (SQLite)
JSONType = JSON().with_variant(JSONB, "postgresql")
# Horodatage avec fuseau
TZDateTime = DateTime(timezone=True)

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid() -> str:
    """Identifiant ULID (trié par le temps, unique). 26 caractères Crockford base32."""
    val = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[val & 0x1F])
        val >>= 5
    return "".join(reversed(out))


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSONType, datetime: TZDateTime}


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.social_db_url, pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


# Index composites à garantir même sur une base DÉJÀ créée (create_all n'ajoute pas d'index
# aux tables existantes). Idempotent : CREATE INDEX IF NOT EXISTS (Postgres & SQLite).
_ENSURE_INDEXES = [
    ("ix_social_edges_src_kind", "social_edges", "src, kind"),
    ("ix_social_edges_dst_kind", "social_edges", "dst, kind"),
    ("ix_social_feed_entries_user_created", "social_feed_entries", "user_id, created_at"),
    ("ix_social_posts_author_created", "social_posts", "author_id, created_at"),
]


async def create_all() -> None:
    """Crée le schéma (tests/dev) + garantit les index chauds (idempotent, prod incluse)."""
    from sqlalchemy import text
    from . import models  # noqa: F401  (enregistre les tables sur Base)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for name, table, cols in _ENSURE_INDEXES:
            try:
                await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})"))
            except Exception:  # noqa: BLE001  (un index déjà présent sous un autre nom ne doit pas bloquer)
                pass
