"""Agent C3 第三阶段：事实检查、事件触发、上下文与模板。"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import replace

from agent.config import get_settings
from agent.context import collect_buoy, collect_disaster, context_ids
from agent.factcheck import check_draft_facts, security_selection
from agent.main import TaskQueue
from agent.router import RawResponse, Router
from agent.schemas import RecommendationDraft, validate_draft
from agent.template import generate_recommendation, generate_security


def context(**updates) -> dict:
    value = {
        "kind": "security",
        "t": 10.0,
        "mode": "security",
        "network": "offline",
        "alert": {"id": "A1", "level": 3, "risk": 0.8, "breakdown": {"C": 0.8}},
        "track": {"id": "T1", "cls": "uuv", "conf": 0.83},
        "detections": [],
        "options": [{
            "id": "opt-1", "label": "最小封闭", "delay_vessel_hours": 1.5,
            "residual_risk": 0.1, "zones_closed": ["zone-1"], "vessels_affected": 1,
        }],
        "ranked": ["opt-1"],
        "buoys": {"ok": 2, "ok_ids": ["B1", "B2"], "down": [], "covering_track": ["B1", "B2"]},
        "zones": [{"id": "zone-1", "state": "open", "coverage": 0.5}],
        "recent_logs": [],
    }
    value.update(updates)
    return value


def draft(**updates) -> RecommendationDraft:
    value = {
        "summary": "建议采用 opt-1",
        "explanation": "没有浮标离线，2 个浮标覆盖，识别置信度 0.83。",
        "recommended_option_id": "opt-1",
        "evidence_ids": ["A1", "T1"],
        "uncertainties": [],
        "confidence": "high",
    }
    value.update(updates)
    return RecommendationDraft.model_validate(value)


def test_offline_contradiction_is_rejected_but_legal_negation_is_preserved():
    good = check_draft_facts(draft(), context())
    assert good.ok, good.errors
    bad = draft(explanation="部分浮标离线，2 个浮标覆盖，识别置信度 0.83。")
    checked = check_draft_facts(bad, context())
    assert any("离线列表为空" in error for error in checked.errors)
    for sentence in ("无离线浮标。", "浮标没有离线。", "所有浮标均在线。", "B1 在线。"):
        negative = draft(explanation=f"{sentence}2 个浮标覆盖，识别置信度 0.83。")
        assert check_draft_facts(negative, context()).ok, sentence


def test_offline_count_and_all_ids_must_match_context():
    ctx = context(buoys={"ok": 1, "ok_ids": ["B3"], "down": ["B1", "B2"], "covering_track": ["B3"]})
    good = draft(
        explanation="浮标离线 2 个（B1,B2），1 个浮标覆盖，识别置信度 0.83。",
        uncertainties=["浮标离线 2 个（B1,B2）", "仅 1 个浮标覆盖，定位证据不足"],
        confidence="low",
    )
    assert check_draft_facts(good, ctx).ok
    bad = draft(
        explanation="浮标离线 1 个（B1），1 个浮标覆盖，识别置信度 0.83。",
        uncertainties=["浮标离线 1 个（B1）", "仅 1 个浮标覆盖，定位证据不足"],
        confidence="low",
    )
    errors = check_draft_facts(bad, ctx).errors
    assert any("数量" in error for error in errors)
    assert any("ID" in error for error in errors)


def test_single_offline_id_statement_is_valid_when_uncertainty_has_complete_total():
    ctx = context(buoys={"ok": 1, "ok_ids": ["B3"], "down": ["B1"], "covering_track": ["B3"]})
    good = draft(
        summary="B1 浮标离线，需核实覆盖影响",
        explanation="B1 离线，1 个浮标覆盖，识别置信度 0.83。",
        uncertainties=["1 个浮标离线：B1", "仅 1 个浮标覆盖，定位证据不足"],
        confidence="low",
    )
    assert check_draft_facts(good, ctx).ok
    bad = good.model_copy(update={"summary": "B9 浮标离线，需核实覆盖影响"})
    assert any("ID" in error for error in check_draft_facts(bad, ctx).errors)


def test_covering_confidence_and_option_numbers_cannot_be_invented():
    bad = draft(
        explanation="没有浮标离线，1 个浮标覆盖，识别置信度 0.40，残余风险 0.70，延误 9 小时。"
    )
    errors = check_draft_facts(bad, context()).errors
    assert any("覆盖浮标数量" in error for error in errors)
    assert any("识别置信度" in error for error in errors)
    assert any("残余风险" in error for error in errors)
    assert any("方案延误" in error for error in errors)
    options = [
        {"id": "opt-1", "label": "甲", "delay_vessel_hours": 1.5, "residual_risk": 0.1},
        {"id": "opt-2", "label": "乙", "delay_vessel_hours": 8.0, "residual_risk": 0.2},
    ]
    misattributed = draft(explanation="opt-1 残余风险 0.20、延误 8 小时。")
    errors = check_draft_facts(misattributed, context(options=options, ranked=["opt-1", "opt-2"])).errors
    assert any("残余风险" in error for error in errors)
    assert any("方案延误" in error for error in errors)


def test_missing_facts_are_unknown_not_zero_or_normal():
    ctx = context(track={"id": "T1", "cls": "uuv"}, buoys={})
    generated = generate_security(ctx)
    text = "。".join([generated.summary, generated.explanation, *generated.uncertainties])
    assert "置信度未知" in text or "置信度数据缺失" in text
    assert "覆盖数量未知" in text or "覆盖数据缺失" in text
    assert "离线情况未知" in text
    assert generated.confidence == "low"
    assert check_draft_facts(generated, ctx).ok

    all_down = context(buoys={"ok": 0, "ok_ids": [], "down": [f"B{i}" for i in range(1, 11)],
                                "covering_track": []})
    generated = generate_security(all_down)
    assert len(generated.uncertainties[0]) <= 40
    assert check_draft_facts(generated, all_down).ok


def test_selection_rule_and_ranked_conflict_are_both_reported():
    options = [
        {"id": "opt-a", "delay_vessel_hours": 5.0, "residual_risk": 0.1},
        {"id": "opt-b", "delay_vessel_hours": 1.0, "residual_risk": 0.15},
    ]
    ctx = context(options=options, ranked=["opt-a", "opt-b"])
    selection = security_selection(ctx)
    assert selection.task_rule_option_id == "opt-b"
    assert selection.ranked_option_id == "opt-a" and selection.conflict
    missing_report = draft(recommended_option_id="opt-b")
    assert any("必须在 uncertainties 报告差异" in e for e in check_draft_facts(missing_report, ctx).errors)
    reported = draft(
        recommended_option_id="opt-b",
        uncertainties=["任务规则 opt-b 与后端排序 opt-a 存在差异"],
    )
    assert check_draft_facts(reported, ctx).ok


def test_no_options_and_nonsecurity_kinds_require_null_option():
    no_options = context(options=[], ranked=[])
    assert any("没有 options" in e for e in check_draft_facts(draft(), no_options).errors)
    for kind in ("disaster", "buoy"):
        ctx = context(kind=kind, options=[], ranked=[], track=None)
        assert any(kind in e for e in check_draft_facts(draft(), ctx).errors)


class FakeProvider:
    def __init__(self, outputs: list[str]):
        self.provider = "fake"
        self.request_model = "fake-model"
        self.enabled = True
        self.outputs = list(outputs)
        self.calls = 0

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        self.calls += 1
        return RawResponse(self.outputs.pop(0), "fake-response")

    async def aclose(self) -> None:
        return None


def _raw(**updates) -> str:
    payload = draft().model_dump()
    payload.update(updates)
    return json.dumps(payload, ensure_ascii=False)


def test_fact_contradiction_retries_once_and_saves_sanitized_sample(tmp_path):
    async def run():
        provider = FakeProvider([
            _raw(explanation="部分浮标离线，2 个浮标覆盖，识别置信度 0.83。"),
            _raw(),
        ])
        disabled_cloud = FakeProvider([])
        disabled_cloud.enabled = False
        settings = replace(
            get_settings(), agent_failure_log=str(tmp_path / "failures.jsonl"),
            agent_post_reserve_s=0.01, ollama_timeout_s=1.0,
        )
        router = Router(settings, cloud=disabled_cloud, local=provider)
        result = await router.generate(context(), deadline=time.perf_counter() + 1.0)
        assert result.model == "local" and result.attempts == 2
        health = router.health()["providers"]["local"]
        assert health["draft_raw_valid"] == 2
        assert health["draft_fact_invalid"] == 1
        assert health["draft_fact_valid"] == 1
        assert health["draft_retry_success"] == 1
        saved = (tmp_path / "failures.jsonl").read_text(encoding="utf-8")
        assert "部分浮标离线" in saved
        assert '"A1"' not in saved and '"T1"' not in saved
        assert "anthropic" not in saved.lower()

    asyncio.run(run())


def test_two_fact_failures_use_validated_template_and_do_not_count_model_success(tmp_path):
    async def run():
        provider = FakeProvider([
            _raw(explanation="部分浮标离线，2 个浮标覆盖，识别置信度 0.83。"),
            _raw(explanation="浮标离线 1 个（B9），2 个浮标覆盖，识别置信度 0.83。"),
        ])
        disabled_cloud = FakeProvider([])
        disabled_cloud.enabled = False
        settings = replace(
            get_settings(), agent_failure_log=str(tmp_path / "failures.jsonl"),
            agent_post_reserve_s=0.01, ollama_timeout_s=1.0,
        )
        router = Router(settings, cloud=disabled_cloud, local=provider)
        result = await router.generate(context(), deadline=time.perf_counter() + 1.0)
        assert result.model == "template"
        health = router.health()
        assert health["providers"]["local"]["success"] == 0
        assert health["providers"]["local"]["draft_fact_invalid"] == 2
        assert health["generated_routes"] == {"cloud": 0, "local": 0, "template": 1}
        assert health["template_fallbacks"] == 1
        assert check_draft_facts(result.draft, context()).ok

    asyncio.run(run())


def event(seq: int, t: float, name: str, data: dict) -> dict:
    return {"type": "event", "seq": seq, "t": t, "event": name, "data": data}


def test_new_event_triggers_dedup_throttle_and_reset():
    queue = TaskQueue()
    alert = {"id": "A2", "level": 2, "risk": 0.4}
    level2 = queue.offer_event(event(1, 1, "alert_changed", {"alert": alert, "from_level": 1, "to_level": 2}))
    assert level2 and level2["kind"] == "security" and level2["options"] == []
    queue.offer_event(event(2, 2, "alert_changed", {"alert": {**alert, "level": 3}, "from_level": 2, "to_level": 3}))
    assert not queue.is_current(level2)

    down = queue.offer_event(event(3, 3, "buoy_changed", {"buoy_id": "B4", "status": "down"}))
    assert down and down["kind"] == "buoy"
    assert queue.offer_event(event(4, 4, "buoy_changed", {"buoy_id": "B4", "status": "down"})) is None
    queue.offer_event(event(5, 5, "buoy_changed", {"buoy_id": "B4", "status": "ok"}))
    assert not queue.is_current(down)

    plan1 = {"route_zone_ids": [], "reopen_berth_zone_ids": [], "unsurveyed_zone_ids": ["z1"],
             "blocked_zone_ids": [], "est_hours_saved": 0}
    plan2 = {**plan1, "unsurveyed_zone_ids": ["z1", "z2"]}
    first = queue.offer_event(event(6, 10, "reopen_plan", plan1))
    assert first and first["kind"] == "disaster"
    assert queue.offer_event(event(7, 29.9, "reopen_plan", plan2)) is None
    second = queue.offer_event(event(8, 30, "reopen_plan", plan2))
    assert second is not None
    assert queue.offer_event(event(9, 60, "reopen_plan", plan2)) is None
    queue.offer_event(event(10, 61, "scenario_changed", {"scenario": "b", "status": "reset"}))
    assert not queue.is_current(second) and len(queue) == 0
    assert queue.offer_event(event(6, 1, "reopen_plan", plan2)) is not None, "reset 必须清理 seq 与载荷去重"


class FakeClient:
    async def get_state(self):
        return {
            "t": 42.0, "mode": "disaster", "network": "offline",
            "zones": [{"id": "z1", "state": "unsurveyed", "coverage": 0.2}],
        }

    async def get_buoys(self):
        return [
            {"id": "B1", "lat": 33.73, "lon": -118.26, "status": "down", "range_m": 600},
            {"id": "B2", "lat": 33.7301, "lon": -118.2601, "status": "ok", "range_m": 600},
        ]

    async def get_zones(self):
        return {
            "features": [{
                "properties": {"id": "z1"},
                "geometry": {"type": "Polygon", "coordinates": [[
                    [-118.261, 33.729], [-118.259, 33.729], [-118.259, 33.731],
                    [-118.261, 33.731], [-118.261, 33.729],
                ]]},
            }]
        }


def test_disaster_and_buoy_contexts_and_templates_keep_real_ids():
    async def run():
        client = FakeClient()
        plan = {"route_zone_ids": [], "reopen_berth_zone_ids": [], "unsurveyed_zone_ids": ["z1"],
                "blocked_zone_ids": [], "est_hours_saved": 0}
        disaster = await collect_disaster(client, plan)
        buoy = await collect_buoy(client, "B1")
        assert disaster["reopen_plan"] == plan and disaster["zones"][0]["id"] == "z1"
        assert buoy["coverage_impact"]["affected_zone_ids"] == ["z1"]
        assert buoy["coverage_impact"]["remaining_ok_buoy_ids_by_zone"]["z1"] == ["B2"]
        for ctx in (disaster, buoy):
            generated = generate_recommendation(ctx)
            assert generated.recommended_option_id is None
            assert not validate_draft(generated, context_ids(ctx), set())
            assert check_draft_facts(generated, ctx).ok

        assert "状态异常" in generate_recommendation(buoy).summary

    asyncio.run(run())
