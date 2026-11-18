"""Rate limiting (NFR-SYS-S-6).

Usage on a route:

    from app.core.rate_limit import limiter

    @router.post("/something")
    @limiter.limit("10/minute")
    async def something(request: Request, ...): ...

The route must take a `request: Request` argument for slowapi to work.
Uses in-memory counters, which is fine for one Render instance.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
