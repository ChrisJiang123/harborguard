"""Real tracking + explicit B stub recognition positive controls, without truth tracks.

The original timing/four-debris expectations describe B's self-contained stub.
Real C weights have separate conservative acceptance; do not silently select a
different detector merely because weights/dependencies happen to be installed.
"""
import hashlib
import json
from collections import Counter

import pytest
from PIL import Image

from backend.app import config
from backend.app.engine import GameEngine
from backend.app.models import EventMsg, StateMsg
from backend.tools.record import record


@pytest.fixture(scope="module", autouse=True)
def explicit_stub_recognition():
    from backend.app.perception import classifier as adapter

    original = adapter.SonarClassifier
    with pytest.MonkeyPatch.context() as patch:
        def stub(*args, **kwargs):
            kwargs["weights"] = config.ROOT / "artifacts/explicitly-absent-stub-weights.pt"
            result = original(*args, **kwargs)
            result.renderer = None
            return result
        patch.setattr(adapter, "SonarClassifier", stub)
        yield


@pytest.fixture(scope="module")
def scenario_runs():
    results = {}
    for sid in ("a","b"):
        game = GameEngine(debug_truth=False)
        events = []
        game.bus.listeners.append(lambda msg, sink=events: sink.append(msg) if msg["type"] == "event" else None)
        game.start(sid,10)
        max_bytes = 0
        while not game._ended:
            game.step(1)
            snapshot = game.state()
            max_bytes = max(max_bytes,len(snapshot.model_dump_json().encode()))
            assert all(len(track.history) <= 60 for track in snapshot.tracks)
        for event in events:
            EventMsg.model_validate(event)
        results[sid] = game,events,max_bytes
    return results


def test_security_scene_timing_options_and_manual_approval(scenario_runs):
    game,events,max_bytes = scenario_runs["a"]
    first = {}
    for msg in events:
        if msg["event"] in ("alert_raised","alert_changed"):
            first.setdefault(msg["data"]["alert"]["level"],msg["t"])
    assert first[1] <= 50
    assert 150 <= first[2] <= 250
    assert 400 <= first[3] <= 500
    ready = next(msg for msg in events if msg["event"] == "options_ready")
    assert 0 <= ready["t"]-first[3] <= 1
    options = ready["data"]["options"]
    assert sum(not option["is_baseline"] for option in options) >= 2
    baseline = next(option for option in options if option["is_baseline"])
    assert baseline["berths_open_pct"] == 0
    assert baseline["delay_vessel_hours"] == max(option["delay_vessel_hours"] for option in options)
    assert not any(zone["state"] == "restricted" for zone in game.decision.zone_statuses.values())
    assert any(msg["event"] == "detection" and msg["data"]["detection"]["cls"] == "uuv" for msg in events)
    assert max_bytes < config.MAX_STATE_BYTES


def test_disaster_scene_faults_detection_and_connected_reopening(scenario_runs):
    game,events,max_bytes = scenario_runs["b"]
    detections = [msg for msg in events if msg["event"] == "detection"]
    assert len(detections) == 4
    assert all(msg["data"]["detection"]["cls"] == "debris" for msg in detections)
    assert not game.decision.alerts
    assert not any(msg["event"].startswith("alert_") for msg in events)
    downs = [msg for msg in events if msg["event"] == "buoy_changed"]
    assert {(msg["t"],msg["data"]["buoy_id"]) for msg in downs} == {(60,"B4"),(60,"B7")}
    assert Counter(z["state"] for z in game.decision.zone_statuses.values()) == {
        "clear":6,"blocked":4,"unsurveyed":2}
    plan = game.decision.reopen_plan
    assert plan["route_zone_ids"] and plan["reopen_berth_zone_ids"]
    assert plan["unsurveyed_zone_ids"] and plan["blocked_zone_ids"]
    assert max_bytes < config.MAX_STATE_BYTES


@pytest.mark.parametrize("scenario",["a","b"])
def test_full_replay_deterministic_and_self_contained(tmp_path, scenario):
    hashes = []
    signatures = []
    for repeat in (1,2):
        destination = tmp_path/str(repeat)/f"replay_{scenario}.jsonl"
        summary = record(scenario,10,destination)
        assert summary["max_state_bytes"] < config.MAX_STATE_BYTES
        previous_ms,previous_seq = -1,-1
        signature = []
        with destination.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                msg = row["msg"]
                assert row["wall_ms"] >= previous_ms
                assert msg["seq"] > previous_seq
                previous_ms,previous_seq = row["wall_ms"],msg["seq"]
                if msg["type"] == "state":
                    StateMsg.model_validate(msg)
                else:
                    EventMsg.model_validate(msg)
                    signature.append((msg["event"],msg["t"]))
                    if msg["event"] == "detection":
                        url = msg["data"]["detection"]["image_url"]
                        image_path = destination.parent/url.lstrip("/")
                        with Image.open(image_path) as image:
                            assert image.size == (640,640)
        assert signature[-1] == ("scenario_changed",summary["duration_s"])
        if scenario == "a":
            assert any(name == "recommendation" for name,_ in signature)
        signatures.append(signature)
        hashes.append(hashlib.sha256(destination.read_bytes()).hexdigest())
    assert signatures[0] == signatures[1]
    assert hashes[0] == hashes[1]
