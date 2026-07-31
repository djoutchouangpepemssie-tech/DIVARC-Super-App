"""Authentification par jeton opaque (Bearer) adossé à la collection `sessions`."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from .db import get_db


async def get_optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """Retourne l'utilisateur courant à partir du header Authorization, ou None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    db = get_db()
    s = await db.sessions.find_one({"token": token})
    if not s:
        return None
    return await db.users.find_one({"id": s["userId"]}, {"_id": 0})


async def require_user(user: dict | None = Depends(get_optional_user)) -> dict:
    """Dépendance pour les routes protégées : lève 401 si non authentifié."""
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    return user
