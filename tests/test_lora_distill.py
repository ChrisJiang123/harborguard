"""C4 distillation: C3 validation, retry semantics, idempotent keys and seeded splits."""
import pytest
pytestmark = pytest.mark.agent_language("zh")


import asyncio
import hashlib
import json

import pytest

from agent.prompts import SYSTEM_PROMPT
from agent.router import RawResponse
from agent.schemas import RecommendationDraft
from ml.lora.distill import (
    assistant_message,
    build_turn_messages,
    context_key,
    distill_batch,
    split_records,
    user_message,
)
from ml.lora.gen_contexts import generate_contexts


class FakeProvider:
    """Teacher stub returns preset responses in order and records retry-message calls."""

    provider = "fake"
    request_model = "fake-teacher"

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[tuple[str, list[dict]]] = []

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        self.calls.append((system, messages))
        text = self.responses.pop(0) if self.responses else "{}"
        return RawResponse(
            text=text,
            response_model="fake-teacher",
            upstream_provider="fake-upstream",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            cost=0.001,
        )


@pytest.fixture(scope="module")
def security_contexts():
    return [c for c in generate_contexts(n=40, seed=3) if c["kind"] == "security"]


def _draft_json(**overrides) -> str:
    payload = {
        "summary": "推荐最小封闭方案，延误最小",
        "explanation": "警报 A1 为二级，目标置信度较高，两个浮标覆盖。按任务书规则推荐残余风险低且延误最少的方案。",
        "recommended_option_id": None,
        "evidence_ids": [],
        "uncertainties": [],
        "confidence": "medium",
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def test_valid_first_attempt_produces_training_record(security_contexts):
    context = next(c for c in security_contexts if c["options"])
    option_id = context["ranked"][0]

    async def run():
        provider = FakeProvider([
            _draft_json(
                recommended_option_id=option_id,
                evidence_ids=[context["alert"]["id"], context["track"]["id"]],
                confidence="high",
            )
        ])
        return provider, await distill_batch([context], provider, concurrency=1, timeout_s=5)

    provider, batch = asyncio.run(run())
    assert len(batch["records"]) == 1 and not batch["failures"]
    record = batch["records"][0]
    assert record["attempts"] == 1 and record["teacher"] == "fake-teacher"
    system, user, assistant = record["messages"]
    assert system == {"role": "system", "content": SYSTEM_PROMPT}
    assert user == {"role": "user", "content": user_message(context)}
    draft = RecommendationDraft.model_validate(json.loads(assistant["content"]))
    assert draft.recommended_option_id == option_id
    assert batch["usage"]["completion_tokens"] == 5


def test_invalid_output_retries_once_with_error_feedback(security_contexts):
    context = next(c for c in security_contexts if c["options"])
    option_id = context["ranked"][0]

    async def run():
        provider = FakeProvider([
            "这不是 JSON",
            _draft_json(
                recommended_option_id=option_id,
                evidence_ids=[context["alert"]["id"]],
                confidence="high",
            ),
        ])
        return provider, await distill_batch([context], provider, concurrency=1, timeout_s=5)

    provider, batch = asyncio.run(run())
    assert len(batch["records"]) == 1 and batch["records"][0]["attempts"] == 2
    first, second = provider.calls
    assert len(first[1]) == 1
    assert len(second[1]) == 3  # User + assistant(original output) + user(validation error).
    assert second[1][2]["role"] == "user" and "校验错误" in second[1][2]["content"]
    assert "JSON" in second[1][2]["content"]


def test_invalid_twice_is_recorded_as_failure(security_contexts):
    context = security_contexts[0]

    async def run():
        provider = FakeProvider(["null", '{"broken": true}'])
        return await distill_batch([context], provider, concurrency=1, timeout_s=5)

    batch = asyncio.run(run())
    assert not batch["records"] and len(batch["failures"]) == 1
    assert "JSON" in batch["failures"][0]["error"] or "结构校验" in batch["failures"][0]["error"]


def test_factcheck_failure_triggers_retry(security_contexts):
    context = next(
        c for c in security_contexts
        if c["options"] and not c["buoys"]["down"]
        and len(c["buoys"]["covering_track"]) >= 2 and c["track"]["conf"] >= 0.6
    )
    option_id = context["ranked"][0]

    async def run():
        provider = FakeProvider([
            # Structure/IDs pass, but the offline-buoy claim contradicts context: fact failure.
            _draft_json(
                recommended_option_id=option_id,
                evidence_ids=[context["alert"]["id"]],
                uncertainties=["浮标 B1 离线"],
                confidence="low",
            ),
            _draft_json(
                recommended_option_id=option_id,
                evidence_ids=[context["alert"]["id"]],
                uncertainties=["当前无浮标离线"],
                confidence="high",
            ),
        ])
        return provider, await distill_batch([context], provider, concurrency=1, timeout_s=5)

    provider, batch = asyncio.run(run())
    assert len(batch["records"]) == 1 and batch["records"][0]["attempts"] == 2
    assert "事实校验失败" in provider.calls[1][1][2]["content"]


def test_guided_retry_keeps_training_messages_clean(security_contexts):
    """After two strict failures, third uses GUIDED_HINT; stored samples omit the hint."""
    from ml.lora.distill import GUIDED_HINT

    context = next(
        c for c in security_contexts
        if c["options"] and not c["buoys"]["down"]
        and len(c["buoys"]["covering_track"]) >= 2 and c["track"]["conf"] >= 0.6
    )
    option_id = context["ranked"][0]

    async def run():
        provider = FakeProvider([
            "不是 JSON",
            _draft_json(uncertainties=["浮标 B1 离线"], confidence="low"),
            _draft_json(
                recommended_option_id=option_id,
                evidence_ids=[context["alert"]["id"]],
                confidence="high",
            ),
        ])
        return provider, await distill_batch([context], provider, concurrency=1, timeout_s=5)

    provider, batch = asyncio.run(run())
    assert len(batch["records"]) == 1 and batch["records"][0]["attempts"] == 3
    guided_messages = provider.calls[2][1]
    assert len(guided_messages) == 3 and GUIDED_HINT in guided_messages[2]["content"]
    stored = batch["records"][0]["messages"]
    assert len(stored) == 3 and all(GUIDED_HINT not in m["content"] for m in stored)


def test_context_key_uses_router_serialization(security_contexts):
    context = security_contexts[0]
    payload = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    assert context_key(context) == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert context_key(context) != context_key({**context, "t": context["t"] + 1})


def test_build_turn_messages_shape():
    plain = build_turn_messages("{}", None, None)
    assert plain == [{"role": "user", "content": "{}"}]
    retried = build_turn_messages("{}", "原输出", "结构校验失败: x")
    assert [m["role"] for m in retried] == ["user", "assistant", "user"]


def test_assistant_message_round_trips_and_keeps_chinese():
    draft = RecommendationDraft.model_validate({
        "summary": "推荐方案 opt-1",
        "explanation": "残余风险 0.10，延误 2.0 船时。",
        "recommended_option_id": "opt-1",
        "evidence_ids": ["A1"],
        "uncertainties": ["仅 1 个浮标覆盖"],
        "confidence": "medium",
    })
    text = assistant_message(draft)
    assert "推荐方案" in text  # ensure_ascii=False
    assert RecommendationDraft.model_validate(json.loads(text)) == draft


def test_split_records_deterministic_and_disjoint():
    records = [{"key": f"key-{i:04d}", "messages": [{"role": "system", "content": str(i)}]} for i in range(520)]
    train, test = split_records(records, test_size=50, train_size=450, seed=0)
    assert len(train) == 450 and len(test) == 50
    keys = {r["key"] for r in train} | {r["key"] for r in test}
    assert len(keys) == 500
    train2, test2 = split_records(records, test_size=50, train_size=450, seed=0)
    assert [r["key"] for r in train] == [r["key"] for r in train2]
    assert [r["key"] for r in test] == [r["key"] for r in test2]
