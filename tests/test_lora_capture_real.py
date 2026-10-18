"""C4 capture_real: event routing, latest-per-alert, key deduplication and append."""

import asyncio
import json

import pytest

import ml.lora.capture_real as cap
from ml.lora.capture_real import RealContextCapture, write_contexts


def _security_context(alert_id: str) -> dict:
    return {
        "kind": "security", "t": 10.0, "mode": "security", "network": "online",
        "alert": {"id": alert_id}, "track": None, "detections": [],
        "options": [], "ranked": [], "buoys": {"ok": 10, "down": [], "covering_track": []},
        "zones": [], "recent_logs": [],
    }


@pytest.fixture()
def patched_collectors(monkeypatch):
    async def fake_security(client, alert_id, options=None, ranked=None):
        return _security_context(alert_id)

    async def fake_disaster(client, plan):
        return {"kind": "disaster", "t": 1.0, "mode": "disaster", "network": "online",
                "reopen_plan": plan, "buoys": {"ok": 10, "ok_ids": [], "down": []},
                "zones": [], "options": [], "ranked": [], "recent_logs": []}

    async def fake_buoy(client, buoy_id):
        return {"kind": "buoy", "t": 1.0, "mode": "security", "network": "online",
                "buoy": {"id": buoy_id, "status": "down", "range_m": 600},
                "buoys": {"ok": 9, "ok_ids": ["B1"], "down": [buoy_id]},
                "coverage_impact": {"method": "buoy_range_intersects_zone_geometry",
                                    "affected_zone_ids": [], "remaining_ok_buoy_ids_by_zone": {}},
                "zones": [], "options": [], "ranked": [], "recent_logs": []}

    monkeypatch.setattr(cap, "collect_security", fake_security)
    monkeypatch.setattr(cap, "collect_disaster", fake_disaster)
    monkeypatch.setattr(cap, "collect_buoy", fake_buoy)


def test_event_routing_and_latest_alert_wins(patched_collectors):
    async def run():
        capture = RealContextCapture()
        client = object()
        await capture.handle_event(client, {"event": "options_ready",
                                            "data": {"alert_id": "A1", "options": [], "ranked": []}})
        await capture.handle_event(client, {"event": "options_ready",
                                            "data": {"alert_id": "A1"}})  # Replace older with newer.
        await capture.handle_event(client, {"event": "alert_changed",
                                            "data": {"alert": {"id": "A1"}, "to_level": 1}})  # Not rising to L2: ignore.
        await capture.handle_event(client, {"event": "buoy_changed",
                                            "data": {"buoy_id": "B4", "status": "ok"}})  # Not down: ignore.
        await capture.flush_security(client)
        assert capture.counts["security"] == 2  # Collect both triggers; live runtime triggers only on changed signature.
        security_keys = {k for k, ctx in capture.by_key.items() if ctx["kind"] == "security"}
        assert len(security_keys) == 1  # Identical payloads deduplicate by key.
        await capture.handle_event(client, {"event": "options_ready", "data": {"alert_id": "A2"}})
        await capture.handle_event(client, {"event": "scenario_changed", "data": {"status": "reset"}})
        await capture.flush_security(client)
        # Flush each event: A2 was collected before reset; reset does not erase collected data.
        assert capture.counts["security"] == 3
        security_keys = {k for k, ctx in capture.by_key.items() if ctx["kind"] == "security"}
        assert len(security_keys) == 2
        await capture.handle_event(client, {"event": "reopen_plan", "data": {"route_zone_ids": ["z1"]}})
        await capture.handle_event(client, {"event": "buoy_changed",
                                            "data": {"buoy_id": "B4", "status": "down"}})
        assert capture.counts["event:options_ready"] == 3  # Diagnostic count of every event.
        return capture

    capture = asyncio.run(run())
    kinds = {ctx["kind"] for ctx in capture.by_key.values()}
    assert kinds == {"security", "disaster", "buoy"}
    assert capture.counts["disaster"] == 1 and capture.counts["buoy"] == 1


def test_write_contexts_appends_only_new_keys(patched_collectors, tmp_path):
    async def run():
        capture = RealContextCapture()
        client = object()
        await capture.handle_event(client, {"event": "options_ready", "data": {"alert_id": "A2"}})
        await capture.handle_event(client, {"event": "reopen_plan", "data": {"route_zone_ids": []}})
        return capture

    capture = asyncio.run(run())
    out = tmp_path / "real_contexts.jsonl"
    added, skipped = write_contexts(capture.by_key, out)
    assert added == 2 and skipped == 0
    added2, skipped2 = write_contexts(capture.by_key, out)
    assert added2 == 0 and skipped2 == 2
    lines = [json.loads(l) for l in out.open(encoding="utf-8") if l.strip()]
    assert {l["kind"] for l in lines} == {"security", "disaster"}
