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


async def create_all() -> None:
    """Crée le schéma (tests/dev). En prod, on utilise Alembic."""
    from . import models  # noqa: F401  (enregistre les tables sur Base)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
