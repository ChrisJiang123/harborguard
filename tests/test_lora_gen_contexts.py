"""C4 gen_contexts contract: C3 structure, internal consistency and seeded determinism."""
import pytest
pytestmark = pytest.mark.agent_language("zh")


import json

import pytest

from agent.context import MAX_CONTEXT_BYTES, context_ids
from agent.factcheck import security_selection
from ml.lora.gen_contexts import (
    RISK_WEIGHTS,
    SURVEY_H,
    generate_contexts,
    kind_counts,
    load_world,
    weighted_risk,
)

N = 200


@pytest.fixture(scope="module")
def contexts():
    return generate_contexts(n=N, seed=0)


@pytest.fixture(scope="module")
def world():
    return load_world()


def _raw(context: dict) -> str:
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))


def _by_kind(contexts):
    return {kind: [c for c in contexts if c["kind"] == kind] for kind in ("security", "disaster", "buoy")}


def test_kind_ratios_match_config(contexts):
    counts = kind_counts(N)
    assert counts == {"security": 140, "disaster": 40, "buoy": 20}
    grouped = _by_kind(contexts)
    assert {k: len(v) for k, v in grouped.items()} == counts


def test_same_seed_reproduces_byte_identical_output():
    first = [_raw(c) for c in generate_contexts(n=30, seed=7)]
    second = [_raw(c) for c in generate_contexts(n=30, seed=7)]
    assert first == second
    assert generate_contexts(n=30, seed=7) != generate_contexts(n=30, seed=8)


def test_all_contexts_within_3kb_and_kind_tag(contexts):
    for context in contexts:
        assert context["kind"] in {"security", "disaster", "buoy"}
        assert context["mode"] in {"security", "disaster"}
        assert context["network"] in {"online", "offline"}
        assert len(_raw(context).encode("utf-8")) <= MAX_CONTEXT_BYTES


def test_shared_ids_come_from_real_data(contexts, world):
    real_ids = set(world["zone_ids"]) | set(world["buoy_ids"]) | {a["id"] for a in world["assets"]}
    for context in contexts:
        assert context_ids(context), "上下文必须含有可引用的真实 ID"
        buoys = context["buoys"]
        assert set(buoys["down"]) <= set(world["buoy_ids"])
        for zone in context["zones"]:
            assert zone["id"] in real_ids
        for key in ("down", "covering_track", "ok_ids"):
            assert set(buoys.get(key) or []) <= set(world["buoy_ids"])


def test_security_risk_is_weighted_sum(contexts):
    for context in _by_kind(contexts)["security"]:
        alert = context["alert"]
        breakdown = alert["breakdown"]
        assert set(breakdown) == set(RISK_WEIGHTS)
        assert alert["risk"] == pytest.approx(weighted_risk(breakdown))
        assert context["track"]["risk"] == alert["risk"]
        assert context["track"]["level"] == alert["level"]
        assert alert["level"] in (2, 3)


def test_security_ranked_follows_task_rule(contexts):
    for context in _by_kind(contexts)["security"]:
        option_ids = {o["id"] for o in context["options"]}
        assert set(context["ranked"]) == option_ids
        if not context["options"]:
            assert context["alert"]["options_ready"] is False
            continue
        selection = security_selection(context)
        assert selection.computable
        assert not selection.conflict, "合成数据 ranked[0] 必须与任务书规则一致"
        assert selection.task_rule_option_id == context["ranked"][0]


def test_security_options_use_contract_fields_and_b_rules(contexts, world):
    fields = {
        "id", "label", "is_baseline", "zones_closed", "speed_limit_zones",
        "berths_open_pct", "vessels_affected", "delay_vessel_hours", "residual_risk",
    }
    for context in _by_kind(contexts)["security"]:
        for option in context["options"]:
            assert set(option) == fields
            assert 0.0 <= option["residual_risk"] <= 1.0
            assert 0.0 <= option["berths_open_pct"] <= 1.0
            assert option["delay_vessel_hours"] >= 0.0
            assert set(option["zones_closed"]) <= set(world["zone_ids"])
        if any(o["id"] == "port-closure" for o in context["options"]):
            baseline = next(o for o in context["options"] if o["id"] == "port-closure")
            assert baseline["is_baseline"] and baseline["zones_closed"] == sorted(world["zone_ids"])
    labels = {o["label"] for c in contexts for o in c["options"]}
    assert labels <= {"最小封闭", "扩大缓冲 + 限速", "资产周边封闭", "全港关闭"}


def test_security_buoys_consistent(contexts, world):
    for context in _by_kind(contexts)["security"]:
        buoys = context["buoys"]
        assert set(buoys) == {"ok", "down", "covering_track"}
        assert not (set(buoys["covering_track"]) & set(buoys["down"]))
        assert buoys["ok"] == len(world["buoy_ids"]) - len(buoys["down"])
        # No-options samples train the recommended_option_id = null branch.
    no_options = [c for c in _by_kind(contexts)["security"] if not c["options"]]
    assert no_options, "必须包含 options_ready 之前的无方案样本"


def test_disaster_plan_internally_consistent(contexts, world):
    for context in _by_kind(contexts)["disaster"]:
        plan = context["reopen_plan"]
        assert set(plan) == {
            "route_zone_ids", "reopen_berth_zone_ids", "unsurveyed_zone_ids",
            "blocked_zone_ids", "est_hours_saved",
        }
        blocked = set(plan["blocked_zone_ids"])
        unsurveyed = set(plan["unsurveyed_zone_ids"])
        route = set(plan["route_zone_ids"])
        assert not (route & blocked) and not (route & unsurveyed)
        assert set(plan["reopen_berth_zone_ids"]) <= route
        assert set(plan["reopen_berth_zone_ids"]) <= set(world["berth_zones"])
        surveyed = len(world["zone_ids"]) - len(unsurveyed) - len(blocked)
        assert plan["est_hours_saved"] == pytest.approx(surveyed * SURVEY_H)
        states = {z["id"]: z["state"] for z in context["zones"]}
        for zid, state in states.items():
            expected = "blocked" if zid in blocked else "unsurveyed" if zid in unsurveyed else "clear"
            assert state == expected
        assert context["options"] == [] and context["ranked"] == []


def test_buoy_impact_uses_real_geometry(contexts, world):
    for context in _by_kind(contexts)["buoy"]:
        assert context["buoy"]["status"] == "down"
        assert context["buoy"]["id"] in context["buoys"]["down"]
        impact = context["coverage_impact"]
        assert impact["method"] == "buoy_range_intersects_zone_geometry"
        affected = impact["affected_zone_ids"]
        assert set(affected) <= set(world["zone_ids"])
        assert set(impact["remaining_ok_buoy_ids_by_zone"]) == set(affected)
        for zone_ids in impact["remaining_ok_buoy_ids_by_zone"].values():
            assert not (set(zone_ids) & set(context["buoys"]["down"]))
        assert {z["id"] for z in context["zones"]} <= set(affected)
        assert context["options"] == [] and context["ranked"] == []


def test_diversity_guards_exist(contexts):
    security = _by_kind(contexts)["security"]
    assert any(c["network"] == "offline" for c in contexts)
    assert any(len(c["buoys"]["down"]) > 0 for c in security)
    assert any(len(c["buoys"]["covering_track"]) <= 1 for c in security)
    assert any((c["track"]["conf"] or 1.0) < 0.6 for c in security)
    assert any(c["track"]["cls"] == "unknown" for c in security)
    assert any("port-closure" in c["ranked"] for c in security)
