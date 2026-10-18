"""Offline C3 budget tests: task eviction, scene-generation invalidation and expired-deadline template
fallback. Historical online Ollama/cancellation/fact-failure cases are in the untracked
acceptance_c4/candidate_json_20261017/test_runtime_events_part2.py.
"""


from __future__ import annotations

import asyncio
import time

from agent.config import load_settings
from agent.main import TaskQueue
from agent.router import Router

MINIMAL_SECURITY_CONTEXT = {
    "kind": "security",
    "t": 0.0,
    "options": [],
    "ranked": [],
    "buoys": {"ok": 10, "down": [], "covering_track": ["B1", "B2", "B3"]},
    "zones": [],
    "recent_logs": [],
}


def _alert_event(seq: int, alert_id: str, risk: float = 0.5) -> dict:
    return {"event": "alert_changed", "seq": seq,
            "data": {"alert": {"id": alert_id, "risk": risk}, "to_level": 2, "from_level": 1}}


def test_duplicate_signature_and_replayed_seq_are_deduped() -> None:
    queue = TaskQueue()
    first = queue.offer_event(_alert_event(1, "A1"))
    assert first is not None
    assert queue.offer_event(_alert_event(2, "A1")) is None  # Deduplicate identical signatures.
    assert queue.offer_event(_alert_event(1, "A1")) is None  # Deduplicate replayed seq.


def test_new_version_invalidates_old_task() -> None:
    queue = TaskQueue()
    old = queue.offer_event(_alert_event(1, "A1", risk=0.5))
    new = queue.offer_event(_alert_event(2, "A1", risk=0.9))
    assert old is not None and new is not None and old is not new
    assert not queue.is_current(old)
    assert queue.is_current(new)


def test_alert_cleared_drops_task_and_invalidates_inflight() -> None:
    queue = TaskQueue()
    task = queue.offer_event(_alert_event(1, "A1"))
    queue.offer_event({"event": "alert_cleared", "seq": 2, "data": {"alert_id": "A1"}})
    assert len(queue) == 0
    assert not queue.is_current(task)


def test_scenario_reset_bumps_generation_and_clears() -> None:
    queue = TaskQueue()
    task = queue.offer_event(_alert_event(1, "A1"))
    generation = queue._generation
    queue.offer_event({"event": "scenario_changed", "seq": 2, "data": {"status": "reset"}})
    assert len(queue) == 0
    assert queue._generation == generation + 1
    assert not queue.is_current(task)


def test_reopen_plan_throttled_within_20s() -> None:
    queue = TaskQueue()
    assert queue.offer_event({"event": "reopen_plan", "seq": 1, "t": 100.0, "data": {"plan_id": "P1"}}) is not None
    assert queue.offer_event({"event": "reopen_plan", "seq": 2, "t": 110.0, "data": {"plan_id": "P2"}}) is None
    assert queue.offer_event({"event": "reopen_plan", "seq": 3, "t": 121.0, "data": {"plan_id": "P3"}}) is not None


def test_take_is_fifo() -> None:
    queue = TaskQueue()
    queue.offer_event(_alert_event(1, "B1"))
    queue.offer_event(_alert_event(2, "B2"))
    first = queue.take()
    assert first is not None and first["alert_id"] == "B1"
    assert len(queue) == 1


def test_expired_deadline_returns_template_without_provider_calls() -> None:
    """Expired deadline directly selects the deterministic template without calling a provider."""
    router = Router(load_settings())
    try:
        started = time.perf_counter()
        result = asyncio.run(router.generate(MINIMAL_SECURITY_CONTEXT, deadline=time.perf_counter()))
        elapsed = time.perf_counter() - started
        assert result is not None and result.model == "template"
        assert result.draft is not None
        assert elapsed < 0.5
        assert router.stats["providers"]["local"]["draft_attempts"] == 0
        assert router.stats["providers"]["cloud"]["draft_attempts"] == 0
    finally:
        asyncio.run(router.aclose())
