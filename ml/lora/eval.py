"""C4 serial Ollama evaluation: paired untuned base versus harborguard-lora, with qwen3:1.7b reported
separately as system_baseline. The paired base shares model, GGUF quantization, chat template and
parameters so differences can be attributed to tuning. Report first/retry structure and ID+facts,
option agreement with explicit denominators, null correctness and latency including failures. No
template fallback; failed calls remain in denominators. Write metrics.json only for a complete
paired comparison; diagnostics stay on stdout.
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
MAX_ATTEMPTS = 2  # Match C3: initial attempt plus one validation-guided retry.
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
    """Read the actual teacher model by majority from distillation output; otherwise use cloud
    configuration.
    """
    counts: Counter = Counter()
    if distilled_path.exists():
        with distilled_path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    counts[json.loads(line).get("teacher") or "unknown"] += 1
    return counts.most_common(1)[0][0] if counts else fallback


def stage_of(raw: str, context: dict, known_ids: set[str],
             option_ids: set[str]) -> tuple[str, RecommendationDraft | None]:
    """Classify one response by the furthest reached C3 stage: json -> struct -> id -> fact -> ok.
    Return (stage, draft or None); ok means every check passed.
    """
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return "json", None
    if not isinstance(payload, dict):
        return "json", None
    try:
        draft = normalize_draft(RecommendationDraft.model_validate(payload))
    except Exception:  # noqa: BLE001 - Pydantic validation or strict type errors.
        return "struct", None
    unknown = [e for e in draft.evidence_ids if e not in known_ids]
    opt = draft.recommended_option_id
    if unknown or (opt is not None and opt not in option_ids):
        return "id", draft
    if not check_draft_facts(draft, context).ok:
        return "fact", draft
    return "ok", draft


async def warmup(provider: LocalProvider) -> None:
    """Warm up once; the initial cold-load request is excluded from latency."""
    try:
        await provider.complete(
            SYSTEM_PROMPT,
            [{"role": "user", "content": '{"kind": "security", "t": 0}'}],
            WARMUP_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001 - Let the actual request report a failed warmup explicitly.
        print(f"  Warning: {provider.request_model} warmup failed: {type(exc).__name__}: {str(exc)[:160]}")


def _passed(stage: str, level: str) -> bool:
    """A reached stage passes a level when it is at or beyond json < struct < id < fact < ok."""
    order = ("json", "struct", "id", "fact", "ok")
    return stage in order and order.index(stage) >= order.index(level)


async def eval_model(provider: LocalProvider, records: list[dict], *, timeout_s: float) -> dict:
    """Evaluate a model serially, without template fallback; transport/timeouts count as failures."""
    first_stages: Counter = Counter()  # Stage reached on first attempt.
    final_stages: Counter = Counter()  # Final stage after retry.
    option_n = option_agree = 0              # All Security samples with options form the denominator.
    option_valid_n = option_agree_valid = 0  # Subset passing both ID and fact checks.
    null_n = null_ok = 0                     # Disaster/buoy samples.
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
            except Exception as exc:  # noqa: BLE001 - Transport failures remain in denominator and never count as success.
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
        f"{model_name}: Structure (first/after retry) {m['struct_valid_raw']:.0%}/{m['struct_valid']:.0%} ; "
        f"IDs+facts (first/after retry) {m['id_fact_valid_raw']:.0%}/{m['id_fact_valid']:.0%} ; "
        f"Option agreement {m['option_agree']:.0%} (n={m['option_agree_n']}, valid IDs+facts only "
        f"{m['option_agree_given_valid']:.0%}, n={m['option_agree_valid_n']}) ; "
        f"Null correctness {m['null_recommend_correct']:.0%} (n={m['null_recommend_n']}) ; "
        f"{m['latency_s']}s/sample"
    )


def _public(m: dict) -> dict:
    """Exclude _diag from metrics.json; diagnostics are stdout-only."""
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
        print(f"Error: missing {args.test_path}; run python -m ml.lora.distill to create train/test splits.")
        return 2
    records = load_test_records(args.test_path, args.limit)
    if not records:
        print(f"Error: no valid samples in {args.test_path}.")
        return 2
    if args.skip_lora and args.skip_baseline:
        print("Error: --skip-lora and --skip-baseline cannot both be used.")
        return 2
    print(f"Evaluating {len(records)} samples serially (C3 validation stages, one retry, no template fallback)")

    results: dict = {}
    if not args.skip_baseline:
        try:
            results["system_baseline"] = await _eval_local(
                settings, args.baseline_model, records, args.timeout_s
            )
        except Exception as exc:  # noqa: BLE001 - An absent system baseline does not block paired evaluation.
            results["system_baseline"] = None
            print(f"Warning: system baseline {args.baseline_model} failed ({type(exc).__name__}: {str(exc)[:160]})")
        else:
            print(_fmt("System baseline", results["system_baseline"]))

    if args.skip_lora:
        print("Paired base/LoRA not evaluated; after deployment, run python -m ml.lora.eval to generate metrics.json.")
        return 0

    for label, model_name in (("base", args.base_model), ("lora", args.lora_model)):
        try:
            results[label] = await _eval_local(settings, model_name, records, args.timeout_s)
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {label} model {model_name} evaluation failed: {type(exc).__name__}: {str(exc)[:200]}")
            print("Deploy first using ml/lora/README.md (ollama create harborguard-lora/-base).")
            return 3
        print(_fmt({"base": "Paired base", "lora": "LoRA"}[label], results[label]))

    metrics = {
        "base": _public(results["base"]),
        "lora": _public(results["lora"]),
        "system_baseline": _public(results["system_baseline"]) if results.get("system_baseline") else None,
        "n_test": len(records),
        "teacher": teacher_name(DEFAULT_DISTILLED, settings.openrouter_model),
        "pairing_note": (
            "base=untuned GGUF paired with lora (same quantization/template/inference parameters); "
            "system_baseline=current local fallback; model-size differences cannot all be attributed to tuning"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} (source of backend GET /api/metrics lora field)")

    lora = metrics["lora"]
    base = metrics["base"]
    ok = lora["struct_valid"] >= 0.90 and lora["option_agree"] >= 0.80
    better = (
        lora["id_fact_valid"] >= base["id_fact_valid"]
        and lora["option_agree"] >= base["option_agree"]
        and (lora["option_agree"] > base["option_agree"] or lora["id_fact_valid"] > base["id_fact_valid"])
    )
    print(f"Acceptance: LoRA structure>=0.90 and option agreement>=0.80 -> {'PASS' if ok else 'FAIL'}")
    print(f"Better than paired base: {'yes' if better else 'no (reported as measured)'}")
    for label in ("base", "lora"):
        diag = results[label]["_diag"]
        if diag["transport_errors"] or diag["last_error"]:
            print(f"Diagnostics [{label}]: {diag}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired base vs LoRA vs system baseline (Ollama, test set)")
    parser.add_argument("--test-path", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N records (smoke)")
    parser.add_argument("--base-model", default="harborguard-base", help="Paired untuned base (Ollama model name)")
    parser.add_argument("--lora-model", default="harborguard-lora")
    parser.add_argument("--baseline-model", default=None, help="System baseline (default OLLAMA_MODEL)")
    parser.add_argument("--timeout-s", type=float, default=30.0, help="Per-request timeout (contract:30 seconds locally)")
    parser.add_argument("--skip-lora", action="store_true", help="Skip paired base/LoRA; do not write metrics.json")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip system baseline")
    parser.add_argument("--out", type=Path, default=DEFAULT_METRICS)
    args = parser.parse_args()
    settings = get_settings()
    if args.baseline_model is None:
        args.baseline_model = settings.ollama_model
    raise SystemExit(asyncio.run(run_eval(args)))


if __name__ == "__main__":
    main()
