"""只读复算 C4 训练/测试/确认集来源；不调用模型、不修改数据文件。"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ml.lora.gen_contexts import generate_contexts
DATA = REPO / "ml/lora/datasets"
CANDIDATE = REPO / "acceptance_c4/candidate_json_20261017"
DELIVERY = (
    REPO
    / "acceptance_c4"
    / "HarborGuard_LoRA_Qwen3.5-0.8B_formal_e3_s93_Q4_K_M_20261017_053229_2957"
)

EXPECTED_SHA256 = {
    "contexts500": "1cdae128ca5f6d269fea321de8ed4064d39f5ee061cc90c82e487522fb5422c5",
    "contexts_extra80": "276e6b2b8229f199322c8f33de65a2d726ba8e046199503dc687e0f5c4af6937",
    "real_contexts51": "45c5588f90d3a2a8b46cf865f998c9986fb01fe1aaa97ef40255cd34a8a71b6d",
    "distilled603": "b06f57161c4a2a3988999a37be1149cddd71879ec093ce4780f127af0f83e079",
    "train501": "b8afd68e3258a08cae76c39e60a6a505b93e011e62e5f1dbd161f8382e3afc87",
    "test50": "4453b8e2e0df089ec8623f14258c6f156db450d6ac2a2569211f731dca793845",
    "confirm_contexts60": "8678746ea194057cc98d11c8e610cf5abc09327cb45d431706457a295466cbaa",
    "confirm_eval60": "d6360787f9bda3d828bd2cdb0ac3990da63cf4793b210a28867f71f239e9aa28",
}

FILES = {
    "contexts500": DATA / "contexts.jsonl",
    "contexts_extra80": DATA / "contexts_extra.jsonl",
    "real_contexts51": DATA / "real_contexts.jsonl",
    "distilled603": DATA / "distilled.jsonl",
    "train501": DATA / "train.jsonl",
    "test50": DATA / "test.jsonl",
    "confirm_contexts60": CANDIDATE / "confirm_contexts_seed424242_n60.jsonl",
    "confirm_eval60": CANDIDATE / "confirm60.eval.jsonl",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def context_key(context: dict) -> str:
    payload = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def message_key(record: dict) -> str:
    # confirm60 的包装使用带空格 JSON；比较上下文，不能把序列化空格当作不同样本。
    return context_key(json.loads(record["messages"][1]["content"]))


def kinds(records: list[dict]) -> dict[str, int]:
    values = [json.loads(record["messages"][1]["content"])["kind"] for record in records]
    return dict(sorted(Counter(values).items()))


def main() -> int:
    rows = {name: load_jsonl(path) for name, path in FILES.items()}
    hashes = {name: sha256(path) for name, path in FILES.items()}
    source_keys = {
        name: {context_key(context) for context in rows[name]}
        for name in ("contexts500", "contexts_extra80", "real_contexts51", "confirm_contexts60")
    }
    distilled_keys = {record["key"] for record in rows["distilled603"]}
    train_keys = [message_key(record) for record in rows["train501"]]
    test_keys = [message_key(record) for record in rows["test50"]]
    confirm_eval_keys = [message_key(record) for record in rows["confirm_eval60"]]

    synthetic_keys = source_keys["contexts500"] | source_keys["contexts_extra80"]
    synthetic_distilled = sorted(
        (record for record in rows["distilled603"] if record["key"] in synthetic_keys),
        key=lambda record: record["key"],
    )
    random.Random(0).shuffle(synthetic_distilled)
    rebuilt_test = [record["key"] for record in synthetic_distilled[:50]]
    rebuilt_train = [record["key"] for record in synthetic_distilled[50:500]]

    training_meta = json.loads((DELIVERY / "training_meta.json").read_text(encoding="utf-8"))
    # 原始交接提交已经记录同一测试文件哈希，避免只依赖本轮新写的期望值。
    baseline_metrics = json.loads(subprocess.check_output(
        ["git", "show", "6da0831:ml/lora/metrics.json"], cwd=REPO, text=True
    ))
    checks = {
        "all_frozen_hashes_match": hashes == EXPECTED_SHA256,
        "contexts500_reproduced_seed0": generate_contexts(n=500, seed=0) == rows["contexts500"],
        "contexts_extra80_reproduced_seed1": generate_contexts(n=80, seed=1) == rows["contexts_extra80"],
        "confirm60_reproduced_seed424242": generate_contexts(n=60, seed=424242) == rows["confirm_contexts60"],
        "distilled_keys_match_message_contexts": all(record["key"] == message_key(record) for record in rows["distilled603"]),
        "test_rebuilt_exact_order_from_synthetic_seed0": rebuilt_test == test_keys,
        "train450_rebuilt_exact_order_from_synthetic_seed0": rebuilt_train == train_keys[:450],
        "all_real51_appended_to_train_tail": train_keys[450:] == [context_key(c) for c in rows["real_contexts51"]],
        "confirm60_wrapper_matches_raw_contexts": confirm_eval_keys == [context_key(c) for c in rows["confirm_contexts60"]],
        "train_test_exact_overlap_zero": not (set(train_keys) & set(test_keys)),
        "test_real_exact_overlap_zero": not (set(test_keys) & source_keys["real_contexts51"]),
        "test_confirm60_exact_overlap_zero": not (set(test_keys) & set(confirm_eval_keys)),
        "train_confirm60_exact_overlap_zero": not (set(train_keys) & set(confirm_eval_keys)),
        "test50_unique": len(set(test_keys)) == len(test_keys) == 50,
        "confirm60_unique": len(set(confirm_eval_keys)) == len(confirm_eval_keys) == 60,
        "training_meta_hash_matches_train501": training_meta["data_sha256"] == hashes["train501"],
        "training_meta_split_is_493_plus_8": training_meta["data_audit"]["train"] == 493
        and training_meta["data_audit"]["internal_validation"] == 8,
        "training_did_not_read_test": training_meta["data_audit"]["test_read"] is False,
        "handoff_commit_test50_hash_unchanged": baseline_metrics["sample_sets"]["test50"]["sha256"] == hashes["test50"],
        "handoff_commit_confirm60_hash_unchanged": baseline_metrics["sample_sets"]["confirm60"]["sha256"] == hashes["confirm_eval60"],
    }

    result = {
        "audit": "HarborGuard C4 dataset provenance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "pass" if all(checks.values()) else "fail",
        "handoff_baseline": "git show 6da0831:ml/lora/metrics.json (original source label corrected; dataset hashes unchanged)",
        "checks": checks,
        "files": {
            name: {
                "path": str(path.relative_to(REPO)),
                "rows": len(rows[name]),
                "sha256": hashes[name],
            }
            for name, path in FILES.items()
        },
        "evidence_files": {
            str(path.relative_to(REPO)): sha256(path)
            for path in (
                REPO / "ml/lora/gen_contexts.py", REPO / "ml/lora/distill.py",
                REPO / "ml/lora/eval.py", DELIVERY / "training_meta.json",
                DELIVERY / "FINAL_REPORT.md", CANDIDATE / "FREEZE.md",
                CANDIDATE / "metrics_candidate_json.json", CANDIDATE / "metrics_confirm60.json",
            )
        },
        "source_membership": {
            name: {
                "distilled": len(keys & distilled_keys),
                "train": len(keys & set(train_keys)),
                "test": len(keys & set(test_keys)),
            }
            for name, keys in source_keys.items()
        },
        "test50": {
            "source": "synthetic gen_contexts outputs, fixed split_records(seed=0); not capture_real",
            "source_breakdown": {"contexts500": 40, "contexts_extra80": 10, "real_contexts51": 0},
            "kinds": kinds(rows["test50"]),
        },
        "train501": {
            "source_breakdown": {"synthetic": 450, "captured_real": 51},
            "kinds": kinds(rows["train501"]),
            "formal_training_first493": {
                "source_breakdown": {"synthetic": 450, "captured_real": 43},
                "kinds": kinds(rows["train501"][:493]),
            },
            "internal_validation_last8": {
                "source_breakdown": {"synthetic": 0, "captured_real": 8},
                "kinds": kinds(rows["train501"][493:]),
            },
        },
        "exact_context_overlap": {
            "train501_vs_test50": len(set(train_keys) & set(test_keys)),
            "real51_vs_test50": len(source_keys["real_contexts51"] & set(test_keys)),
            "confirm60_vs_test50": len(set(confirm_eval_keys) & set(test_keys)),
            "confirm60_vs_train501": len(set(confirm_eval_keys) & set(train_keys)),
            "confirm60_vs_formal_train493": len(set(confirm_eval_keys) & set(train_keys[:493])),
            "confirm60_vs_internal_validation8": len(set(confirm_eval_keys) & set(train_keys[493:])),
        },
        "split_details": {
            "valid_synthetic_distilled": len(synthetic_distilled),
            "selected_train": 450,
            "selected_test": 50,
            "valid_synthetic_not_selected": len(synthetic_distilled) - 500,
        },
        "limitations": [
            "Exact context hashes prove split membership and absence of byte-equivalent contexts; they do not prove semantic independence of every generated scenario.",
            "real_contexts.jsonl has no per-row capture-run identifier, so the three reported A/B capture runs cannot be reconstructed as separate batches from this file alone.",
            "Both test50 and confirm60 are synthetic-context evaluations and do not establish real-harbor generalization.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
