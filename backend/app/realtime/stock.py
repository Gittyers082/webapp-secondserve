"""Live stock updates over WebSockets (FR-SYS-6).

Browsers connect to /ws/stock and receive messages like:

    {"type": "stock", "listingId": "...", "quantity": 3, "status": "active"}

This in-memory version works while the API runs as a single Render instance.
TODO(Role 3): to run more than one instance, publish these messages through
Upstash Redis pub/sub and have each instance forward them to its own sockets.
"""

import asyncio
import json
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class StockBroadcaster:
    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()
        self._lock = asyncio.Lock()

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
