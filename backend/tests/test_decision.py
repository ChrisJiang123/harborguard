from types import SimpleNamespace

import numpy as np
import pytest

from backend.app.decision import DecisionEngine, RiskScorer, Zones
from backend.app.decision.alerts import AlertManager, raw_level
from backend.app.decision.optimizer import Optimizer
from backend.app.decision.pinger import Pinger
from backend.app.geo import to_geo


def feature(zid, bounds, kind="channel", neighbors=(), entrance=False, sensitivity=.6, berths=0):
    x1, y1, x2, y2 = bounds
    ring = [[to_geo(x, y)[1], to_geo(x, y)[0]] for x, y in
            [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]]
    return {"type": "Feature", "properties": {"id": zid, "name": zid, "kind": kind,
            "neighbors": list(neighbors), "entrance": entrance, "sensitivity": sensitivity,
            "berths": berths}, "geometry": {"type": "Polygon", "coordinates": [ring]}}


def fixtures():
    geojson = {"type": "FeatureCollection", "features": [
        feature("entrance", (-100, -100, 100, 100), neighbors=["main"], entrance=True),
        feature("main", (-100, 100, 100, 300), neighbors=["entrance", "berth", "remote"]),
        feature("berth", (-100, 300, 100, 500), "berth", ["main"], sensitivity=.7, berths=2),
        feature("remote", (100, 100, 500, 300), "berth", ["main"], berths=3),
        feature("far", (1000, 1000, 1500, 1500), "berth", [], berths=1),
    ]}
    lat, lon = to_geo(0, 400)
    asset = {"id": "asset", "lat": lat, "lon": lon, "sensitivity": .7}
    vessels = [{"id": "v1", "zone_id": "berth", "movement": "arrive", "t_h": 1},
               {"id": "v2", "zone_id": "remote", "movement": "depart", "t_h": 3},
               {"id": "v3", "zone_id": "far", "movement": "at_berth", "t_h": 1}]
    return geojson, [asset], vessels


def track(tid="T1", x=0, y=0, **kw):
    lat, lon = to_geo(x, y)
    return {"id": tid, "lat": lat, "lon": lon, "depth_m": 12, "vel_e": 0, "vel_n": 1,
            "vel_d": 0, "cls": "unknown", "conf": 0, "cue": "narrowband", "status": "confirmed",
            "history": [], "level": 0, "risk": 0, "detection_id": None, **kw}


class FakeClassifier:
    def classify(self, targets, seed=0):
        return {"model": "stub", "image": b"PNG", "detections": [
            {"cls": target["cls"], "conf": .8, "bbox": [300, 300, 340, 340]} for target in targets]}


def world(t=0, targets=None):
    lat, lon = to_geo(0, 0)
    return SimpleNamespace(t=t, mode="security", rng=np.random.default_rng(42), targets=targets or [],
                           buoys={"B1": {"id": "B1", "lat": lat, "lon": lon,
                                         "status": "ok", "range_m": 600, "pinging": False}})


@pytest.mark.parametrize("cue,cls,conf,expected", [
    ("narrowband", "unknown", 0, .6), ("broadband", "unknown", 0, .2),
    ("call", "unknown", 0, .05), ("narrowband", "uuv", .8, .92),
    ("narrowband", "fish_school", .8, .2),
])
def test_risk_five_hand_computed_cases(cue, cls, conf, expected):
    zones = Zones(*fixtures()[:2])
    scorer = RiskScorer(zones)
    tr = track(cue=cue, cls=cls, conf=conf)
    result = scorer.score(tr, 0)
    assert result["breakdown"] == pytest.approx({"C": expected, "P": .8, "B": 0, "Z": .6, "D": 0})
    assert result["risk"] == pytest.approx(.3*expected+.25*.8+.15*.6)
    assert result["eta_s"] == pytest.approx(400)


def test_behavior_terms_history_requirement_and_eta():
    zones = Zones(*fixtures()[:2])
    scorer = RiskScorer(zones)
    tr = track(y=100, vel_n=1, vel_e=0)
    tr["history"] = [[*to_geo(0, y), 12, t] for t, y in [(0, 40), (30, 70), (60, 100)]]
    # Constant depth, straight and toward asset, against northward current.
    assert scorer.score(tr, 60)["breakdown"]["B"] == 1
    tr["vel_n"] = -.1
    assert scorer.score(tr, 60)["eta_s"] is None
    tr["history"] = tr["history"][-1:]
    assert scorer.score(tr, 60)["breakdown"]["B"] == 0


def score(risk, behavior=0):
    return {"risk": risk, "breakdown": {"C": .6, "P": .5, "B": behavior, "Z": .6, "D": .1},
            "zone_id": "entrance", "asset_id": "asset", "distance_m": 300, "eta_s": 300}


def test_alert_hysteresis_and_deleted_track():
    manager = AlertManager()
    tr = track()
    assert manager.update(tr, score(.41), 0)[0][0] == "alert_raised"
    for t, risk in [(1, .39), (10, .41), (20, .39), (49, .39)]:
        manager.update(tr, score(risk), t)
        assert tr["level"] == 2
    events = manager.update(tr, score(.39), 50)
    assert tr["level"] == 1
    assert events[0][1]["from_level"] == 2
    assert manager.remove_missing(set(), 51)[0][0] == "alert_cleared"
    assert not manager.alerts and not manager.levels


def test_level_conditions_and_vessel_exclusion():
    assert raw_level(track(status="tentative"), score(.9)) == 2
    assert raw_level(track(), score(.9)) == 3
    assert raw_level(track(cls="vessel"), score(.9)) == 0
    assert raw_level(track(), score(.1, 1)) == 2
    value = score(.9)
    value.update(distance_m=1000, eta_s=None)
    assert raw_level(track(), value) == 2


def test_mammal_ping_prohibition_limit_and_duration():
    pinger = Pinger(FakeClassifier())
    w = world(targets=[{"id": "hidden", "cls": "uuv", "x": 0, "y": 100}])
    tr = track(y=100, level=2)
    events = pinger.step([tr, track("T2", x=400, cue="call")], w)
    assert not pinger.detections
    assert "海洋哺乳动物" in events[0][1]["log"]["text"]
    events = pinger.step([tr], w)
    assert events[0][0] == "detection" and tr["cls"] == "uuv"
    assert w.buoys["B1"]["pinging"]
    w.t = 1.5
    pinger.step([tr], w)
    assert not w.buoys["B1"]["pinging"]
    for t in [20, 40, 60, 80, 100, 120]:
        w.t = t
        pinger.step([tr], w)
    assert len(pinger.detections) == 5


def test_optimizer_metrics_dedup_and_ranking():
    geojson, assets, vessels = fixtures()
    optimizer = Optimizer(Zones(geojson, assets), vessels)
    tr = track(vel_n=.3)
    result = optimizer.generate(tr, {"id": "A1", "asset_id": "asset"})
    options = result["options"]
    assert len({tuple(o["zones_closed"]) for o in options}) == len(options)
    baseline = next(o for o in options if o["is_baseline"])
    assert baseline["berths_open_pct"] == 0
    assert baseline["vessels_affected"] == 2
    assert baseline["delay_vessel_hours"] == 12
    assert baseline["residual_risk"] == 0
    assert baseline["delay_vessel_hours"] >= max(o["delay_vessel_hours"] for o in options)
    selected = optimizer.option("test", "test", False, {"berth"}, set(), tr)
    assert selected["berths_open_pct"] == pytest.approx(1-2/6)
    assert selected["delay_vessel_hours"] == 2
    assert set(result["ranked"]) == {o["id"] for o in options}


def test_only_operator_approve_can_restrict_and_reset_clears():
    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())
    tr = track(y=300, cls="uuv", conf=1, cue="narrowband")
    tr["history"] = [[*to_geo(0, y), 12, t] for t, y in [(240, 240), (270, 270), (300, 300)]]
    w = world(t=300)
    engine.step([tr], w, .1)
    aid = next(iter(engine.alerts))
    assert engine.options[aid]["options"]
    assert all(s["state"] == "open" for s in engine.zone_statuses.values())
    oid = engine.options[aid]["options"][0]["id"]
    assert [n for n, _ in engine.approve(aid, oid, "reject", "Chris", 300)] == ["log"]
    assert not engine.operator_restrictions
    events = engine.approve(aid, oid, "approve", "Chris", 301)
    assert any(name == "decision" for name, _ in events)
    restricted = engine.operator_restrictions.copy()
    assert restricted
    engine.set_mode("disaster", 302)
    engine.set_mode("security", 303)
    assert all(engine.zone_statuses[z]["state"] == "restricted" for z in restricted)
    engine.reset()
    assert not engine.alerts and not engine.options and not engine.detections
    assert all(s["state"] == "open" for s in engine.zone_statuses.values())
    with pytest.raises(ValueError):
        engine.approve(aid, oid, "approve", "Chris", 304)

def test_active_sonar_fallback_png_and_all_outbound_event_models():
    from io import BytesIO

    from PIL import Image

    from backend.app.models import EventMsg

    engine = DecisionEngine(*fixtures())
    tr = track(y=300, cls="uuv", conf=1)
    tr["history"] = [[*to_geo(0, y), 12, t] for t, y in [(240, 240), (270, 270), (300, 300)]]
    w = world(t=300, targets=[{"cls": "uuv", "x": 0, "y": 300}])
    # A track exactly 300m from a buoy can differ below machine precision in WGS84.
    w.buoys["B1"]["lat"], w.buoys["B1"]["lon"] = to_geo(0, 10)
    events = engine.step([tr], w, .1)
    aid = next(iter(engine.alerts))
    events += engine.approve(aid, "port-closure", "approve", "Chris", w.t)
    events += engine.set_mode("disaster", w.t)
    for seq, (name, data) in enumerate(events):
        EventMsg(type="event", seq=seq, t=w.t, event=name, data=data)
    assert engine.detections
    did = next(iter(engine.images))
    with Image.open(BytesIO(engine.images[did])) as image:
        assert image.size == (640, 640)
        assert image.format == "PNG"

def test_scenario_reset_cannot_reuse_stale_alert_or_detection_ids():
    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())

    def create_alert_and_detection():
        tr = track(y=200, cls="uuv", conf=1)
        tr["history"] = [[*to_geo(0, y), 12, t] for t, y in [(240, 140), (270, 170), (300, 200)]]
        w = world(t=300, targets=[{"cls": "uuv", "x": 0, "y": 200}])
        engine.step([tr], w, .1)
        return next(iter(engine.alerts)), next(iter(engine.detections))

    first_alert, first_detection = create_alert_and_detection()
    first_option = engine.options[first_alert]["options"][0]["id"]
    engine.reset()
    assert not engine.risk.first_seen
    second_alert, second_detection = create_alert_and_detection()
    assert first_alert != second_alert
    assert first_detection != second_detection
    assert first_alert not in engine.alerts and first_detection not in engine.images
    with pytest.raises(ValueError, match="no longer available"):
        engine.approve(first_alert, first_option, "approve", "Chris", 301)
    assert not engine.operator_restrictions

def test_noise_injection_is_idempotent_and_restores_acoustic_noise_floor():
    from backend.app import config
    from backend.app.engine import GameEngine
    from backend.app.geo import to_local
    from backend.app.sim.acoustics import Acoustics

    game = GameEngine(debug_truth=False)
    game.start("a")
    buoy = game.world.buoys["B1"]
    game.world.buoys = {"B1": buoy}
    bx, by = to_local(buoy["lat"], buoy["lon"])
    game.world.targets = [SimpleNamespace(cls="uuv", x=bx+100, y=by, depth=12)]

    def snr():
        game.world.rng = np.random.default_rng(42)
        return Acoustics().observe(game.world)[0]["snr_db"]

    baseline = snr()
    game.inject("noise_up")
    game.inject("noise_up")
    assert snr() == pytest.approx(baseline-config.NOISE_INCREASE_DB)
    game.inject("noise_down")
    game.inject("noise_down")
    assert snr() == pytest.approx(baseline)
    assert not game.world.noise_up
    game.inject("noise_up")
    game.reset()
    assert not game.world.noise_up

def test_optimization_event_is_stable_and_recompute_keeps_only_human_restrictions():
    import copy

    from backend.app.bus import EventBus

    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())
    tr = track(y=200, cls="uuv", conf=1)
    tr["history"] = [[*to_geo(0, y), 12, t] for t, y in [(240, 140), (270, 170), (300, 200)]]
    w = world(t=300)
    events = engine.step([tr], w, .1)
    name, data = next(event for event in events if event[0] == "options_ready")
    event = EventBus().publish_event(name, data, w.t)
    original_event = copy.deepcopy(event)
    aid = data["alert_id"]
    original_options = copy.deepcopy(engine.options[aid])
    option = next(o for o in original_options["options"] if not o["is_baseline"])
    engine.approve(aid, option["id"], "approve", "Chris", w.t)
    assert engine.options[aid] == original_options
    restricted = engine.operator_restrictions.copy()
    assert restricted == set(option["zones_closed"])
    w.t += 30
    tr["vel_e"] = 4
    engine.step([tr], w, 30)
    assert engine.options[aid] is not data
    assert event == original_event
    assert engine.operator_restrictions == restricted
    assert {z for z, s in engine.zone_statuses.items() if s["state"] == "restricted"} == restricted
    engine.step([], w, .1)
    assert aid not in engine.alerts and aid not in engine.options
    with pytest.raises(ValueError, match="no longer available"):
        engine.approve(aid, option["id"], "approve", "Chris", w.t)
    assert engine.operator_restrictions == restricted
