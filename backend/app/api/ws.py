import asyncio
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket(websocket: WebSocket):
    # Browsers send Origin; the local Python Agent connects without one.
    # Use the same startup allowlist as REST CORS, before accepting the socket.
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in websocket.app.state.allowed_origins:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    game = websocket.app.state.engine
    queue = game.bus.subscribe()
    tasks = []
    try:
        await websocket.send_text(game.state().model_dump_json())

        async def sender():
            while True:
                msg = await queue.get()
                if msg is None:
                    await websocket.close(code=1013, reason="Slow consumer; reconnect and recover /api/events")
                    return
                await websocket.send_json(msg)

        async def receiver():
            while True:
                await websocket.receive_text()  # Receive only to notice client disconnects.

        tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        game.bus.unsubscribe(queue)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError, OSError):
                await task
