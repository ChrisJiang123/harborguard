"""C4 真实上下文截取：B 后端跑场景时，按 C3 触发规则用 collect_* 截取真实上下文。

任务书 C4：「B 的后端可用时，再加 50–100 个从真实场景运行中截取的上下文。」
本脚本订阅 ws://localhost:8000/ws（复用 agent.backend_client.BackendClient 的
重连与补齐逻辑），在 C3 的四类触发上用 agent.context.collect_* 拉齐真实上下文，
按 key 去重后追加写入 JSONL——之后 ``python -m ml.lora.distill --contexts ...
real_contexts.jsonl --append-train`` 会只蒸馏新增部分并追加进训练集
（已合格样本绝不重复请求，测试集保持合成基准不重划）。

触发规则与 C3 main.py 一致：
- options_ready                -> collect_security(alert_id, options, ranked)
- alert_changed 升到二级       -> collect_security(alert_id)（尚无方案）
- reopen_plan                  -> collect_disaster(plan)
- buoy_changed 且为 down       -> collect_buoy(buoy_id)

与 C3 在线任务的差异：这是离线截取工具，不做 10 秒预算与「同警报只处理最新」
的丢弃策略——同一警报的新触发替换待处理参数（新替旧），但已完成的上下文保留；
security 在每个事件处理后立即冲刷，避免场景切换 reset 丢数据。

用法（先启动后端与场景）::

    make backend                                    # 或 python -m uvicorn backend.app.main:app
    curl -X POST localhost:8000/api/scenario/a/start -H 'content-type: application/json' -d '{"speed": 10}'
    python -m ml.lora.capture_real --seconds 180 --out ml/lora/datasets/real_contexts.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
from collections import Counter
from pathlib import Path

from agent.backend_client import BackendClient
from agent.context import collect_buoy, collect_disaster, collect_security
from ml.lora.distill import context_key

REPO_ROOT = Path(__file__).resolve().parents[2]


class RealContextCapture:
    """按 C3 触发规则收集真实上下文；逐事件冲刷，key 去重，全事件计数。"""

    def __init__(self):
        self.by_key: dict[str, dict] = {}
        self.counts: Counter = Counter()
        self.pending_security: dict[str, tuple] = {}  # alert_id -> (options, ranked)

    async def _collect_security(self, client: BackendClient, alert_id: str,
                                options: list | None, ranked: list | None) -> None:
        try:
            context = await collect_security(client, alert_id, options, ranked)
        except Exception as exc:  # noqa: BLE001 - 警报已被 reset/过期：记录后丢弃
            self.counts[f"dropped:{type(exc).__name__}"] += 1
            return
        self.counts["security"] += 1
        self.by_key[context_key(context)] = context

    async def flush_security(self, client: BackendClient) -> None:
        pending, self.pending_security = self.pending_security, {}
        for alert_id, (options, ranked) in pending.items():
            await self._collect_security(client, alert_id, options, ranked)

    async def handle_event(self, client: BackendClient, msg: dict) -> None:
        event, data = msg.get("event"), msg.get("data") or {}
        self.counts[f"event:{event}"] += 1
        if event == "options_ready" and data.get("alert_id"):
            self.pending_security[data["alert_id"]] = (data.get("options"), data.get("ranked"))
        elif event == "alert_changed":
            alert = data.get("alert") or {}
            if data.get("to_level") == 2 and alert.get("id"):
                self.pending_security[alert["id"]] = (None, None)
        elif event == "reopen_plan":
            try:
                context = await collect_disaster(client, data)
            except Exception as exc:  # noqa: BLE001
                self.counts[f"dropped:{type(exc).__name__}"] += 1
            else:
                self.counts["disaster"] += 1
                self.by_key[context_key(context)] = context
        elif event == "buoy_changed":
            if data.get("status") == "down" and data.get("buoy_id"):
                try:
                    context = await collect_buoy(client, data["buoy_id"])
                except Exception as exc:  # noqa: BLE001
                    self.counts[f"dropped:{type(exc).__name__}"] += 1
                else:
                    self.counts["buoy"] += 1
                    self.by_key[context_key(context)] = context
        elif event == "scenario_changed" and data.get("status") == "reset":
            self.pending_security.clear()  # 尚未收集的警报已失效
        await self.flush_security(client)

    async def run(self, *, seconds: float, stop: asyncio.Event) -> BackendClient:
        client = BackendClient()

        async def on_event(msg: dict) -> None:
            await self.handle_event(client, msg)

        stream = asyncio.create_task(client.stream_events(on_event, stop=stop))
        try:
            await asyncio.wait_for(stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
        finally:
            stop.set()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(stream, timeout=5)
            await self.flush_security(client)
            await client.aclose()
        return client


def write_contexts(contexts: dict[str, dict], out: Path) -> tuple[int, int]:
    """追加写入尚未记录过的上下文；返回 (新增, 跳过已有)。"""
    existing: set[str] = set()
    if out.exists():
        with out.open(encoding="utf-8") as stream:
            existing = {context_key(json.loads(line)) for line in stream if line.strip()}
    fresh = {key: ctx for key, ctx in contexts.items() if key not in existing}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as stream:
        for key, ctx in fresh.items():
            stream.write(json.dumps(ctx, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    return len(fresh), len(contexts) - len(fresh)


async def run_capture(args: argparse.Namespace) -> int:
    capture = RealContextCapture()
    stop = asyncio.Event()
    # 预检：后端不可达时立即给出指引，而不是静默等满 --seconds。
    probe = BackendClient()
    try:
        await probe.get_state()
    except Exception as exc:  # noqa: BLE001
        await probe.aclose()
        print(f"错误：后端不可达（{type(exc).__name__}: {str(exc)[:160]}）。")
        print("先启动后端并跑场景：make backend && curl -X POST localhost:8000/api/scenario/a/start "
              "-H 'content-type: application/json' -d '{\"speed\": 10}'")
        return 2
    await probe.aclose()
    print(
        f"订阅 {args.ws or 'BACKEND_WS_URL'}，截取 {args.seconds} 秒"
        "（触发规则同 C3：options_ready / 升二级 / reopen_plan / buoy down）"
    )
    try:
        await capture.run(seconds=args.seconds, stop=stop)
    except Exception as exc:  # noqa: BLE001
        print(f"错误：截取中断（{type(exc).__name__}: {str(exc)[:160]}）")
        return 2

    total = len(capture.by_key)
    if total == 0:
        print("未截取到任何上下文：确认场景已产生警报/灾害/浮标事件。")
        print("收到事件计数: " + (", ".join(f"{k}={v}" for k, v in sorted(capture.counts.items())) or "无"))
        return 1
    added, skipped = write_contexts(capture.by_key, args.out)
    dropped = {k: v for k, v in capture.counts.items() if k.startswith("dropped:")}
    summary = ", ".join(
        f"{k}={v}" for k, v in sorted(capture.counts.items())
        if k in {"security", "disaster", "buoy"}
    )
    print(f"截取 {total} 条唯一上下文（{summary}）；新增 {added}，跳过已有 {skipped} -> {args.out}")
    if dropped:
        print(f"丢弃（警报已过期等）: {dropped}")
    print("下一步：python -m ml.lora.distill --contexts " + str(args.out) +
          " --append-train   # 只蒸馏新增部分并追加进训练集")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="从运行中的 B 后端截取真实上下文（C4 补充数据）")
    parser.add_argument("--seconds", type=float, default=180.0, help="截取时长（秒，默认 180）")
    parser.add_argument("--out", type=Path,
                        default=REPO_ROOT / "ml/lora/datasets/real_contexts.jsonl")
    parser.add_argument("--ws", default=None, help="WebSocket 地址（默认读 BACKEND_WS_URL）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_capture(args)))


if __name__ == "__main__":
    main()
