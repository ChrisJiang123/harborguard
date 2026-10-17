"""C4 eval 管线测试：记录加载、教师名推断、指标聚合与重试语义。"""

import asyncio
import json

import pytest

from ml.lora.distill import SYSTEM_PROMPT, user_message  # noqa: F401  (SYSTEM_PROMPT 供对照)
from ml.lora.eval import eval_model, load_test_records, teacher_name
from ml.lora.gen_contexts import generate_contexts
from agent.prompts import SYSTEM_PROMPT as RUNTIME_SYSTEM_PROMPT
from agent.schemas import RecommendationDraft


class FakeProvider:
    provider = "fake"
    request_model = "fake-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, system: str, messages: list[dict], timeout_s: float):
        self.calls += 1
        assert system == RUNTIME_SYSTEM_PROMPT
        text = self.responses.pop(0) if self.responses else "{}"
        return type("R", (), {"text": text, "response_model": "fake-model", "usage": None, "cost": None})


@pytest.fixture(scope="module")
def contexts():
    contexts = [
        c for c in generate_contexts(n=40, seed=5)
        if c["kind"] == "security" and len(c["ranked"]) >= 2
    ]
    return contexts[:4]


def _draft(context, use_ranked=True) -> str:
    option_id = context["ranked"][0] if use_ranked else context["ranked"][-1]
    payload = {
        "summary": "推荐方案",
        "explanation": "按规则推荐延误最少且残余风险达标的方案。",
        "recommended_option_id": option_id,
        "evidence_ids": [context["alert"]["id"]],
        "uncertainties": [],
        "confidence": "medium",
    }
    return json.dumps(payload, ensure_ascii=False)


def _record(context) -> dict:
    return {"messages": [
        {"role": "system", "content": RUNTIME_SYSTEM_PROMPT},
        {"role": "user", "content": user_message(context)},
        {"role": "assistant", "content": _draft(context)},
    ]}


def test_load_test_records_filters_and_limits(tmp_path):
    context = next(c for c in generate_contexts(n=20, seed=1)
                   if c["kind"] == "security" and len(c["ranked"]) >= 2)
    good = _record(context)
    bad = {"messages": [{"role": "user", "content": "缺 system/assistant"}]}
    path = tmp_path / "test.jsonl"
    path.write_text(
        json.dumps(good, ensure_ascii=False) + "\n" + "\n" + json.dumps(bad) + "\n",
        encoding="utf-8",
    )
    records = load_test_records(path, limit=None)
    assert len(records) == 1 and len(records[0]["messages"]) == 3
    assert load_test_records(path, limit=0) == []


def test_teacher_name_majority_and_fallback(tmp_path):
    path = tmp_path / "distilled.jsonl"
    with path.open("w", encoding="utf-8") as stream:
        for teacher in ("gemini", "gemini", "other"):
            stream.write(json.dumps({"teacher": teacher}) + "\n")
    assert teacher_name(path, "fallback") == "gemini"
    assert teacher_name(tmp_path / "missing.jsonl", "fallback") == "fallback"


def test_eval_model_counts_valid_agree_and_retry(contexts):
    # 第一个响应被 warmup 消耗
    responses = ["warmup"]
    for index, context in enumerate(contexts):
        if index == 0:
            responses.append("不是 JSON")       # 首次失败
            responses.append(_draft(context))   # 重试成功
        elif index == 1:
            responses.append(_draft(context, use_ranked=False))  # 合法但不一致
        elif index == 2:
            responses.append("{{{")             # 两次都失败
            responses.append("{{{")
        else:
            responses.append(_draft(context))

    provider = FakeProvider(responses)
    result = asyncio.run(eval_model(provider, [_record(c) for c in contexts], timeout_s=5))

    assert result["model"] == "fake-model"
    assert result["json_valid"] == 0.75            # 3/4 合法（含一次重试成功）
    assert result["option_agree"] == 0.5           # 4 条都有 ranked：index0 与 index3 一致
    assert result["latency_s"] >= 0.0
    assert result["_diag"]["valid"] == 3
    assert result["_diag"]["retry_success"] == 1
    assert provider.calls == 1 + 2 + 1 + 2 + 1     # warmup + 各条尝试数


def test_eval_model_without_ranked_has_no_agree_denominator():
    context = {
        "kind": "disaster", "t": 1.0, "mode": "disaster", "network": "online",
        "reopen_plan": {"route_zone_ids": [], "reopen_berth_zone_ids": [],
                        "unsurveyed_zone_ids": [], "blocked_zone_ids": [], "est_hours_saved": 0.0},
        "buoys": {"ok": 10, "ok_ids": ["B1"], "down": []},
        "zones": [], "options": [], "ranked": [], "recent_logs": [],
    }
    payload = {
        "summary": "可复航", "explanation": "暂无分区数据。",
        "recommended_option_id": None, "evidence_ids": [],
        "uncertainties": [], "confidence": "high",
    }
    payload_text = json.dumps(payload, ensure_ascii=False)
    provider = FakeProvider([payload_text, payload_text])  # 第一个被 warmup 消耗
    result = asyncio.run(eval_model(provider, [{"messages": [
        {"role": "system", "content": RUNTIME_SYSTEM_PROMPT},
        {"role": "user", "content": user_message(context)},
        {"role": "assistant", "content": "{}"},
    ]}], timeout_s=5))
    assert result["option_agree"] == 0.0 and result["_diag"]["ranked_total"] == 0
    assert result["json_valid"] == 1.0
