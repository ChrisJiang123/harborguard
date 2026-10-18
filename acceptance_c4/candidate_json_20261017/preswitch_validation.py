"""① 切换前补验：harborguard-lora(json) 走完整 C3 事件链（真实 Router/预算/校验/兜底）。

隔离措施：
- CLOUD_PROVIDER=disabled（零云端流量）；BACKEND 采集与 POST 全部 monkeypatch 为进程内桩，
  不触碰 8000 共享后端、不干扰联调终端演示验收。
- OLLAMA_MODEL=harborguard-lora + OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json（候选配置）。

覆盖：security（有方案/无方案）、disaster、buoy；推荐方案与 null 情形；
重置后旧任务不迟到 POST（is_current 守卫）；POST 前预算耗尽守卫。
逐事件记录：模型合格 / 事实失败→模板 / 超时→模板 / 丢弃，及本地 provider 统计。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# 必须在 import agent.* 之前设置环境（隔离 + 候选配置）
os.environ["CLOUD_PROVIDER"] = "disabled"
os.environ.setdefault("OLLAMA_MODEL", "harborguard-lora")
os.environ["OLLAMA_FORMAT_OVERRIDES"] = "harborguard-lora:json"

REPO = Path("/Users/chrisjiang/Projects/harborguard")
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import httpx  # noqa: E402

PASS: list[tuple[str, bool]] = []


def check(name: str, ok: bool) -> None:
    PASS.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name, flush=True)


async def warm_and_verify_model() -> None:
    digest = ""
    for m in httpx.get("http://localhost:11434/api/tags", timeout=10.0).json()["models"]:
        if m["name"].startswith("harborguard-lora"):
            digest = m.get("digest", "")
    gguf_sha = hashlib.sha256((REPO / "ml/lora/harborguard.gguf").read_bytes()).hexdigest()
    check(f"模型 digest 在册（{digest[:16]}…）", len(digest) == 64)
    check(f"GGUF 哈希一致（{gguf_sha[:16]}…）", gguf_sha.startswith("95704489c1ee021b"))
    started = time.perf_counter()
    httpx.post("http://localhost:11434/api/generate",
               json={"model": "harborguard-lora", "prompt": "warm", "stream": False}, timeout=60.0)
    print(f"  预热完成 {time.perf_counter()-started:.1f}s")


async def main() -> int:
    await warm_and_verify_model()

    import agent.main as am
    from agent.schemas import Recommendation

    assert am.settings.cloud_provider == "disabled", "云端必须禁用"
    assert am.settings.ollama_model == "harborguard-lora"
    assert am.router.local.format_overrides.get("harborguard-lora") == "json"

    # ---- 桩：后端采集/POST（进程内，绝不触网） ----
    contexts = []
    for l in open("acceptance_c4/candidate_json_20261017/confirm60.eval.jsonl", encoding="utf-8"):
        if l.strip():
            contexts.append(json.loads(json.loads(l)["messages"][1]["content"]))
    sec_opt = next(c for c in contexts if c["kind"] == "security" and c.get("ranked"))
    sec_null = next(c for c in contexts if c["kind"] == "security" and not c.get("ranked"))
    dis = next(c for c in contexts if c["kind"] == "disaster")
    buy = next(c for c in contexts if c["kind"] == "buoy")

    posted: list[dict] = []

    async def fake_collect(client, *args, **kwargs):
        return fake_collect.next_context

    async def fake_post_rec(payload):
        posted.append(payload)
        return None

    async def fake_post_log(*a, **k):
        return None

    am.collect_security = fake_collect  # type: ignore[assignment]
    am.collect_disaster = fake_collect  # type: ignore[assignment]
    am.collect_buoy = fake_collect  # type: ignore[assignment]
    am.client.post_recommendation = fake_post_rec  # type: ignore[assignment]
    am.client.post_log = fake_post_log  # type: ignore[assignment]

    def offer(context_kind_key: str, ctx: dict) -> dict:
        offer.n = getattr(offer, "n", 0) + 1
        return am.queue.offer_event({
            "event": "alert_changed" if ctx["kind"] == "security" else
                     ("reopen_plan" if ctx["kind"] == "disaster" else "buoy_changed"),
            "seq": offer.seq,
            "t": ctx.get("t", 0.0),
            "data": ({"alert": {"id": f"AT{offer.n}"}, "to_level": 2, "from_level": 1}
                     if ctx["kind"] == "security" else
                     ({"plan_id": f"P{offer.n}"} if ctx["kind"] == "disaster"
                      else {"buoy_id": f"B{offer.n}", "status": "down"})),
        }) or {}

    async def run_event(name: str, ctx: dict) -> dict:
        offer.seq = getattr(offer, "seq", 100) + 1
        fake_collect.next_context = ctx
        task = offer("", ctx)
        assert task, "任务入队失败"
        started = time.perf_counter()
        processed = await am.process_task(task)
        elapsed = time.perf_counter() - started
        row: dict = {"event": name, "kind": ctx["kind"], "elapsed_s": round(elapsed, 2)}
        if processed is None:
            row["outcome"] = "dropped"
            print(f"  {name}: dropped", flush=True)
            return row
        rec, result = processed
        row.update({
            "outcome": result.model,
            "attempts": result.attempts,
            "rec_option": rec.recommended_option_id,
            "expected": (ctx.get("ranked") or [None])[0],
            "posted": len(posted),
        })
        if result.model == "local":
            row["outcome"] = "model_pass"
        elif am.router.stats["providers"]["local"].get("timeouts", 0) and elapsed > am.settings.agent_event_budget_s - 1.5:
            row["outcome"] = "timeout->template"
        else:
            row["outcome"] = "fact_or_id_fail->template"
        print(f"  {name}: {row['outcome']} option={row['rec_option']} 期望={row['expected']} "
              f"attempts={row['attempts']} {row['elapsed_s']}s", flush=True)
        return row

    # ---- 事件矩阵：三类 × 方案/null ----
    rows = []
    rows.append(await run_event("security-有方案", sec_opt))
    rows.append(await run_event("security-无方案", sec_null))
    rows.append(await run_event("disaster(null)", dis))
    rows.append(await run_event("buoy(null)", buy))

    check("每事件恰好一次提交或安全丢弃", all(
        (r["outcome"] == "dropped") or (r.get("posted") == i + 1) for i, r in enumerate(rows)))
    check("本地模型至少一次合格（model_pass）", any(r["outcome"] == "model_pass" for r in rows))
    check("security 有方案时推荐 ranked[0] 或落入兜底",
          rows[0]["outcome"] != "model_pass" or rows[0]["rec_option"] == rows[0]["expected"])
    check("null 类（disaster/buoy）推荐 null 或落入兜底",
          all(r["outcome"] != "model_pass" or r["rec_option"] is None for r in rows[2:]))

    # ---- 重置后旧任务不迟到 POST ----
    posted.clear()
    fake_collect.next_context = sec_opt
    offer.seq += 1
    task = offer("", sec_opt)
    am.queue.offer_event({"event": "scenario_changed", "seq": offer.seq + 1000, "data": {"status": "reset"}})
    dropped_before = am.stats["dropped"]
    processed = await am.process_task(task)
    check("重置后旧任务被丢弃（process_task 返回 None）", processed is None)
    check("重置后零 POST（无迟到提交）", len(posted) == 0)
    check("丢弃计数递增", am.stats["dropped"] == dropped_before + 1)

    # ---- POST 前预算耗尽守卫 ----
    posted.clear()
    offer.seq += 1
    task = offer("", sec_opt)
    task["queued_at"] = time.perf_counter() - am.settings.agent_event_budget_s - 1  # 人为过期
    raised = False
    dropped_early = False
    try:
        result_expired = await am.process_task(task)
        dropped_early = result_expired is None  # 预算耗尽在采集前：直接安全丢弃
    except TimeoutError:
        raised = True  # 预算耗尽在 POST 前：显式 TimeoutError
    check("预算耗尽被守卫拦截（提前丢弃或 POST 前 TimeoutError）", raised or dropped_early)
    check("预算耗尽零 POST", len(posted) == 0)

    stat = am.router.stats["providers"]["local"]
    print(f"\n本地 provider 统计: {stat}")
    check("云端零流量", am.router.stats["providers"]["cloud"].get("draft_attempts", 0) == 0
          and am.router.stats["providers"]["cloud"].get("ask_attempts", 0) == 0)

    (REPO / "acceptance_c4/candidate_json_20261017/preswitch_events.json").write_text(
        json.dumps({"events": rows, "local_stats": stat,
                    "config": {"ollama_model": am.settings.ollama_model,
                                "format_overrides": am.settings.ollama_format_overrides,
                                "cloud_provider": am.settings.cloud_provider,
                                "budget_s": am.settings.agent_event_budget_s}},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = all(v for _, v in PASS)
    print(f"\n{'全部通过' if ok else '存在失败'}：{sum(v for _, v in PASS)}/{len(PASS)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
