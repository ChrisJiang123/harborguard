"""C4 评估：Ollama 上对比「配对未微调基座」vs「harborguard-lora」，另报「当前系统基线」。

配对原则：base 与 lora 必须来自同一基座（同一 GGUF 量化 / chat template / 推理参数，
由 train_lora.ipynb 成对导出），LoRA 与 base 的差异才能归因于微调；
qwen3:1.7b 是当前系统在用的本地兜底，单列为 system_baseline——它与 0.8B 级 LoRA
的差距包含模型规模差异，不能全部记在微调头上。

每个模型分别报告（任务书 C4 验收 + 训练前检查第 7 条）：
- struct_valid_raw / struct_valid：首次 / 重试一次后的结构合法率（JSON 对象 + 六字段 pydantic）；
- id_fact_valid_raw / id_fact_valid：首次 / 重试后「ID 存在性 + 确定性事实」双合格率（C3 全套）；
- option_agree：有方案的 security 样本中 recommended_option_id == ranked[0] 的比例，
  分母 option_agree_n 为该类样本总数（含生成失败的）；另报仅双合格口径及分母；
- null_recommend_correct：disaster/buoy 样本中 recommended_option_id 正确为 null 的比例及分母；
- latency_s：平均每条总耗时（含重试与失败尝试；串行评测，不受并发排队干扰）。

评测请求与 C3 运行时完全同构（同一 SYSTEM_PROMPT、Ollama 原生 /api/chat、同一
JSON Schema 约束、超时 30 秒）。评测**没有模板兜底**：请求失败/超时的样本按不合格
计入分母，绝不计作生成成功。配对 base 与 lora 都评测成功才写 ml/lora/metrics.json
（后端 /api/metrics 读取）；system_baseline 未测时写 null。

用法::

    python -m ml.lora.eval                    # 配对 base + LoRA + 系统基线 -> metrics.json
    python -m ml.lora.eval --skip-lora        # 只评当前系统基线（训练前），不写 metrics.json
    python -m ml.lora.eval --skip-baseline    # 只跑配对对比
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
from agent.factcheck import check_draft_facts
from agent.prompts import SYSTEM_PROMPT
from agent.router import LocalProvider, Router
from agent.schemas import RecommendationDraft, normalize_draft

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


def stage_of(raw: str, context: dict, known_ids: set[str],
             option_ids: set[str]) -> tuple[str, RecommendationDraft | None]:
    """把一次输出按 C3 校验链分箱，返回（到达的最远阶段，draft 或 None）。

    阶段：json（可解析对象）→ struct（六字段 pydantic）→ id（ID 存在性）→
    fact（确定性事实）→ ok。失败停在失败阶段；ok 表示全部通过。
    """
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return "json", None
    if not isinstance(payload, dict):
        return "json", None
    try:
        draft = normalize_draft(RecommendationDraft.model_validate(payload))
    except Exception:  # noqa: BLE001 - pydantic ValidationError / strict 类型错误
        return "struct", None
    unknown = [e for e in draft.evidence_ids if e not in known_ids]
    opt = draft.recommended_option_id
    if unknown or (opt is not None and opt not in option_ids):
        return "id", draft
    if not check_draft_facts(draft, context).ok:
        return "fact", draft
    return "ok", draft


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


def _passed(stage: str, level: str) -> bool:
    """stage 到达或超过 level 视为通过该级（顺序 json < struct < id < fact < ok）。"""
    order = ("json", "struct", "id", "fact", "ok")
    return stage in order and order.index(stage) >= order.index(level)


async def eval_model(provider: LocalProvider, records: list[dict], *, timeout_s: float) -> dict:
    """串行评测一个模型；无模板兜底，传输失败/超时按不合格计入分母。"""
    first_stages: Counter = Counter()  # 首次尝试到达的阶段
    final_stages: Counter = Counter()  # 重试后最终阶段
    option_n = option_agree = 0              # 有方案 security 样本（全量分母）
    option_valid_n = option_agree_valid = 0  # 仅双合格（fact 通过）口径
    null_n = null_ok = 0                     # disaster/buoy 样本
    total_latency = 0.0
    retried_ok = 0
    transport_errors = 0
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
        want_option = context.get("kind") == "security" and ranked_first is not None
        want_null = context.get("kind") in {"disaster", "buoy"}
        if want_option:
            option_n += 1
        if want_null:
            null_n += 1

        raw: str | None = None
        error: str | None = None
        draft: RecommendationDraft | None = None
        stage = "transport"
        first_stage: str | None = None
        attempts = 0
        started = time.perf_counter()
        for attempt in range(MAX_ATTEMPTS):
            attempts = attempt + 1
            try:
                response = await provider.complete(
                    SYSTEM_PROMPT,
                    Router._retry_messages(user_content, raw, error),
                    timeout_s,
                )
            except Exception as exc:  # noqa: BLE001 - 传输失败=未生成，计入分母不计成功
                transport_errors += 1
                last_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                stage = "transport"
                break
            raw = response.text
            stage, draft = stage_of(raw, context, known_ids, option_ids)
            if first_stage is None:
                first_stage = stage
            if stage == "ok":
                break
            error = f"校验未通过（阶段 {stage}）"
        total_latency += time.perf_counter() - started

        first_stages[first_stage or "transport"] += 1
        final_stages[stage] += 1
        if attempts > 1 and stage == "ok":
            retried_ok += 1

        if want_option:
            if draft is not None and draft.recommended_option_id == ranked_first:
                option_agree += 1
            if stage == "ok":
                option_valid_n += 1
                if draft.recommended_option_id == ranked_first:
                    option_agree_valid += 1
        if want_null and draft is not None and draft.recommended_option_id is None:
            null_ok += 1
        if index % 10 == 0 or index == len(records):
            print(f"  [{provider.request_model}] {index}/{len(records)}", flush=True)

    n = len(records)

    def rate(count: int) -> float:
        return round(count / n, 3) if n else 0.0

    def sub_rate(count: int, denom: int) -> float:
        return round(count / denom, 3) if denom else 0.0

    struct_raw = sum(v for s, v in first_stages.items() if _passed(s, "id"))
    struct_final = sum(v for s, v in final_stages.items() if _passed(s, "id"))
    return {
        "model": provider.request_model,
        "struct_valid_raw": rate(struct_raw),
        "struct_valid": rate(struct_final),
        "id_fact_valid_raw": rate(first_stages.get("ok", 0)),
        "id_fact_valid": rate(final_stages.get("ok", 0)),
        "option_agree": sub_rate(option_agree, option_n),
        "option_agree_n": option_n,
        "option_agree_given_valid": sub_rate(option_agree_valid, option_valid_n),
        "option_agree_valid_n": option_valid_n,
        "null_recommend_correct": sub_rate(null_ok, null_n),
        "null_recommend_n": null_n,
        "latency_s": round(total_latency / n, 2) if n else 0.0,
        "_diag": {
            "first_stage": dict(first_stages),
            "final_stage": dict(final_stages),
            "retried_ok": retried_ok,
            "transport_errors": transport_errors,
            "last_error": last_error,
        },
    }


def _fmt(model_name: str, m: dict) -> str:
    return (
        f"{model_name}: 结构合法(首/重试后) {m['struct_valid_raw']:.0%}/{m['struct_valid']:.0%}、"
        f"ID+事实(首/重试后) {m['id_fact_valid_raw']:.0%}/{m['id_fact_valid']:.0%}、"
        f"方案一致 {m['option_agree']:.0%} (n={m['option_agree_n']}，仅双合格 "
        f"{m['option_agree_given_valid']:.0%}, n={m['option_agree_valid_n']})、"
        f"null正确 {m['null_recommend_correct']:.0%} (n={m['null_recommend_n']})、"
        f"{m['latency_s']}s/条"
    )


def _public(m: dict) -> dict:
    """metrics.json 不收 _diag（诊断只在 stdout）。"""
    return {k: v for k, v in m.items() if not k.startswith("_")}


async def _eval_local(settings, model_name: str, records: list[dict], timeout_s: float) -> dict:
    provider = LocalProvider(replace(settings, ollama_model=model_name))
    try:
        return await eval_model(provider, records, timeout_s=timeout_s)
    finally:
        await provider.aclose()


async def run_eval(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not args.test_path.exists():
        print(f"错误：缺少 {args.test_path}；先运行 python -m ml.lora.distill 生成 train/test 划分")
        return 2
    records = load_test_records(args.test_path, args.limit)
    if not records:
        print(f"错误：{args.test_path} 无有效样本")
        return 2
    if args.skip_lora and args.skip_baseline:
        print("错误：--skip-lora 与 --skip-baseline 不能同时使用")
        return 2
    print(f"评测样本 {len(records)} 条（串行；分阶段校验 = C3 同一套，含一次重试；无模板兜底）")

    results: dict = {}
    if not args.skip_baseline:
        try:
            results["system_baseline"] = await _eval_local(
                settings, args.baseline_model, records, args.timeout_s
            )
        except Exception as exc:  # noqa: BLE001 - 基线缺失不阻塞配对对比
            results["system_baseline"] = None
            print(f"警告：系统基线 {args.baseline_model} 评测失败（{type(exc).__name__}: {str(exc)[:160]}）")
        else:
            print(_fmt("系统基线", results["system_baseline"]))

    if args.skip_lora:
        print("未评测配对 base/LoRA：训练部署完成后运行 python -m ml.lora.eval 生成 metrics.json")
        return 0

    for label, model_name in (("base", args.base_model), ("lora", args.lora_model)):
        try:
            results[label] = await _eval_local(settings, model_name, records, args.timeout_s)
        except Exception as exc:  # noqa: BLE001
            print(f"错误：{label} 模型 {model_name} 评测失败：{type(exc).__name__}: {str(exc)[:200]}")
            print("请先按 ml/lora/README.md 部署（ollama create harborguard-lora/-base）。")
            return 3
        print(_fmt({"base": "配对基座", "lora": "LoRA"}[label], results[label]))

    metrics = {
        "base": _public(results["base"]),
        "lora": _public(results["lora"]),
        "system_baseline": _public(results["system_baseline"]) if results.get("system_baseline") else None,
        "n_test": len(records),
        "teacher": teacher_name(DEFAULT_DISTILLED, settings.openrouter_model),
        "pairing_note": (
            "base=与 lora 同一基座的未微调 GGUF（同量化/同模板/同推理参数）；"
            "system_baseline=当前系统本地兜底（规模不同，差异不能全归因微调）"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {args.out}（后端 GET /api/metrics 的 lora 字段即此文件）")

    lora = metrics["lora"]
    base = metrics["base"]
    ok = lora["struct_valid"] >= 0.90 and lora["option_agree"] >= 0.80
    better = (
        lora["id_fact_valid"] >= base["id_fact_valid"]
        and lora["option_agree"] >= base["option_agree"]
        and (lora["option_agree"] > base["option_agree"] or lora["id_fact_valid"] > base["id_fact_valid"])
    )
    print(f"验收线: LoRA 结构合法≥0.90 且 方案一致≥0.80 -> {'通过' if ok else '未达标'}")
    print(f"明显好于配对基座: {'是' if better else '否（指标卡如实显示）'}")
    for label in ("base", "lora"):
        diag = results[label]["_diag"]
        if diag["transport_errors"] or diag["last_error"]:
            print(f"诊断[{label}]: {diag}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="配对基座 vs LoRA vs 系统基线（Ollama，测试集）")
    parser.add_argument("--test-path", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--limit", type=int, default=None, help="只评前 N 条（冒烟）")
    parser.add_argument("--base-model", default="harborguard-base", help="配对未微调基座（Ollama 模型名）")
    parser.add_argument("--lora-model", default="harborguard-lora")
    parser.add_argument("--baseline-model", default=None, help="当前系统基线（默认 OLLAMA_MODEL）")
    parser.add_argument("--timeout-s", type=float, default=30.0, help="单次请求超时（契约：本地 30 秒）")
    parser.add_argument("--skip-lora", action="store_true", help="不评配对 base/LoRA（不写 metrics.json）")
    parser.add_argument("--skip-baseline", action="store_true", help="不评当前系统基线")
    parser.add_argument("--out", type=Path, default=DEFAULT_METRICS)
    args = parser.parse_args()
    settings = get_settings()
    if args.baseline_model is None:
        args.baseline_model = settings.ollama_model
    raise SystemExit(asyncio.run(run_eval(args)))


if __name__ == "__main__":
    main()
