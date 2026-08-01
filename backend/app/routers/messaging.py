"""Routes messagerie : conversations, communautés, messages, réactions, amitié, médias."""
from __future__ import annotations

import base64
import random
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response

from ..data import BOT_REPLIES, COLORS
from ..db import get_db
from ..helpers import body_of, bump_friendship, err, get_friendship, now, ok, uid
from ..notify import notify
from ..realtime import manager
from ..seed import ensure_demo_users
from ..security import require_user

router = APIRouter()

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Médias autorisés dans le chat (image / vidéo / audio) en data-URL base64
_MEDIA_RE = re.compile(r"^data:((?:image|video|audio)/[\w.+-]+);base64,(.+)$", re.S)
_MEDIA_LABELS = {"image": "📷 Photo", "video": "🎥 Vidéo", "audio": "🎤 Message vocal"}


# ---------------- Médias du chat ----------------
@router.get("/chat/media/{media_id}")
async def chat_media(media_id: str):
    """Sert un média (les balises <img>/<video> n'envoient pas de Bearer -> route publique)."""
    db = get_db()
    m = await db.chat_media.find_one({"id": media_id})
    if not m:
        return err("Média introuvable", 404)
    raw = base64.b64decode(m["data"])
    return Response(content=raw, media_type=m.get("contentType") or "application/octet-stream",
                    headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.post("/chat/upload")
async def chat_upload(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    data = str(body.get("data") or "")
    m = _MEDIA_RE.match(data)
    if not m:
        return err("Média invalide (format attendu : data-URL image/vidéo/audio)")
    content_type = m.group(1)
    b64 = m.group(2)
    # ~9 Mo de base64 ≈ 6,7 Mo binaire : on reste sous la limite d'un document Mongo (16 Mo)
    if len(b64) > 9_000_000:
        return err("Fichier trop lourd (max ~6 Mo)", 413)
    kind = content_type.split("/", 1)[0]  # image | video | audio
    iid = uid()
    await db.chat_media.insert_one({"id": iid, "userId": me["id"], "data": b64,
                                    "contentType": content_type, "kind": kind, "createdAt": now()})
    return ok({"id": iid, "url": f"/api/chat/media/{iid}", "kind": kind, "contentType": content_type})


@router.get("/conversations")
async def list_conversations(me: dict = Depends(require_user)):
    db = get_db()
    await ensure_demo_users(db)
    convos = await db.conversations.find({"memberIds": me["id"]}, {"_id": 0}).sort("lastMessageAt", -1).to_list(length=None)
    out = []
    for c in convos:
        title, avatar_color, other, friendship = c.get("name"), c.get("avatarColor"), None, None
        if c["type"] == "dm":
            other_id = next((m for m in c["memberIds"] if m != me["id"]), None)
            other = await db.users.find_one({"id": other_id}, {"_id": 0, "email": 0})
            title = (other or {}).get("name")
            avatar_color = (other or {}).get("avatarColor")
            friendship = await get_friendship(db, me["id"], other_id)
        last_read = (c.get("reads") or {}).get(me["id"])
        unread = await db.messages.count_documents({
            "conversationId": c["id"], "senderId": {"$ne": me["id"]},
            "createdAt": {"$gt": last_read if last_read else EPOCH},
        })
        out.append({"id": c["id"], "type": c["type"], "title": title, "avatarColor": avatar_color, "other": other,
                    "friendship": friendship, "memberCount": len(c["memberIds"]), "lastText": c.get("lastText"),
                    "lastMessageAt": c.get("lastMessageAt"), "unread": unread, "topic": c.get("topic")})
    return ok(out)


@router.get("/communities")
async def list_communities(me: dict = Depends(require_user)):
    db = get_db()
    await ensure_demo_users(db)
    comms = await db.conversations.find({"type": "community", "isPublic": True}, {"_id": 0}).to_list(length=None)
    return ok([{"id": c["id"], "name": c["name"], "topic": c.get("topic"), "avatarColor": c.get("avatarColor"),
               "memberCount": len(c["memberIds"]), "joined": me["id"] in c["memberIds"]} for c in comms])


@router.post("/conversations")
async def create_conversation(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    ctype = body.get("type") or "dm"
    handles = [(h if h.startswith("@") else "@" + h) for h in (body.get("memberHandles") or [])]
    members = await db.users.find({"handle": {"$in": handles}}).to_list(length=None)
    member_ids = [me["id"]] + [m["id"] for m in members]
    if ctype == "dm":
        other_id = next((m for m in member_ids if m != me["id"]), None)
        if not other_id:
            return err("Destinataire introuvable", 404)
        # Blocage : impossible de démarrer un DM si l'un a bloqué l'autre
        if await db.blocks.find_one({"$or": [{"blockerId": me["id"], "blockedId": other_id},
                                             {"blockerId": other_id, "blockedId": me["id"]}]}):
            return err("Vous ne pouvez pas contacter cet utilisateur", 403)
        existing = await db.conversations.find_one({"type": "dm", "memberIds": {"$all": [me["id"], other_id], "$size": 2}})
        if existing:
            return ok({"id": existing["id"], "existing": True})
    conv = {"id": uid(), "type": ctype, "name": body.get("name"), "topic": body.get("topic"),
            "avatarColor": body.get("avatarColor") or random.choice(COLORS),
            "memberIds": list(dict.fromkeys(member_ids)), "createdBy": me["id"], "isPublic": ctype == "community",
            "reads": {}, "lastText": None, "lastMessageAt": now(), "createdAt": now()}
    await db.conversations.insert_one(dict(conv))
    return ok({"id": conv["id"]})


@router.post("/conversations/{cid}/join")
async def join_conversation(cid: str, me: dict = Depends(require_user)):
    db = get_db()
    await db.conversations.update_one({"id": cid}, {"$addToSet": {"memberIds": me["id"]}})
    return ok({"ok": True})


@router.get("/conversations/{cid}/messages")
async def get_messages(cid: str, me: dict = Depends(require_user)):
    db = get_db()
    conv = await db.conversations.find_one({"id": cid})
    if not conv or me["id"] not in conv["memberIds"]:
        return err("Conversation introuvable", 404)
    msgs = await db.messages.find({"conversationId": cid, "deletedFor": {"$ne": me["id"]}}, {"_id": 0}).sort("createdAt", 1).limit(200).to_list(length=200)
    await db.conversations.update_one({"id": cid}, {"$set": {f"reads.{me['id']}": now()}})
    friendship, other = None, None
    if conv["type"] == "dm":
        other_id = next((m for m in conv["memberIds"] if m != me["id"]), None)
        other = await db.users.find_one({"id": other_id}, {"_id": 0, "email": 0})
        friendship = await get_friendship(db, me["id"], other_id)
    return ok({"conversation": {"id": conv["id"], "type": conv["type"], "name": conv.get("name"),
                                "topic": conv.get("topic"), "memberCount": len(conv["memberIds"]),
                                "other": other, "friendship": friendship}, "messages": msgs})


@router.post("/conversations/{cid}/messages")
async def send_message(cid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    conv = await db.conversations.find_one({"id": cid})
    if not conv or me["id"] not in conv["memberIds"]:
        return err("Conversation introuvable", 404)
    body = await body_of(request)
    text = str(body.get("text") or "").strip()
    kind = body.get("kind") or "text"
    media_url = body.get("mediaUrl")
    media_type = body.get("mediaType")  # image | video | audio
    # Un message doit avoir du texte OU un média
    if not text and not media_url:
        return err("Message vide")
    msg = {"id": uid(), "conversationId": cid, "senderId": me["id"], "senderName": me.get("name"), "text": text,
           "kind": kind, "mediaUrl": media_url, "mediaType": media_type, "reactions": [], "createdAt": now()}
    await db.messages.insert_one(dict(msg))
    # Aperçu dans la liste : le texte, sinon un libellé média
    preview = text or _MEDIA_LABELS.get(media_type, "Pièce jointe")
    await db.conversations.update_one({"id": cid}, {"$set": {"lastText": preview, "lastMessageAt": now()}})
    msg.pop("_id", None)
    others = [m for m in conv["memberIds"] if m != me["id"]]
    # push temps réel du nouveau message aux autres membres
    await manager.send_to_users(others, {"type": "message", "conversationId": cid, "message": msg})
    # notification pour chaque destinataire humain (les bots n'en reçoivent pas)
    convo_label = conv.get("name") or me.get("name")
    for oid in others:
        if not oid.startswith("bot-"):
            await notify(db, oid, "message", f"💬 {convo_label}", preview[:80], {"conversationId": cid})
    friendship = None
    if conv["type"] == "dm":
        other_id = next((m for m in conv["memberIds"] if m != me["id"]), None)
        friendship = await bump_friendship(db, me["id"], other_id, 10)
        other = await db.users.find_one({"id": other_id})
        if other and other.get("isBot"):
            reply = random.choice(BOT_REPLIES)
            reply_at = now() + timedelta(milliseconds=900)
            bot_msg = {"id": uid(), "conversationId": cid, "senderId": other["id"],
                       "senderName": other["name"], "text": reply, "kind": "text",
                       "reactions": [], "createdAt": reply_at}
            await db.messages.insert_one(dict(bot_msg))
            await db.conversations.update_one({"id": cid}, {"$set": {"lastText": reply, "lastMessageAt": reply_at}})
            bot_msg.pop("_id", None)
            await manager.send_to_user(me["id"], {"type": "message", "conversationId": cid, "message": bot_msg})
            friendship = await bump_friendship(db, other_id, me["id"], 10)
    return ok({"message": msg, "friendship": friendship})


@router.post("/messages/{mid}/react")
async def react_message(mid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    msg = await db.messages.find_one({"id": mid})
    if not msg:
        return err("Message introuvable", 404)
    body = await body_of(request)
    emoji = body.get("emoji") or "❤️"
    reactions = [r for r in (msg.get("reactions") or []) if r["userId"] != me["id"]]
    had = any(r["userId"] == me["id"] and r["emoji"] == emoji for r in (msg.get("reactions") or []))
    if not had:
        reactions.append({"userId": me["id"], "emoji": emoji})
    await db.messages.update_one({"id": mid}, {"$set": {"reactions": reactions}})
    # push temps réel de la réaction aux autres membres de la conversation
    conv = await db.conversations.find_one({"id": msg["conversationId"]})
    if conv:
        others = [m for m in conv["memberIds"] if m != me["id"]]
        await manager.send_to_users(others, {"type": "reaction", "messageId": mid,
                                             "conversationId": msg["conversationId"], "reactions": reactions})
    return ok({"reactions": reactions})


@router.post("/messages/{mid}/delete")
async def delete_message(mid: str, request: Request, me: dict = Depends(require_user)):
    """Supprime un message : scope 'me' (masqué pour moi) ou 'all' (pour tout le monde, expéditeur seul)."""
    db = get_db()
    msg = await db.messages.find_one({"id": mid})
    if not msg:
        return err("Message introuvable", 404)
    conv = await db.conversations.find_one({"id": msg["conversationId"]})
    if not conv or me["id"] not in conv["memberIds"]:
        return err("Accès refusé", 403)
    body = await body_of(request)
    scope = body.get("scope") or "me"
    if scope == "all":
        if msg["senderId"] != me["id"]:
            return err("Seul l'expéditeur peut supprimer pour tout le monde", 403)
        await db.messages.update_one({"id": mid}, {"$set": {
            "deleted": True, "text": "", "mediaUrl": None, "mediaType": None,
            "reactions": [], "deletedAt": now()}})
        # met à jour l'aperçu de la liste si c'était le dernier message
        if conv.get("lastMessageAt") == msg.get("createdAt"):
            await db.conversations.update_one({"id": conv["id"]}, {"$set": {"lastText": "🚫 Message supprimé"}})
        others = [m for m in conv["memberIds"] if m != me["id"]]
        await manager.send_to_users(others, {"type": "message:deleted", "conversationId": conv["id"], "messageId": mid})
        return ok({"ok": True, "scope": "all"})
    # scope 'me' : on masque uniquement pour l'utilisateur courant
    await db.messages.update_one({"id": mid}, {"$addToSet": {"deletedFor": me["id"]}})
    return ok({"ok": True, "scope": "me"})
