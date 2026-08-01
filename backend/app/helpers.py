"""Fonctions utilitaires transverses (portées depuis route.js)."""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from .config import settings
from .data import COLORS, EU_CC, LEVELS

# ---------------- Réponses HTTP normalisées ----------------

def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid.uuid4())


def strip_id(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


def ok(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(content=jsonable_encoder(data), status_code=status)


async def body_of(request) -> dict:
    """Lit le corps JSON de la requête (dict vide si absent/invalide), comme route.js."""
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def err(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(content={"error": message}, status_code=status)


# ---------------- Utilitaires purs ----------------

def initials_of(name: str) -> str:
    parts = [w for w in (name or "").split(" ") if w][:2]
    return "".join(w[0].upper() for w in parts)


def sha(s: Any) -> str:
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()


# ---------------- Découverte : normalisation + hachage (RGPD) ----------------

def norm_email(email: str | None) -> str:
    return (email or "").strip().lower()


def norm_phone(phone: str | None) -> str:
    """Numéro national = 9 derniers chiffres, pour matcher '06 12 34 56 78' et '+33 6 12 34 56 78'."""
    digits = re.sub(r"\D", "", phone or "")
    return digits[-9:] if len(digits) >= 9 else ""


def hash_email(email: str | None) -> str | None:
    e = norm_email(email)
    return sha(e) if e else None


def hash_phone(phone: str | None) -> str | None:
    n = norm_phone(phone)
    return sha(n) if n else None


def today_str() -> str:
    return now().isoformat()[:10]


def yesterday_str() -> str:
    return (now() - timedelta(days=1)).isoformat()[:10]


def level_info(xp: int) -> dict:
    idx = 0
    for i in range(len(LEVELS)):
        if xp >= LEVELS[i]["min"]:
            idx = i
    cur = LEVELS[idx]
    nxt = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None
    base = cur["min"]
    span = (nxt["min"] - base) if nxt else 1
    pct = min(100, round((xp - base) / span * 100)) if nxt else 100
    return {
        "level": idx, "name": cur["name"], "emoji": cur["emoji"], "xp": xp, "pct": pct,
        "next": ({"name": nxt["name"], "at": nxt["min"]} if nxt else None),
    }


def eur(cents: int | None) -> str:
    if cents is None:
        return ""
    val = cents / 100
    if val == int(val):
        s = f"{int(val):,}".replace(",", " ")
    else:
        s = f"{val:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} €"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    d_lat = (lat2 - lat1) * math.pi / 180
    d_lon = (lon2 - lon1) * math.pi / 180
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------- Grand livre en partie double + wallet ----------------

async def post_ledger(db, entries: list[dict]) -> str:
    batch = uid()
    docs = [{"id": uid(), "batch": batch, **e, "createdAt": now()} for e in entries]
    await db.ledger.insert_many(docs)
    return batch


def is_plus(user: dict | None) -> bool:
    """True si l'utilisateur a un abonnement DIVARC+ actif."""
    if not user:
        return False
    until = user.get("plusUntil")
    return bool(until and until > now())


async def credit_wallet(db, user_id: str, amt: int) -> None:
    r = await db.wallets.update_one({"userId": user_id}, {"$inc": {"balanceCents": amt}})
    if r.matched_count == 0:
        await db.wallets.insert_one({
            "id": uid(), "userId": user_id, "balanceCents": amt, "currency": "EUR",
            "sepaInstant": True, "carbonMonthKg": 0, "createdAt": now(),
        })


# ---------------- Amitié (XP, niveaux, streak) ----------------

async def bump_friendship(db, uid_a: str, other_id: str, xp_gain: int = 10) -> dict:
    key = "|".join(sorted([uid_a, other_id]))
    f = await db.friendships.find_one({"key": key})
    today = today_str()
    if not f:
        f = {"id": uid(), "key": key, "members": sorted([uid_a, other_id]), "xp": 0,
             "streak": 0, "streakLastDay": None, "activeDays": {}, "createdAt": now()}
        await db.friendships.insert_one(dict(f))
    active_days = f.get("activeDays") or {}
    active_days[uid_a] = today
    both_today = all(active_days.get(m) == today for m in f["members"])
    streak = f.get("streak") or 0
    streak_last_day = f.get("streakLastDay")
    if both_today and streak_last_day != today:
        streak = streak + 1 if streak_last_day == yesterday_str() else 1
        streak_last_day = today
    xp = (f.get("xp") or 0) + xp_gain
    await db.friendships.update_one(
        {"key": key},
        {"$set": {"activeDays": active_days, "streak": streak, "streakLastDay": streak_last_day, "xp": xp}},
    )
    return {"streak": streak, "xp": xp, **level_info(xp)}


async def get_friendship(db, uid_a: str, other_id: str) -> dict:
    key = "|".join(sorted([uid_a, other_id]))
    f = await db.friendships.find_one({"key": key})
    xp = (f or {}).get("xp") or 0
    return {"streak": (f or {}).get("streak") or 0, "streakLastDay": (f or {}).get("streakLastDay"), **level_info(xp)}


# ---------------- E-mail OTP (Resend, mode preview sans clé) ----------------

async def send_otp_email(email: str, code: str) -> dict:
    if not settings.RESEND_API_KEY:
        return {"preview": True}
    try:
        from .emails import otp_email_html, otp_email_text
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": settings.RESEND_FROM, "to": [email],
                      "subject": f"Ton code DIVARC : {code}",
                      "html": otp_email_html(code), "text": otp_email_text(code)},
            )
            j = r.json()
            if isinstance(j, dict) and j.get("error"):
                return {"error": str(j["error"])}
            return {"sent": True}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


async def send_welcome_email(email: str, name: str | None = None) -> dict:
    """E-mail de bienvenue à la création du compte (best effort, ne bloque jamais)."""
    if not settings.RESEND_API_KEY:
        return {"preview": True}
    try:
        from .emails import welcome_email_html, welcome_email_text
        app_url = (settings.APP_URL or "https://www.divarc.fr").rstrip("/")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": settings.RESEND_FROM, "to": [email],
                      "subject": "Bienvenue sur DIVARC 🎉",
                      "html": welcome_email_html(name or "", app_url),
                      "text": welcome_email_text(name or "", app_url)},
            )
            j = r.json()
            if isinstance(j, dict) and j.get("error"):
                return {"error": str(j["error"])}
            return {"sent": True}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ---------------- Géolocalisation (Geoapify + repli Nominatim) ----------------

async def geo_autocomplete(q: str, country: str | None = None) -> list[dict]:
    key = settings.GEOAPIFY_API_KEY
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if key:
                r = await client.get("https://api.geoapify.com/v1/geocode/autocomplete", params={
                    "text": q, "apiKey": key, "limit": "8", "lang": "fr",
                    "filter": f"countrycode:{country.lower() if country else EU_CC}",
                })
                j = r.json()
                out = []
                for f in (j.get("features") or []):
                    p = f.get("properties", {})
                    out.append({
                        "label": p.get("formatted"), "city": p.get("city") or p.get("county") or p.get("name") or "",
                        "postcode": p.get("postcode") or "", "country": (p.get("country_code") or "").upper(),
                        "lat": p.get("lat"), "lon": p.get("lon"), "provider": "geoapify",
                    })
                return out
            r = await client.get("https://nominatim.openstreetmap.org/search", params={
                "q": q, "format": "jsonv2", "addressdetails": "1", "limit": "8", "accept-language": "fr",
                "countrycodes": country.lower() if country else EU_CC,
            }, headers={"User-Agent": "DIVARC-Marketplace/1.0 (contact@divarc.eu)"})
            arr = r.json()
            out = []
            for a in (arr if isinstance(arr, list) else []):
                addr = a.get("address", {})
                out.append({
                    "label": a.get("display_name"),
                    "city": addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or a.get("name") or "",
                    "postcode": addr.get("postcode") or "", "country": (addr.get("country_code") or "").upper(),
                    "lat": float(a["lat"]), "lon": float(a["lon"]), "provider": "osm",
                })
            return out
    except Exception as e:  # noqa: BLE001
        print("geoAutocomplete", e)
        return []


async def geo_reverse(lat: float, lon: float) -> dict:
    key = settings.GEOAPIFY_API_KEY
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if key:
                r = await client.get("https://api.geoapify.com/v1/geocode/reverse", params={
                    "lat": str(lat), "lon": str(lon), "lang": "fr", "apiKey": key,
                })
                j = r.json()
                feats = j.get("features") or []
                p = feats[0].get("properties", {}) if feats else {}
                return {"label": p.get("formatted") or "", "city": p.get("city") or p.get("county") or "",
                        "postcode": p.get("postcode") or "", "country": (p.get("country_code") or "").upper(),
                        "lat": float(lat), "lon": float(lon)}
            r = await client.get("https://nominatim.openstreetmap.org/reverse", params={
                "lat": str(lat), "lon": str(lon), "format": "jsonv2", "addressdetails": "1", "accept-language": "fr",
            }, headers={"User-Agent": "DIVARC-Marketplace/1.0 (contact@divarc.eu)"})
            a = r.json()
            addr = a.get("address", {})
            return {"label": a.get("display_name") or "", "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
                    "postcode": addr.get("postcode") or "", "country": (addr.get("country_code") or "").upper(),
                    "lat": float(lat), "lon": float(lon)}
    except Exception as e:  # noqa: BLE001
        print("geoReverse", e)
        return {"label": "", "city": "", "postcode": "", "country": "", "lat": float(lat), "lon": float(lon)}


# ---------------- Publicités : dérivés, estimation, historique, sponsorisés ----------------

def ad_derived(c: dict) -> dict:
    impr = c.get("impressions") or 0
    clk = c.get("clicks") or 0
    spent = c.get("spentCents") or 0
    conv = c.get("conversions") or 0
    return {
        **c,
        "ctr": round(clk / impr * 100, 2) if impr else 0,
        "cpcCents": round(spent / clk) if clk else 0,
        "cpmCents": round(spent / impr * 1000) if impr else 0,
        "convRate": round(conv / clk * 100, 2) if clk else 0,
        "cpaCents": round(spent / conv) if conv else 0,
        "remainingCents": max(0, (c.get("budgetCents") or 0) - spent),
    }


def estimate_reach(daily_budget_cents: int = 0, bid_strategy: str = "cpc", max_bid_cents: int = 0, targeting: dict | None = None) -> dict:
    targeting = targeting or {}
    locs = len(targeting.get("locations") or [])
    ints = len(targeting.get("interests") or [])
    ages = len(targeting.get("ageRange") or [])
    breadth = 1.0
    breadth *= 1 if locs == 0 else min(1, 0.25 + locs * 0.15)
    breadth *= 1 if ints == 0 else min(1, 0.3 + ints * 0.12)
    breadth *= 1 if ages == 0 else min(1, 0.35 + ages * 0.14)
    audience = round(2_400_000 * breadth)
    cpm_base = max(300, max_bid_cents or 500) if bid_strategy == "cpm" else 550
    cpc_base = max(15, max_bid_cents or 45) if bid_strategy in ("cpc", "maximize") else 45
    daily_impr = round(daily_budget_cents / cpm_base * 1000) if daily_budget_cents > 0 else 0
    ctr = 0.012 + random.random() * 0.006
    daily_clicks = round(daily_impr * ctr)
    daily_reach = min(audience, round(daily_impr * 0.78))
    return {
        "audience": audience,
        "impressionsPerDay": [round(daily_impr * 0.75), round(daily_impr * 1.25)],
        "clicksPerDay": [round(daily_clicks * 0.7), round(daily_clicks * 1.3)],
        "reachPerDay": [round(daily_reach * 0.75), round(daily_reach * 1.25)],
        "estCpcCents": cpc_base, "estCtr": round(ctr * 100, 2),
    }


def simulate_history(camp: dict, days: int = 7) -> dict:
    daily = []
    tot_impr = tot_clk = tot_spent = tot_conv = 0
    per_day_budget = (camp.get("dailyBudgetCents") or round(camp["budgetCents"] / 30)) if camp.get("budgetType") == "daily" else round(camp["budgetCents"] / 14)
    for i in range(days - 1, -1, -1):
        date = (now() - timedelta(days=i)).isoformat()[:10]
        spend = min(per_day_budget, round(per_day_budget * (0.55 + random.random() * 0.5)))
        ctr = 0.012 + random.random() * 0.008
        impr = round(spend / (6 if camp.get("type") in ("display", "video") else 5.2))
        clicks = max(0, round(impr * ctr))
        conv = max(0, round(clicks * (0.03 + random.random() * 0.05)))
        daily.append({"date": date, "impressions": impr, "clicks": clicks, "spentCents": spend, "conversions": conv})
        tot_impr += impr
        tot_clk += clicks
        tot_spent += spend
        tot_conv += conv
    capped = min(tot_spent, camp["budgetCents"])
    return {"daily": daily, "impressions": tot_impr, "clicks": tot_clk, "spentCents": capped, "conversions": tot_conv}


def ad_keyword_suggest(seed: str | None) -> list[dict]:
    s = (seed or "produit").lower().strip()
    mods = ["pas cher", "en ligne", "livraison", "avis", "meilleur", "promo", "près de moi", "occasion", "neuf", "2025"]
    base = [s] + [f"{s} {m}" for m in mods]
    return [{
        "text": text, "matchType": "broad",
        "volume": random.randint(1000, 41000),
        "competition": random.choice(["Faible", "Moyenne", "Élevée"]),
        "suggestedBidCents": random.randint(20, 100),
    } for text in base[:10]]


async def get_sponsored(db) -> list[dict]:
    camps = await db.campaigns.find({"status": "active"}).to_list(length=None)
    out = []
    for c in camps:
        if (c.get("spentCents") or 0) >= c["budgetCents"]:
            continue
        creative = c.get("creative") or {}
        out.append({
            "id": "ad-" + c["id"], "sponsored": True, "campaignId": c["id"],
            "author": {"id": c.get("ownerId"), "name": c.get("brand") or "Annonceur",
                       "handle": c.get("brandHandle") or "@annonceur",
                       "initials": (c.get("brand") or "AD")[:2].upper(),
                       "avatarColor": c.get("color") or "#4353F0", "verified": True},
            "caption": f"{creative.get('headline') or c.get('name')}\n{creative.get('body') or ''}".strip(),
            "hashtags": [], "likes": 0, "comments": 0, "saves": 0, "views": c.get("impressions") or 0,
            "product": ({"title": creative.get("cta") or "Découvrir", "priceCents": creative["priceCents"], "emoji": creative.get("emoji") or "🛍️"} if creative.get("priceCents") else None),
            "aiGenerated": False, "liked": False, "saved": False, "following": False,
            "cta": creative.get("cta") or "En savoir plus", "color": c.get("color") or "#4353F0", "emoji": creative.get("emoji") or "📣",
            "mediaUrl": creative.get("mediaUrl"), "reason": "Sponsorisé", "createdAt": now(),
        })
        if len(out) >= 3:
            break
    return out


def inject_ads(out: list[dict], ads: list[dict]) -> list[dict]:
    if not ads:
        return out
    merged = list(out)
    pos = 1
    for ad in ads:
        if pos <= len(merged):
            merged.insert(pos, ad)
            pos += 4
    return merged
