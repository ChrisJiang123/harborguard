from test_decision import FakeClassifier, fixtures, track, world

from backend.app.decision import DecisionEngine
from backend.app.decision.disaster import DisasterSurvey
from backend.app.decision.zones import Zones


def test_bfs_requires_continuous_clear_channels_and_adjacent_clear_berths():
    survey = DisasterSurvey(Zones(*fixtures()[:2]))
    statuses = {z: {"id": z, "state": "clear", "coverage": 1} for z in survey.zones.polygons}
    plan = survey.reopen(statuses)
    assert plan["route_zone_ids"] == ["entrance", "main"]
    assert plan["reopen_berth_zone_ids"] == ["berth", "remote"]
    assert "far" not in plan["reopen_berth_zone_ids"]
    assert plan["est_hours_saved"] == 7.5
    statuses["main"]["state"] = "blocked"
    plan = survey.reopen(statuses)
    assert plan["route_zone_ids"] == ["entrance"]
    assert not plan["reopen_berth_zone_ids"]
    statuses["entrance"]["state"] = "unsurveyed"
    assert not survey.reopen(statuses)["route_zone_ids"]


def test_disaster_debris_detection_once_blocks_and_coverage_clears():
    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())
    engine.reset("disaster")
    w = world(targets=[{"id": "private-truth-id", "cls": "debris", "x": 0, "y": 200}])
    w.mode = "disaster"
    events = engine.step([], w, 60)
    assert sum(name == "detection" for name, _ in events) == 1
    detection = next(iter(engine.detections.values()))
    assert detection["track_id"] == ""
    assert "private-truth-id" not in str(detection)
    assert engine.zone_statuses["main"]["state"] == "blocked"
    assert engine.zone_statuses["entrance"]["state"] == "clear"
    assert engine.zone_statuses["far"]["state"] == "unsurveyed"
    assert engine.zone_statuses["far"]["coverage"] == 0
    assert any(name == "reopen_plan" for name, _ in events)
    w.t += 60
    assert not any(name == "detection" for name, _ in engine.step([], w, 60))
    w.buoys["B1"]["status"] = "down"
    coverage = engine.zone_statuses["berth"]["coverage"]
    w.t += 60
    engine.step([], w, 60)
    assert engine.zone_statuses["berth"]["coverage"] == coverage


def test_debris_tracks_do_not_raise_security_alert_in_disaster():
    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())
    w = world(t=100)
    w.mode = "disaster"
    tr = track(cls="debris", conf=.9, y=300)
    events = engine.step([tr], w, .1)
    assert tr["level"] == 0
    assert not any(n == "alert_raised" for n, _ in events)


def test_operator_restricted_zone_never_reopens_from_coverage():
    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())
    engine.reset("disaster")
    engine.operator_restrictions.add("entrance")
    engine.zone_statuses["entrance"]["state"] = "restricted"
    w = world()
    w.mode = "disaster"
    engine.step([], w, 1000)
    assert engine.zone_statuses["entrance"]["state"] == "restricted"
    assert not engine.reopen_plan["route_zone_ids"]
