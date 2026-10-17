"""Agent C3 阶段一测试：地址构造 / 事件队列 / 上下文计算 / 模板 / 双重校验。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.backend_client import BackendClient, api_url, normalize_base, ws_url  # noqa: E402
from agent.context import MAX_CONTEXT_BYTES, context_ids, history_summary  # noqa: E402
from agent.main import TaskQueue  # noqa: E402
from agent.schemas import RecommendationDraft, normalize_draft, validate_draft  # noqa: E402
from agent.template import generate_answer, generate_security  # noqa: E402


# ---------------------------------------------------------------- 地址构造

def test_api_url_exactly_one_api_prefix():
    assert api_url("http://localhost:8000", "alerts/A1") == "http://localhost:8000/api/alerts/A1"
    assert api_url("http://localhost:8000/", "/api/alerts/A1") == "http://localhost:8000/api/alerts/A1"
    assert api_url("http://localhost:8000/api/", "alerts/A1") == "http://localhost:8000/api/alerts/A1"
    assert api_url("http://localhost:8000/api", "api/alerts/A1") == "http://localhost:8000/api/alerts/A1"
    assert api_url("http://localhost:8000", "log?limit=10") == "http://localhost:8000/api/log?limit=10"


def test_ws_url_derivation():
    assert ws_url("http://localhost:8000", None) == "ws://localhost:8000/ws"
    assert ws_url("http://localhost:8000", "") == "ws://localhost:8000/ws"
    assert ws_url("http://localhost:8000", "ws://localhost:8000/ws") == "ws://localhost:8000/ws"
    assert ws_url("https://demo.example.com", None) == "wss://demo.example.com/ws"


def test_stream_events_initial_recovery_accepts_sync_callback(monkeypatch):
    """首次连接也补事件；main.handle_event 是同步函数，客户端不得错误 await None。"""
    class EmptyWebSocket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def __aiter__(self):
            async def empty():
                if False:
                    yield None
            return empty()

    async def run():
        client = BackendClient()
        stop = asyncio.Event()
        received = []

        async def get_state():
            return {"seq": 7}

        async def get_events(since_seq):
            assert since_seq == 0
            return [_opts_ready(7)]

        client.get_state = get_state
        client.get_events = get_events
        monkeypatch.setattr("agent.backend_client.websockets.connect", lambda *a, **k: EmptyWebSocket())

        def callback(msg):
            received.append(msg["seq"])
            stop.set()

        await client.stream_events(callback, stop=stop, reconnect_delay_s=0)
        await client.aclose()
        assert received == [7]

    asyncio.run(run())


# ---------------------------------------------------------------- 事件队列

def _opts_ready(seq, alert_id="A1", ranked=("opt-1",), opts=("opt-1",)):
    return {"type": "event", "seq": seq, "t": 1.0, "event": "options_ready",
            "data": {"alert_id": alert_id, "ranked": list(ranked),
                     "options": [{"id": o} for o in opts]}}


def test_task_queue_dedup_and_coalesce():
    q = TaskQueue()
    assert q.offer_event(_opts_ready(1)) is not None
    assert q.offer_event(_opts_ready(1)) is None, "同 seq 事件必须去重"
    assert q.offer_event(_opts_ready(2)) is None, "同警报同方案集不得重复入队"
    assert q.offer_event(_opts_ready(3, ranked=("opt-2", "opt-1"))) is not None, "新方案集可触发新建议"
    assert len(q) == 1, "同警报只保留最新任务"
    task = q.take()
    assert task["ranked"] == ["opt-2", "opt-1"]
    assert q.is_current(task)
    assert q.offer_event(_opts_ready(4, ranked=("opt-2", "opt-1"))) is None, (
        "已取出/已处理的相同载荷也必须去重"
    )
    assert q.take() is None


def test_task_queue_changed_payload_supersedes_inflight():
    q = TaskQueue()
    first = _opts_ready(1)
    first["data"]["options"][0]["residual_risk"] = 0.7
    old_task = q.offer_event(first)
    assert q.take() == old_task and q.is_current(old_task)

    changed = _opts_ready(2)
    changed["data"]["options"][0]["residual_risk"] = 0.1
    new_task = q.offer_event(changed)
    assert new_task is not None, "方案 ID 不变但指标变化时必须处理最新载荷"
    assert not q.is_current(old_task), "处理中旧任务必须失效"
    assert q.is_current(new_task)


def test_task_queue_multi_alert_and_clear():
    q = TaskQueue()
    q.offer_event(_opts_ready(1, alert_id="A1"))
    q.offer_event(_opts_ready(2, alert_id="A2"))
    assert len(q) == 2
    q.offer_event({"type": "event", "seq": 3, "t": 2.0, "event": "alert_cleared",
                   "data": {"alert_id": "A1"}})
    assert len(q) == 1, "已清除警报的旧任务必须丢弃"
    q.offer_event({"type": "event", "seq": 4, "t": 3.0, "event": "scenario_changed",
                   "data": {"scenario": "a", "status": "reset"}})
    assert len(q) == 0, "场景重置必须清空全部待处理任务"
    stale = q.offer_event(_opts_ready(5, alert_id="A9"))
    q.offer_event({"type": "event", "seq": 6, "t": 4.0, "event": "scenario_changed",
                   "data": {"scenario": "b", "status": "started"}})
    assert len(q) == 0, "新场景开始同样清空旧任务，不得提交旧场景建议"
    assert not q.is_current(stale), "已从队列取出或正在处理的旧场景任务也必须失效"


# ---------------------------------------------------------------- 上下文计算

def test_history_summary_metrics():
    # 直线匀深：直度 1.0，深度 std 0
    straight = [[0.0, 0.0, 10.0, 0], [0.001, 0.001, 10.0, 30], [0.002, 0.002, 10.0, 60]]
    s = history_summary(straight, t_now=60)
    assert s["straightness"] == 1.0 and s["depth_std_m"] == 0.0
    # 转弯路径：弦长 < 路径长 → 直度 < 1；窗口外的旧点不计入
    turning = [[0.0, 0.0, 10.0, 0], [0.01, 0.0, 12.0, 30], [0.0, 0.01, 8.0, 55], [0.0, 0.0, 99.0, 500]]
    s2 = history_summary(turning, t_now=60)
    assert 0.0 < s2["straightness"] < 1.0
    assert s2["depth_std_m"] > 0
    # 近 60 秒深度 [10,12,8] 的总体标准差（与 np.std 一致）；窗口外的 99 不得计入
    assert abs(s2["depth_std_m"] - 1.633) < 0.01, "60 秒窗口外的点(深度99)不得参与统计"


def test_context_ids_collects_real_ids():
    ctx = {
        "alert": {"id": "A1"}, "track": {"id": "T7", "detection_id": "det-4"},
        "detections": [{"id": "det-4"}],
        "options": [{"id": "opt-1"}, {"id": "opt-2"}], "ranked": ["opt-1", "port-closure"],
        "buoys": {"ok": 3, "down": ["B4"], "covering_track": ["B3", "B5"]},
        "zones": [{"id": "zone-B2"}],
    }
    ids = context_ids(ctx)
    for expected in {"A1", "T7", "det-4", "opt-1", "opt-2", "port-closure", "B3", "B5", "B4", "zone-B2"}:
        assert expected in ids


# ---------------------------------------------------------------- 模板与校验

def _sample_context():
    return {
        "kind": "security", "t": 312.0, "mode": "security", "network": "online",
        "alert": {"id": "A3", "level": 3, "risk": 0.80,
                  "breakdown": {"C": 0.87, "P": 0.80, "B": 0.75, "Z": 0.90, "D": 0.30},
                  "track_id": "T7"},
        "track": {"id": "T7", "cls": "uuv", "conf": 0.87, "depth_m": 12.1, "speed_mps": 2.0},
        "detections": [{"id": "det-4", "cls": "uuv", "conf": 0.87, "model": "stub"}],
        "options": [
            {"id": "opt-1", "label": "限速通行", "zones_closed": [], "vessels_affected": 2,
             "delay_vessel_hours": 0.5, "residual_risk": 0.18},
            {"id": "opt-2", "label": "关闭泊位", "zones_closed": ["zone-B2"], "vessels_affected": 6,
             "delay_vessel_hours": 3.0, "residual_risk": 0.10},
        ],
        "ranked": ["opt-1", "opt-2"],
        "buoys": {"ok": 10, "down": [], "covering_track": ["B3", "B5"]},
        "zones": [{"id": "zone-B2", "state": "open"}],
        "recent_logs": ["log1"],
    }


def test_template_recommends_first_valid_ranked():
    ctx = _sample_context()
    draft = normalize_draft(generate_security(ctx))
    assert draft.recommended_option_id == "opt-1", "必须推荐有效 ranked 的首个方案"
    assert len(draft.summary) <= 60 and len(draft.explanation) <= 300
    assert draft.confidence == "high", "证据充分且残余风险 <= 0.2"
    ids = context_ids(ctx)
    assert set(draft.evidence_ids) <= ids, "evidence 必须全部来自上下文真实 ID"
    assert "A3" in draft.evidence_ids and "T7" in draft.evidence_ids
    errors = validate_draft(draft, ids, {o["id"] for o in ctx["options"]})
    assert errors == []


def test_template_weak_evidence_and_no_options():
    ctx = _sample_context()
    ctx["track"]["conf"] = 0.4
    ctx["buoys"] = {"ok": 10, "down": ["B4"], "covering_track": ["B3"]}
    draft = normalize_draft(generate_security(ctx))
    assert draft.confidence == "low"
    assert any("置信度" in u for u in draft.uncertainties)
    assert any("浮标" in u for u in draft.uncertainties)

    no_opts = _sample_context()
    no_opts["options"], no_opts["ranked"] = [], []
    d2 = normalize_draft(generate_security(no_opts))
    assert d2.recommended_option_id is None, "无可用方案必须返回 null"
    assert d2.confidence == "low"
    assert validate_draft(d2, context_ids(no_opts), set()) == []


def test_validate_draft_catches_fake_ids():
    draft = RecommendationDraft(
        summary="x", explanation="y", recommended_option_id="opt-99",
        evidence_ids=["A3", "fake-buoy"], uncertainties=[], confidence="low",
    )
    ctx = _sample_context()
    errors = validate_draft(draft, context_ids(ctx), {o["id"] for o in ctx["options"]})
    assert any("fake-buoy" in e for e in errors)
    assert any("opt-99" in e for e in errors)


def test_normalize_draft_truncates():
    draft = normalize_draft({
        "summary": "长" * 100, "explanation": "长" * 500,
        "recommended_option_id": None, "evidence_ids": ["A1", "A1"],
        "uncertainties": ["u" * 100], "confidence": "low",
    })
    assert len(draft.summary) <= 60 and draft.summary.endswith("…")
    assert len(draft.explanation) <= 300
    assert draft.recommended_option_id is None
    assert draft.evidence_ids == ["A1", "A1"], "规范化不得删除或改写模型给出的 ID"
    assert all(len(u) <= 40 for u in draft.uncertainties)


def test_context_stays_under_3kb():
    ctx = _sample_context()
    ctx["recent_logs"] = ["长日志" * 200] * 20
    ctx["zones"] = [{"id": f"zone-{i}", "state": "open", "coverage": 0.5} for i in range(50)]
    from agent.context import _trim
    trimmed = _trim(ctx)
    encoded = json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(encoded) <= MAX_CONTEXT_BYTES


def test_ask_template_answer_uses_backend_facts():
    state = {"t": 312.0, "alerts": [{"id": "A3", "level": 3, "risk": 0.8}]}
    track = {"id": "T7", "cls": "uuv", "conf": 0.87, "depth_m": 12.1, "speed_mps": 2.0}
    answer = generate_answer("现在什么情况？", track=track, state=state)
    assert "T7" in answer and "0.87" in answer and "A3" in answer and len(answer) <= 150
    fallback = generate_answer("?", track=None, state=None)
    assert "后端数据暂不可用" not in fallback and len(fallback) <= 150
