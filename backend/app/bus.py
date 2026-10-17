"""One monotonic sequence and bounded per-client queues for all public messages."""
import asyncio
from collections import deque
from collections.abc import Callable

from . import config
from .models import EventMsg, StateMsg


class EventBus:
    def __init__(self):
        self.seq = 0
        self.events: deque[dict] = deque(maxlen=config.EVENT_CACHE_SIZE)
        self.connections: set[asyncio.Queue] = set()
        self.listeners: list[Callable[[dict], None]] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=config.WS_QUEUE_SIZE)
        self.connections.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.connections.discard(queue)

    def _broadcast(self, msg):
        for queue in tuple(self.connections):
            if queue.full():
                self.unsubscribe(queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(None)  # Slow consumer reconnects and recovers via /api/events.
            else:
                queue.put_nowait(msg)
        for listener in self.listeners:
            listener(msg)
        return msg

    def publish_state(self, msg: StateMsg | dict) -> dict:
        payload = msg.model_dump(mode="json") if isinstance(msg, StateMsg) else dict(msg)
        candidate = self.seq + 1
        payload["seq"] = candidate
        validated = StateMsg.model_validate(payload).model_dump(mode="json")
        self.seq = candidate
        return self._broadcast(validated)

    def publish_event(self, name: str, data: dict, t: float) -> dict:
        msg = EventMsg(type="event", seq=self.seq + 1, t=t, event=name, data=data).model_dump(mode="json")
        self.seq += 1
        self.events.append(msg)
        return self._broadcast(msg)

    def since(self, seq: int) -> list[dict]:
        return [msg for msg in self.events if msg["seq"] > seq]
