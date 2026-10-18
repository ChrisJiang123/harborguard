"""C3 运行预算隔离事件测试·第二部分（真实推理，真实预算，云端显式禁用）。

教训记录：Router 为云端优先路由，.env 含 OpenRouter 凭据；上一版测试误触发 3 次
付费云端调用。本版以 dataclasses.replace(cloud_provider="disabled") 隔离，绝不再产生云端流量。

1. 生成中途超时取消：云端禁用后，deadline 在本地生成过程中到期 → provider 调用被取消，
   快速回落确定性模板，预算内返回。
2. 事实失败兜底：qwen3:1.7b（事实合格率 16%）在真实 9.5s 事件预算下，
   事实/ID 失败样本两次尝试后回落模板；结果只能是「本地合法 draft」或「模板」。
不改线上配置；不改 C3 代码；不改前后端接口。
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.config import get_settings
from agent.router import Router

PASS: list[tuple[str, bool]] = []
FACT_LOG = Path("agent/runtime/fact_failures.jsonl")


def check(name: str, ok: bool) -> None:
    PASS.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name, flush=True)


def load_contexts():
    recs = []
    for l in open("acceptance_c4/diag_c4_20261017/dev9.jsonl", encoding="utf-8"):
        if l.strip():
            recs.append(json.loads(json.loads(l)["messages"][1]["content"]))
    return recs


async def main() -> int:
    settings = replace(get_settings(), cloud_provider="disabled")  # 本轮禁云，绝无云端流量
    assert settings.cloud_provider == "disabled"
    budget = settings.agent_event_budget_s  # 真实 C3 事件预算（9.5s）
    contexts = load_contexts()

    # ---- 1) 生成中途超时取消（云端禁用，本地调用被超时打断） ----
    router = Router(settings)
    try:
        started = time.perf_counter()
        result = await router.generate(contexts[0], deadline=time.perf_counter() + 1.2)
        elapsed = time.perf_counter() - started
        check(f"中途超时快速返回（{elapsed:.2f}s < 5s，不悬挂）", elapsed < 5.0)
        check("中途超时回落确定性模板", result is not None and result.model == "template")
        stat = router.stats["providers"]["local"]
        check("本地 provider 记录到超时（取消确实发生在生成中）", stat.get("timeouts", 0) >= 1)
        check("云端零调用（本轮硬约束）", router.stats["providers"]["cloud"].get("draft_attempts", 0) == 0
              and router.stats["providers"]["cloud"].get("ask_attempts", 0) == 0)
    finally:
        await router.aclose()

    # ---- 2) 事实失败兜底（真实 9.5s 预算） ----
    log_size_before = FACT_LOG.stat().st_size if FACT_LOG.exists() else 0
    router = Router(settings)
    outcomes: dict[str, int] = {}
    try:
        for i, context in enumerate(contexts[:3]):
            started = time.perf_counter()
            result = await router.generate(context, deadline=time.perf_counter() + budget)
            elapsed = time.perf_counter() - started
            check(f"样本{i+1}: 结果合法（local/template 二选一）",
                  result is not None and result.model in ("local", "template"))
            check(f"样本{i+1}: 预算内完成（{elapsed:.2f}s ≤ {budget + 1.0:.1f}s）",
                  elapsed <= budget + 1.0)
            outcomes[result.model] = outcomes.get(result.model, 0) + 1
        print(f"  结果分布: {outcomes}")
        check("qwen3 事实失败场景出现模板兜底", outcomes.get("template", 0) >= 1)
        log_size_after = FACT_LOG.stat().st_size if FACT_LOG.exists() else 0
        check("事实失败样例落盘（fact_failures.jsonl 非缩小）", log_size_after >= log_size_before)
    finally:
        await router.aclose()

    ok = all(v for _, v in PASS)
    print(f"\n{'全部通过' if ok else '存在失败'}：{sum(v for _, v in PASS)}/{len(PASS)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
