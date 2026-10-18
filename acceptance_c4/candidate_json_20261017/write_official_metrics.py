"""③ 正式指标写入：归档旧失败记录 → 生成富结构 ml/lora/metrics.json → 校验可解析。

保留全部口径：schema 模式历史失败、json 模式 50 条合成固定测试集回归、
confirm60 新集（合成上下文，事实 39/60）、配对基座与系统基线、
模型/格式/评估配置/样本集哈希。结构、事实、方案、null、延迟分列，保留整数分母。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAND = REPO / "acceptance_c4" / "candidate_json_20261017"
OFFICIAL = REPO / "ml" / "lora" / "metrics.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


candidate_50 = json.loads((CAND / "metrics_candidate_json.json").read_text(encoding="utf-8"))
confirm60 = json.loads((CAND / "metrics_confirm60.json").read_text(encoding="utf-8"))
previous = json.loads(OFFICIAL.read_text(encoding="utf-8"))

# 归档（时间戳副本 + 哈希）
archive_dir = CAND / "archived_metrics"
archive_dir.mkdir(exist_ok=True)
archived_copy = archive_dir / "metrics.schema-mode-failure.20261017.json"
if not archived_copy.exists():
    if "history_schema_mode" in previous or previous.get("mode") == "json-candidate":
        raise RuntimeError("缺少原始 schema 失败归档；拒绝用 json 候选指标冒充或覆盖历史证据")
    shutil.copy2(OFFICIAL, archived_copy)
schema_failure = json.loads(archived_copy.read_text(encoding="utf-8"))


def with_counts(metric: dict, total: int) -> dict:
    """从历史三位小数聚合值唯一还原整数；歧义或不一致时拒绝编造。"""
    counts = {}
    for key, denominator in (
        ("struct_valid", total), ("id_fact_valid", total),
        ("option_agree", metric["option_agree_n"]),
        ("null_recommend_correct", metric["null_recommend_n"]),
    ):
        candidates = [n for n in range(denominator + 1) if round(n / denominator, 3) == metric[key]]
        if len(candidates) != 1:
            raise ValueError(f"{key} 无唯一整数分子")
        counts[key] = {"pass": candidates[0], "total": denominator}
    return {**metric, "counts": counts}


for label in ("base", "lora", "system_baseline"):
    if candidate_50.get(label):
        candidate_50[label] = with_counts(candidate_50[label], candidate_50["n_test"])
for label in ("base", "lora"):
    confirm60[label] = with_counts(confirm60[label], confirm60["n_test"])

confirm_fact_n = 39  # confirm60 LoRA ID+事实合格 65% × 60 = 39（0.65 整数还原）
official = {
    # ---- 顶层保持 eval.py 输出形状：当前生效配置（json 模式 50 条合成固定集） ----
    **candidate_50,
    "mode": "json-candidate",
    "generated_at": previous.get("generated_at", datetime.now(timezone.utc).isoformat()),
    "metadata_corrected_at": datetime.now(timezone.utc).isoformat(),
    "counts_note": "整数分子由原始三位小数聚合指标唯一还原；原始结果文件与历史失败归档保留不变。",
    "eval_config": {
        "runtime": "Ollama 0.40.5 (qwen35)",
        "model": "harborguard-lora",
        "model_gguf_sha256": sha(REPO / "ml/lora/harborguard.gguf"),
        "paired_base_model": "harborguard-base",
        "paired_base_gguf_sha256": sha(REPO / "ml/lora/harborguard-base.gguf"),
        "output_format": "format=json（OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json,harborguard-base:json；候选配置）",
        "format_note": "完整 schema 约束下该 LoRA 在 Mac/Ollama 循环不终止（见 history_schema_mode）；format=json 为最小修复",
        "sampling": "temperature 0 / seed 0 / num_predict 450 / think false / 请求级覆盖 Modelfile",
        "validation": "与 C3 运行时同一链：JSON→pydantic 六字段→ID 存在性→确定性事实；无模板兜底；失败/超时计入分母",
        "attempts": "首试 + 附校验错误重试 1 次（temp0/seed0 确定性）",
        "timeout_s": 30,
    },
    "sample_sets": {
        "test50": {
            "provenance": "gen_contexts.py 固定种子合成上下文；552 条合格合成蒸馏记录经 split_records(seed=0) 取前 50 条（contexts.jsonl 来源 40 条，contexts_extra.jsonl 来源 10 条）；不是 capture_real 真实采集",
            "path": "ml/lora/datasets/test.jsonl",
            "sha256": sha(REPO / "ml/lora/datasets/test.jsonl"),
            "n": 50,
        },
        "confirm60": {
            "provenance": "gen_contexts.py 合成上下文（--n 60 --seed 424242，含故障注入）；非真实采集",
            "path": "acceptance_c4/candidate_json_20261017/confirm60.eval.jsonl",
            "sha256": sha(CAND / "confirm60.eval.jsonl"),
            "n": 60,
        },
        "train501": {
            "provenance": "450 条合成固定划分 + 51 条 capture_real 真实场景上下文；Lenovo 训练程序取前 493 条训练、末 8 条仅作内部验证",
            "path": "ml/lora/datasets/train.jsonl",
            "sha256": sha(REPO / "ml/lora/datasets/train.jsonl"),
            "n": 501,
            "formal_training_n": 493,
            "formal_training_composition": {"synthetic": 450, "captured_real": 43},
            "internal_validation_n": 8,
            "internal_validation_composition": {"synthetic": 0, "captured_real": 8},
        },
        "source_audit": "acceptance_c4/data_provenance_20261017/audit.json",
    },
    # ---- confirm60：结构与业务行为在新上下文上的确认（合成口味，事实率单列不与 test50 混算） ----
    "confirm60_synthetic": {
        "note": "seed=424242 的独立合成确认集，与 test50 无精确上下文重复；事实合格率保留独立分母，不与 test50 平均或替代",
        "lora": confirm60["lora"],
        "base": confirm60["base"],
        "lora_id_fact_pass_n": confirm_fact_n,
        "lora_id_fact_total_n": 60,
        "n_test": confirm60["n_test"],
    },
    # ---- 历史：schema 模式验收失败（完整保留，未删改） ----
    "history_schema_mode": {
        "date": "2026-10-17",
        "config": "format=完整 RecommendationDraft JSON Schema（C3 原口径），模型同 harborguard-lora",
        "outcome": "未达标：LoRA 结构合法 20%、方案一致 30.3%、null 0%、14.4s/条；未切线上",
        "root_cause": "Mac/Ollama 下 schema grammar 约束解码循环不终止；键序经 Ollama 不可达（Windows 原生键序效应不适用于 Mac）",
        "full_metrics": schema_failure,
    },
    "runtime_budget_events": {
        "preswitch": "12/12：三类上下文×方案/null 覆盖；模型合格 3、事实失败→模板 1、超时 0；重置零迟到 POST；云端隔离",
        "part1_pure": "16/16：任务淘汰/代际失效/过期 deadline→模板（provider 零调用）",
        "part2_real_budget": "12/12：生成中取消→模板 0.71s；qwen3 事实失败→模板兜底 3/3（8.6-9.0s ≤ 9.5s 预算）",
        "artifacts": "acceptance_c4/candidate_json_20261017/{preswitch_events.json,test_runtime_events_part1,2}.py",
    },
    "reports": {
        "diagnosis": "acceptance_c4/diag_c4_20261017/report_diagnosis.md",
        "crossruntime_supplement": "~/Desktop/HarborGuard-C4-crossruntime-supplement.zip",
        "lenovo_order_minrepro": "acceptance_c4/lenovo_minrepro_20261017/",
        "matrix_note": "Windows 原生 b11707：声明序 9/9 EOS、字母序 1-2/9 循环（键序敏感，限定已测版本配置）；Mac 原生 b11707 未验证",
    },
}

OFFICIAL.write_text(json.dumps(official, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
# 完整性自检
json.loads(OFFICIAL.read_text(encoding="utf-8"))
print(f"已写入 {OFFICIAL}")
print(f"归档: {archived_copy} sha256={sha(archived_copy)[:16]}…")
print(f"官方文件 sha256={sha(OFFICIAL)[:16]}…")
