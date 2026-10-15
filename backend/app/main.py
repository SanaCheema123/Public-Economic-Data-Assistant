from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import auth, catalog, chat, dashboard, export, me, query, saved, search
from app.core.config import settings
from app.database.init_db import init_db
from app.database.seed import seed_source_registry
from app.database.session import SessionLocal, engine
from app.security.middleware import InMemoryRateLimitMiddleware, RequestContextMiddleware
from app.services.live_data import live_data_status, sync_live_data

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("peda.main")


async def _sync_live_data_once(*, force: bool = False) -> None:
    db = SessionLocal()
    try:
        result = await sync_live_data(db, force=force)
        if not result.get("ok") and not result.get("skipped"):
            logger.warning("live_data_sync_failed result=%s", result)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        db.rollback()
        logger.warning("live_data_sync_failed error_type=%s", type(exc).__name__)
    finally:
        db.close()


async def _live_refresh_loop() -> None:
    # Wake at the shorter source cadence. Each connector performs its own
    # freshness check, so GASTAT can refresh more often without repeatedly
    # downloading the slower-changing World Bank annual series.
    interval_seconds = max(300, min(settings.data_refresh_hours * 3600, settings.gastat_refresh_minutes * 60))
    while True:
        await asyncio.sleep(interval_seconds)
        await _sync_live_data_once(force=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_source_registry(db)
    finally:
        db.close()

    if settings.data_sync_on_startup and settings.data_mode == "live":
        await _sync_live_data_once(force=False)

    refresh_task: asyncio.Task | None = None
    if settings.data_background_refresh and settings.data_mode == "live":
        refresh_task = asyncio.create_task(_live_refresh_loop(), name="live-data-refresh")

    try:
        yield
    finally:
        if refresh_task:
            refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await refresh_task


app = FastAPI(
    title="Public Economic Data Assistant API",
    version="1.3.0-official-live",
    description="Bilingual, citation-first public economic data API with live verified synchronization, safe Text-to-SQL and RAG.",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(InMemoryRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.frontend_url.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

for router in [auth.router, me.router, catalog.router, chat.router, query.router, dashboard.router, saved.router, export.router, search.router]:
    app.include_router(router)


@app.get("/health", tags=["System"])
def health():
    db_ok = False
    data = {"ready": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
        db = SessionLocal()
        try:
            data = live_data_status(db)
        finally:
            db.close()
    except Exception:
        db_ok = False
    overall = "ok" if db_ok and data.get("ready") else "degraded"
    return {
        "status": overall,
        "database": "ok" if db_ok else "unavailable",
        "data_mode": settings.data_mode,
        "live_data": data,
        "ai_mode": settings.effective_ai_mode,
        "ai_runtime": settings.ai_runtime,
        "ai_provider": settings.ai_provider,
        "environment": settings.environment,
    }


@app.get("/", include_in_schema=False)
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/health", "data_mode": settings.data_mode}
