"""Live consumers must receive changed metrics, even when geometry is unchanged."""
import copy

import pytest

from backend.app import checkpoint, config
from backend.app.bus import EventBus
from backend.app.decision import DecisionEngine
from backend.app.geo import to_geo
from backend.app.models import EventMsg
from backend.tests.test_decision import FakeClassifier, fixtures, track, world


@pytest.mark.parametrize("field", [
    "residual_risk", "delay_vessel_hours", "berths_open_pct", "vessels_affected", "ranked",
])
def test_metric_only_options_update_is_broadcast_once_without_applying_restrictions(monkeypatch, field):
    engine = DecisionEngine(*fixtures(), classifier=FakeClassifier())
    tr = track(y=200, cls="uuv", conf=1)
    tr["history"] = [[*to_geo(0, y), 12, t] for t, y in [(240, 140), (270, 170), (300, 200)]]
    w = world(t=300)
    # The classification/risk are already confirmed. Only optimizer output changes.
    monkeypatch.setattr(engine.pinger, "step", lambda *_: [])
    first = next(data for name, data in engine.step([tr], w, .1) if name == "options_ready")
    original = copy.deepcopy(first)
    changed = copy.deepcopy(first)
    if field == "ranked":
        changed["ranked"] = changed["ranked"][::-1]
    elif field == "residual_risk":
        changed["options"][0][field] = .55
    elif field == "berths_open_pct":
        changed["options"][0][field] = .25
    else:
        changed["options"][0][field] += 1
    assert [(o["zones_closed"], o["speed_limit_zones"]) for o in changed["options"]] == [
        (o["zones_closed"], o["speed_limit_zones"]) for o in first["options"]]
    monkeypatch.setattr(engine.optimizer, "generate", lambda *_: copy.deepcopy(changed))
    w.t += config.OPTIMIZE_EVERY_S
    updates = [data for name, data in engine.step([tr], w, .1) if name == "options_ready"]
    assert updates == [changed], "REST changed but live frontend/Agent did not receive updated options"
    EventMsg.model_validate(EventBus().publish_event("options_ready", updates[0], w.t))
    assert first == original  # An older event remains a stable history record.
    assert not engine.operator_restrictions
    assert all(zone["state"] == "open" for zone in engine.zone_statuses.values())
    # Checkpoint round-trip preserves deduplication; unchanged payloads do not flood.
    engine.option_sets = checkpoint.decode(checkpoint.encode(engine.option_sets))
    w.t += config.OPTIMIZE_EVERY_S
    assert not [data for name, data in engine.step([tr], w, .1) if name == "options_ready"]
