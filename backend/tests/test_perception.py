import math
from types import SimpleNamespace

import numpy as np
import pytest

from backend.app import config
from backend.app.geo import to_geo, to_local
from backend.app.perception.kalman import Kalman3D
from backend.app.perception.localize import localize
from backend.app.perception.tracker import Tracker
from backend.app.sim.acoustics import Acoustics


def buoy(name, x, y, range_m=600):
    lat, lon = to_geo(x, y)
    return {"id": name, "lat": lat, "lon": lon, "range_m": range_m, "status": "ok", "pinging": False}


def observation(buoy_id, bx, by, x, y, depth=12, cue="narrowband"):
    distance = math.hypot(x - bx, y - by)
    return {"buoy_id": buoy_id, "bearing_deg": math.degrees(math.atan2(x - bx, y - by)),
            "elevation_deg": math.degrees(math.atan2(depth, distance)), "snr_db": 20,
            "bearing_sigma_deg": 2, "cue": cue}


def measurement(x=0, y=0, depth=12, cue="narrowband"):
    return {"x": x, "y": y, "depth": depth, "covariance": np.eye(3) * 25, "cue": cue}


def test_triangulation_depth_positive_rays_and_covariance():
    buoys = {"B1": buoy("B1", -100, 0), "B2": buoy("B2", 100, 0)}
    result = localize([observation("B1", -100, 0, 0, 100), observation("B2", 100, 0, 0, 100)], buoys)
    assert len(result) == 1
    assert [result[0][k] for k in ("x", "y", "depth")] == pytest.approx([0, 100, 12], abs=1e-6)
    assert np.linalg.eigvalsh(result[0]["covariance"]).min() > 0
    assert localize([observation("B1", -100, 0, 0, 100)], buoys) == []
    wrong = observation("B2", 100, 0, 0, 100)
    wrong["bearing_deg"] += 180
    assert localize([observation("B1", -100, 0, 0, 100), wrong], buoys) == []
    far = [observation("B1", -100, 0, 0, 1500), observation("B2", 100, 0, 0, 1500)]
    assert localize(far, buoys) == []


def test_passive_observations_anonymous_seeded_and_no_debris():
    def world(seed):
        return SimpleNamespace(buoys={"B1": buoy("B1", 0, 0)}, targets=[
            SimpleNamespace(id="secret-uuv", cls="uuv", x=100, y=100, depth=12),
            SimpleNamespace(id="secret-debris", cls="debris", x=50, y=50, depth=18)],
            noise_up=False, t=1, rng=np.random.default_rng(seed))
    a, b = Acoustics().observe(world(3)), Acoustics().observe(world(3))
    assert a == b
    assert a and all("target_id" not in item and "id" not in item and "cls" not in item for item in a)
    assert all("secret" not in str(item) for item in a)


def test_noise_and_failed_buoy_reduce_hearing():
    target = SimpleNamespace(cls="uuv", x=500, y=0, depth=12)
    world = SimpleNamespace(buoys={"B1": buoy("B1", 0, 0)}, targets=[target], noise_up=False,
                            t=1, rng=np.random.default_rng(3))
    assert Acoustics().observe(world)
    world.noise_up = True
    assert not [o for o in Acoustics().observe(world) if o["snr_db"] > config.DT_DB]
    world.buoys["B1"]["status"] = "down"
    assert Acoustics().observe(world) == []


def test_kalman_constant_velocity_and_positive_covariance():
    kf = Kalman3D([0, 0, 12], np.eye(3))
    for t in range(1, 61):
        kf.predict(1)
        kf.update([2 * t, -t, 12], np.eye(3))
    assert kf.x == pytest.approx([120, -60, 12, 2, -1, 0], abs=0.01)
    ellipse = kf.error_ellipse()
    assert ellipse["a_m"] >= ellipse["b_m"] > 0
    assert np.linalg.eigvalsh(kf.P).min() > 0
    with pytest.raises(ValueError):
        kf.predict(-1)


def test_noisy_three_buoy_track_accuracy_velocity_and_id():
    target = SimpleNamespace(id="truth-never-associated", cls="uuv", x=-50, y=50, depth=12)
    buoys = {"B1": buoy("B1", -200, -200), "B2": buoy("B2", 200, -200), "B3": buoy("B3", 0, 300)}
    world = SimpleNamespace(buoys=buoys, targets=[target], noise_up=False, t=0, rng=np.random.default_rng(42))
    acoustics, tracker = Acoustics(), Tracker()
    errors, ids, velocities = [], [], []
    for t in range(91):
        if t:
            tracker.predict(1)
        target.x, target.y = -50 + t, 50 + 0.5 * t
        world.t = t
        tracks = tracker.update(localize(acoustics.observe(world), buoys), t, targets=world.targets)
        if t >= 30:
            confirmed = [track for track in tracks if track["status"] == "confirmed"]
            assert len(confirmed) == 1
            track = confirmed[0]
            x, y = to_local(track["lat"], track["lon"])
            errors.append(math.hypot(x - target.x, y - target.y))
            velocities.append(math.hypot(track["vel_e"] - 1, track["vel_n"] - 0.5))
            ids.append(track["id"])
    assert np.sqrt(np.mean(np.square(errors))) < 30
    assert np.sqrt(np.mean(np.square(velocities))) < 0.3
    assert len(set(ids)) == 1
    assert track["cls"] == "unknown"  # Passive sound alone is never a truth classifier.


def test_confirmation_history_prediction_timeout_and_classification():
    tracker = Tracker()
    assert tracker.update([measurement()], 0)[0]["status"] == "tentative"
    tracker.predict(1)
    tracker.update([], 1)
    tracker.predict(1)
    track = tracker.update([measurement(2)], 2)[0]
    assert track["status"] == "confirmed"
    assert len(track["history"]) == 2
    assert len(track["predicted"]) == 10
    assert track["predicted"][-1][3] == 302
    tracker.set_classification(track["id"], "uuv", 0.85, "det-1")
    assert tracker.tracks(2)[0]["detection_id"] == "det-1"
    tracker.predict(10)
    assert tracker.update([], 12) == []


def test_ais_only_uses_nearby_vessels():
    tracker = Tracker()
    targets = [SimpleNamespace(cls="uuv", x=0, y=0), SimpleNamespace(cls="vessel", x=500, y=500)]
    track = tracker.update([measurement(cue="broadband")], 0, targets)[0]
    assert track["cls"] == "unknown"
    targets[1].x, targets[1].y = 20, 20
    tracker.predict(1)
    assert tracker.update([measurement(1, cue="broadband")], 1, targets)[0]["cls"] == "vessel"


def test_a_surface_ship_cannot_overwrite_a_nearby_narrowband_uuv():
    tracker = Tracker()
    target = SimpleNamespace(cls="vessel", x=0, y=0)
    track = tracker.update([measurement()], 0, [target])[0]
    assert track["cls"] == "unknown"
    tracker.set_classification(track["id"], "uuv", 0.9, "det-1")
    tracker.predict(1)
    track = tracker.update([measurement(1)], 1, [target])[0]
    assert track["cls"] == "uuv"
    assert track["detection_id"] == "det-1"


def test_five_minutes_false_observations_do_not_create_confirmed_tracks():
    world = SimpleNamespace(buoys={f"B{i}": buoy(f"B{i}", i * 80, (i % 3) * 100) for i in range(10)},
                            targets=[], noise_up=False, t=0, rng=np.random.default_rng(42))
    tracker, acoustics = Tracker(), Acoustics()
    confirmed_ids = set()
    false_observation_count = 0
    for t in range(300):
        tracker.predict(1)
        observations = acoustics.observe(world)
        false_observation_count += len(observations)
        confirmed_ids.update(track["id"] for track in tracker.update(localize(observations, world.buoys), t) if track["status"] == "confirmed")
    assert false_observation_count > 0
    assert len(confirmed_ids) <= 1


def test_multiple_broadband_sources_do_not_manufacture_cross_pair_tracks():
    buoys = {"B1": buoy("B1", -200, 0), "B2": buoy("B2", 200, 0), "B3": buoy("B3", 0, -200)}
    targets = [SimpleNamespace(cls="vessel", x=148, y=52, depth=0),
               SimpleNamespace(cls="vessel", x=-118, y=89, depth=0),
               SimpleNamespace(cls="vessel", x=94, y=158, depth=0)]
    world = SimpleNamespace(buoys=buoys, targets=targets, noise_up=False, t=1, rng=np.random.default_rng(1))
    points = localize(Acoustics().observe(world), buoys)
    assert len(points) == 3
    for target in targets:
        assert min(math.hypot(point["x"]-target.x, point["y"]-target.y) for point in points) < 40


def test_an_uncertain_birth_cannot_steal_an_established_track():
    tracker = Tracker()
    tracker.update([measurement()], 0)
    tracker.predict(0.1)
    original = tracker.update([measurement()], 0.1)[0]["id"]
    tracker.predict(0.1)
    noisy_birth = measurement(100)
    noisy_birth["covariance"] = np.eye(3) * 900
    tracker.update([noisy_birth], 0.2)
    tracker.predict(0.1)
    result = tracker.update([measurement(17)], 0.3)
    established = next(track for track in result if track["id"] == original)
    assert established["status"] == "confirmed"
    assert tracker._tracks[original].updated_t == 0.3
    assert sum(track["status"] == "confirmed" for track in result) == 1
