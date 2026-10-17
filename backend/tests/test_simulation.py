from math import hypot

import numpy as np
import pytest

from backend.app import config
from backend.app.geo import to_geo, to_local
from backend.app.sim.scenario import load_scenario
from backend.app.sim.targets import UUV, Debris, FishSchool, Mammal, Vessel
from backend.app.sim.world import World


@pytest.mark.parametrize("x,y", [(0, 0), (-2400, -3200), (3300, 2500), (.5, -.75)])
def test_geo_round_trip_has_sub_decimeter_error(x, y):
    lat, lon = to_geo(x, y)
    actual = to_local(lat, lon)
    assert hypot(actual[0] - x, actual[1] - y) < .1


def test_uuv_reaches_300m_waypoint_at_200_seconds():
    uuv = UUV("uuv1", [(0., 0., 12.), (300., 0., 12.)], speed_mps=1.5, heading_sigma=0)
    rng = np.random.default_rng(42)
    for _ in range(1999):
        uuv.step(.1, rng)
    assert uuv.x == pytest.approx(299.85)
    uuv.step(.1, rng)
    assert uuv.x == pytest.approx(300) and uuv.y == pytest.approx(0)
    assert uuv.depth == 12 and uuv.vx == 0


def positions(world):
    return [(target.id, target.cls, target.x, target.y, target.depth,
             target.vx, target.vy, target.vz) for target in world.targets]


def test_scene_seed_is_repeatable_and_large_steps_match_fixed_steps():
    first, second, third = World(), World(), World()
    for world in [first, second, third]:
        world.start("a")
    for _ in range(1200):
        first.step(.1)
        second.step(.1)
    third.step(120)
    assert positions(first) == positions(second) == positions(third)
    assert first.t == second.t == third.t == 120


def test_pause_resume_reset_and_duration_clamp():
    world = World()
    assert world.scenario_id is None and world.paused and not world.targets
    world.start("a", speed=4)
    assert world.speed == 4
    world.step(1)
    before = positions(world)
    world.paused = True
    assert world.step(10) == [] and world.t == 1 and positions(world) == before
    world.paused = False
    world.duration_s = 2
    world.step(10)
    assert world.t == 2 and world.paused
    world.inject("network_down")
    world.inject("buoy_down", "B2")
    world.inject("noise_up")
    world.reset()
    assert world.t == 0 and world.network == "online" and not world.noise_up
    assert world.scenario_id is None and all(b["status"] == "ok" for b in world.buoys.values())


def test_b_scheduled_buoy_failures_are_exact_and_repeatable():
    runs = []
    for _ in range(2):
        world = World()
        world.start("b")
        events = world.step(59.9)
        assert world.buoys["B4"]["status"] == world.buoys["B7"]["status"] == "ok"
        events += world.step(.1)
        assert world.t == 60
        assert world.buoys["B4"]["status"] == world.buoys["B7"]["status"] == "down"
        assert sum(name == "buoy_changed" for name, _ in events) == 2
        runs.append(events)
    assert runs[0] == runs[1]


def test_target_depth_speed_and_mammal_call_constraints():
    rng = np.random.default_rng(7)
    fish = FishSchool("fish", 0, 0, rng)
    vessel = Vessel("ship", [(0, 0, 5), (1000, 0, 12)], speed_mps=5)
    debris = Debris("debris", 0, 0, drift=True)
    mammal = Mammal("mammal", 0, 0, rng)
    for _ in range(600):
        for target in [fish, vessel, debris, mammal]:
            target.step(.1, rng)
        assert config.SIM_FISH_SPEED_MPS[0] <= hypot(fish.vx, fish.vy) <= config.SIM_FISH_SPEED_MPS[1] + 1e-10
        assert 5 <= fish.depth <= config.SEABED_DEPTH_M
        assert vessel.depth == 0
    assert hypot(debris.vx, debris.vy) == pytest.approx(.05)
    assert mammal.calling(0) and mammal.calling(1.99) and not mammal.calling(2)
    assert mammal.calling(20) and not mammal.calling(19.99)


def test_invalid_scenario_speed_and_dt_do_not_mutate_world():
    world = World()
    for speed in [0, -1, float("nan"), config.MAX_SPEED + 1]:
        with pytest.raises(ValueError):
            world.start("a", speed)
        assert world.scenario_id is None
    with pytest.raises(ValueError):
        load_scenario("../a")
    for dt in [-1, float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            world.step(dt)
