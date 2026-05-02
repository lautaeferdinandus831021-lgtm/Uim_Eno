import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from shared.config import settings
from shared.logging import setup_logging
from app.core.database import init_db
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routes import auth_router, trades_router, bot_router, backtest_router, ws_router

import app.models  # noqa: F401

setup_logging("backend")
logger = logging.getLogger("bgbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("BG-BOT v5 API Starting")
    await init_db()
    logger.info("Database connected")
    logger.info("=" * 50)
    yield
    logger.info("BG-BOT v5 API shutting down")


app = FastAPI(title="BG-BOT v5", version="5.0.0", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, max_req=settings.MAX_REQUESTS_PER_MINUTE)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(auth_router)
app.include_router(trades_router)
app.include_router(bot_router)
app.include_router(backtest_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0", "service": "backend"}
