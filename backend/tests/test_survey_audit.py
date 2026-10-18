"""P0 business correctness, separate from browser/transport acceptance."""
import pytest
from test_decision import fixtures, world
from test_model_safety import Responses, survey

from backend.app import config
from backend.app.decision import DecisionEngine
from backend.app.decision.pinger import Pinger
from backend.app.decision.zones import Zones
from backend.app.perception.classifier import sonar_pixel
from backend.app.sim.sonar import sonar_scene, survey_contacts


@pytest.mark.parametrize("response,reason", [
    ((None, 0), "no_detection"), (("uuv", .5951961875), "non_debris"),
    (("debris", .49), "low_confidence"),
])
def test_failed_observation_survives_coverage_threshold_and_retry_exhaustion(response, reason):
    classifier = Responses(response)
    engine, w = survey(classifier, [{"id": "private-truth", "cls": "debris", "x": 0, "y": 250}])
    engine.zone_statuses["main"]["coverage"] = .89
    for t in (.1, 20.1, 30.7, 40.1, 40.2, 1000):
        w.t = t
        engine.step([], w, 1)
    assert engine.zone_statuses["main"]["coverage"] >= .9
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"
    assert "main" not in engine.reopen_plan["route_zone_ids"]
    attempt = next(iter(engine.disaster.attempts.values()))
    assert attempt["count"] == 3 and attempt["reason"] == reason
    assert len(classifier.calls) == 3
    assert "private-truth" not in engine.disaster.attempts


def test_zero_range_has_persisted_reason_without_fabricated_thirty_metre_image():
    classifier = Responses(("debris", .9))
    engine, w = survey(classifier, [{"cls": "debris", "x": 0, "y": 0}])
    events = []
    for t in (.1, 30.7, 40.2, 1000):
        w.t = t
        events.extend(engine.step([], w, 60))
    assert not classifier.calls and not engine.detections
    assert engine.zone_statuses["entrance"]["coverage"] == 1
    assert engine.zone_statuses["entrance"]["state"] == "unsurveyed"
    assert next(iter(engine.disaster.attempts.values()))["reason"] == "near_field"
    logs = [d["log"]["text"] for name, d in events if name == "log"]
    assert sum("near-field imaging boundary" in line for line in logs) == 1
    assert not engine.reopen_plan["route_zone_ids"]


def test_zero_range_render_input_stays_zero_when_azimuth_is_undefined():
    w = world(targets=[{"cls": "debris", "x": 0, "y": 0}])
    frame = sonar_scene(w, w.buoys["B1"], 1, 1)
    assert len(frame) == 1
    assert frame[0]["range_m"] == 0
    assert frame[0]["bearing_deg"] == 0


def test_observation_identity_does_not_depend_on_true_class_or_true_id():
    rows = []
    for cls in ("debris", "uuv", "fish_school", "marine_mammal", "vessel", "unknown"):
        rows.append(survey_contacts(world(targets=[{"id": f"private-{cls}", "cls": cls, "x": 1.2, "y": 201.3}])))
    assert all(row == rows[0] for row in rows)
    assert set(vars(rows[0][0])) == {"key", "x", "y", "uncertainty_m"}


def test_policy_cannot_read_true_class_or_id_even_when_observation_is_misclassified(monkeypatch):
    class Reflector:
        x, y = 0, 200

        @property
        def cls(self):
            raise AssertionError("Policy must not read truth class")

        @property
        def id(self):
            raise AssertionError("Policy must not associate by truth ID")

    # Replace only image generation with a supplied captured sensor frame. The
    # contact generator and policy still see the poison-pill reflector object.
    monkeypatch.setattr("backend.app.decision.disaster.sonar_scene", lambda *args: [])
    engine = DecisionEngine(*fixtures(), classifier=Responses(("uuv", .595)))
    engine.reset("disaster")
    w = world(targets=[Reflector()])
    w.mode = "disaster"
    engine.step([], w, 100)
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"


def test_non_debris_true_reflector_is_still_an_unresolved_contact():
    engine, w = survey(Responses(("fish_school", .99)), [
        {"id": "not-a-debris-label", "cls": "fish_school", "x": 0, "y": 200}])
    engine.step([], w, 100)
    assert engine.disaster.attempts
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"
    assert engine.zone_statuses["entrance"]["state"] == "clear"


def test_route_berths_and_saved_time_exclude_restricted_blocked_and_unresolved():
    from backend.app.decision.disaster import DisasterSurvey

    surveyor = DisasterSurvey(Zones(*fixtures()[:2]))
    statuses = {z: {"state": "clear"} for z in surveyor.zones.polygons}
    statuses["main"]["state"] = "unsurveyed"
    statuses["remote"]["state"] = "restricted"
    statuses["far"]["state"] = "blocked"
    plan = surveyor.reopen(statuses)
    assert plan["route_zone_ids"] == ["entrance"]
    assert plan["reopen_berth_zone_ids"] == []
    assert plan["est_hours_saved"] == 2*config.SURVEY_H  # Count actual clear survey zones, not a target total.


def test_multitarget_association_matches_actual_C_rendered_boxes():
    render = pytest.importorskip("ml.sonar.render").render_ping
    targets = [{"cls": "uuv", "range_m": 164, "bearing_deg": 30, "length_m": 10, "width_m": 4, "aspect_deg": 0},
               {"cls": "debris", "range_m": 280, "bearing_deg": 0, "length_m": 10, "width_m": 4, "aspect_deg": 0}]
    _, boxes = render(targets, max_range_m=300, fov_deg=120, seed=7, size=640)
    assert len(boxes) == 2
    class CapturedDetector:
        def classify(self, targets, seed=0):
            return {"model": "stub", "image": b"PNG", "_projection": "c_fan",
                    "detections": [{**box, "conf": .8} for box in boxes]}
    w = world()
    result, _ = Pinger(CapturedDetector()).detect("T1", w.buoys["B1"], [], w,
                                                expected_range=164, expected_bearing=30)
    assert result["cls"] == "uuv"
    expected = sonar_pixel(164, 30, projection="c_fan")
    actual = next(box["bbox"] for box in boxes if box["cls"] == "uuv")
    assert ((actual[0]+actual[2])/2, (actual[1]+actual[3])/2) == pytest.approx(expected, abs=3)
    legacy = (320, 639-164/300*639)
    assert min(boxes, key=lambda b: ((b["bbox"][0]+b["bbox"][2])/2-legacy[0])**2
               + ((b["bbox"][1]+b["bbox"][3])/2-legacy[1])**2)["cls"] == "debris"


def test_association_without_prediction_does_not_use_renderer_target_range():
    class NoTruthRange(dict):
        def __getitem__(self, key):
            raise AssertionError("Association must not read renderer target metadata")
    result, _ = Pinger(Responses(("uuv", .8))).detect("T1", world().buoys["B1"], [NoTruthRange()], world())
    assert result["cls"] == "uuv"


def test_confirmed_and_unresolved_regions_are_not_cleared_by_disappearing_contacts():
    engine, w = survey(Responses((None, 0)))
    engine.step([], w, 100)
    w.targets = []
    engine.step([], w, 100)
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"


def test_quantized_boundary_contact_keeps_both_possible_zones_unresolved():
    engine, w = survey(Responses((None, 0)), [{"cls": "debris", "x": 99.7, "y": 200}])
    engine.step([], w, 100)
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"
    assert engine.zone_statuses["remote"]["state"] == "unsurveyed"
    assert not engine.reopen_plan["reopen_berth_zone_ids"]


def test_moving_anonymous_contact_cannot_reset_retry_budget_by_changing_grid_cells():
    classifier = Responses((None, 0))
    target = {"id": "private", "cls": "fish_school", "x": 0, "y": 150}
    engine, w = survey(classifier, [target])
    for t in range(101):
        w.t = float(t)
        target["y"] = 150+t*.5
        engine.step([], w, 1)
    assert len(engine.disaster.attempts) == 1
    assert len(classifier.calls) == 3
    assert next(iter(engine.disaster.attempts.values()))["count"] == 3
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"


def test_exact_delivered_weights_reproduce_250m_wrong_class_and_zero_range_miss():
    from backend.app.perception.classifier import SonarClassifier

    classifier = SonarClassifier()
    if classifier.detector is None:
        pytest.skip("Delivered real weights/runtime unavailable; captured-frame recheck pending")
    bad = classifier.classify([dict(cls="debris", range_m=249.99999989924544, bearing_deg=0,
                                    length_m=8, width_m=3, aspect_deg=0)], seed=2029167940)
    missing = classifier.classify([dict(cls="debris", range_m=0, bearing_deg=0,
                                        length_m=8, width_m=3, aspect_deg=0)], seed=1926751965)
    assert bad["model"] == missing["model"] == "yolo26n"
    assert any(d["cls"] == "uuv" and d["conf"] == pytest.approx(.5951961875, abs=.005)
               for d in bad["detections"])
    assert missing["detections"] == []
    # Replay the unchanged erroneous model output through current policy.
    class Captured:
        survey_min_range_m = 30

        def classify(self, targets, seed=0):
            return bad
    engine, w = survey(Captured(), [{"cls": "debris", "x": 0, "y": 250}])
    engine.step([], w, 100)
    assert engine.zone_statuses["main"]["state"] == "unsurveyed"
