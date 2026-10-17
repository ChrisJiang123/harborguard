"""HarborGuard Agent 服务入口（C3 阶段一：真实后端事件 → 上下文 → 模板建议 → 后端广播）。

用法（仓库根目录）::

    .venv/bin/python -m agent.main     # 读取 .env，监听 AGENT_HOST:AGENT_PORT（默认 8001）

链路：WS 订阅 /ws → options_ready → REST 拉齐上下文 → 模板建议 →
pydantic + 真实 ID 双重校验 → POST /api/recommendations。
本阶段不接云端/Ollama；恒不改警报等级、绝不调用 /api/decision。
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
from .context import collect_security, context_ids
from .schemas import Recommendation, normalize_draft, validate_draft
from .template import generate_answer, generate_security

MAX_SEEN_SEQS = 2000  # 事件去重窗口（seq 有界集合）
ASK_BUDGET_S = 18.0  # B 的代理预算是 20 秒，预留序列化与转发余量


class TaskQueue:
    """事件去重 + 每警报仅保留最新任务 + 场景重置清空。

    - seq 去重：重连补事件与实时推送重叠时不会重复入队；
    - 同一警报：新 options_ready（方案集签名不同）覆盖旧任务 → 可触发新建议，
      相同方案集签名则跳过；
    - alert_cleared / scenario_changed(reset|started)：丢弃相关/全部待处理任务。
    """

    def __init__(self) -> None:
        self._seen: set[int] = set()
        self._seen_order: deque[int] = deque()
        self._tasks: dict[str, dict] = {}
        self._generation = 0
        self._versions: dict[str, int] = {}
        self._signatures: dict[str, str] = {}

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
            self.drop(data.get("alert_id"))
            return None
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
        if self._signatures.get(alert_id) == signature:
            return None  # 排队中、处理中或已提交的相同载荷均只处理一次
        version = self._versions.get(alert_id, 0) + 1
        self._versions[alert_id] = version
        self._signatures[alert_id] = signature
        task = {
            "kind": "options_ready",
            "alert_id": alert_id,
            "options": options,
            "ranked": ranked,
            "signature": signature,
            "generation": self._generation,
            "version": version,
            "t": msg.get("t"),
            "queued_at": time.perf_counter(),
        }
        self._tasks[alert_id] = task  # 覆盖旧任务：同警报只处理最新
        return task

    def take(self) -> dict | None:
        """取最早入队的任务（串行处理）。"""
        for alert_id in list(self._tasks):
            return self._tasks.pop(alert_id)
        return None

    def clear(self) -> None:
        self._generation += 1
        self._tasks.clear()
        self._versions.clear()
        self._signatures.clear()

    def drop(self, alert_id: str | None) -> None:
        if not alert_id:
            return
        self._tasks.pop(alert_id, None)
        self._signatures.pop(alert_id, None)
        self._versions[alert_id] = self._versions.get(alert_id, 0) + 1

    def is_current(self, task: dict) -> bool:
        """处理中任务只有在场景代际和警报版本均未变化时才可提交。"""
        return (
            task.get("generation") == self._generation
            and task.get("version") == self._versions.get(task.get("alert_id"))
        )

    def __len__(self) -> int:
        return len(self._tasks)


settings = get_settings()
queue = TaskQueue()
client = BackendClient(settings)
wake = asyncio.Event()
stop = asyncio.Event()
stats = {"processed": 0, "submitted": 0, "errors": 0, "dropped": 0}


def handle_event(msg: dict) -> None:
    if queue.offer_event(msg) is not None:
        wake.set()


async def process_options_ready(task: dict) -> Recommendation | None:
    """上下文 → 模板 → 双重校验 → POST。返回 None 表示任务被安全丢弃。"""
    alert_id = task["alert_id"]
    started = time.perf_counter()
    try:
        context = await collect_security(client, alert_id, task["options"], task["ranked"])
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            stats["dropped"] += 1  # 场景已重置/警报已清除：不得提交旧任务的建议
            return None
        raise

    if not queue.is_current(task):
        stats["dropped"] += 1
        return None

    draft = normalize_draft(generate_security(context))
    errors = validate_draft(draft, context_ids(context), {o["id"] for o in context.get("options", [])})
    if errors:  # 模板链路应为确定性正确；出现错误则拒绝提交（宁缺勿假）
        raise ValueError("模板建议未通过双重校验: " + "; ".join(errors))

    if not queue.is_current(task):
        stats["dropped"] += 1
        return None

    rec = Recommendation(
        id=f"rec-{uuid.uuid4().hex[:12]}",
        kind="security",
        alert_id=alert_id,
        model="template",
        summary=draft.summary,
        explanation=draft.explanation,
        recommended_option_id=draft.recommended_option_id,
        evidence_ids=draft.evidence_ids,
        uncertainties=draft.uncertainties,
        confidence=draft.confidence,
        created_t=float(context.get("t", 0.0)),
        latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
    )
    await client.post_recommendation(rec.model_dump())
    stats["submitted"] += 1
    return rec


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
            rec = await process_options_ready(task)
            if rec is not None:
                try:
                    await client.post_log(
                        "info",
                        f"已提交模板建议 {rec.id}（{rec.alert_id} → {rec.recommended_option_id}，"
                        f"{rec.latency_ms:.0f} ms）",
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
                await client.post_log("warn", f"Agent 建议提交失败 {task['alert_id']}: {detail}")
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001 - 单任务失败不拖垮服务
            stats["errors"] += 1
            try:
                await client.post_log("warn", f"Agent 处理异常 {task['alert_id']}: {exc}")
            except Exception:  # noqa: BLE001
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop.clear()
    wake.clear()
    ws_task = asyncio.create_task(client.stream_events(handle_event, stop=stop))
    worker = asyncio.create_task(worker_loop())
    yield
    stop.set()
    wake.set()
    for t in (ws_task, worker):
        t.cancel()
    await asyncio.gather(ws_task, worker, return_exceptions=True)
    await client.aclose()


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
    return {
        "ok": True,
        "service": "agent",
        "model": "template",
        "phase": "c3-stage1",
        "pending_tasks": len(queue),
        "stats": dict(stats),
        "backend": client.base,
    }


@app.post("/ask")
async def ask(body: AskBody) -> dict:
    """/ask 模板回答（后端 /api/agent/ask 转发）：只引用后端事实，总预算 << 20 秒。"""
    track: dict | None = None
    state: dict | None = None
    try:
        async with asyncio.timeout(ASK_BUDGET_S):
            state = await client.get_state()
            if body.track_id:
                try:
                    track = await client.get_track(body.track_id)
                except httpx.HTTPStatusError:
                    track = None
            answer = generate_answer(body.question, track=track, state=state)
    except Exception:  # noqa: BLE001 - 任何失败都要在预算内给出模板答案
        answer = "后端数据暂不可用，请稍后重试；最终判断由值班员作出。"
    return {"answer": answer, "model": "template"}


if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(app, host=s.agent_host, port=s.agent_port, log_level="info")
