"""C4 cloud-teacher distillation using the same C3 prompts, structured provider and structure/ID/fact
validators. First failure gets one validation-guided retry; persistent failure gets a teacher-only
formatting hint. Stored training messages always use the standard system/user/assistant shape,
without hints. Three failures are recorded and excluded. Idempotency keys use the exact runtime
sorted compact JSON SHA256; existing valid/failure records are skipped unless retry-failed is
requested. Synthetic split is deterministic 450/50; runtime simulation captures append to training
only, preserving test comparability.
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
MAX_ATTEMPTS = 2  # Match C3: initial attempt plus one validation-guided retry.
GUIDED_ATTEMPT = 1  # Then one teacher-only guided retry; hints never enter training examples.

# Teacher scaffolding makes deterministic fact-check requirements explicit.
# Only retry messages to the teacher include this hint; stored examples always
# use standard system/user/assistant messages matching C3 runtime.
GUIDED_HINT = """补充格式要求（必须全部满足，只输出修正后的完整 JSON 对象）：
1. 有浮标离线时，uncertainties 必须含一条「浮标离线 N 个:ID1,ID2」，N 与 ID 列表和上下文 buoys.down 完全一致（按上下文顺序）。
2. 覆盖浮标不超过 1 个时，uncertainties 必须含「仅 N 个浮标覆盖，定位证据不足」。
3. 识别置信度低于 0.6 时，uncertainties 必须含「识别置信度 X.XX，低于 0.6」；不低于 0.6 时不得称置信度低。
4. 存在上述任一情形、有浮标离线或字段缺失时，confidence 必须为 "low"。
5. security 且有 options 时，recommended_option_id 必须为 residual_risk ≤ 0.2 的方案中 delay_vessel_hours 最小的 id；都大于 0.2 时取 residual_risk 最小的 id；disaster/buoy 或没有 options 时为 null。
6. evidence_ids 只能取自这些字段的值：alert.id、track.id、detections[].id、options[].id、ranked[]、buoys.covering_track、buoys.down、zones[].id（灾害/浮标事件另含 reopen_plan 各列表、buoy.id、coverage_impact 内的 ID）；asset_id、zone_id 等其他字段值不得作为 evidence_ids，不得编造。"""


def context_key(context: dict) -> str:
    """Serialize exactly as router.generate (sorted keys, compact separators); SHA256 is the
    idempotency key.
    """
    payload = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def user_message(context: dict) -> str:
    """User message is the context JSON, byte-identical to the C3 runtime path."""
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_turn_messages(context_json: str, raw: str | None, error: str | None) -> list[dict]:
    """Reuse C3 Router retry-message formatting; provider prepends the system message."""
    return Router._retry_messages(context_json, raw, error)


def assistant_message(draft) -> str:
    """Assistant target is normalized/truncated compact draft JSON in Pydantic field order."""
    return json.dumps(
        normalize_draft(draft).model_dump(), ensure_ascii=False, separators=(",", ":")
    )


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def record_key_from_messages(messages: list[dict]) -> str:
    """Delivered messages-only sample key is the SHA256 of its serialized-context user message."""
    return hashlib.sha256(messages[1]["content"].encode("utf-8")).hexdigest()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as stream:
        return sum(1 for line in stream if line.strip())


async def distill_one(provider, context: dict, *, timeout_s: float) -> dict:
    """Distill one context and return ok/invalid plus diagnostics. First two attempts match the C3
    retry route; the third adds teacher-only GUIDED_HINT. The first valid result is stored without
    the hint. Only three failed attempts produce invalid.
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
    """Distill contexts with eight-way concurrency; inject a provider for tests."""
    semaphore = asyncio.Semaphore(max(1, concurrency))
    done = 0
    total = len(contexts)

    async def run(context: dict) -> dict:
        nonlocal done
        async with semaphore:
            result = await distill_one(provider, context, timeout_s=timeout_s)
        done += 1
        if done % 25 == 0 or done == total:
            print(f"  Progress {done}/{total}", flush=True)
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
    """Sort by key, shuffle with a fixed seed and take test before train deterministically."""
    ordered = sorted(records, key=lambda r: r["key"])
    random.Random(seed).shuffle(ordered)
    test = ordered[:test_size]
    train = ordered[test_size:test_size + train_size]
    return train, test


def write_split(train: list[dict], test: list[dict], train_path: Path, test_path: Path) -> None:
    """Delivery format: one object containing only messages=[system,user,assistant] per line."""
    for path, records in ((train_path, train), (test_path, test)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")


def _usage_line(usage: dict, cost: float) -> str:
    parts = [f"{key}={value}" for key, value in usage.items() if value]
    text = ", ".join(parts) if parts else "usage unavailable"
    return f"{text}, cost≈${cost:.4f}" if cost else text


async def run_distill(args: argparse.Namespace) -> int:
    settings = get_settings()
    provider = OpenRouterProvider(settings)
    if not provider.enabled:
        print("Error: OPENROUTER_API_KEY is unset; cannot distill (see .env.example).")
        return 2

    contexts = []
    new_records: list[dict] = []
    for path in args.contexts:
        contexts.extend(load_jsonl(path))
    if not contexts:
        print(f"Error: no contexts in {args.contexts}; run python -m ml.lora.gen_contexts first.")
        return 2
    contexts = list({context_key(c): c for c in contexts}.values())  # Deduplicate by key.

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
        f"Contexts {len(contexts)}: already distilled {len(done_keys)}, "
        f"Known failures {len(failures_known)} ({'retry' if retry_failed else 'skip'}), requesting {len(pending)}"
    )
    if not pending:
        print("No pending contexts to distill.")
        new_records = []
    else:
        started = time.perf_counter()
        batch = await distill_batch(
            pending, provider, concurrency=args.concurrency, timeout_s=args.timeout_s
        )
        await provider.aclose()
        new_records = batch["records"]
        for record in new_records:
            if record["key"] in failures_known:  # Successful retry removes the prior failure.
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
            f"This batch: valid {len(batch['records'])} (valid after retry {retried_ok}), invalid {len(batch['failures'])}, "
            f"elapsed {time.perf_counter() - started:.1f}s; {_usage_line(batch['usage'], batch['cost'])}"
        )
        if batch["failures"]:
            sample = batch["failures"][0]["error"]
            print(f"Failure example: {sample[:200]}")

    all_records = load_jsonl(args.out)
    print(f"Total valid samples: {len(all_records)}")

    if getattr(args, "append_train", False):
        # Runtime-simulation supplements append to training only; retain the benchmark
        # so base/LoRA evaluation remains comparable on the same test set.
        known_keys = {
            record_key_from_messages(r["messages"])
            for r in (json.loads(line) for line in args.train_path.open(encoding="utf-8") if line.strip())
        }
        fresh = [r for r in new_records if r["key"] not in known_keys]
        with args.train_path.open("a", encoding="utf-8") as stream:
            for record in fresh:
                stream.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")
        print(f"Append {len(fresh)} newly distilled training samples (test set unchanged): {args.train_path}")
        print(f"Training total {count_lines(args.train_path)}; test total {count_lines(args.test_path)}")
        return 0

    if not args.split_only and not all_records:
        return 1
    train, test = split_records(
        all_records, test_size=args.test, train_size=args.train, seed=args.seed
    )
    write_split(train, test, args.train_path, args.test_path)
    print(f"Split: train {len(train)} -> {args.train_path}")
    print(f"       test  {len(test)} -> {args.test_path}")
    if len(train) < args.min_train:
        print(
            f"Warning: training samples {len(train)} < required minimum {args.min_train}. "
            "Run python -m ml.lora.gen_contexts --n 560 and repeat distillation; valid cached samples are never requested again."
        )
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenRouter distillation -> SFT JSONL (same C3 prompts/validation)")
    parser.add_argument("--contexts", type=Path, nargs="+", default=[DEFAULT_CONTEXTS],
                        help="Context JSONL files, merged and deduplicated by key")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="All valid samples, including metadata")
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--train-path", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--test-path", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrency (taskbook:8)")
    parser.add_argument("--timeout-s", type=float, default=60.0, help="Per-request timeout (larger for batch jobs)")
    parser.add_argument("--train", type=int, default=450, help="Training record count")
    parser.add_argument("--test", type=int, default=50, help="Test record count")
    parser.add_argument("--min-train", type=int, default=400, help="Acceptance minimum:400 valid training samples")
    parser.add_argument("--seed", type=int, default=0, help="Split shuffle seed")
    parser.add_argument("--limit", type=int, default=None, help="Request only the first N pending records (smoke)")
    parser.add_argument("--retry-failed", action="store_true", help="Retry previously invalid contexts")
    parser.add_argument("--append-train", action="store_true",
                        help="Supplement mode:append new samples to training without changing test split")
    parser.add_argument("--split-only", action="store_true", help="Skip requests and rewrite train/test split only")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_distill(args)))


if __name__ == "__main__":
    main()
