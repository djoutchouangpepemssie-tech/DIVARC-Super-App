"""Endpoint WebSocket temps réel + présence (REST)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from ..db import get_db
from ..helpers import ok
from ..realtime import manager
from ..security import require_user

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    """WS authentifié par ?token=... (les navigateurs n'envoient pas de header Authorization sur les WS)."""
    db = get_db()
    session = await db.sessions.find_one({"token": token}) if token else None
    if not session:
        await websocket.close(code=4401)
        return
    user = await db.users.find_one({"id": session["userId"]}, {"_id": 0})
    if not user:
        await websocket.close(code=4401)
        return
    uid = user["id"]

    await manager.connect(uid, websocket)
    await manager.broadcast({"type": "presence", "userId": uid, "online": True}, exclude=uid)
    # état initial : liste des utilisateurs actuellement en ligne
    await manager.send_to_user(uid, {"type": "presence_state", "online": [u for u in manager.active if u != uid]})

    try:
        while True:
            data = await websocket.receive_json()
            t = data.get("type")
            if t == "ping":
                await manager.send_to_user(uid, {"type": "pong"})
            elif t == "typing":
                cid = data.get("conversationId")
                conv = await db.conversations.find_one({"id": cid})
                if conv and uid in conv["memberIds"]:
                    others = [m for m in conv["memberIds"] if m != uid]
                    await manager.send_to_users(others, {"type": "typing", "conversationId": cid, "userId": uid})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(uid, websocket)
        await manager.broadcast({"type": "presence", "userId": uid, "online": False}, exclude=uid)


@router.get("/presence")
async def presence(request: Request, me: dict = Depends(require_user)):
    ids = [i for i in (request.query_params.get("ids") or "").split(",") if i]
    return ok({uid: {"online": manager.is_online(uid), "lastSeen": manager.last_seen.get(uid)} for uid in ids})
