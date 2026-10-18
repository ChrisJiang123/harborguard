"""C3 运行预算隔离事件测试·第一部分（不发起模型推理，可与评估并行）。

覆盖：
1. 过期任务淘汰：alert_cleared 掉任务、scenario reset 清空并升代、同键新版本使旧任务失效、
   重复 signature 去重、reopen_plan 20s 节流、take FIFO。
2. 超时取消（无推理路径）：deadline 已过期时 Router.generate 直接走确定性模板兜底，
   不触碰任何 provider（stats 零调用），预算内返回。
不修改任何共享接口；不改线上服务。
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.config import get_settings
from agent.main import TaskQueue as TaskStore
from agent.router import Router

PASS: list[tuple[str, bool]] = []


def check(name: str, ok: bool) -> None:
    PASS.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name)


def test_task_store() -> None:
    store = TaskStore()
    alert = {"id": "A9", "level": 2}
    t1 = store.offer_event({"event": "alert_changed", "seq": 1,
                            "data": {"alert": alert, "to_level": 2, "from_level": 1}})
    check("alert_changed 入队", t1 is not None)
    check("重复 signature 去重", store.offer_event({"event": "alert_changed", "seq": 2,
                                                   "data": {"alert": alert, "to_level": 2, "from_level": 1}}) is None)
    check("seq 重放去重", store.offer_event({"event": "alert_changed", "seq": 1,
                                            "data": {"alert": alert, "to_level": 2, "from_level": 1}}) is None)
    check("is_current(True) 对当前任务", store.is_current(t1))

    # 同键新版本：旧任务失效（过期淘汰语义）
    t2 = store.offer_event({"event": "alert_changed", "seq": 3,
                            "data": {"alert": {**alert, "risk": 0.9}, "to_level": 2, "from_level": 1}})
    check("同键更新产生新任务", t2 is not None and t2 is not t1)
    check("旧版本任务过期失效", not store.is_current(t1) and store.is_current(t2))

    # alert_cleared 掉任务
    store.offer_event({"event": "alert_cleared", "seq": 4, "data": {"alert_id": "A9"}})
    check("alert_cleared 淘汰任务", len(store) == 0)
    check("cleared 后旧任务不 current", not store.is_current(t2))

    # scenario reset 清空并升代
    t3 = store.offer_event({"event": "alert_changed", "seq": 5,
                            "data": {"alert": {**alert, "id": "A10"}, "to_level": 2, "from_level": 1}})
    gen_before = store._generation
    store.offer_event({"event": "scenario_changed", "seq": 6, "data": {"status": "reset"}})
    check("reset 清空任务", len(store) == 0)
    check("reset 升代使在处理任务失效", store._generation == gen_before + 1 and not store.is_current(t3))

    # reopen_plan 20s 节流
    ok1 = store.offer_event({"event": "reopen_plan", "seq": 7, "t": 100.0, "data": {"plan_id": "P1"}})
    ok2 = store.offer_event({"event": "reopen_plan", "seq": 8, "t": 110.0, "data": {"plan_id": "P2"}})
    ok3 = store.offer_event({"event": "reopen_plan", "seq": 9, "t": 121.0, "data": {"plan_id": "P3"}})
    check("reopen 20s 内节流", ok1 is not None and ok2 is None and ok3 is not None)

    # take FIFO
    store2 = TaskStore()
    store2.offer_event({"event": "alert_changed", "seq": 10,
                        "data": {"alert": {"id": "B1"}, "to_level": 2, "from_level": 1}})
    store2.offer_event({"event": "alert_changed", "seq": 11,
                        "data": {"alert": {"id": "B2"}, "to_level": 2, "from_level": 1}})
    first = store2.take()
    check("take 按入队序弹出", first is not None and first["alert_id"] == "B1" and len(store2) == 1)


async def test_expired_deadline_template_fallback() -> None:
    """deadline 已过：不调用任何 provider，直接确定性模板兜底且双重校验通过。"""
    settings = get_settings()
    router = Router(settings)
    rec = next(json.loads(l) for l in open(
        "acceptance_c4/diag_c4_20261017/dev9.jsonl", encoding="utf-8") if l.strip())
    context = json.loads(rec["messages"][1]["content"])

    started = time.perf_counter()
    result = await router.generate(context, deadline=time.perf_counter())  # 已过期
    elapsed = time.perf_counter() - started
    try:
        check("过期 deadline 走模板兜底", result is not None and result.model == "template")
        check("过期 deadline 未调用本地 provider",
              router.stats["providers"]["local"].get("ask_attempts", 0) == 0
              and router.stats["providers"]["local"].get("draft_attempts", 0) == 0)
        check("过期 deadline 快速返回(<0.5s)", elapsed < 0.5)
        check("模板兜底带合法 draft", result is not None and result.draft is not None)
    finally:
        await router.aclose()


def main() -> int:
    test_task_store()
    asyncio.run(test_expired_deadline_template_fallback())
    ok = all(v for _, v in PASS)
    print(f"\n{'全部通过' if ok else '存在失败'}：{sum(v for _, v in PASS)}/{len(PASS)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
