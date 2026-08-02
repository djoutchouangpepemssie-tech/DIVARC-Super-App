"""Application FastAPI DIVARC — backend Python (remplace app/api/route.js)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .db import close_mongo, connect_to_mongo
from .indexes import ensure_indexes
from .routers import (admin, ads, arcade, assistant, auth, dating, discovery, eclats, market, messaging,
                      notifications, pay, plus, push, social, store, wallet, ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le démarrage ne doit JAMAIS être bloqué ni crashé par la base : même une URL Mongo
    # malformée ou injoignable laisse l'app démarrer (le healthcheck /api/health répond),
    # ce qui permet de diagnostiquer via /api/debug/db.
    try:
        db = await connect_to_mongo()
        await db.command("ping")
        n = await ensure_indexes(db)
        print(f"[startup] MongoDB OK, {n} index prêts")
    except Exception as e:  # noqa: BLE001
        print(f"[startup] MongoDB indisponible au démarrage (l'app démarre quand même): {e}")
    # Contexte social (PostgreSQL) : crée le schéma si la base est configurée (idempotent)
    if settings.social_enabled:
        try:
            from .social.adapters.persistence.db import create_all as social_create_all
            await social_create_all()
            print("[startup] Social PostgreSQL : schéma prêt")
        except Exception as e:  # noqa: BLE001
            print(f"[startup] Social DB indisponible (l'app démarre quand même) : {e}")
    yield
    await close_mongo()


app = FastAPI(title="DIVARC API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Uniformise TOUTES les erreurs HTTP au format { "error": ... } (comme route.js).
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.get("/api")
@app.get("/api/")
@app.get("/api/health")
async def health():
    from .helpers import now
    return {"service": "DIVARC API", "status": "live", "time": now().isoformat()}


for r in (auth, wallet, messaging, social, market, ads, store, admin, assistant, ws, notifications, pay, discovery, push, eclats, dating, plus, arcade):
    app.include_router(r.router, prefix="/api")

# Nouveau contexte social (réseau type Facebook) — PostgreSQL/hexagonal
from .social.api.router import router as social_net_router  # noqa: E402
app.include_router(social_net_router, prefix="/api")
