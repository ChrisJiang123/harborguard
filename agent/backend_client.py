"""与 B 后端的 REST / WebSocket 客户端（C3）。

地址约定（任务书 C3 + 后端 README）：
- BACKEND_BASE_URL 保持**后端根地址**语义（如 http://localhost:8000）；
- REST 统一补且仅补一个 /api 前缀（防漏 /api 或重复 /api/api）；
- WS 使用 /ws（.env 的 BACKEND_WS_URL 为空时由根地址推导）。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from typing import Any, Awaitable, Callable

import httpx
import websockets

from .config import Settings, get_settings


def normalize_base(base: str) -> str:
    """后端根地址：去尾斜杠；误填 /api 结尾时剥掉，防止 /api/api。"""
    value = (base or "").strip().rstrip("/")
    return re.sub(r"/api$", "", value, flags=re.IGNORECASE)


def api_url(base: str, path: str) -> str:
    """统一构造 REST 地址：恰好一个 /api 前缀。"""
    p = "/" + (path or "").strip().lstrip("/")
    if not (p == "/api" or p.startswith("/api/")):
        p = "/api" + p
    return normalize_base(base) + p


def ws_url(base: str, ws: str | None = None) -> str:
    explicit = (ws or "").strip()
    if explicit:
        return explicit
    return normalize_base(base).replace("http", "ws", 1) + "/ws"


class BackendClient:
    """契约 REST 的薄封装 + 断线重连的 WS 事件流。"""

    def __init__(self, settings: Settings | None = None, timeout: float | None = None):
        self.settings = settings or get_settings()
        s = self.settings
        self.base = normalize_base(s.backend_base_url)
        self.ws_endpoint = ws_url(s.backend_base_url, s.backend_ws_url)
        self._http = httpx.AsyncClient(timeout=timeout or s.backend_timeout_s)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get_json(self, path: str) -> Any:
        resp = await self._http.get(api_url(self.base, path))
        resp.raise_for_status()
        return resp.json()

    # ---- 契约 GET 封装（本阶段用到的） ----
    async def get_state(self) -> dict:
        return await self._get_json("state")

    async def get_alert(self, alert_id: str) -> dict:
        return await self._get_json(f"alerts/{alert_id}")

    async def get_track(self, track_id: str) -> dict:
        return await self._get_json(f"tracks/{track_id}")

    async def get_detection(self, det_id: str) -> dict:
        return await self._get_json(f"detections/{det_id}")

    async def get_buoys(self) -> list:
        return await self._get_json("buoys")

    async def get_zones(self) -> dict:
        return await self._get_json("zones")

    async def get_options(self, alert_id: str) -> dict:
        return await self._get_json(f"options/{alert_id}")

    async def get_logs(self, limit: int = 10) -> list:
        return await self._get_json(f"log?limit={int(limit)}")

    async def get_events(self, since_seq: int) -> list:
        return await self._get_json(f"events?since_seq={int(since_seq)}")

    # ---- POST ----
    async def post_recommendation(self, rec: dict) -> dict:
        resp = await self._http.post(api_url(self.base, "recommendations"), json=rec)
        resp.raise_for_status()
        return resp.json()

    async def post_log(self, level: str, text: str) -> dict:
        resp = await self._http.post(
            api_url(self.base, "log"),
            json={"level": level, "source": "agent", "text": text[:2000]},
        )
        resp.raise_for_status()
        return resp.json()

    # ---- WebSocket：断线自动重连，重连后用 since_seq 补齐漏掉的事件 ----
    async def stream_events(
        self,
        on_event: Callable[[dict], Awaitable[None] | None],
        *,
        stop: asyncio.Event,
        reconnect_delay_s: float = 2.0,
    ) -> None:
        """持续投递事件，并在首次连接/重连时从 REST 缓存补齐。

        WebSocket 先建立再补事件，因此补齐期间发生的实时事件会留在 WS 缓冲区；
        ``last_seq`` 会过滤二者重叠。后端进程重启后 seq 会回退，此时从 0
        重新建立游标。回调既可为普通函数，也可为 async 函数。
        """
        last_seq: int | None = None

        async def deliver(msg: dict) -> None:
            nonlocal last_seq
            seq = int(msg.get("seq", 0))
            if last_seq is not None and seq <= last_seq:
                return
            result = on_event(msg)
            if inspect.isawaitable(result):
                await result
            last_seq = seq if last_seq is None else max(last_seq, seq)

        while not stop.is_set():
            try:
                async with websockets.connect(self.ws_endpoint, open_timeout=5) as ws:
                    state = await self.get_state()
                    state_seq = int(state.get("seq", 0))
                    if last_seq is None or state_seq < last_seq:
                        last_seq = 0  # 首次启动补缓存；seq 回退表示后端已重启
                    for msg in await self.get_events(last_seq):
                        if msg.get("type") == "event":
                            await deliver(msg)
                    async for raw in ws:
                        if stop.is_set():
                            break
                        msg = json.loads(raw)
                        if msg.get("type") == "event":
                            await deliver(msg)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - 网络抖动一律退避重连
                if stop.is_set():
                    return
                await asyncio.sleep(reconnect_delay_s)


def build_client(settings: Settings | None = None) -> BackendClient:
    return BackendClient(settings)
