"""C4 云端蒸馏：OpenRouter 教师 × C3 同一提示词、同一校验，产出 SFT JSONL。

与 C3 在线路径严格共用（任务书 C4「同一份提示词 / 同一套校验」）：
- agent.prompts.SYSTEM_PROMPT + agent.router.OpenRouterProvider（结构化 JSON schema，
  require_parameters，禁 fallback）；
- agent.schemas.parse_model_draft（结构 + ID 存在性）与
  agent.factcheck.check_draft_facts（确定性事实校验）；
- 不合格时附校验错误重试一次（Router._retry_messages 同格式）；仍不合格时做一次
  教师侧引导重试（附 GUIDED_HINT，把 factcheck 的格式要求显式化）——引导提示只给教师，
  入库样本恒为标准三段 messages，训练分布与运行时不漂移；三次全失败才记录、不入库。

幂等：每条上下文以「与 router.generate 完全一致的序列化」的 SHA256 为键。
distilled.jsonl 已有的合格样本、failures 已记录的失败样本都直接跳过，
绝不重复请求（--retry-failed 才重试失败项）。后续补跑（如真实场景截取的上下文）
只会增量请求新键。

用法::

    python -m ml.lora.distill --limit 5          # 冒烟
    python -m ml.lora.distill                    # 全量蒸馏 + 450/50 划分
    python -m ml.lora.distill --retry-failed     # 重试上轮失败项
    python -m ml.lora.distill --split-only       # 只重写 train/test 划分

批量任务没有在线 9.5 秒预算，故请求超时默认放宽到 60 秒（--timeout-s 可调）。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import time
from pathlib import Path

from agent.context import context_ids
from agent.config import get_settings
from agent.factcheck import check_draft_facts
from agent.prompts import SYSTEM_PROMPT
from agent.router import OpenRouterProvider, Router
from agent.schemas import DraftOutputError, normalize_draft, parse_model_draft

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS = REPO_ROOT / "ml" / "lora" / "datasets"
DEFAULT_CONTEXTS = DATASETS / "contexts.jsonl"
DEFAULT_OUT = DATASETS / "distilled.jsonl"
DEFAULT_FAILURES = DATASETS / "distill_failures.jsonl"
DEFAULT_TRAIN = DATASETS / "train.jsonl"
DEFAULT_TEST = DATASETS / "test.jsonl"
MAX_ATTEMPTS = 2  # 与 C3 一致：首次 + 附错误重试一次
GUIDED_ATTEMPT = 1  # 仍失败时，教师侧引导重试一次（提示只影响教师，不入训练样本）

# 教师侧脚手架：把 agent.factcheck 的确定性要求转写成显式格式说明。
# 只出现在给教师的重试消息里；入库样本的 messages 恒为标准三段（system/user/assistant），
# 因此训练分布与 C3 在线路径完全一致。
GUIDED_HINT = """补充格式要求（必须全部满足，只输出修正后的完整 JSON 对象）：
1. 有浮标离线时，uncertainties 必须含一条「浮标离线 N 个:ID1,ID2」，N 与 ID 列表和上下文 buoys.down 完全一致（按上下文顺序）。
2. 覆盖浮标不超过 1 个时，uncertainties 必须含「仅 N 个浮标覆盖，定位证据不足」。
3. 识别置信度低于 0.6 时，uncertainties 必须含「识别置信度 X.XX，低于 0.6」；不低于 0.6 时不得称置信度低。
4. 存在上述任一情形、有浮标离线或字段缺失时，confidence 必须为 "low"。
5. security 且有 options 时，recommended_option_id 必须为 residual_risk ≤ 0.2 的方案中 delay_vessel_hours 最小的 id；都大于 0.2 时取 residual_risk 最小的 id；disaster/buoy 或没有 options 时为 null。
6. evidence_ids 只能取自这些字段的值：alert.id、track.id、detections[].id、options[].id、ranked[]、buoys.covering_track、buoys.down、zones[].id（灾害/浮标事件另含 reopen_plan 各列表、buoy.id、coverage_impact 内的 ID）；asset_id、zone_id 等其他字段值不得作为 evidence_ids，不得编造。"""


def context_key(context: dict) -> str:
    """序列化与 router.generate 一致（sort_keys + 紧凑分隔符），SHA256 作幂等键。"""
    payload = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def user_message(context: dict) -> str:
    """User 消息 = 上下文 JSON 字符串（与 C3 在线路径逐字节一致）。"""
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_turn_messages(context_json: str, raw: str | None, error: str | None) -> list[dict]:
    """重试消息格式复用 C3 Router 的实现（system 由 provider 统一前置）。"""
    return Router._retry_messages(context_json, raw, error)


def assistant_message(draft) -> str:
    """Assistant 目标 = 截断归一后的 draft 紧凑 JSON（字段顺序 = pydantic 定义序）。"""
    return json.dumps(
        normalize_draft(draft).model_dump(), ensure_ascii=False, separators=(",", ":")
    )


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def record_key_from_messages(messages: list[dict]) -> str:
    """交付文件（仅 messages）里的样本键 = user 消息（即序列化上下文）的 SHA256。"""
    return hashlib.sha256(messages[1]["content"].encode("utf-8")).hexdigest()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as stream:
        return sum(1 for line in stream if line.strip())


async def distill_one(provider, context: dict, *, timeout_s: float) -> dict:
    """蒸馏单条上下文；返回 status=ok/invalid 及诊断信息。

    前两次与 C3 在线路径一致（附校验错误重试一次）；仍不合格时做一次
    教师侧引导重试（附 GUIDED_HINT）。任何一次合格即入库，且入库样本的
    messages 不含引导内容。三次全部失败才记为 invalid。
    """
    known_ids = context_ids(context)
    option_ids = {o["id"] for o in context.get("options", [])}
    context_json = user_message(context)
    raw: str | None = None
    error: str | None = None
    usage_total: dict = {}
    started = time.perf_counter()

    for attempt in range(MAX_ATTEMPTS + GUIDED_ATTEMPT):
        feedback = error
        if error is not None and attempt == MAX_ATTEMPTS:
            feedback = f"{error}\n{GUIDED_HINT}"
        response = await provider.complete(
            SYSTEM_PROMPT, build_turn_messages(context_json, raw, feedback), timeout_s
        )
        for key, value in (response.usage or {}).items():
            usage_total[key] = usage_total.get(key, 0) + (value or 0)
        raw = response.text
        try:
            draft = parse_model_draft(raw, known_ids, option_ids)
        except DraftOutputError as exc:
            error = str(exc)
            continue
        fact = check_draft_facts(draft, context)
        if not fact.ok:
            error = "事实校验失败: " + "; ".join(fact.errors)
            continue
        return {
            "status": "ok",
            "record": {
                "key": context_key(context),
                "teacher": provider.request_model,
                "response_model": response.response_model,
                "upstream_provider": response.upstream_provider,
                "attempts": attempt + 1,
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 1),
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context_json},
                    {"role": "assistant", "content": assistant_message(draft)},
                ],
            },
            "usage": usage_total,
            "cost": response.cost,
        }
    return {
        "status": "invalid",
        "key": context_key(context),
        "error": error,
        "attempts": MAX_ATTEMPTS + GUIDED_ATTEMPT,
        "usage": usage_total,
        "cost": None,
    }


async def distill_batch(contexts: list[dict], provider, *, concurrency: int, timeout_s: float) -> dict:
    """8 路并发（任务书 C4）蒸馏一批上下文；provider 可注入以便测试。"""
    semaphore = asyncio.Semaphore(max(1, concurrency))
    done = 0
    total = len(contexts)

    async def run(context: dict) -> dict:
        nonlocal done
        async with semaphore:
            result = await distill_one(provider, context, timeout_s=timeout_s)
        done += 1
        if done % 25 == 0 or done == total:
            print(f"  进度 {done}/{total}", flush=True)
        return result

    results = await asyncio.gather(*(run(context) for context in contexts))
    records = [r["record"] for r in results if r["status"] == "ok"]
    failures = [
        {"key": r["key"], "error": r["error"], "attempts": r["attempts"]}
        for r in results
        if r["status"] == "invalid"
    ]
    usage: dict = {}
    cost = 0.0
    for r in results:
        for key, value in r["usage"].items():
            usage[key] = usage.get(key, 0) + value
        cost += r["cost"] or 0.0
    return {"records": records, "failures": failures, "usage": usage, "cost": round(cost, 6)}


def split_records(records: list[dict], *, test_size: int, train_size: int, seed: int) -> tuple[list, list]:
    """按 key 排序后以固定 seed 洗牌，先取测试集再取训练集；确定性可重跑。"""
    ordered = sorted(records, key=lambda r: r["key"])
    random.Random(seed).shuffle(ordered)
    test = ordered[:test_size]
    train = ordered[test_size:test_size + train_size]
    return train, test


def write_split(train: list[dict], test: list[dict], train_path: Path, test_path: Path) -> None:
    """交付格式：每行仅 {"messages": [system, user, assistant]}。"""
    for path, records in ((train_path, train), (test_path, test)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")


def _usage_line(usage: dict, cost: float) -> str:
    parts = [f"{key}={value}" for key, value in usage.items() if value]
    text = ", ".join(parts) if parts else "usage 不可用"
    return f"{text}, cost≈${cost:.4f}" if cost else text


async def run_distill(args: argparse.Namespace) -> int:
    settings = get_settings()
    provider = OpenRouterProvider(settings)
    if not provider.enabled:
        print("错误：OPENROUTER_API_KEY 未配置，无法蒸馏（.env 见 .env.example）")
        return 2

    contexts = []
    new_records: list[dict] = []
    for path in args.contexts:
        contexts.extend(load_jsonl(path))
    if not contexts:
        print(f"错误：{args.contexts} 无上下文；先运行 python -m ml.lora.gen_contexts")
        return 2
    contexts = list({context_key(c): c for c in contexts}.values())  # 按 key 去重

    distilled = load_jsonl(args.out)
    done_keys = {r["key"] for r in distilled}
    failures_known = {f["key"]: f for f in load_jsonl(args.failures)}
    retry_failed = args.retry_failed
    pending = [
        c for c in contexts
        if context_key(c) not in done_keys
        and (retry_failed or context_key(c) not in failures_known)
    ]
    if args.limit:
        pending = pending[: args.limit]
    print(
        f"上下文 {len(contexts)} 条：已蒸馏 {len(done_keys)}，"
        f"已知失败 {len(failures_known)}（{'重试' if retry_failed else '跳过'}），本次请求 {len(pending)}"
    )
    if not pending:
        print("无待蒸馏上下文。")
        new_records = []
    else:
        started = time.perf_counter()
        batch = await distill_batch(
            pending, provider, concurrency=args.concurrency, timeout_s=args.timeout_s
        )
        await provider.aclose()
        new_records = batch["records"]
        for record in new_records:
            if record["key"] in failures_known:  # 重试成功：移出失败清单
                failures_known.pop(record["key"])
        for failure in batch["failures"]:
            failures_known[failure["key"]] = failure
        with args.out.open("a", encoding="utf-8") as stream:
            for record in new_records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        args.failures.parent.mkdir(parents=True, exist_ok=True)
        with args.failures.open("w", encoding="utf-8") as stream:
            for failure in failures_known.values():
                stream.write(json.dumps(failure, ensure_ascii=False) + "\n")

        retried_ok = sum(1 for r in batch["records"] if r["attempts"] > 1)
        print(
            f"本次：合格 {len(batch['records'])}（重试后合格 {retried_ok}），不合格 {len(batch['failures'])}，"
            f"耗时 {time.perf_counter() - started:.1f}s；{_usage_line(batch['usage'], batch['cost'])}"
        )
        if batch["failures"]:
            sample = batch["failures"][0]["error"]
            print(f"失败示例: {sample[:200]}")

    all_records = load_jsonl(args.out)
    print(f"累计合格样本 {len(all_records)} 条")

    if getattr(args, "append_train", False):
        # 真实场景补充数据：只追加进训练集，测试集保持既有基准不被重划
        # （eval 的基座/LoRA 对比必须在同一测试集上可比）。
        known_keys = {
            record_key_from_messages(r["messages"])
            for r in (json.loads(line) for line in args.train_path.open(encoding="utf-8") if line.strip())
        }
        fresh = [r for r in new_records if r["key"] not in known_keys]
        with args.train_path.open("a", encoding="utf-8") as stream:
            for record in fresh:
                stream.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")
        print(f"追加 {len(fresh)} 条新蒸馏样本到训练集（测试集不变）: {args.train_path}")
        print(f"训练集合计 {count_lines(args.train_path)} 条；测试集 {count_lines(args.test_path)} 条")
        return 0

    if not args.split_only and not all_records:
        return 1
    train, test = split_records(
        all_records, test_size=args.test, train_size=args.train, seed=args.seed
    )
    write_split(train, test, args.train_path, args.test_path)
    print(f"划分: train {len(train)} -> {args.train_path}")
    print(f"       test  {len(test)} -> {args.test_path}")
    if len(train) < args.min_train:
        print(
            f"警告：训练样本 {len(train)} < 验收下限 {args.min_train}。"
            "可 python -m ml.lora.gen_contexts --n 560 后重跑蒸馏（已合格样本不会重复请求）。"
        )
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenRouter 云端蒸馏 -> SFT JSONL（C3 同提示词同校验）")
    parser.add_argument("--contexts", type=Path, nargs="+", default=[DEFAULT_CONTEXTS],
                        help="上下文 JSONL（可多个，按 key 去重合并）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="全部合格样本（含元数据）")
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--train-path", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--test-path", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--concurrency", type=int, default=8, help="并发数（任务书：8）")
    parser.add_argument("--timeout-s", type=float, default=60.0, help="单次请求超时（批量任务放宽）")
    parser.add_argument("--train", type=int, default=450, help="训练集条数")
    parser.add_argument("--test", type=int, default=50, help="测试集条数")
    parser.add_argument("--min-train", type=int, default=400, help="验收下限：合格训练样本 ≥ 400")
    parser.add_argument("--seed", type=int, default=0, help="划分洗牌种子")
    parser.add_argument("--limit", type=int, default=None, help="只请求前 N 条待蒸馏（冒烟）")
    parser.add_argument("--retry-failed", action="store_true", help="重试历史上不合格的上下文")
    parser.add_argument("--append-train", action="store_true",
                        help="补充数据模式：新样本只追加进训练集，不重划测试集")
    parser.add_argument("--split-only", action="store_true", help="跳过请求，只重写 train/test 划分")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_distill(args)))


if __name__ == "__main__":
    main()
