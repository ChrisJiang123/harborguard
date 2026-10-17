"""C4 评估：Ollama 上对比「基座 + 提示词」与「harborguard-lora」（50 条测试上下文）。

指标（任务书 C4 验收）：
- json_valid：输出经 C3 同一套 parse_model_draft（结构 + ID 存在性）通过的比例，含一次附错误重试；
- option_agree：有 ranked[0] 的上下文中，recommended_option_id == ranked[0] 的比例
  （输出不合法按不一致计，不剔除分母）；
- latency_s：平均每条总耗时（含重试与失败尝试；串行评测，不受并发排队干扰）。

两者都成功评测才写 ml/lora/metrics.json（后端 /api/metrics 读取）；只评基座时
不写文件——与 ml/yolo/eval.py 的「无权重不写占位数据」同一约定。

用法::

    python -m ml.lora.eval                       # 基座(qwen3:1.7b) + LoRA(harborguard-lora)
    python -m ml.lora.eval --skip-lora           # 只评基座（LoRA 未训练前）
    python -m ml.lora.eval --base-model qwen3:0.6b
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

from agent.config import get_settings
from agent.context import context_ids
from agent.prompts import SYSTEM_PROMPT
from agent.router import LocalProvider, Router
from agent.schemas import DraftOutputError, parse_model_draft

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS = REPO_ROOT / "ml" / "lora" / "datasets"
DEFAULT_TEST = DATASETS / "test.jsonl"
DEFAULT_DISTILLED = DATASETS / "distilled.jsonl"
DEFAULT_METRICS = REPO_ROOT / "ml" / "lora" / "metrics.json"
MAX_ATTEMPTS = 2  # 与 C3 一致：首次 + 附校验错误重试一次
WARMUP_TIMEOUT_S = 30.0


def load_test_records(path: Path, limit: int | None) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                record = json.loads(line)
                messages = record.get("messages", [])
                if len(messages) == 3:
                    records.append(record)
    if limit is not None:
        records = records[:limit]
    return records


def teacher_name(distilled_path: Path, fallback: str) -> str:
    """从蒸馏产物读实际教师模型（多数票）；无记录时退回配置的云端模型名。"""
    counts: Counter = Counter()
    if distilled_path.exists():
        with distilled_path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    counts[json.loads(line).get("teacher") or "unknown"] += 1
    return counts.most_common(1)[0][0] if counts else fallback


async def warmup(provider: LocalProvider) -> None:
    """预热一次（首次调用含模型冷加载，不计入延迟）。"""
    try:
        await provider.complete(
            SYSTEM_PROMPT,
            [{"role": "user", "content": '{"kind": "security", "t": 0}'}],
            WARMUP_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001 - 预热失败留给正式请求报明确错误
        print(f"  警告：{provider.request_model} 预热失败: {type(exc).__name__}: {str(exc)[:160]}")


async def eval_model(provider: LocalProvider, records: list[dict], *, timeout_s: float) -> dict:
    """串行评测一个模型；返回 json_valid / option_agree / latency_s 及诊断计数。"""
    valid = 0
    agree = 0
    ranked_total = 0
    total_latency = 0.0
    retried_ok = 0
    last_error = None

    await warmup(provider)
    started_all = time.perf_counter()
    for index, record in enumerate(records, start=1):
        user_content = record["messages"][1]["content"]
        context = json.loads(user_content)
        known_ids = context_ids(context)
        option_ids = {o["id"] for o in context.get("options", [])}
        ranked = [r for r in context.get("ranked", []) if r in option_ids]
        ranked_first = ranked[0] if ranked else None
        if ranked_first is not None:
            ranked_total += 1

        raw: str | None = None
        error: str | None = None
        draft = None
        started = time.perf_counter()
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await provider.complete(
                    SYSTEM_PROMPT,
                    Router._retry_messages(user_content, raw, error),
                    timeout_s,
                )
            except Exception as exc:  # noqa: BLE001 - 传输错误不算 JSON 不合法，直接终止本条
                last_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                break
            raw = response.text
            try:
                draft = parse_model_draft(raw, known_ids, option_ids)
                valid += 1
                if attempt:
                    retried_ok += 1
                break
            except DraftOutputError as exc:
                error = str(exc)
                last_error = error[:160]
        total_latency += time.perf_counter() - started

        if draft is not None and ranked_first is not None:
            if draft.recommended_option_id == ranked_first:
                agree += 1
        if index % 10 == 0 or index == len(records):
            print(f"  [{provider.request_model}] {index}/{len(records)}", flush=True)

    n = len(records)
    return {
        "model": provider.request_model,
        "json_valid": round(valid / n, 3) if n else 0.0,
        "option_agree": round(agree / ranked_total, 3) if ranked_total else 0.0,
        "latency_s": round(total_latency / n, 2) if n else 0.0,
        "_diag": {
            "n": n,
            "valid": valid,
            "retry_success": retried_ok,
            "ranked_total": ranked_total,
            "wall_s": round(time.perf_counter() - started_all, 1),
            "last_error": last_error,
        },
    }


async def run_eval(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not args.test_path.exists():
        print(f"错误：缺少 {args.test_path}；先运行 python -m ml.lora.distill 生成 train/test 划分")
        return 2
    records = load_test_records(args.test_path, args.limit)
    if not records:
        print(f"错误：{args.test_path} 无有效样本")
        return 2
    print(f"评测样本 {len(records)} 条（串行；JSON 校验 = C3 parse_model_draft，含一次重试）")

    base_provider = LocalProvider(replace(settings, ollama_model=args.base_model))
    results: dict = {}
    try:
        results["base"] = await eval_model(base_provider, records, timeout_s=args.timeout_s)
    except Exception as exc:  # noqa: BLE001 - Ollama 未启动等：给明确指引
        print(f"错误：基座模型 {args.base_model} 评测失败：{type(exc).__name__}: {str(exc)[:200]}")
        print("请确认 Ollama 正在运行（curl localhost:11434/api/tags）且基座已 ollama pull。")
        return 2
    finally:
        await base_provider.aclose()
    print(
        f"基座 {results['base']['model']}: json_valid={results['base']['json_valid']}, "
        f"option_agree={results['base']['option_agree']}, latency={results['base']['latency_s']}s"
    )

    if args.skip_lora:
        print("未评测 LoRA：部署 harborguard-lora 后重跑本命令生成 metrics.json")
        return 0

    lora_provider = LocalProvider(replace(settings, ollama_model=args.lora_model))
    try:
        results["lora"] = await eval_model(lora_provider, records, timeout_s=args.timeout_s)
        print(
            f"LoRA {results['lora']['model']}: json_valid={results['lora']['json_valid']}, "
            f"option_agree={results['lora']['option_agree']}, latency={results['lora']['latency_s']}s"
        )
    except Exception as exc:  # noqa: BLE001 - 模型未部署等：不写占位数据
        print(f"错误：LoRA 模型 {args.lora_model} 评测失败：{type(exc).__name__}: {str(exc)[:200]}")
        print("请先部署（见 ml/lora/Modelfile 注释），或部署前用 --skip-lora 只评基座。")
        return 3
    finally:
        await lora_provider.aclose()

    metrics = {
        "base": {k: results["base"][k] for k in ("model", "json_valid", "option_agree", "latency_s")},
        "lora": {k: results["lora"][k] for k in ("model", "json_valid", "option_agree", "latency_s")},
        "n_test": len(records),
        "teacher": teacher_name(DEFAULT_DISTILLED, settings.openrouter_model),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {args.out}（后端 GET /api/metrics 的 lora 字段即此文件）")

    lora_ok = metrics["lora"]["json_valid"] >= 0.9 and metrics["lora"]["option_agree"] >= 0.8
    better = (
        metrics["lora"]["json_valid"] > metrics["base"]["json_valid"]
        and metrics["lora"]["option_agree"] >= metrics["base"]["option_agree"]
    )
    print(f"验收线: LoRA json_valid≥0.90 且 option_agree≥0.80 -> {'通过' if lora_ok else '未达标'}")
    print(f"明显好于基座: {'是' if better else '否（指标卡如实显示）'}")
    if not results["lora"]["_diag"]["last_error"] and not results["base"]["_diag"]["last_error"]:
        return 0
    print(f"诊断: base={results['base']['_diag']} lora={results['lora']['_diag']}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="基座 vs LoRA 对比评估（Ollama，50 条测试上下文）")
    parser.add_argument("--test-path", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--limit", type=int, default=None, help="只评前 N 条（冒烟）")
    parser.add_argument("--base-model", default=None, help="基座模型名（默认 OLLAMA_MODEL，qwen3:1.7b）")
    parser.add_argument("--lora-model", default="harborguard-lora")
    parser.add_argument("--timeout-s", type=float, default=30.0, help="单次请求超时（契约：本地 30 秒）")
    parser.add_argument("--skip-lora", action="store_true", help="只评基座，不写 metrics.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_METRICS)
    args = parser.parse_args()
    settings = get_settings()
    if args.base_model is None:
        args.base_model = settings.ollama_model
    raise SystemExit(asyncio.run(run_eval(args)))


if __name__ == "__main__":
    main()
