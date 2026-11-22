"""Live stock updates over WebSockets (FR-SYS-6).

Browsers connect to /ws/stock and receive messages like:

    {"type": "stock", "listingId": "...", "quantity": 3, "status": "active"}

With REDIS_URL set, messages go through Redis pub/sub: every API instance
subscribes and forwards what it hears to its own sockets, so scaling to several
instances works. Without Redis (local dev) it falls back to this process only.
Postgres stays the source of truth for stock; Redis only carries the change events.
"""

import asyncio
import json
import logging

from fastapi import WebSocket

from app.core.config import get_settings

log = logging.getLogger(__name__)

CHANNEL = "secondserve:stock"


class StockBroadcaster:
    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._redis = None
        self._listener: asyncio.Task | None = None

    async def start(self) -> None:
        """Connect to Redis and start forwarding. Called once when the API starts."""
        url = get_settings().redis_url
        if not url:
            return
        from redis.asyncio import from_url  # only needed when Redis is configured

        self._redis = from_url(url, decode_responses=True)
        self._listener = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._listener:
            self._listener.cancel()
        if self._redis:
            await self._redis.aclose()

    async def _listen(self) -> None:
        while True:  # reconnect if Redis drops
            try:
                pubsub = self._redis.pubsub()
                await pubsub.subscribe(CHANNEL)
                async for item in pubsub.listen():
                    if item["type"] == "message":
                        await self._send_local(item["data"])
            except asyncio.CancelledError:
                raise
            except Exception:
                log.warning("stock subscriber lost Redis; retrying in 2s", exc_info=True)
                await asyncio.sleep(2)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._sockets.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._sockets.discard(ws)

    async def publish(self, listing_id: str, quantity: int, status: str) -> None:
        message = json.dumps(
            {"type": "stock", "listingId": listing_id, "quantity": quantity, "status": status}
        )
        if self._redis is not None:
            try:
                await self._redis.publish(CHANNEL, message)  # our own listener sends it on
                return
            except Exception:
                log.warning("Redis publish failed; sending to this instance only", exc_info=True)
        await self._send_local(message)

    async def _send_local(self, message: str) -> None:
        async with self._lock:
            sockets = list(self._sockets)
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:  # client went away
                log.debug("dropping closed websocket")
                await self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._sockets)


stock = StockBroadcaster()
