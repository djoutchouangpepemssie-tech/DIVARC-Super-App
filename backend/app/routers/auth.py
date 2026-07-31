"""Routes d'authentification (OTP e-mail) et de profil."""
from __future__ import annotations

import random
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from ..db import get_db
from ..helpers import body_of, err, initials_of, now, ok, send_otp_email, sha
from ..seed import ensure_demo_users, provision_user
from ..security import require_user

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
        user = await provision_user(db, email, body.get("name"))
        is_new = True
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
    await db.users.update_one({"id": me["id"]}, {"$set": upd})
    u = await db.users.find_one({"id": me["id"]}, {"_id": 0})
    return ok(u)


@router.get("/users")
async def list_users(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    await ensure_demo_users(db)
    q = (request.query_params.get("q") or "").lower()
    users = await db.users.find({"id": {"$ne": me["id"]}}, {"_id": 0, "email": 0}).limit(50).to_list(length=50)
    if q:
        users = [u for u in users if q in u["name"].lower() or q in u["handle"].lower()]
    return ok(users)
