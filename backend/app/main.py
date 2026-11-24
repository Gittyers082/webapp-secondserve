"""SecondServe API entry point.

Run locally:   uvicorn app.main:app --reload
Docs:          http://localhost:8000/docs  (interactive, generated from the code)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.realtime.stock import stock
from app.routers import (
    admin,
    health,
    internal,
    listings,
    me,
    notifications,
    orders,
    partners,
    ws,
)

log = logging.getLogger("app")


async def _catch_errors(request: Request, call_next):
    """Turn a crash into a JSON 500 *inside* the CORS layer.

    Starlette answers unhandled errors from its outermost layer, after CORS has been
    skipped, so the browser reports a CORS error and hides the real 500. Catching it
    here keeps the CORS headers, and the traceback still goes to the Render logs.
    """
    try:
        return await call_next(request)
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            {"detail": "Something went wrong on our side. Try again in a moment."},
            status_code=500,
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await stock.start()
    yield
    await stock.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SecondServe API",
        version="0.1.0",
        description="Marketplace for surplus and near-expiry food. Pickup only.",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    # Added before CORS so it runs inside it (the last middleware added runs first).
    app.middleware("http")(_catch_errors)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (health, me, listings, orders, partners, notifications, admin, internal, ws):
        app.include_router(module.router)

    return app


app = create_app()
