"""SecondServe API entry point.

Run locally:   uvicorn app.main:app --reload
Docs:          http://localhost:8000/docs  (interactive, generated from the code)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    seller,
    ws,
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (
        health,
        me,
        listings,
        orders,
        partners,
        seller,
        notifications,
        admin,
        internal,
        ws,
    ):
        app.include_router(module.router)

    return app


app = create_app()
