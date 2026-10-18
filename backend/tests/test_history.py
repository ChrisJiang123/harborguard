"""Durability, transaction failure and frozen-v1 recovery boundaries."""
import json
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.engine import GameEngine
from backend.app.main import create_app
from backend.app.models import EventMsg, Recommendation
from backend.app.perception.classifier import SonarClassifier
from backend.app.storage import HistoryStore, StorageError
from backend.tools.make_samples import samples


def seed(game):
    """Explicit contract fixture, not evidence of real scenario escalation."""
    state, events = samples()
    game.start("a", 10)
    game.world.t = state["t"]
    game._tracks = state["tracks"]
    alert = state["alerts"][0]
    game.decision.alerts[alert["id"]] = alert
    game.decision.alert_manager.counter = 1
    game.decision.alert_manager.by_track[alert["track_id"]] = alert["id"]
    game.decision.alert_manager.levels[alert["track_id"]] = 3
    option = next(e["data"] for e in events if e["event"] == "options_ready")
    game.decision.options[alert["id"]] = option
    detection = next(e["data"]["detection"] for e in events if e["event"] == "detection")
    game.decision.detections[detection["id"]] = detection
    game.decision.pinger.counter = 1
    game.decision.images[detection["id"]] = SonarClassifier().classify([], 42)["image"]
    game.save()
    return next(e["data"]["recommendation"] for e in events if e["event"] == "recommendation")


def application(path):
    return create_app(run_loop=False, debug_truth=False, storage_path=path)


def test_identical_log_text_at_same_sim_time_remains_two_durable_events(tmp_path):
    path = tmp_path / "repeated-logs.sqlite3"
    body = dict(level="info", source="operator", text="same legitimate message")
    with TestClient(application(path)) as client:
        for _ in range(2):
            assert client.post("/api/log", json=body).status_code == 200
        events = [event for event in client.get("/api/events").json() if event["event"] == "log"]
        logs = client.get("/api/log").json()
        assert len(events) == len(logs) == 2
        assert events[0]["seq"] < events[1]["seq"]
        assert events[0]["t"] == events[1]["t"] == 0
        assert events[0]["data"] == events[1]["data"]
    with TestClient(application(path)) as client:
        assert client.get("/api/events").json() == events
        assert client.get("/api/log").json() == logs


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_same_time_decisions_from_distinct_operators_survive_restart(tmp_path, action):
    path = tmp_path / "multiple-operators.sqlite3"
    with TestClient(application(path)) as client:
        seed(client.app.state.engine)  # Contract fixture; not a scenario/browser acceptance claim.
        for operator in ("operator-A", "operator-B"):
            body = dict(alert_id="A1", option_id="opt-1", action=action, operator=operator)
            assert client.post("/api/decision", json=body).status_code == 200
        events = [event for event in client.get("/api/events").json() if event["event"] == "decision"]
        assert len(events) == 2
        assert events[0]["seq"] < events[1]["seq"]
        assert events[0]["t"] == events[1]["t"]
        assert [event["data"]["operator"] for event in events] == ["operator-A", "operator-B"]
        assert client.app.state.engine.store.get_object("latest_decision", "A1") == body
    with TestClient(application(path)) as client:
        assert [event for event in client.get("/api/events").json() if event["event"] == "decision"] == events
        assert client.app.state.engine.store.get_object("latest_decision", "A1") == body


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_decision_recommendation_details_and_state_survive_restart(tmp_path, action):
    path = tmp_path / "history.sqlite3"
    body = dict(alert_id="A1", option_id="opt-1", action=action, operator="operator-A")
    with TestClient(application(path)) as client:
        rec = seed(client.app.state.engine)
        assert client.post("/api/recommendations", json=rec).json() == {"ok": True}
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            assert client.post("/api/decision", json=body).json() == {"ok": True}
            notification = ws.receive_json()
            assert notification["event"] == "decision" and notification["data"] == body
            EventMsg.model_validate(notification)
        before = client.get("/api/state").json()
        events = client.get("/api/events").json()
        logs = client.get("/api/log?limit=1000").json()
        details = {route: client.get(route).json() for route in (
            "/api/alerts/A1", "/api/options/A1", "/api/detections/det-1", "/api/tracks/T1")}
        png = client.get("/api/sonar/det-1.png").content
        client.app.state.engine.publish_state()
        high_water = client.app.state.engine.bus.seq
    with TestClient(application(path)) as client:
        state = client.get("/api/state").json()
        assert state == {**before, "paused": True, "seq": high_water}
        assert client.get("/api/events").json() == events
        assert client.get("/api/log?limit=1000").json() == logs
        assert all(client.get(route).json() == value for route, value in details.items())
        assert client.get("/api/sonar/det-1.png").content == png
        assert client.app.state.engine.recommendations["A1"] == rec
        last = next(e for e in reversed(events) if e["event"] == "decision")
        assert last["data"] == body
        restricted = [z for z in state["zones"] if z["state"] == "restricted"]
        assert bool(restricted) == (action == "approve")
        # Public Alert stays exactly v1; it has no fabricated approval status.
        assert "action" not in client.get("/api/alerts/A1").json()
        assert client.post("/api/log", json=dict(level="info", source="operator", text="after restart")).status_code == 200
        assert client.get(f"/api/events?since_seq={high_water}").json()[0]["seq"] > high_water


def test_more_than_500_events_remain_archived_but_public_window_is_unchanged(tmp_path):
    path = tmp_path / "history.sqlite3"
    with TestClient(application(path)) as client:
        game = client.app.state.engine
        rec = seed(game)
        game.recommend(Recommendation.model_validate(rec))
        game.decide("A1", "opt-1", "reject", "demo")
        first_seq = next(e["seq"] for e in game.bus.events if e["event"] == "decision")
        # States consume sequence numbers but do not consume the 500-event window.
        game.publish_state()
        for i in range(520):
            assert client.post("/api/log", json=dict(level="info", source="operator", text=f"filler-{i}")).status_code == 200
        recent = client.get("/api/events?since_seq=0").json()
        assert len(recent) == 500
        assert recent[0]["data"]["log"]["text"] == "filler-20"
        assert all(a["seq"] < b["seq"] for a, b in zip(recent, recent[1:], strict=False))
        assert not any(e["event"] in {"recommendation", "decision"} for e in recent)
        assert client.get(f"/api/events?since_seq={first_seq}").json() == recent
        assert len(client.get("/api/events?since_seq=" + str(recent[-3]["seq"])).json()) == 2
        total = game.store.connection.execute("SELECT count(*) FROM events").fetchone()[0]
        assert total == 526
        assert game.store.get_object("latest_decision", "A1")["action"] == "reject"
        assert game.store.get_object("recommendation", rec["id"]) == rec
        assert len(game.store._objects) <= 5
        assert len(client.get("/api/log?limit=1000").json()) == 522
    with TestClient(application(path)) as client:
        assert client.get("/api/events").json() == recent
        assert client.get("/api/options/A1").status_code == 200
        assert client.app.state.engine.store.connection.execute("SELECT count(*) FROM events").fetchone()[0] == total
        # No undeclared archive API was added.
        assert client.get("/api/history/events").status_code == 404


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_real_sqlite_failure_rolls_back_decision_state_events_logs_and_fanout(tmp_path, action):
    path = tmp_path / "history.sqlite3"
    with TestClient(application(path)) as client:
        game = client.app.state.engine
        seed(game)
        before, logs, sequence = game.state().model_dump(), list(game.logs), game.bus.seq
        queue = game.bus.subscribe()
        connection = game.store.connection
        connection.execute("CREATE TRIGGER fail_decision BEFORE INSERT ON events WHEN json_extract(NEW.payload,'$.event')='decision' BEGIN SELECT RAISE(ABORT,'injected disk write failure'); END")
        response = client.post("/api/decision", json=dict(alert_id="A1", option_id="opt-1", action=action, operator="demo"))
        assert response.status_code == 503 and "ok" not in response.json()
        assert game.state().model_dump() == before
        assert game.bus.seq == sequence and list(game.logs) == logs and queue.empty()
        assert connection.execute("SELECT count(*) FROM objects WHERE kind='decision'").fetchone()[0] == 0
        assert client.get("/api/health").status_code == 503
        connection.execute("DROP TRIGGER fail_decision")
    with TestClient(application(path)) as client:
        assert not any(z["state"] == "restricted" for z in client.get("/api/state").json()["zones"])
        assert not any(e["event"] == "decision" for e in client.get("/api/events").json())


def test_recommendation_projection_failure_is_atomic_and_retry_succeeds(tmp_path):
    with TestClient(application(tmp_path / "history.sqlite3")) as client:
        game = client.app.state.engine
        rec = seed(game)
        sequence = game.bus.seq
        queue = game.bus.subscribe()
        game.store.connection.execute("CREATE TRIGGER fail_rec BEFORE INSERT ON objects WHEN NEW.kind='recommendation' BEGIN SELECT RAISE(ABORT,'injected projection failure'); END")
        assert client.post("/api/recommendations", json=rec).status_code == 503
        assert game.recommendations == {} and game.bus.seq == sequence and queue.empty()
        assert not any(e["event"] == "recommendation" for e in game.bus.events)
        game.store.connection.execute("DROP TRIGGER fail_rec")
        assert client.post("/api/recommendations", json=rec).status_code == 200
        assert queue.get_nowait()["event"] == "recommendation"
        assert client.get("/api/health").status_code == 200


def test_checkpoint_failure_rolls_back_controls_and_scenario_reset(tmp_path):
    with TestClient(application(tmp_path / "history.sqlite3")) as client:
        game = client.app.state.engine
        rec = seed(game)
        game.recommend(Recommendation.model_validate(rec))
        before = game.state().model_dump()
        game.store.connection.execute("CREATE TRIGGER fail_runtime BEFORE UPDATE ON runtime BEGIN SELECT RAISE(ABORT,'checkpoint failure'); END")
        for route, body in (("/api/control", {"action": "reset"}), ("/api/control", {"action": "pause"}),
                            ("/api/scenario/b/start", {"speed": 4}), ("/api/inject", {"type": "network_down"})):
            assert client.post(route, json=body).status_code == 503
            assert game.state().model_dump() == before
            assert game.recommendations["A1"] == rec


def test_archive_details_png_and_counters_survive_reset_and_restart(tmp_path):
    path = tmp_path / "history.sqlite3"
    with TestClient(application(path)) as client:
        game = client.app.state.engine
        seed(game)
        png = client.get("/api/sonar/det-1.png").content
        assert client.post("/api/control", json={"action": "reset"}).status_code == 200
        assert client.get("/api/state").json()["alerts"] == []
        for route in ("/api/alerts/A1", "/api/options/A1", "/api/detections/det-1", "/api/tracks/T1"):
            assert client.get(route).status_code == 200
        # Archived historical objects must never authorize an old action.
        assert client.post("/api/decision", json=dict(alert_id="A1", option_id="opt-1", action="approve", operator="demo")).status_code == 409
    with TestClient(application(path)) as client:
        game = client.app.state.engine
        assert (game.decision.alert_manager.counter, game.decision.pinger.counter) == (1, 1)
        assert client.get("/api/sonar/det-1.png").content == png
        game.start("b", 10)
        game.step(1)
        assert "det-1" not in game.decision.detections
        assert all(int(did.split("-")[1]) > 1 for did in game.decision.detections)
        assert client.get("/api/sonar/det-1.png").content == png


@pytest.mark.parametrize("scenario", ["a", "b"])
def test_checkpoint_resume_preserves_rng_kalman_and_event_reproducibility(tmp_path, scenario):
    path = tmp_path / "history.sqlite3"
    reference = GameEngine(debug_truth=False)
    reference.start(scenario, 10)
    # B generates debris PNGs immediately; A exercises nontrivial Kalman state.
    for _ in range(25):
        reference.step(1)
    store = HistoryStore(path)
    from backend.app import checkpoint
    durable = GameEngine(debug_truth=False, store=store)
    checkpoint.restore(durable, checkpoint.capture(reference), dict(reference.decision.images))
    durable.bus.seq = reference.bus.seq
    durable.save()
    store.close()
    store = HistoryStore(path)
    restored = GameEngine(debug_truth=False, store=store)
    assert restored.world.paused
    restored.control("resume")
    for _ in range(30):
        reference.step(1)
        restored.step(1)
    assert restored.state() == reference.state()
    assert restored.world.rng.bit_generator.state == reference.world.rng.bit_generator.state
    assert list(restored.logs) == list(reference.logs)
    for key in reference.decision.images:
        assert restored.image(key) == reference.image(key)
    store.close()


def test_database_schema_corruption_and_writer_ownership_are_explicit(tmp_path):
    path = tmp_path / "history.sqlite3"
    store = HistoryStore(path)
    with pytest.raises(StorageError):
        HistoryStore(path)
    game = GameEngine(debug_truth=False, store=store)
    game.log("info", "operator", "keep")
    store.connection.execute("UPDATE runtime SET fingerprint='incompatible'")
    store.connection.commit()
    store.close()
    store = HistoryStore(path)
    with pytest.raises(StorageError, match="differs"):
        GameEngine(debug_truth=False, store=store)
    store.close()
    corrupt = tmp_path / "bad.sqlite3"
    corrupt.write_bytes(b"this is not sqlite")
    with pytest.raises(StorageError):
        HistoryStore(corrupt)
    future = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(future)
    connection.execute("PRAGMA user_version=99")
    connection.close()
    with pytest.raises(StorageError):
        HistoryStore(future)


def test_public_contract_has_no_new_fields_paths_or_statuses():
    from backend.app.models import EVENT_DATA, DecisionRequest
    # No frontend history route, state additions or event enums were introduced.
    app = application(":memory:")
    schema = app.openapi()
    assert sum(len([m for m in entry if m in {"get", "post"}]) for entry in schema["paths"].values()) == 21
    assert set(schema["components"]["schemas"]["StateMsg"]["properties"]) == {
        "type", "seq", "t", "mode", "network", "scenario", "paused", "speed", "buoys", "tracks", "alerts", "zones"}
    assert EVENT_DATA["decision"] is DecisionRequest
    assert set(DecisionRequest.model_json_schema()["properties"]["action"]["enum"]) == {"approve", "reject"}


def test_handoff_fixtures_validate_against_unchanged_public_models():
    from backend.app.models import DecisionRequest, Detection, StateMsg

    directory = Path(__file__).resolve().parents[1] / "fixtures/history"
    for name, model in (("recommendation.json", Recommendation), ("decision-reject.json", DecisionRequest),
                        ("decision-approve.json", DecisionRequest), ("state-before-restart.json", StateMsg),
                        ("det-6.json", Detection)):
        model.model_validate_json((directory / name).read_text(encoding="utf-8"))
    events = json.loads((directory / "events-before-overflow.json").read_text(encoding="utf-8"))
    for event in events:
        EventMsg.model_validate(event)
    assert [e["data"]["action"] for e in events if e["event"] == "decision"] == ["reject", "approve"]


def test_committed_durable_write_is_not_rolled_back_by_optional_observer(tmp_path):
    def broken_observer(message):
        raise OSError("observer sink failed")

    with TestClient(application(tmp_path / "history.sqlite3")) as client:
        game = client.app.state.engine
        game.bus.listeners.append(broken_observer)
        assert client.post("/api/log", json=dict(level="info", source="operator", text="committed")).status_code == 200
        assert game.store.connection.execute("SELECT count(*) FROM events").fetchone()[0] == 1
        assert client.get("/api/events").json()[0]["data"]["log"]["text"] == "committed"
    # Offline recorders still propagate write failures, rather than claiming a
    # successful recording when their output disk/sink failed.
    memory = GameEngine(debug_truth=False)
    memory.bus.listeners.append(broken_observer)
    with pytest.raises(OSError, match="sink failed"):
        memory.log("info", "operator", "offline")


def test_running_loop_storage_failure_stays_alive_unhealthy_and_can_reset(tmp_path):
    with TestClient(create_app(debug_truth=False, storage_path=tmp_path / "history.sqlite3")) as client:
        assert client.post("/api/scenario/a/start", json={"speed": 10}).status_code == 200
        game = client.app.state.engine
        client.portal.call(game.store.connection.execute,
            "CREATE TRIGGER fail_loop BEFORE UPDATE ON runtime BEGIN SELECT RAISE(ABORT,'live storage failure'); END")
        for _ in range(100):
            if client.app.state.runtime_error:
                break
            time.sleep(.01)
        assert client.app.state.runtime_error == "simulation failure"
        assert client.get("/api/health").status_code == 503
        assert client.get("/api/state").json()["paused"]
        client.portal.call(game.store.connection.execute, "DROP TRIGGER fail_loop")
        assert client.post("/api/control", json={"action": "reset"}).status_code == 200
        assert client.get("/api/health").status_code == 200
