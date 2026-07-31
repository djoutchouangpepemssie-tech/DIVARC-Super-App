"""Connexion MongoDB asynchrone (Motor)."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    """Retourne la base courante. Lève si la connexion n'est pas initialisée."""
    if _db is None:
        raise RuntimeError("La base de données n'est pas initialisée (connect_to_mongo non appelé).")
    return _db


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        # tz_aware=True : les dates relues de Mongo restent en UTC "aware", cohérent avec helpers.now()
        _client = AsyncIOMotorClient(settings.MONGO_URL, uuidRepresentation="standard", tz_aware=True)
        _db = _client[settings.DB_NAME]
    return _db


async def close_mongo() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
