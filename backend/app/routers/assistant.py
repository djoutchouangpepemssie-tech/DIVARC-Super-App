"""Routes Assistant IA « DIVA » : historique, chat (Anthropic), exécution d'actions réelles."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from ..ai import ai_build_context, ai_build_messages, ai_complete, ai_parse_json, ai_system_prompt
from ..config import settings
from ..data import ADS_CONFIG, MARKET_CATEGORIES
from ..db import get_db
from ..helpers import body_of, credit_wallet, err, now, ok, post_ledger, simulate_history, uid
from ..notify import notify
from ..security import require_user

router = APIRouter()

_REMINDER = ('\n\n[Rappel système : réponds UNIQUEMENT avec un objet JSON valide '
            '{"assistant_message": string, "actions": [...]} — AUCUN texte hors du JSON, AUCUN markdown, '
            'AUCUN conseil générique. Si l’intention est d’envoyer de l’argent / vendre-acheter / lancer une pub / '
            'ouvrir un écran, PROPOSE l’action correspondante dans "actions".]')


@router.get("/ai/history")
async def ai_history(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    session_id = request.query_params.get("sessionId")
    if not session_id:
        return ok({"messages": []})
    msgs = await db.ai_messages.find({"userId": me["id"], "sessionId": session_id}, {"_id": 0}).sort("createdAt", 1).to_list(length=None)
    return ok({"messages": msgs})


@router.post("/ai/chat")
async def ai_chat(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    session_id = body.get("sessionId") or uid()
    text = str(body.get("text") or "").strip()
    if not text:
        return err("Message vide")
    if not settings.ANTHROPIC_API_KEY:
        return err("Assistant IA non configuré", 503)

    history = await db.ai_messages.find({"userId": me["id"], "sessionId": session_id}, {"_id": 0}).sort("createdAt", 1).limit(20).to_list(length=20)
    ctx = await ai_build_context(db, me)
    system = ai_system_prompt(ctx)
    try:
        raw = await run_in_threadpool(ai_complete, system, ai_build_messages(history, text + _REMINDER))
        parsed = ai_parse_json(raw)
        if not parsed["_json"]:
            raw = await run_in_threadpool(ai_complete, system, ai_build_messages(history, f'Message de l’utilisateur : "{text}".' + _REMINDER))
            p2 = ai_parse_json(raw)
            if p2["_json"]:
                parsed = p2
    except Exception as e:  # noqa: BLE001
        print("ai/chat", e)
        return err("L’assistant est momentanément indisponible", 502)

    ts = now()
    user_msg = {"id": uid(), "userId": me["id"], "sessionId": session_id, "role": "user", "content": text, "createdAt": ts}
    actions = [{**a, "status": "pending"} for a in parsed["actions"]]
    ai_msg = {"id": uid(), "userId": me["id"], "sessionId": session_id, "role": "assistant",
              "content": parsed["assistant_message"], "actions": actions, "createdAt": ts + timedelta(milliseconds=1)}
    await db.ai_messages.insert_many([dict(user_msg), dict(ai_msg)])
    user_msg.pop("_id", None)
    ai_msg.pop("_id", None)
    return ok({"sessionId": session_id, "userMessage": user_msg, "message": ai_msg})


@router.post("/ai/actions/{action_id}/execute")
async def ai_execute(action_id: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    session_id = body.get("sessionId")
    msg = await db.ai_messages.find_one({"userId": me["id"], "sessionId": session_id, "actions.id": action_id})
    if not msg:
        return err("Action introuvable", 404)
    action = next((a for a in (msg.get("actions") or []) if a["id"] == action_id), None)
    if not action:
        return err("Action introuvable", 404)
    if action.get("status") == "executed":
        return err("Action déjà exécutée", 409)

    p = action.get("payload") or {}
    result: dict = {}
    try:
        if action["type"] == "send_money":
            amount = round(p.get("amountCents") or 0)
            if amount <= 0:
                return err("Montant invalide")
            wallet = await db.wallets.find_one({"userId": me["id"]})
            if not wallet or wallet["balanceCents"] < amount:
                return err("Solde insuffisant", 402)
            to_name = p.get("toName") or ""
            recip = await db.users.find_one({"$or": [{"name": to_name}, {"handle": to_name}, {"handle": to_name.lstrip("@")}]}, {"_id": 0})
            await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -amount}})
            if recip:
                await credit_wallet(db, recip["id"], amount)
                await notify(db, recip["id"], "payment", "💸 Paiement reçu",
                             f"{amount / 100:.2f} € de {me.get('name')}", {})
            batch = await post_ledger(db, [{"account": f"user:{me['id']}", "direction": "debit", "amountCents": amount},
                                           {"account": f"user:{(recip or {}).get('id') or 'external'}", "direction": "credit", "amountCents": amount}])
            await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Envoyé à {(recip or {}).get('name') or to_name or 'un ami'} (via DIVA)",
                                              "category": "P2P", "amountCents": -amount, "carbonKg": 0, "icon": "🤖", "route": "A2A",
                                              "ledgerBatch": batch, "status": "settled", "createdAt": now()})
            updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
            result = {"kind": "send_money", "amountCents": amount, "to": (recip or {}).get("name") or to_name, "balanceCents": updated["balanceCents"]}

        elif action["type"] == "create_listing":
            cat_def = next((c for c in MARKET_CATEGORIES if c["id"] == p.get("category")), None)
            listing = {"id": uid(), "sellerId": me["id"], "title": p.get("title") or "Annonce", "description": p.get("description") or "",
                       "priceCents": max(0, round(p.get("priceCents") or 0)), "category": cat_def["id"] if cat_def else "maison",
                       "subcategory": (cat_def.get("subcats") or ["Autre"])[0] if cat_def else "Autre", "transactionType": "sale",
                       "condition": "Bon état", "attributes": {}, "images": [], "city": p.get("city") or "", "postcode": "",
                       "country": "FR", "lat": None, "lon": None, "status": "active", "favorites": 0, "views": 0, "createdAt": now()}
            await db.listings.insert_one(dict(listing))
            result = {"kind": "create_listing", "listingId": listing["id"], "title": listing["title"]}

        elif action["type"] == "launch_ad":
            budget_cents = round(p.get("budgetCents") or 0)
            wallet = await db.wallets.find_one({"userId": me["id"]})
            if not wallet or wallet["balanceCents"] < budget_cents:
                return err("Solde insuffisant pour la campagne", 402)
            await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -budget_cents}})
            type_def = next((t for t in ADS_CONFIG["types"] if t["id"] == p.get("type")), ADS_CONFIG["types"][0])
            camp = {"id": uid(), "ownerId": me["id"], "name": p.get("name") or "Campagne", "type": type_def["id"],
                    "objective": p.get("objective") or "awareness", "brand": me.get("name"), "brandHandle": me.get("handle"),
                    "budgetCents": budget_cents, "budgetType": "total", "dailyBudgetCents": round(budget_cents / 14),
                    "bidStrategy": type_def["defaultBid"], "maxBidCents": 45, "targetCpaCents": 0,
                    "targeting": {"locations": [], "radiusKm": 0, "ageRange": [], "genders": ["Tous"], "interests": [], "devices": ADS_CONFIG["devices"]},
                    "keywords": [], "creative": {"headline": p.get("name") or "Découvre DIVARC", "headline2": "", "body": "",
                                                 "cta": "En savoir plus", "emoji": "📣", "mediaUrl": None, "priceCents": None, "finalUrl": ""},
                    "color": type_def["color"], "impressions": 0, "clicks": 0, "spentCents": 0, "conversions": 0, "daily": [],
                    "status": "active", "createdAt": now()}
            hist = simulate_history(camp)
            camp.update(daily=hist["daily"], impressions=hist["impressions"], clicks=hist["clicks"], spentCents=hist["spentCents"], conversions=hist["conversions"])
            await db.campaigns.insert_one(dict(camp))
            await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Budget pub : {camp['name']} (via DIVA)",
                                              "category": "Publicité", "amountCents": -budget_cents, "carbonKg": 0, "icon": "🤖", "route": None, "createdAt": now()})
            updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
            result = {"kind": "launch_ad", "campaignId": camp["id"], "name": camp["name"], "balanceCents": updated["balanceCents"]}

        elif action["type"] == "navigate":
            result = {"kind": "navigate", "tab": p.get("tab") or "hub"}
    except Exception as e:  # noqa: BLE001
        print("ai/execute", e)
        return err("Échec de l’exécution", 500)

    await db.ai_messages.update_one({"userId": me["id"], "sessionId": session_id, "actions.id": action_id},
                                    {"$set": {"actions.$.status": "executed", "actions.$.result": result}})
    return ok({"ok": True, "result": result})
