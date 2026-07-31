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
from .routers import admin, ads, assistant, auth, market, messaging, notifications, social, store, wallet, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await connect_to_mongo()
    await ensure_indexes(db)
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


for r in (auth, wallet, messaging, social, market, ads, store, admin, assistant, ws, notifications):
    app.include_router(r.router, prefix="/api")
