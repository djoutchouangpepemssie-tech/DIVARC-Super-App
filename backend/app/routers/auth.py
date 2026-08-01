"""Routes d'authentification (OTP e-mail) et de profil."""
from __future__ import annotations

import random
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from ..db import get_db
from ..helpers import (body_of, credit_wallet, err, hash_email, hash_phone, initials_of, now, ok,
                       send_otp_email, sha, uid)
from ..notify import notify
from ..seed import ensure_demo_users, provision_user
from ..security import require_user

import re

_HANDLE_RE = re.compile(r"^@?[a-z0-9_]{3,20}$")

router = APIRouter()


@router.post("/auth/otp/send")
async def otp_send(request: Request):
    db = get_db()
    body = await body_of(request)
    email = str(body.get("email") or "").strip().lower()
    if "@" not in email:
        return err("E-mail invalide")
    code = str(random.randint(100000, 999999))
    await db.otp_codes.update_one(
        {"email": email},
        {"$set": {"email": email, "codeHash": sha(code), "expiresAt": now() + timedelta(minutes=10), "attempts": 0, "createdAt": now()}},
        upsert=True,
    )
    mail = await send_otp_email(email, code)
    exists = bool(await db.users.find_one({"email": email}))
    return ok({
        "ok": True, "isNew": not exists,
        "previewCode": code if mail.get("preview") else None,
        "delivery": "email" if mail.get("sent") else "preview",
    })


@router.post("/auth/otp/verify")
async def otp_verify(request: Request):
    db = get_db()
    body = await body_of(request)
    email = str(body.get("email") or "").strip().lower()
    code = str(body.get("code") or "").strip()
    row = await db.otp_codes.find_one({"email": email})
    if not row or row["expiresAt"] < now():
        return err("Code expiré ou introuvable")
    if row["codeHash"] != sha(code):
        await db.otp_codes.update_one({"email": email}, {"$inc": {"attempts": 1}})
        return err("Code invalide")
    await db.otp_codes.delete_one({"email": email})
    user = await db.users.find_one({"email": email}, {"_id": 0})
    is_new = False
    if not user:
        user = await provision_user(db, email, body.get("name"), body.get("phone"))
        is_new = True
        # Bonus de parrainage : inscription via un lien d'invitation
        invite_code = (body.get("invite") or "").strip()
        if invite_code:
            inv = await db.invites.find_one({"code": invite_code})
            if inv and inv["inviterId"] != user["id"] and email not in (inv.get("usedEmails") or []):
                await credit_wallet(db, inv["inviterId"], 500)
                await db.transactions.insert_one({"id": uid(), "userId": inv["inviterId"],
                    "label": f"Parrainage : {user['name']} a rejoint DIVARC", "category": "Parrainage",
                    "amountCents": 500, "carbonKg": 0, "icon": "🎁", "route": None, "createdAt": now()})
                await db.invites.update_one({"code": invite_code},
                    {"$addToSet": {"usedEmails": email}, "$inc": {"count": 1}})
                await notify(db, inv["inviterId"], "invite", "🎁 Parrainage réussi",
                             f"{user['name']} a rejoint DIVARC — +5,00 € pour toi !", {})
    token = secrets.token_hex(24)
    await db.sessions.insert_one({"token": token, "userId": user["id"], "createdAt": now()})
    user.pop("_id", None)
    return ok({"token": token, "user": user, "isNew": is_new})


@router.get("/auth/me")
async def auth_me(me: dict = Depends(require_user)):
    return ok(me)


@router.post("/auth/logout")
async def auth_logout(request: Request):
    db = get_db()
    auth = request.headers.get("authorization") or ""
    token = auth[7:] if auth.startswith("Bearer ") else None
    if token:
        await db.sessions.delete_one({"token": token})
    return ok({"ok": True})


@router.patch("/users/me")
async def update_me(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    upd: dict = {}
    if body.get("name"):
        upd["name"] = body["name"]
        upd["initials"] = initials_of(body["name"])
    if body.get("bio") is not None:
        upd["bio"] = body["bio"]
    if body.get("avatarColor"):
        upd["avatarColor"] = body["avatarColor"]
    # Numéro de téléphone (+ hash pour la découverte, jamais indexé en clair)
    if "phone" in body:
        phone = (body.get("phone") or "").strip() or None
        upd["phone"] = phone
        upd["phoneHash"] = hash_phone(phone)
    # Réglages de découverte (opt-in) — fusion avec l'existant
    if isinstance(body.get("discoverable"), dict):
        cur = me.get("discoverable") or {}
        allowed = {k: bool(v) for k, v in body["discoverable"].items()
                   if k in ("byHandle", "byEmail", "byPhone", "byPhoto")}
        upd["discoverable"] = {**cur, **allowed}
    # @handle — modifiable UNE seule fois
    if body.get("handle"):
        if me.get("handleChanged"):
            return err("Le @handle ne peut être modifié qu'une seule fois", 409)
        raw = body["handle"].lstrip("@").lower()
        if not _HANDLE_RE.match(raw):
            return err("Handle invalide (3 à 20 caractères : lettres, chiffres, _)")
        h = "@" + raw
        if await db.users.find_one({"handle": h, "id": {"$ne": me["id"]}}):
            return err("Ce @handle est déjà pris", 409)
        upd["handle"] = h
        upd["handleChanged"] = True
    if upd:
        await db.users.update_one({"id": me["id"]}, {"$set": upd})
    u = await db.users.find_one({"id": me["id"]}, {"_id": 0})
    return ok(u)


@router.get("/handle/available")
async def handle_available(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    raw = (request.query_params.get("handle") or "").lstrip("@").lower()
    if not _HANDLE_RE.match(raw):
        return ok({"available": False, "reason": "format"})
    h = "@" + raw
    taken = await db.users.find_one({"handle": h, "id": {"$ne": me["id"]}})
    return ok({"available": not taken, "handle": h})


@router.get("/users")
async def list_users(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    await ensure_demo_users(db)
    q = (request.query_params.get("q") or "").lower()
    users = await db.users.find({"id": {"$ne": me["id"]}}, {"_id": 0, "email": 0}).limit(50).to_list(length=50)
    if q:
        users = [u for u in users if q in u["name"].lower() or q in u["handle"].lower()]
    return ok(users)
