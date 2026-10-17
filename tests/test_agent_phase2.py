"""Agent C3 第二阶段：严格输出、重试、截止时间与三级路由。"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import replace

import pytest
from pydantic import ValidationError

from agent.config import get_settings
from agent.router import CloudProvider, RawResponse, Router
from agent.schemas import DraftOutputError, RecommendationDraft, parse_model_draft


def sample_context(network: str = "online") -> dict:
    return {
        "kind": "security",
        "t": 10.0,
        "mode": "security",
        "network": network,
        "alert": {"id": "A1", "level": 3, "risk": 0.8, "breakdown": {"C": 0.8}, "track_id": "T1"},
        "track": {"id": "T1", "cls": "uuv", "conf": 0.8, "depth_m": 8.0, "speed_mps": 1.5},
        "detections": [{"id": "det-1", "cls": "uuv", "conf": 0.8, "model": "stub"}],
        "options": [{
            "id": "opt-1", "label": "最小封闭", "zones_closed": ["zone-1"],
            "vessels_affected": 1, "delay_vessel_hours": 0.5, "residual_risk": 0.1,
        }],
        "ranked": ["opt-1"],
        "buoys": {"ok": 2, "down": [], "covering_track": ["B1", "B2"]},
        "zones": [{"id": "zone-1", "state": "open"}],
        "recent_logs": [],
    }


def valid_payload(**updates) -> dict:
    payload = {
        "summary": "建议采用最小封闭",
        "explanation": "警报 A1 风险 0.80，依据航迹 T1 与方案 opt-1。",
        "recommended_option_id": "opt-1",
        "evidence_ids": ["A1", "T1", "det-1", "B1"],
        "uncertainties": [],
        "confidence": "high",
    }
    payload.update(updates)
    return payload


class FakeProvider:
    def __init__(self, provider: str, request_model: str, outputs: list):
        self.provider = provider
        self.request_model = request_model
        self.enabled = True
        self.outputs = list(outputs)
        self.calls: list[tuple[str, list[dict], float]] = []
        self.cancelled = False

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        self.calls.append((system, messages, timeout_s))
        value = self.outputs.pop(0)
        if value == "SLEEP":
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        if isinstance(value, BaseException):
            raise value
        return RawResponse(str(value), self.request_model + "-response")

    async def aclose(self) -> None:
        return None


def test_recommendation_draft_requires_all_six_fields_and_rejects_extra_or_wrong_type():
    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate({})
    for missing in valid_payload():
        payload = valid_payload()
        payload.pop(missing)
        with pytest.raises(ValidationError):
            RecommendationDraft.model_validate(payload)
    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate(valid_payload(evidence_ids="A1"))
    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate({**valid_payload(), "extra": 1})
    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate(valid_payload(summary="   "))
    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate(valid_payload(explanation="\n\t"))


def test_cloud_without_credentials_is_disabled_without_constructing_sdk_client():
    settings = replace(get_settings(), anthropic_api_key=None, anthropic_auth_token=None)
    provider = CloudProvider(settings)
    assert provider.enabled is False
    assert provider._client is None


def test_parse_rejects_non_json_and_all_bad_ids_without_filtering():
    known = {"A1", "T1", "det-1", "B1", "opt-1"}
    with pytest.raises(DraftOutputError, match="不是 JSON"):
        parse_model_draft("```json\n{}\n```", known, {"opt-1"})
    bad = valid_payload(
        recommended_option_id="opt-fake",
        evidence_ids=["A1", "fake-id", "T1"],
    )
    with pytest.raises(DraftOutputError) as exc:
        parse_model_draft(json.dumps(bad, ensure_ascii=False), known, {"opt-1"})
    assert "fake-id" in str(exc.value) and "opt-fake" in str(exc.value)


def test_parse_truncates_only_legal_long_text():
    payload = valid_payload(summary="长" * 100, explanation="长" * 500, uncertainties=["疑" * 80])
    draft = parse_model_draft(
        json.dumps(payload, ensure_ascii=False),
        {"A1", "T1", "det-1", "B1", "opt-1"},
        {"opt-1"},
    )
    assert len(draft.summary) == 60 and len(draft.explanation) == 300
    assert len(draft.uncertainties[0]) == 40
    assert draft.evidence_ids == payload["evidence_ids"]


def test_invalid_cloud_output_retries_once_with_error_then_succeeds():
    async def run():
        cloud = FakeProvider(
            "test-cloud", "cloud-request",
            ["{}", json.dumps(valid_payload(), ensure_ascii=False)],
        )
        local = FakeProvider("test-local", "local-request", [RuntimeError("must not run")])
        settings = replace(
            get_settings(), agent_post_reserve_s=0.01, agent_cloud_budget_s=1.0,
            anthropic_timeout_s=1.0, ollama_timeout_s=1.0,
        )
        router = Router(settings, cloud=cloud, local=local)
        result = await router.generate(sample_context(), deadline=time.perf_counter() + 1.5)
        assert result.model == "cloud" and result.attempts == 2
        assert len(cloud.calls) == 2 and len(local.calls) == 0
        retry_messages = cloud.calls[1][1]
        assert "校验错误" in retry_messages[-1]["content"]
        assert router.health()["providers"]["cloud"]["draft_retries"] == 1

    asyncio.run(run())


def test_offline_skips_cloud_and_uses_local():
    async def run():
        cloud = FakeProvider("test-cloud", "cloud-request", [json.dumps(valid_payload())])
        local = FakeProvider("ollama", "qwen3:1.7b", [json.dumps(valid_payload(), ensure_ascii=False)])
        settings = replace(get_settings(), agent_post_reserve_s=0.01, ollama_timeout_s=1.0)
        router = Router(settings, cloud=cloud, local=local)
        result = await router.generate(sample_context("offline"), deadline=time.perf_counter() + 1.0)
        assert result.model == "local"
        assert cloud.calls == [] and len(local.calls) == 1
        assert router.health()["cloud_skipped_offline"] == 1

    asyncio.run(run())


def test_empty_bad_id_and_non_json_exhaust_retries_then_template():
    async def run():
        bad_id = json.dumps(valid_payload(evidence_ids=["A1", "fake-id"]), ensure_ascii=False)
        cloud = FakeProvider("test-cloud", "cloud-request", ["{}", bad_id])
        local = FakeProvider("ollama", "qwen3:1.7b", ["not-json", "[]"])
        settings = replace(
            get_settings(), agent_post_reserve_s=0.01, agent_cloud_budget_s=1.0,
            anthropic_timeout_s=1.0, ollama_timeout_s=1.0,
        )
        router = Router(settings, cloud=cloud, local=local)
        result = await router.generate(sample_context(), deadline=time.perf_counter() + 1.8)
        assert result.model == "template"
        health = router.health()
        assert health["providers"]["cloud"]["draft_invalid"] == 2
        assert health["providers"]["local"]["draft_invalid"] == 2
        assert health["generated_routes"] == {"cloud": 0, "local": 0, "template": 1}
        assert health["cloud_circuit"]["open"] is False

    asyncio.run(run())


def test_timeout_is_cancelled_before_template_result():
    async def run():
        cloud = FakeProvider("test-cloud", "cloud-request", ["SLEEP"])
        local = FakeProvider("ollama", "qwen3:1.7b", [ConnectionError("offline")])
        settings = replace(
            get_settings(), agent_post_reserve_s=0.01, agent_cloud_budget_s=0.08,
            anthropic_timeout_s=1.0, ollama_timeout_s=0.1,
        )
        router = Router(settings, cloud=cloud, local=local)
        started = time.perf_counter()
        result = await router.generate(sample_context(), deadline=started + 0.2)
        assert result.model == "template"
        assert cloud.cancelled
        assert time.perf_counter() - started < 0.5

    asyncio.run(run())


def test_cloud_failure_opens_short_circuit_and_network_recovery_resets_it():
    async def run():
        good = json.dumps(valid_payload(), ensure_ascii=False)
        cloud = FakeProvider("test-cloud", "cloud-request", [RuntimeError("auth failed"), good])
        local = FakeProvider("ollama", "qwen3:1.7b", [good, good])
        settings = replace(
            get_settings(), agent_post_reserve_s=0.01, agent_cloud_budget_s=0.5,
            anthropic_timeout_s=0.5, ollama_timeout_s=0.5,
        )
        router = Router(settings, cloud=cloud, local=local)
        first = await router.generate(sample_context(), deadline=time.perf_counter() + 1.0)
        second = await router.generate(sample_context(), deadline=time.perf_counter() + 1.0)
        assert first.model == second.model == "local"
        assert len(cloud.calls) == 1, "熔断期间不得反复消耗云端预算"
        router.reset_cloud_circuit()
        third = await router.generate(sample_context(), deadline=time.perf_counter() + 1.0)
        assert third.model == "cloud" and len(cloud.calls) == 2

    asyncio.run(run())


def test_ask_routes_cloud_and_offline_local_with_correct_model_labels():
    async def run():
        cloud = FakeProvider("test-cloud", "cloud-request", ["云端事实回答"])
        local = FakeProvider("ollama", "qwen3:1.7b", ["本地事实回答"])
        settings = replace(get_settings(), anthropic_timeout_s=1.0, ollama_timeout_s=1.0)
        router = Router(settings, cloud=cloud, local=local)
        online = await router.answer(
            "情况？", {"network": "online", "t": 1},
            deadline=time.perf_counter() + 1.0, template_answer="模板",
        )
        offline = await router.answer(
            "情况？", {"network": "offline", "t": 1},
            deadline=time.perf_counter() + 1.0, template_answer="模板",
        )
        assert (online.answer, online.model) == ("云端事实回答", "cloud")
        assert (offline.answer, offline.model) == ("本地事实回答", "local")

    asyncio.run(run())
