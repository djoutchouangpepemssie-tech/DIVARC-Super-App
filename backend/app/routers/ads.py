"""Routes Ads Manager v2 : config, mots-clés, estimation, campagnes, insights, tracking."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..data import ADS_CONFIG
from ..db import get_db
from ..helpers import (ad_derived, ad_keyword_suggest, body_of, err, estimate_reach, now, ok,
                       simulate_history, today_str, uid)
from ..security import require_user

router = APIRouter()


@router.get("/ads/config")
async def ads_config(me: dict = Depends(require_user)):
    return ok(ADS_CONFIG)


@router.get("/ads/keywords")
async def ads_keywords(request: Request, me: dict = Depends(require_user)):
    return ok(ad_keyword_suggest(request.query_params.get("q") or ""))


@router.post("/ads/estimate")
async def ads_estimate(request: Request, me: dict = Depends(require_user)):
    body = await body_of(request)
    return ok(estimate_reach(
        daily_budget_cents=round(body.get("dailyBudgetCents") or 0),
        bid_strategy=body.get("bidStrategy") or "cpc",
        max_bid_cents=round(body.get("maxBidCents") or 0),
        targeting=body.get("targeting") or {},
    ))


@router.get("/ads/insights")
async def ads_insights(me: dict = Depends(require_user)):
    db = get_db()
    camps = await db.campaigns.find({"ownerId": me["id"]}, {"_id": 0}).to_list(length=None)
    tot = {"impressions": 0, "clicks": 0, "spentCents": 0, "conversions": 0, "budgetCents": 0}
    for c in camps:
        tot["impressions"] += c.get("impressions") or 0
        tot["clicks"] += c.get("clicks") or 0
        tot["spentCents"] += c.get("spentCents") or 0
        tot["conversions"] += c.get("conversions") or 0
        tot["budgetCents"] += c.get("budgetCents") or 0
    agg: dict = {}
    for c in camps:
        for d in (c.get("daily") or []):
            row = agg.setdefault(d["date"], {"date": d["date"], "impressions": 0, "clicks": 0, "spentCents": 0, "conversions": 0})
            row["impressions"] += d["impressions"]
            row["clicks"] += d["clicks"]
            row["spentCents"] += d["spentCents"]
            row["conversions"] += d["conversions"]
    daily = sorted(agg.values(), key=lambda r: r["date"])[-14:]
    top = sorted([ad_derived(c) for c in camps], key=lambda c: c.get("impressions") or 0, reverse=True)[:5]
    totals = {**tot,
              "ctr": round(tot["clicks"] / tot["impressions"] * 100, 2) if tot["impressions"] else 0,
              "cpcCents": round(tot["spentCents"] / tot["clicks"]) if tot["clicks"] else 0,
              "convRate": round(tot["conversions"] / tot["clicks"] * 100, 2) if tot["clicks"] else 0}
    counts = {"total": len(camps),
              "active": len([c for c in camps if c.get("status") == "active"]),
              "paused": len([c for c in camps if c.get("status") == "paused"])}
    return ok({"totals": totals, "daily": daily, "top": top, "counts": counts})


@router.post("/ads/campaigns")
async def create_campaign(request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    budget_cents = round(body.get("budgetCents") or 0)
    if budget_cents <= 0:
        return err("Budget invalide")
    wallet = await db.wallets.find_one({"userId": me["id"]})
    if not wallet or wallet["balanceCents"] < budget_cents:
        return err("Solde insuffisant pour financer la campagne", 402)
    await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": -budget_cents}})
    type_def = next((t for t in ADS_CONFIG["types"] if t["id"] == body.get("type")), ADS_CONFIG["types"][0])
    tg = body.get("targeting") or {}
    creative = body.get("creative") or {}
    keywords = []
    if isinstance(body.get("keywords"), list):
        for k in body["keywords"]:
            keywords.append({"text": k if isinstance(k, str) else k.get("text"),
                             "matchType": (k.get("matchType") if isinstance(k, dict) else None) or "broad",
                             "bidCents": (k.get("bidCents") if isinstance(k, dict) else None) or round(body.get("maxBidCents") or 45)})
    camp = {
        "id": uid(), "ownerId": me["id"], "name": body.get("name") or "Campagne",
        "type": type_def["id"], "objective": body.get("objective") or "awareness",
        "brand": body.get("brand") or me.get("name"), "brandHandle": me.get("handle"),
        "budgetCents": budget_cents, "budgetType": "daily" if body.get("budgetType") == "daily" else "total",
        "dailyBudgetCents": round(body.get("dailyBudgetCents") or 0),
        "bidStrategy": body.get("bidStrategy") or type_def["defaultBid"], "maxBidCents": round(body.get("maxBidCents") or 45),
        "targetCpaCents": round(body.get("targetCpaCents") or 0),
        "targeting": {"locations": tg.get("locations") or [], "radiusKm": tg.get("radiusKm") or 0,
                      "ageRange": tg.get("ageRange") or [], "genders": tg.get("genders") or ["Tous"],
                      "interests": tg.get("interests") or [], "devices": tg.get("devices") or ADS_CONFIG["devices"]},
        "keywords": keywords,
        "creative": {"headline": creative.get("headline") or "Découvre DIVARC", "headline2": creative.get("headline2") or "",
                     "body": creative.get("body") or "", "cta": creative.get("cta") or "En savoir plus",
                     "emoji": creative.get("emoji") or "📣", "mediaUrl": creative.get("mediaUrl"),
                     "priceCents": creative.get("priceCents"), "finalUrl": creative.get("finalUrl") or ""},
        "color": type_def["color"], "impressions": 0, "clicks": 0, "spentCents": 0, "conversions": 0, "daily": [],
        "status": "active", "createdAt": now(),
    }
    hist = simulate_history(camp)
    camp.update(daily=hist["daily"], impressions=hist["impressions"], clicks=hist["clicks"],
                spentCents=hist["spentCents"], conversions=hist["conversions"])
    await db.campaigns.insert_one(dict(camp))
    await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Budget pub : {camp['name']}",
                                      "category": "Publicité", "amountCents": -budget_cents, "carbonKg": 0,
                                      "icon": "📣", "route": None, "createdAt": now()})
    updated = await db.wallets.find_one({"userId": me["id"]}, {"_id": 0})
    camp.pop("_id", None)
    return ok({"campaign": ad_derived(camp), "balanceCents": updated["balanceCents"]})


@router.get("/ads/campaigns")
async def list_campaigns(me: dict = Depends(require_user)):
    db = get_db()
    camps = await db.campaigns.find({"ownerId": me["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(length=None)
    return ok([ad_derived(c) for c in camps])


@router.get("/ads/campaigns/{cid}")
async def get_campaign(cid: str, me: dict = Depends(require_user)):
    db = get_db()
    c = await db.campaigns.find_one({"id": cid, "ownerId": me["id"]}, {"_id": 0})
    if not c:
        return err("Campagne introuvable", 404)
    return ok(ad_derived(c))


@router.patch("/ads/campaigns/{cid}")
async def update_campaign(cid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    c = await db.campaigns.find_one({"id": cid, "ownerId": me["id"]})
    if not c:
        return err("Campagne introuvable", 404)
    upd: dict = {}
    if body.get("status"):
        if body["status"] == "ended" and c["status"] != "ended":
            refund = max(0, c["budgetCents"] - (c.get("spentCents") or 0))
            if refund > 0:
                await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": refund}})
                await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Remboursement pub : {c['name']}",
                                                  "category": "Publicité", "amountCents": refund, "carbonKg": 0, "icon": "↩️", "route": None, "createdAt": now()})
        upd["status"] = body["status"]
    if body.get("name"):
        upd["name"] = body["name"]
    if body.get("maxBidCents") is not None:
        upd["maxBidCents"] = round(body["maxBidCents"])
    if body.get("bidStrategy"):
        upd["bidStrategy"] = body["bidStrategy"]
    if body.get("dailyBudgetCents") is not None:
        upd["dailyBudgetCents"] = round(body["dailyBudgetCents"])
    if body.get("targeting"):
        upd["targeting"] = {**(c.get("targeting") or {}), **body["targeting"]}
    if body.get("creative"):
        upd["creative"] = {**(c.get("creative") or {}), **body["creative"]}
    if body.get("keywords"):
        upd["keywords"] = body["keywords"]
    await db.campaigns.update_one({"id": c["id"]}, {"$set": upd})
    updated = await db.campaigns.find_one({"id": c["id"]}, {"_id": 0})
    return ok(ad_derived(updated))


@router.delete("/ads/campaigns/{cid}")
async def delete_campaign(cid: str, me: dict = Depends(require_user)):
    db = get_db()
    c = await db.campaigns.find_one({"id": cid, "ownerId": me["id"]})
    if not c:
        return err("Campagne introuvable", 404)
    if c["status"] != "ended":
        refund = max(0, c["budgetCents"] - (c.get("spentCents") or 0))
        if refund > 0:
            await db.wallets.update_one({"userId": me["id"]}, {"$inc": {"balanceCents": refund}})
            await db.transactions.insert_one({"id": uid(), "userId": me["id"], "label": f"Remboursement pub : {c['name']}",
                                              "category": "Publicité", "amountCents": refund, "carbonKg": 0, "icon": "↩️", "route": None, "createdAt": now()})
    await db.campaigns.delete_one({"id": c["id"]})
    return ok({"ok": True})


@router.post("/ads/campaigns/{cid}/track")
async def track_campaign(cid: str, request: Request, me: dict = Depends(require_user)):
    db = get_db()
    body = await body_of(request)
    c = await db.campaigns.find_one({"id": cid})
    if not c or c["status"] != "active":
        return ok({"ok": False})
    ttype = body.get("type") if body.get("type") in ("click", "conversion") else "impression"
    cpc = c.get("maxBidCents") or 45
    if ttype == "click":
        cost = cpc
    elif ttype == "conversion":
        cost = 0
    else:
        cost = max(1, round((c.get("maxBidCents") or 500 if c.get("bidStrategy") == "cpm" else 550) / 1000))
    new_spent = min((c.get("spentCents") or 0) + cost, c["budgetCents"])
    upd: dict = {"spentCents": new_spent}
    if new_spent >= c["budgetCents"]:
        upd["status"] = "ended"
    inc = {"clicks": 1} if ttype == "click" else {"conversions": 1} if ttype == "conversion" else {"impressions": 1}
    today = today_str()
    daily = list(c.get("daily") or [])
    td = next((d for d in daily if d["date"] == today), None)
    if not td:
        td = {"date": today, "impressions": 0, "clicks": 0, "spentCents": 0, "conversions": 0}
        daily.append(td)
    td["impressions"] += 1 if ttype == "impression" else 0
    td["clicks"] += 1 if ttype == "click" else 0
    td["conversions"] += 1 if ttype == "conversion" else 0
    td["spentCents"] += cost
    upd["daily"] = daily
    await db.campaigns.update_one({"id": c["id"]}, {"$set": upd, "$inc": inc})
    return ok({"ok": True})
