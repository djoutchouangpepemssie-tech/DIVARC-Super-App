"""Endpoint WebSocket temps réel + présence (REST)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from ..config import settings
from ..db import get_db
from ..helpers import ok
from ..realtime import manager
from ..security import require_user

router = APIRouter()

# Types de signalisation d'appel relayés tels quels vers le destinataire (`to`)
_CALL_TYPES = {"call:invite", "call:accept", "call:reject", "call:offer", "call:answer",
               "call:ice", "call:hangup", "call:busy"}


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
            elif t in _CALL_TYPES:
                # Signalisation d'appel WebRTC : on relaie au destinataire en injectant l'émetteur
                to = data.get("to")
                if not to:
                    continue
                data["from"] = uid
                data["fromName"] = user.get("name")
                data["fromAvatarColor"] = user.get("avatarColor")
                if t == "call:invite" and not manager.is_online(to):
                    # destinataire hors ligne -> on prévient l'appelant
                    await manager.send_to_user(uid, {"type": "call:unavailable", "callId": data.get("callId")})
                else:
                    await manager.send_to_user(to, data)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(uid, websocket)
        await manager.broadcast({"type": "presence", "userId": uid, "online": False}, exclude=uid)


@router.get("/rtc/config")
async def rtc_config(me: dict = Depends(require_user)):
    """Serveurs ICE pour WebRTC : STUN public (gratuit) + TURN si configuré (env)."""
    ice = [{"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}]
    if settings.TURN_URL:
        ice.append({
            "urls": settings.TURN_URL,
            "username": settings.TURN_USERNAME,
            "credential": settings.TURN_PASSWORD,
        })
    return ok({"iceServers": ice})


@router.get("/presence")
async def presence(request: Request, me: dict = Depends(require_user)):
    ids = [i for i in (request.query_params.get("ids") or "").split(",") if i]
    return ok({uid: {"online": manager.is_online(uid), "lastSeen": manager.last_seen.get(uid)} for uid in ids})
