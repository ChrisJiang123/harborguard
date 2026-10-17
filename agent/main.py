"""HarborGuard Agent 服务入口（C3：真实事件 → 云端/本地/模板建议 → 后端广播）。

用法（仓库根目录）::

    .venv/bin/python -m agent.main     # 读取 .env，监听 AGENT_HOST:AGENT_PORT（默认 8001）

链路：WS 订阅 /ws → 四类任务触发 → REST 拉齐上下文 → 云端/本地/模板 →
pydantic + 真实 ID + 确定性事实校验 → POST /api/recommendations。
恒不改警报等级、绝不调用 /api/decision。
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from .backend_client import BackendClient
from .config import get_settings
from .context import collect_buoy, collect_disaster, collect_security
from .router import AnswerResult, GenerationResult, Router
from .schemas import Recommendation
from .template import generate_answer

MAX_SEEN_SEQS = 2000  # 事件去重窗口（seq 有界集合）


class TaskQueue:
    """事件去重 + 同一对象仅保留最新任务 + 场景重置清空。

    - seq 去重：重连补事件与实时推送重叠时不会重复入队；
    - security 以 alert 为键，buoy 以 buoy 为键，disaster 为单例；
    - reopen_plan 同计划不重复，且仿真时间最多每 20 秒接受一次；
    - alert_cleared / buoy_up / scenario_changed(reset|started) 会使旧任务失效。
    """

    def __init__(self) -> None:
        self._seen: set[int] = set()
        self._seen_order: deque[int] = deque()
        self._tasks: dict[str, dict] = {}
        self._generation = 0
        self._versions: dict[str, int] = {}
        self._signatures: dict[str, str] = {}
        self._last_reopen_t: float | None = None

    def _offer(self, key: str, signature: str, **payload) -> dict | None:
        if self._signatures.get(key) == signature:
            return None
        version = self._versions.get(key, 0) + 1
        self._versions[key] = version
        self._signatures[key] = signature
        task = {
            "key": key,
            "signature": signature,
            "generation": self._generation,
            "version": version,
            "queued_at": time.perf_counter(),
            **payload,
        }
        self._tasks[key] = task
        return task

    def offer_event(self, msg: dict) -> dict | None:
        seq = msg.get("seq")
        if seq is not None:
            if seq in self._seen:
                return None
            self._seen.add(int(seq))
            self._seen_order.append(int(seq))
            while len(self._seen_order) > MAX_SEEN_SEQS:
                self._seen.discard(self._seen_order.popleft())
        name = msg.get("event")
        data = msg.get("data") or {}

        if name == "scenario_changed" and data.get("status") in ("reset", "started"):
            self.clear()
            return None
        if name == "alert_cleared":
            self.drop(f"security:{data.get('alert_id')}")
            return None
        if name == "alert_changed":
            alert = data.get("alert") or {}
            alert_id = alert.get("id")
            key = f"security:{alert_id}"
            if data.get("to_level") != 2 or not isinstance(data.get("from_level"), int) or data["from_level"] >= 2:
                self.drop(key)
                return None
            signature = json.dumps(
                {"trigger": name, "alert": alert}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            return self._offer(
                key,
                signature,
                kind="security",
                trigger=name,
                alert_id=alert_id,
                options=[],
                ranked=[],
                t=msg.get("t"),
            )
        if name == "reopen_plan":
            event_t = float(msg.get("t", 0.0))
            if self._last_reopen_t is not None and event_t - self._last_reopen_t < 20.0:
                return None
            signature = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            task = self._offer(
                "disaster",
                signature,
                kind="disaster",
                trigger=name,
                alert_id=None,
                plan=dict(data),
                t=event_t,
            )
            if task is not None:
                self._last_reopen_t = event_t
            return task
        if name == "buoy_changed":
            buoy_id = data.get("buoy_id")
            key = f"buoy:{buoy_id}"
            if data.get("status") != "down":
                self.drop(key)
                return None
            signature = json.dumps(
                {"buoy_id": buoy_id, "status": "down"}, sort_keys=True, separators=(",", ":")
            )
            return self._offer(
                key,
                signature,
                kind="buoy",
                trigger=name,
                alert_id=None,
                buoy_id=buoy_id,
                t=msg.get("t"),
            )
        if name != "options_ready":
            return None

        alert_id = data.get("alert_id")
        options = data.get("options") or []
        ranked = data.get("ranked") or []
        signature = json.dumps(
            {"options": options, "ranked": ranked},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return self._offer(
            f"security:{alert_id}",
            signature,
            kind="security",
            trigger=name,
            alert_id=alert_id,
            options=options,
            ranked=ranked,
            t=msg.get("t"),
        )

    def take(self) -> dict | None:
        """取最早入队的任务（串行处理）。"""
        for key in list(self._tasks):
            return self._tasks.pop(key)
        return None

    def clear(self) -> None:
        self._generation += 1
        self._seen.clear()
        self._seen_order.clear()
        self._tasks.clear()
        self._versions.clear()
        self._signatures.clear()
        self._last_reopen_t = None

    def drop(self, key: str | None) -> None:
        if not key:
            return
        self._tasks.pop(key, None)
        self._signatures.pop(key, None)
        self._versions[key] = self._versions.get(key, 0) + 1

    def is_current(self, task: dict) -> bool:
        """处理中任务只有在场景代际和对象版本均未变化时才可提交。"""
        return (
            task.get("generation") == self._generation
            and task.get("version") == self._versions.get(task.get("key"))
        )

    def __len__(self) -> int:
        return len(self._tasks)


settings = get_settings()
queue = TaskQueue()
client = BackendClient(settings)
router = Router(settings)
wake = asyncio.Event()
stop = asyncio.Event()
stats = {
    "processed": 0,
    "submitted": 0,
    "errors": 0,
    "dropped": 0,
    "routes": {"cloud": 0, "local": 0, "template": 0},
    "kinds": {"security": 0, "disaster": 0, "buoy": 0},
}
last_announced_model: str | None = None
model_log_lock = asyncio.Lock()


def handle_event(msg: dict) -> None:
    if msg.get("event") == "network_changed" and (msg.get("data") or {}).get("network") == "online":
        router.reset_cloud_circuit()
    if queue.offer_event(msg) is not None:
        wake.set()


async def process_task(task: dict) -> tuple[Recommendation, GenerationResult] | None:
    """沿用既有链路加入模型路由；返回 None 表示任务被安全丢弃。"""
    alert_id = task.get("alert_id")
    started = float(task.get("queued_at", time.perf_counter()))
    deadline = started + settings.agent_event_budget_s
    try:
        context_remaining = deadline - settings.agent_post_reserve_s - time.perf_counter()
        if context_remaining <= 0:
            stats["dropped"] += 1
            return None
        async with asyncio.timeout(context_remaining):
            if task["kind"] == "security":
                context = await collect_security(client, alert_id, task["options"], task["ranked"])
            elif task["kind"] == "disaster":
                context = await collect_disaster(client, task["plan"])
            else:
                context = await collect_buoy(client, task["buoy_id"])
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            stats["dropped"] += 1  # 场景已重置/警报已清除：不得提交旧任务的建议
            return None
        raise

    if not queue.is_current(task):
        stats["dropped"] += 1
        return None

    result = await router.generate(context, deadline=deadline)

    if not queue.is_current(task):
        stats["dropped"] += 1
        return None

    rec = Recommendation(
        id=f"rec-{uuid.uuid4().hex[:12]}",
        kind=context["kind"],
        alert_id=alert_id,
        model=result.model,
        summary=result.draft.summary,
        explanation=result.draft.explanation,
        recommended_option_id=result.draft.recommended_option_id,
        evidence_ids=result.draft.evidence_ids,
        uncertainties=result.draft.uncertainties,
        confidence=result.draft.confidence,
        created_t=float(context.get("t", 0.0)),
        latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
    )
    if not queue.is_current(task):
        stats["dropped"] += 1
        return None
    post_remaining = deadline - time.perf_counter()
    if post_remaining <= 0:
        raise TimeoutError("事件总预算在 POST 前已耗尽")
    async with asyncio.timeout(post_remaining):
        await client.post_recommendation(rec.model_dump())
    stats["submitted"] += 1
    stats["routes"][rec.model] += 1
    stats["kinds"][rec.kind] += 1
    return rec, result


async def announce_model_switch(result: GenerationResult | AnswerResult) -> None:
    """只在实际路由变化时写后端 agent 日志，不记录密钥或原始模型输出。"""
    global last_announced_model
    async with model_log_lock:
        if result.model == last_announced_model:
            return
        previous = last_announced_model or "none"
        text = (
            f"Agent 模型路由 {previous} → {result.model}；provider={result.provider}；"
            f"request_model={result.request_model or 'none'}；"
            f"response_model={result.response_model or 'none'}；"
            f"upstream_provider={result.upstream_provider or 'unknown'}"
        )
        try:
            await client.post_log("info", text)
        except Exception:  # 日志失败不影响主链路，也不提前更新状态以便下次重试
            return
        last_announced_model = result.model


async def worker_loop() -> None:
    while not stop.is_set():
        task = queue.take()
        if task is None:
            try:
                await asyncio.wait_for(wake.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                pass
            wake.clear()
            continue
        stats["processed"] += 1
        try:
            processed = await process_task(task)
            if processed is not None:
                rec, result = processed
                await announce_model_switch(result)
                try:
                    await client.post_log(
                        "info",
                        f"已提交 {rec.model}/{rec.kind} 建议 {rec.id}（{rec.alert_id} → "
                        f"{rec.recommended_option_id}，{rec.latency_ms:.0f} ms）",
                    )
                except Exception:  # noqa: BLE001 - 日志失败不影响建议链路
                    pass
        except httpx.HTTPStatusError as exc:
            stats["errors"] += 1
            detail = f"HTTP {exc.response.status_code}"
            if exc.response.status_code == 422:
                detail += "（后端校验拒绝——场景可能已重置，建议已丢弃）"
                stats["dropped"] += 1
            try:
                await client.post_log("warn", f"Agent 建议提交失败 {task['key']}: {detail}")
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001 - 单任务失败不拖垮服务
            stats["errors"] += 1
            try:
                await client.post_log("warn", f"Agent 处理异常 {task['key']}: {exc}")
            except Exception:  # noqa: BLE001
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop.clear()
    wake.clear()
    await router.startup()
    ws_task = asyncio.create_task(client.stream_events(handle_event, stop=stop))
    worker = asyncio.create_task(worker_loop())
    yield
    stop.set()
    wake.set()
    for t in (ws_task, worker):
        t.cancel()
    await asyncio.gather(ws_task, worker, return_exceptions=True)
    await client.aclose()
    await router.aclose()


app = FastAPI(title="HarborGuard Agent", version="0.1.0", lifespan=lifespan)


class AskBody(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=4000)]
    track_id: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


@app.get("/health")
async def health() -> dict:
    route_health = router.health()
    current_model = (route_health.get("last_route") or {}).get("model") or "idle"
    return {
        "ok": True,
        "service": "agent",
        "model": current_model,
        "phase": "c3-openrouter",
        "pending_tasks": len(queue),
        "stats": dict(stats),
        "router": route_health,
        "backend": client.base,
    }


@app.post("/ask")
async def ask(body: AskBody) -> dict:
    """事实型问答沿用云端 → 本地 → 模板路由，总预算保持 18 秒。"""
    started = time.perf_counter()
    deadline = started + settings.agent_ask_budget_s
    track: dict | None = None
    state: dict | None = None
    try:
        async with asyncio.timeout(settings.agent_ask_budget_s):
            state = await client.get_state()
            if body.track_id:
                try:
                    track = await client.get_track(body.track_id)
                except httpx.HTTPStatusError:
                    track = None
            template_answer = generate_answer(body.question, track=track, state=state)
            track_fields = (
                "id", "status", "cls", "conf", "cue", "depth_m",
                "speed_mps", "heading_deg", "level", "risk", "detection_id",
            )
            facts = {
                "t": state.get("t"),
                "mode": state.get("mode"),
                "network": state.get("network"),
                "scenario": state.get("scenario"),
                "track": {k: track.get(k) for k in track_fields if track and track.get(k) is not None}
                if track else None,
                "alerts": [
                    {k: alert.get(k) for k in ("id", "track_id", "level", "risk", "zone_id", "asset_id")}
                    for alert in state.get("alerts", [])
                ],
            }
            result = await router.answer(
                body.question,
                facts,
                deadline=deadline,
                template_answer=template_answer,
            )
            answer, model = result.answer, result.model
            await announce_model_switch(result)
    except Exception:  # noqa: BLE001 - 任何失败都要在预算内给出模板答案
        answer = "后端数据暂不可用，请稍后重试；最终判断由值班员作出。"
        model = "template"
    return {"answer": answer, "model": model}


if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(app, host=s.agent_host, port=s.agent_port, log_level="info")
