"""
Application lifecycle: manage the shared Playwright browser instance.

A single persistent Chromium profile is launched once at startup and reused
for every request. The browser is NOT headless so the user can log in manually
on first use. Set HEADLESS=1 in .env after authentication is confirmed.
"""

import logging
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.deps import browser_manager, limiter
from app.routes import router

logger = logging.getLogger("humain-webai-to-api")

app = FastAPI(
    title="humain-webai-to-api",
    version="0.1.0",
    description="Local OpenAI-compatible API wrapper for HUMAIN Chat",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Lifecycle hooks ─────────────────────────────────────────────────────


@app.on_event("startup")
async def startup() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    )
    logger.info("Launching persistent browser (profile=%s)", settings.browser_profile_dir)
    await browser_manager.start()
    logger.info("Browser ready – humain-webai-to-api started on %s:%s", settings.host, settings.port)


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("Shutting down browser…")
    await browser_manager.stop()
    logger.info("Bye.")


# ── Request logging middleware ──────────────────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("→ %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("← %s %s  status=%s", request.method, request.url.path, response.status_code)
    return response


# ── Routes ──────────────────────────────────────────────────────────────

app.include_router(router)
