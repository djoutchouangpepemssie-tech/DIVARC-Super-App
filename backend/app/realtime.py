"""Temps réel : gestionnaire de connexions WebSocket + présence en ligne.

Note d'échelle : l'état est en mémoire (une instance). Pour un déploiement multi-instance,
brancher un bus Redis Pub/Sub pour propager les événements entre instances (prévu par la
vision DIVARC). Pour une instance unique, ceci suffit.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from .helpers import now


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}
        self.last_seen: dict[str, datetime] = {}

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        conns = self.active.get(user_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self.active.pop(user_id, None)
        self.last_seen[user_id] = now()

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active

    async def _send(self, ws: WebSocket, message: dict) -> bool:
        try:
            await ws.send_text(json.dumps(jsonable_encoder(message)))
            return True
        except Exception:  # noqa: BLE001 — connexion morte, on ignore
            return False

    async def send_to_user(self, user_id: str, message: dict) -> None:
        for ws in list(self.active.get(user_id, set())):
            ok = await self._send(ws, message)
            if not ok:
                self.disconnect(user_id, ws)

    async def send_to_users(self, user_ids, message: dict) -> None:
        for uid in set(user_ids):
            await self.send_to_user(uid, message)

    async def broadcast(self, message: dict, exclude: str | None = None) -> None:
        for uid in list(self.active.keys()):
            if uid != exclude:
                await self.send_to_user(uid, message)


manager = ConnectionManager()
