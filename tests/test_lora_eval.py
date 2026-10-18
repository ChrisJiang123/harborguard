"""C4 eval 管线测试：记录加载、教师名推断、分阶段校验与指标聚合。"""
import pytest
pytestmark = pytest.mark.agent_language("zh")


import asyncio
import json

import pytest

from agent.prompts import SYSTEM_PROMPT as RUNTIME_SYSTEM_PROMPT
from agent.schemas import RecommendationDraft
from ml.lora.eval import eval_model, load_test_records, stage_of, teacher_name
from ml.lora.gen_contexts import generate_contexts


class FakeProvider:
    """按序返回预设响应的教师桩；第一个响应被 warmup 消耗。"""

    provider = "fake"
    request_model = "fake-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, system: str, messages: list[dict], timeout_s: float):
        self.calls += 1
        assert system == RUNTIME_SYSTEM_PROMPT
        text = self.responses.pop(0) if self.responses else "{}"
        return type("R", (), {"text": text})


@pytest.fixture(scope="module")
def contexts():
    contexts = [
        c for c in generate_contexts(n=40, seed=5)
        if c["kind"] == "security" and len(c["ranked"]) >= 2
        and not c["buoys"]["down"] and len(c["buoys"]["covering_track"]) >= 2
        and c["track"]["conf"] >= 0.6
    ]
    return contexts[:4]


def _draft(context, option_id) -> str:
    payload = {
        "summary": "推荐方案",
        "explanation": "按规则推荐延误最少且残余风险达标的方案。",
        "recommended_option_id": option_id,
        "evidence_ids": [context["alert"]["id"]],
        "uncertainties": [],
        "confidence": "high",
    }
    return json.dumps(payload, ensure_ascii=False)


def _record(context) -> dict:
    # assistant 内容只是占位：eval 只读取 user（上下文），输出由被测 provider 给出
    placeholder = (_draft(context, context["ranked"][0]) if context.get("ranked")
                   else json.dumps({"summary": "占位"}, ensure_ascii=False))
    return {"messages": [
        {"role": "system", "content": RUNTIME_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False,
                                               separators=(",", ":"), sort_keys=True)},
        {"role": "assistant", "content": placeholder},
    ]}


def test_load_test_records_filters_and_limits(tmp_path):
    good = _record(generate_contexts(n=20, seed=1)[0])
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


def test_stage_of_boxes_each_failure_stage(contexts):
    context = contexts[0]
    known = {context["alert"]["id"], context["track"]["id"], *context["ranked"]}
    options = {o["id"] for o in context["options"]}
    assert stage_of("这不是JSON", context, known, options)[0] == "json"
    assert stage_of('{"summary": "缺字段"}', context, known, options)[0] == "struct"
    stage, draft = stage_of(_draft(context, context["ranked"][0]).replace(
        f'"{context["alert"]["id"]}"', '"T-ghost"'), context, known, options)
    assert stage == "id" and draft is not None
    # 推荐与任务书规则（=ranked[0]）不符 -> 事实阶段拦截
    stage, draft = stage_of(_draft(context, context["ranked"][-1]), context, known, options)
    assert stage == "fact" and draft is not None
    assert stage_of(_draft(context, context["ranked"][0]), context, known, options)[0] == "ok"


def test_eval_model_counts_stages_agree_and_retry(contexts):
    responses = ["warmup"]
    for index, context in enumerate(contexts):
        if index == 0:
            responses.append("不是 JSON")                      # 首次 json 失败
            responses.append(_draft(context, context["ranked"][0]))  # 重试后 ok，一致
        elif index == 1:
            responses.append(_draft(context, context["ranked"][-1]))  # id 过、事实拦截
            responses.append(_draft(context, context["ranked"][-1]))  # 仍拦截 -> 最终 fact
        elif index == 2:
            responses.append("{{{")                            # 两次都 json 失败
            responses.append("{{{")
        else:
            responses.append(_draft(context, context["ranked"][0]))  # ok，一致

    provider = FakeProvider(responses)
    result = asyncio.run(eval_model(provider, [_record(c) for c in contexts], timeout_s=5))

    assert result["model"] == "fake-model"
    assert result["struct_valid_raw"] == 0.5        # 首次：c1(fact) + c3(ok)
    assert result["struct_valid"] == 0.75           # 重试后：c0/c3(ok) + c1(fact)
    assert result["id_fact_valid_raw"] == 0.25      # 仅 c3
    assert result["id_fact_valid"] == 0.5           # c0 + c3
    assert result["option_agree"] == 0.5            # c0 + c3；c1/fact 也计分母但不一致
    assert result["option_agree_n"] == 4
    assert result["option_agree_given_valid"] == 1.0 and result["option_agree_valid_n"] == 2
    assert result["null_recommend_n"] == 0 and result["null_recommend_correct"] == 0.0
    assert result["latency_s"] >= 0.0
    diag = result["_diag"]
    assert diag["retried_ok"] == 1 and diag["transport_errors"] == 0
    assert diag["first_stage"] == {"json": 2, "fact": 1, "ok": 1}
    assert diag["final_stage"] == {"json": 1, "fact": 1, "ok": 2}
    assert provider.calls == 1 + 2 + 2 + 2 + 1      # warmup + 各条尝试数


def test_eval_model_null_recommendation_for_disaster_and_buoy(contexts):
    disaster = next(c for c in generate_contexts(n=60, seed=9) if c["kind"] == "disaster")

    def disaster_draft(null_ok: bool) -> str:
        return json.dumps({
            "summary": "可复航", "explanation": "无阻塞分区，全部可复航。",
            "recommended_option_id": None if null_ok else "opt-1",
            "evidence_ids": [], "uncertainties": [], "confidence": "high",
        }, ensure_ascii=False)

    # 第一个响应被 warmup 消耗；第二条 null 正确；第三条违规推荐 opt-1（disaster 无 options，
    # 先被 ID 校验拦下；重试时响应耗尽返回 "{}"，最终停在 struct 阶段）
    provider = FakeProvider([disaster_draft(True), disaster_draft(True), disaster_draft(False)])
    result = asyncio.run(eval_model(provider, [_record(disaster)] * 2, timeout_s=5))
    assert result["null_recommend_correct"] == 0.5 and result["null_recommend_n"] == 2
    assert result["id_fact_valid"] == 0.5
    assert result["_diag"]["final_stage"] == {"ok": 1, "struct": 1}
