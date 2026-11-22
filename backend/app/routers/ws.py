"""WebSocket endpoint for live stock counts. Owner: Role 3."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.stock import stock

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/stock")
async def stock_updates(ws: WebSocket) -> None:
    """Public, read-only feed: anyone browsing the shop can see stock change live."""
    await stock.connect(ws)
    try:
        while True:
            # We don't expect messages from the browser; this just keeps the socket open.
            await ws.receive_text()
    except WebSocketDisconnect:
        await stock.disconnect(ws)
