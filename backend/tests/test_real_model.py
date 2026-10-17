"""Real delivered C weights. Separate from B's controlled stub positive tests."""
import pytest

from backend.app import config
from backend.app.engine import GameEngine


def test_real_disaster_never_reopens_unconfirmed_obstacles():
    if not config.SONAR_WEIGHTS_PATH.is_file():
        pytest.skip("C delivered weights absent; real model acceptance pending")
    game = GameEngine(debug_truth=False)
    classifier = game.decision.pinger.classifier
    if classifier.detector is None:
        pytest.skip(f"Real model runtime unavailable: {classifier.last_error}")
    assert classifier.warmup()["model"] == "yolo26n"
    game.start("b", 10)
    while not game._ended:
        game.step(1)
    assert all(d["model"] == "yolo26n" for d in game.decision.detections.values())
    zones = game.decision.zone_statuses
    for target in game.world.targets:
        zid = game.decision.zones.zone_of(target.x, target.y)
        assert zones[zid]["state"] in {"blocked", "unsurveyed"}
        assert zid not in game.decision.reopen_plan["route_zone_ids"]
        assert zid not in game.decision.reopen_plan["reopen_berth_zone_ids"]
    assert zones["channel_entrance"]["state"] == zones["channel_main_s"]["state"] == "clear"
    assert zones["berth_container_1"]["state"] == "clear"
    assert game.decision.reopen_plan["route_zone_ids"] == ["channel_entrance", "channel_main_s"]
    assert game.decision.reopen_plan["reopen_berth_zone_ids"] == ["berth_container_1"]
    assert game.decision.reopen_plan["est_hours_saved"] == 9
    assert "channel_main_n" in game.decision.disaster.blocked_zones  # Positive detection control.
    assert all(a["count"] <= config.DISASTER_RETRY_MAX for a in game.decision.disaster.attempts.values())
