"""C4 evaluation: record loading, teacher inference, staged checks and metrics."""
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
    """Teacher stub returns preset responses in order; warmup consumes the first."""

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
    # Assistant is a placeholder: eval reads user context; the provider supplies output.
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
    # Recommendation conflicts with the taskbook rule (=ranked[0]); fact stage rejects it.
    stage, draft = stage_of(_draft(context, context["ranked"][-1]), context, known, options)
    assert stage == "fact" and draft is not None
    assert stage_of(_draft(context, context["ranked"][0]), context, known, options)[0] == "ok"


def test_eval_model_counts_stages_agree_and_retry(contexts):
    responses = ["warmup"]
    for index, context in enumerate(contexts):
        if index == 0:
            responses.append("不是 JSON")                      # First attempt fails JSON parsing.
            responses.append(_draft(context, context["ranked"][0]))  # Retry passes and agrees.
        elif index == 1:
            responses.append(_draft(context, context["ranked"][-1]))  # IDs pass; facts reject.
            responses.append(_draft(context, context["ranked"][-1]))  # Rejected again; final fact failure.
        elif index == 2:
            responses.append("{{{")                            # Both attempts fail JSON parsing.
            responses.append("{{{")
        else:
            responses.append(_draft(context, context["ranked"][0]))  # Passes and agrees.

    provider = FakeProvider(responses)
    result = asyncio.run(eval_model(provider, [_record(c) for c in contexts], timeout_s=5))

    assert result["model"] == "fake-model"
    assert result["struct_valid_raw"] == 0.5        # First: c1(fact) + c3(ok).
    assert result["struct_valid"] == 0.75           # After retry: c0/c3(ok) + c1(fact).
    assert result["id_fact_valid_raw"] == 0.25      # Only c3.
    assert result["id_fact_valid"] == 0.5           # c0 + c3
    assert result["option_agree"] == 0.5            # c0+c3; c1/fact counts in denominator but disagrees.
    assert result["option_agree_n"] == 4
    assert result["option_agree_given_valid"] == 1.0 and result["option_agree_valid_n"] == 2
    assert result["null_recommend_n"] == 0 and result["null_recommend_correct"] == 0.0
    assert result["latency_s"] >= 0.0
    diag = result["_diag"]
    assert diag["retried_ok"] == 1 and diag["transport_errors"] == 0
    assert diag["first_stage"] == {"json": 2, "fact": 1, "ok": 1}
    assert diag["final_stage"] == {"json": 1, "fact": 1, "ok": 2}
    assert provider.calls == 1 + 2 + 2 + 2 + 1      # Warmup + attempts for each record.


def test_eval_model_null_recommendation_for_disaster_and_buoy(contexts):
    disaster = next(c for c in generate_contexts(n=60, seed=9) if c["kind"] == "disaster")

    def disaster_draft(null_ok: bool) -> str:
        return json.dumps({
            "summary": "可复航", "explanation": "无阻塞分区，全部可复航。",
            "recommended_option_id": None if null_ok else "opt-1",
            "evidence_ids": [], "uncertainties": [], "confidence": "high",
        }, ensure_ascii=False)

    # Warmup consumes the first response; second null is valid; third wrongly picks opt-1.
    # Disaster has no options: IDs reject it, retry exhausts responses and returns "{}",
    # leaving the final failure at the structural stage.
    provider = FakeProvider([disaster_draft(True), disaster_draft(True), disaster_draft(False)])
    result = asyncio.run(eval_model(provider, [_record(disaster)] * 2, timeout_s=5))
    assert result["null_recommend_correct"] == 0.5 and result["null_recommend_n"] == 2
    assert result["id_fact_valid"] == 0.5
    assert result["_diag"]["final_stage"] == {"ok": 1, "struct": 1}
