import json
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from hpao.realtime.postgres import RealtimeListener


def make_realtime_router(listener: RealtimeListener) -> APIRouter:
    """Build the realtime WebSocket router bound to a shared RealtimeListener.

    Auth is intentionally deferred for the hackathon: anyone who knows a
    channel name (UUIDs in practice) can subscribe. Phase 8 will gate this
    behind the same HMAC scheme used for inter-agent calls.
    """
    router = APIRouter()

    @router.websocket("/v1/realtime")
    async def realtime_ws(
        websocket: WebSocket,
        channel: Annotated[list[str] | None, Query()] = None,
    ) -> None:
        if not channel:
            await websocket.close(code=1008, reason="at least one channel required")
            return

        await websocket.accept()
        try:
            async with listener.subscribe(channel) as queue:
                while True:
                    received_channel, payload = await queue.get()
                    await websocket.send_json(
                        {"channel": received_channel, "event": json.loads(payload)}
                    )
        except WebSocketDisconnect:
            return

    return router
