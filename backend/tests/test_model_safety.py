"""B-owned conservative recovery, projection and warmup regressions."""
import copy
from math import cos, radians, sin

import numpy as np
import pytest
from test_decision import FakeClassifier, fixtures, world

from backend.app import checkpoint, config
from backend.app.decision import DecisionEngine
from backend.app.decision.pinger import Pinger
from backend.app.engine import GameEngine
from backend.app.geo import to_geo
from backend.app.perception.classifier import SonarClassifier, sonar_pixel
from backend.app.storage import HistoryStore, StorageError


class Responses:
    def __init__(self, *responses):
        self.responses = responses
        self.calls = []

    def classify(self, targets, seed=0):
        self.calls.append(copy.deepcopy(targets))
        cls, conf = self.responses[min(len(self.calls)-1, len(self.responses)-1)]
        return {"model": "stub", "image": b"PNG", "detections": [] if cls is None else [
            {"cls": cls, "conf": conf, "bbox": [300, 300, 340, 340]}]}


def survey(classifier, targets=None):
    engine = DecisionEngine(*fixtures(), classifier=classifier)
    engine.reset("disaster")
    w = world(targets=targets or [{"id": "private", "cls": "debris", "x": 0, "y": 200}])
    w.mode = "disaster"
    return engine, w


@pytest.mark.parametrize("cls,conf", [(None, 0), ("uuv", .9), ("debris", .49)])
def test_unconfirmed_obstacle_cannot_turn_clear_or_enter_reopen_route(cls, conf):
    classifier = Responses((cls, conf))
    engine, w = survey(classifier)
    for t in (0, 1, 19.9, 20, 21, 40, 60, 1000):
        w.t = t
        engine.step([], w, 60)
    assert len(classifier.calls) == config.DISASTER_RETRY_MAX == 3
    assert engine.zone_statuses["main"]["coverage"] == 1
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"
    assert engine.zone_statuses["entrance"]["state"] == "clear"
    assert engine.zone_statuses["far"]["state"] == "unsurveyed"
    assert "main" not in engine.reopen_plan["route_zone_ids"]
    assert "main" in engine.reopen_plan["unsurveyed_zone_ids"]
    assert engine.disaster.detected_debris == set()
    assert len(engine.detections) == 3
    engine.reset("disaster")
    assert not engine.disaster.attempts


def test_retry_uses_another_suitable_buoy_and_preserves_physical_distance():
    classifier = Responses((None, 0), ("debris", .8))
    engine, w = survey(classifier)
    lat, lon = to_geo(0, 200)  # Degenerate zero range; must not be relabelled 30m.
    w.buoys["zero"] = dict(w.buoys["B1"], id="zero", lat=lat, lon=lon)
    lat, lon = to_geo(0, 50)
    w.buoys["B2"] = dict(w.buoys["B1"], id="B2", lat=lat, lon=lon)
    engine.step([], w, 60)
    w.t = 19.9
    engine.step([], w, 60)
    assert len(classifier.calls) == 1
    w.t = 20
    engine.step([], w, 60)
    detections = list(engine.detections.values())
    assert [d["buoy_id"] for d in detections] == ["B2", "B1"]
    assert [c[0]["range_m"] for c in classifier.calls] == pytest.approx([150, 200])
    assert all(d["track_id"] == "" for d in detections)
    assert engine.zone_statuses["main"]["state"] == "blocked"
    w.t = 200
    engine.step([], w, 60)
    assert len(classifier.calls) == 2


def test_near_field_only_and_mammal_protection_stay_uncertain_without_emitting():
    classifier = Responses(("debris", .9))
    engine, w = survey(classifier, [{"id": "private", "cls": "debris", "x": 0, "y": 0}])
    engine.step([], w, 60)
    assert not classifier.calls
    assert engine.zone_statuses["entrance"]["state"] == "unsurveyed"
    from test_decision import track
    engine, w = survey(classifier)
    engine.step([track(cls="marine_mammal", cue="call")], w, 60)
    assert not classifier.calls and not engine.detections
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"


def test_multiple_obstacles_and_human_restrictions_cannot_be_cleared_by_one_success():
    engine, w = survey(Responses((None, 0), ("debris", .9)), [
        {"id": "first", "cls": "debris", "x": 0, "y": 180},
        {"id": "second", "cls": "debris", "x": 0, "y": 220}])
    engine.step([], w, 60)
    assert engine.zone_statuses["main"]["state"] == "blocked"
    engine.operator_restrictions.add("main")
    engine.step([], w, 60)
    assert engine.zone_statuses["main"]["state"] == "restricted"
    assert "main" not in engine.reopen_plan["route_zone_ids"]


def test_projection_selects_correct_box_and_distinguishes_renderer_from_model():
    class Classifier:
        def __init__(self, projection):
            self.projection = projection

        def classify(self, targets, seed=0):
            return {"model": "stub", "image": b"PNG", "_projection": self.projection,
                    "detections": [{"cls": "debris", "conf": .9, "bbox": [312, 280, 328, 300]},
                                   {"cls": "uuv", "conf": .8, "bbox": [312, 430, 328, 446]}]}
    w = world()
    for projection, expected in (("c_fan", "uuv"), ("stub_linear", "debris")):
        pinger = Pinger(Classifier(projection))
        result, _ = pinger.detect("T1", w.buoys["B1"], [], w, expected_range=164)
        assert result["cls"] == expected
        assert "_projection" not in result


@pytest.mark.parametrize("distance,bearing", [(0, 0), (164, 0), (300, -60), (100, 30)])
def test_fan_geometry_matches_c_formula(distance, bearing):
    x, y = sonar_pixel(distance, bearing, projection="c_fan")
    radius = min(639, 319/sin(radians(60)))*distance/300
    assert (x, y) == pytest.approx((319.5+radius*sin(radians(bearing)), 639-radius*cos(radians(bearing))))


def test_renderer_failure_uses_linear_geometry_even_when_detector_available():
    def broken(*args, **kwargs):
        raise RuntimeError("render failed")
    classifier = SonarClassifier(renderer=broken, detector=object())
    assert classifier.classify([], 0)["_projection"] == "stub_linear"


def test_warmup_is_once_per_classifier_and_reset_reuses_it():
    calls = []
    class Detector:
        def detect(self, image):
            calls.append(image.copy())
            return []
    def renderer(*args, **kwargs):
        return np.zeros((640, 640), dtype=np.uint8), []
    classifier = SonarClassifier(renderer=renderer, detector=Detector())
    engine, w = survey(classifier)
    rng = copy.deepcopy(w.rng.bit_generator.state)
    before = copy.deepcopy(w.__dict__)
    assert classifier.warmup()["model"] == "yolo26n"
    assert classifier.warmup()["model"] == "yolo26n"
    assert len(calls) == 1
    engine.reset()
    assert engine.pinger.classifier is classifier
    assert w.t == before["t"] and w.rng.bit_generator.state == rng
    assert not engine.detections and engine.pinger.counter == 0


def test_default_classifier_is_reused_across_scenario_resets(monkeypatch):
    created = []
    def factory():
        instance = FakeClassifier()
        created.append(instance)
        return instance
    monkeypatch.setattr("backend.app.perception.classifier.SonarClassifier", factory)
    game = GameEngine(debug_truth=False)
    game.start("a")
    game.reset()
    game.start("b")
    assert len(created) == 1
    assert game.decision.pinger.classifier is created[0]


def test_pending_retry_state_survives_same_database_restart_and_failed_commit(tmp_path):
    path = tmp_path/"candidate.sqlite3"
    store = HistoryStore(path)
    game = GameEngine(debug_truth=False, store=store)
    game.start("b", 10)
    game.decision.pinger.classifier = Responses((None, 0))
    game.step(1)
    attempts = copy.deepcopy(game.decision.disaster.attempts)
    assert {a["zone_id"]: a["count"] for a in attempts.values()} == {
        "channel_main_n": 1, "channel_turning": 1, "berth_fuel": 0, "anchorage_north": 1}
    before = checkpoint.capture(game)
    seq = game.bus.seq
    store.connection.execute("CREATE TRIGGER fail_tick BEFORE UPDATE ON runtime BEGIN SELECT RAISE(ABORT,'injected failure'); END")
    with pytest.raises(StorageError):
        game.step(20)
    assert checkpoint.encode(checkpoint.capture(game)) == checkpoint.encode(before)
    assert game.bus.seq == seq and game.bus.pending is None
    store.connection.execute("DROP TRIGGER fail_tick")
    store.close()
    store = HistoryStore(path)
    restored = GameEngine(debug_truth=False, store=store)
    assert restored.world.paused
    assert restored.decision.disaster.attempts == attempts
    restored.decision.pinger.classifier = Responses((None, 0))
    restored.control("resume")
    restored.step(18)
    assert restored.decision.disaster.attempts == attempts
    restored.step(2)
    assert {a["zone_id"]: a["count"] for a in restored.decision.disaster.attempts.values()} == {
        "channel_main_n": 2, "channel_turning": 2, "berth_fuel": 0, "anchorage_north": 2}
    store.close()
